"""Offline, manifest-verified inpainting lifecycle with bounded OOM recovery."""

from __future__ import annotations

import gc
import sys
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from certvic.cvpr.model_snapshot_manifest import verify_manifest


class InpaintingError(RuntimeError):
    pass


def validate_mask_contract(image: Image.Image, mask: Image.Image) -> dict[str, Any]:
    mask_l = mask.convert("L")
    if mask_l.size != image.size:
        raise InpaintingError("mask dimensions must exactly match source image")
    extrema = mask_l.getextrema()
    if extrema == (0, 0):
        raise InpaintingError("inpainting mask is empty")
    histogram = mask_l.histogram()
    values = {index for index, count in enumerate(histogram) if count}
    if not values.issubset({0, 255}):
        raise InpaintingError("mask must be binary with 0/255 semantics")
    return {
        "schema": "certvic.cvpr.inpainting_mask.v1",
        "semantics": "255=regenerate_target_region;0=preserve_source_pixel",
        "size": list(mask_l.size),
        "masked_pixels": histogram[255],
    }


def _oom(exc: BaseException) -> bool:
    return "out of memory" in str(exc).lower() or exc.__class__.__name__ == "OutOfMemoryError"


class OfflineInpaintingAdapter:
    """Load once, generate many, release once.

    ``pipeline_factory`` is injectable so lifecycle and OOM behavior can be tested
    without importing diffusers or downloading model bytes.
    """

    def __init__(
        self,
        *,
        snapshot_dir: str | Path,
        snapshot_manifest: str | Path,
        expected_model_id: str,
        expected_model_commit: str,
        expected_architecture: str,
        pipeline_factory: Callable[..., Any] | None = None,
        device: str = "cuda",
    ) -> None:
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_manifest = Path(snapshot_manifest)
        self.expected_model_id = expected_model_id
        self.expected_model_commit = expected_model_commit
        self.expected_architecture = expected_architecture
        self.pipeline_factory = pipeline_factory
        self.device = device
        self.pipeline: Any | None = None
        self.prepare_calls = 0

    def prepare(self) -> dict[str, Any]:
        if self.pipeline is not None:
            return {"status": "ALREADY_PREPARED", "prepare_calls": self.prepare_calls}
        verification = verify_manifest(
            self.snapshot_dir,
            self.snapshot_manifest,
            expected_model_id=self.expected_model_id,
            expected_model_commit=self.expected_model_commit,
            expected_architecture=self.expected_architecture,
        )
        if not verification["passed"]:
            raise InpaintingError("snapshot verification failed: " + "; ".join(verification["errors"]))
        factory = self.pipeline_factory
        if factory is None:
            try:
                import torch
                from diffusers import AutoPipelineForInpainting
            except ImportError as exc:  # pragma: no cover - depends on optional Kaggle image
                raise InpaintingError("diffusers/torch unavailable in the locked offline environment") from exc
            def factory(path: str) -> Any:
                return AutoPipelineForInpainting.from_pretrained(
                    path, local_files_only=True, torch_dtype=torch.float16,
                )
        self.pipeline = factory(str(self.snapshot_dir))
        if hasattr(self.pipeline, "enable_attention_slicing"):
            self.pipeline.enable_attention_slicing()
        if hasattr(self.pipeline, "enable_vae_slicing"):
            self.pipeline.enable_vae_slicing()
        if hasattr(self.pipeline, "to"):
            self.pipeline.to(self.device)
        self.prepare_calls += 1
        return {
            "status": "OFFLINE_INPAINTING_READY",
            "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
            "files_verified": verification.get("files_verified"),
            "prepare_calls": self.prepare_calls,
        }

    def generate_batch(
        self,
        requests: list[dict[str, Any]],
        *,
        batch_size: int,
        seed: int,
    ) -> tuple[list[Image.Image], list[dict[str, Any]]]:
        if self.pipeline is None:
            raise InpaintingError("prepare() must be called before generate_batch()")
        if batch_size < 1:
            raise InpaintingError("batch_size must be positive")
        outputs: list[Image.Image] = []
        events: list[dict[str, Any]] = []
        index = 0
        effective = min(batch_size, max(1, len(requests)))
        while index < len(requests):
            chunk = requests[index:index + effective]
            images: list[Image.Image] = []
            masks: list[Image.Image] = []
            prompts: list[str] = []
            for request in chunk:
                image = request["image"].convert("RGB")
                mask = request["mask"].convert("L")
                validate_mask_contract(image, mask)
                images.append(image)
                masks.append(mask)
                prompts.append(str(request["prompt"]))
            try:
                generators: Any = None
                try:
                    if self.device.startswith("cuda"):
                        import torch
                        generators = [
                            torch.Generator(device=self.device).manual_seed(seed + index + offset)
                            for offset in range(len(chunk))
                        ]
                except (ImportError, RuntimeError):  # pragma: no cover - optional GPU runtime
                    generators = None
                result = self.pipeline(
                    prompt=prompts,
                    image=images,
                    mask_image=masks,
                    num_inference_steps=int(chunk[0].get("num_inference_steps", 30)),
                    guidance_scale=float(chunk[0].get("guidance_scale", 7.5)),
                    generator=generators,
                )
                generated = list(result.images)
                if len(generated) != len(chunk):
                    raise InpaintingError("inpainting pipeline returned the wrong batch length")
            except Exception as exc:
                if _oom(exc) and effective > 1:
                    events.append({"event": "CUDA_OOM_BATCH_REDUCTION", "from": effective,
                                   "to": max(1, effective // 2), "seed": seed})
                    effective = max(1, effective // 2)
                    try:
                        torch = sys.modules.get("torch")
                        if torch is None:
                            raise AttributeError
                        torch.cuda.empty_cache()
                    except AttributeError:
                        pass
                    continue
                raise
            outputs.extend(image.convert("RGB") for image in generated)
            events.append({"event": "INPAINT_BATCH_COMPLETE", "count": len(chunk),
                           "effective_batch_size": effective, "seed": seed + index})
            index += len(chunk)
        return outputs, events

    def release(self) -> None:
        if self.pipeline is not None and hasattr(self.pipeline, "to"):
            try:
                self.pipeline.to("cpu")
            except Exception:
                pass
        self.pipeline = None
        gc.collect()
        try:
            torch = sys.modules.get("torch")
            if torch is None:
                raise AttributeError
            torch.cuda.empty_cache()
        except AttributeError:
            pass

    def __enter__(self) -> "OfflineInpaintingAdapter":
        self.prepare()
        return self

    def __exit__(self, *_args: Any) -> None:
        self.release()
