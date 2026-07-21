"""Deterministic, target-safe control generation for CVPR studies.

The deterministic engines in this module are the required execution path.  The
optional diffusion path is deliberately lazy and offline-only: absence of a
local snapshot is an explicit capability result, never a call to a disabled
stub or an implicit download.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image, ImageFilter


ENGINE_VERSION = "certvic.cvpr.generation.v1"
DETERMINISTIC_ENGINES = (
    "structured_texture_patch",
    "neutral_color_patch",
    "distant_region_blur",
)


class GenerationError(ValueError):
    """A generation input or output violated the frozen contract."""


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _atomic_image(path: Path, image: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix or ".png"
    handle, temporary = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=suffix, dir=path.parent)
    os.close(handle)
    try:
        image.save(temporary)
        with Path(temporary).open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _bbox(value: Any, width: int, height: int) -> tuple[int, int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise GenerationError("target_bbox must be [x0, y0, x1, y1]")
    x0, y0, x1, y1 = (int(round(float(part))) for part in value)
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise GenerationError("target_bbox is outside the image")
    return x0, y0, x1, y1


def _target_mask(task: dict[str, Any], size: tuple[int, int]) -> np.ndarray:
    width, height = size
    mask_path = (
        task.get("protected_scene_mask_path")
        if task.get("queried_category_absent") is True
        else task.get("target_mask_path")
    )
    if mask_path:
        path = Path(str(mask_path))
        if not path.is_file():
            raise GenerationError(f"missing target mask: {path}")
        try:
            with Image.open(path) as image:
                if image.size != size:
                    raise GenerationError("target mask dimensions do not match source")
                mask = np.asarray(image.convert("L")) > 0
        except GenerationError:
            raise
        except Exception as exc:
            raise GenerationError(f"invalid target mask: {path}") from exc
        if not mask.any():
            raise GenerationError("target mask is empty")
        return mask
    x0, y0, x1, y1 = _bbox(task.get("target_bbox"), width, height)
    mask = np.zeros((height, width), dtype=bool)
    mask[y0:y1, x0:x1] = True
    return mask


def _expanded(mask: np.ndarray, distance: int) -> np.ndarray:
    if distance <= 0:
        return mask.copy()
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return mask.copy()
    result = np.zeros_like(mask)
    height, width = mask.shape
    for y, x in zip(ys.tolist(), xs.tolist(), strict=True):
        result[max(0, y - distance):min(height, y + distance + 1),
               max(0, x - distance):min(width, x + distance + 1)] = True
    return result


def plan_placement(
    task: dict[str, Any],
    image_size: tuple[int, int],
    *,
    seed: int,
    area_fraction: float = 0.01,
    minimum_distance_px: int = 75,
) -> tuple[int, int, int, int]:
    """Choose a deterministic valid rectangle outside the protected target region."""
    width, height = image_size
    if not 0 < area_fraction < 1:
        raise GenerationError("area_fraction must be between zero and one")
    side = max(2, int(round(math.sqrt(width * height * area_fraction))))
    patch_width = min(side, width)
    patch_height = min(side, height)
    protected = _expanded(_target_mask(task, image_size), minimum_distance_px)
    frozen_background = task.get("background_edit_region")
    if task.get("queried_category_absent") is True and frozen_background is not None:
        x0, y0, x1, y1 = _bbox(frozen_background, width, height)
        if protected[y0:y1, x0:x1].any():
            raise GenerationError("frozen negative-item background region touches protected scene")
        return x0, y0, x1, y1
    candidates: list[tuple[int, int, int, int]] = []
    step = max(1, min(patch_width, patch_height) // 4)
    for y in range(0, height - patch_height + 1, step):
        for x in range(0, width - patch_width + 1, step):
            rectangle = (x, y, x + patch_width, y + patch_height)
            if not protected[y:y + patch_height, x:x + patch_width].any():
                candidates.append(rectangle)
    if not candidates:
        raise GenerationError("no target-safe placement satisfies the frozen geometry")
    candidates.sort()
    return candidates[random.Random(f"{seed}:{task.get('edit_id', task.get('item_id'))}").randrange(
        len(candidates)
    )]


def _phash_bits(image: Image.Image, size: int = 8) -> str:
    gray = np.asarray(image.convert("L").resize((size, size), Image.Resampling.LANCZOS), dtype=float)
    return "".join("1" if value >= float(np.mean(gray)) else "0" for value in gray.flat)


def _dhash_bits(image: Image.Image, size: int = 8) -> str:
    gray = np.asarray(
        image.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS), dtype=int
    )
    return "".join("1" if value else "0" for value in (gray[:, 1:] > gray[:, :-1]).flat)


def _edge_energy(array: np.ndarray) -> float:
    gray = array.astype(float).mean(axis=2)
    dx = np.abs(np.diff(gray, axis=1)).mean() if gray.shape[1] > 1 else 0.0
    dy = np.abs(np.diff(gray, axis=0)).mean() if gray.shape[0] > 1 else 0.0
    return float((dx + dy) / (2 * 255.0))


def image_metrics(source: Image.Image, output: Image.Image, target_mask: np.ndarray) -> dict[str, Any]:
    if source.size != output.size or source.mode != output.mode:
        raise GenerationError("output dimensions or mode differ from source")
    before = np.asarray(source.convert("RGB"), dtype=np.int16)
    after = np.asarray(output.convert("RGB"), dtype=np.int16)
    absolute = np.abs(after - before)
    changed = np.any(absolute > 0, axis=2)
    difference_area = float(changed.mean())
    mad = float(absolute.mean() / 255.0)
    mse = float(np.mean((after.astype(float) - before.astype(float)) ** 2))
    similarity = 1.0 / (1.0 + mse / (255.0**2))
    target_overlap = int(np.logical_and(changed, target_mask).sum())
    changed_pixels = int(changed.sum())
    local_contrast = float(abs(after.std() - before.std()) / 255.0)
    edge_change = abs(_edge_energy(after) - _edge_energy(before))
    return {
        "pixel_difference_area_fraction": difference_area,
        "mean_absolute_difference": mad,
        "similarity_equivalent": similarity,
        "local_contrast_change": local_contrast,
        "edge_energy_change": edge_change,
        "target_overlap_pixels": target_overlap,
        "changed_pixels": changed_pixels,
        "phash": _phash_bits(output),
        "dhash": _dhash_bits(output),
    }


def _apply_engine(
    image: Image.Image,
    rectangle: tuple[int, int, int, int],
    engine: str,
    *,
    seed: int,
) -> Image.Image:
    if engine not in DETERMINISTIC_ENGINES:
        raise GenerationError(f"unsupported deterministic engine: {engine}")
    result = image.copy()
    x0, y0, x1, y1 = rectangle
    crop = image.crop(rectangle).convert("RGB")
    array = np.asarray(crop, dtype=np.uint8).copy()
    rng = np.random.default_rng(seed)
    if engine == "structured_texture_patch":
        base = np.asarray(image.convert("RGB"), dtype=float).mean(axis=(0, 1))
        delta = rng.integers(18, 38)
        yy, xx = np.indices(array.shape[:2])
        sign = np.where(((xx // 3) + (yy // 3)) % 2 == 0, 1, -1)[..., None]
        array = np.clip(base + sign * delta, 0, 255).astype(np.uint8)
    elif engine == "neutral_color_patch":
        mean = np.asarray(image.convert("RGB"), dtype=float).mean(axis=(0, 1))
        offset = rng.integers(-12, 13, size=3)
        array[:] = np.clip(mean + offset, 0, 255).astype(np.uint8)
    else:
        blurred = crop.filter(ImageFilter.GaussianBlur(radius=max(1.0, min(x1 - x0, y1 - y0) / 12)))
        array = np.asarray(blurred, dtype=np.uint8).copy()
        if np.array_equal(array, np.asarray(crop)):
            array[0, 0] = 255 - array[0, 0]
    result.paste(Image.fromarray(array, mode="RGB").convert(image.mode), rectangle)
    return result


@dataclass(frozen=True)
class GenerationSettings:
    engine: str
    seed: int
    area_fraction: float = 0.01
    minimum_distance_px: int = 75
    minimum_changed_fraction: float = 0.0025
    maximum_changed_fraction: float = 0.02


def generate_one(task: dict[str, Any], output_path: str | Path, settings: GenerationSettings) -> dict[str, Any]:
    source_value = task.get("source_image_path", task.get("image_path"))
    if not source_value:
        raise GenerationError("task is missing source_image_path")
    source_path = Path(str(source_value))
    if not source_path.is_file():
        raise GenerationError(f"missing source image: {source_path}")
    try:
        with Image.open(source_path) as opened:
            opened.load()
            source = opened.copy()
    except Exception as exc:
        raise GenerationError(f"corrupt source image: {source_path}") from exc
    if source.mode not in {"RGB", "RGBA", "L"}:
        raise GenerationError(f"unsupported source mode: {source.mode}")
    target = _target_mask(task, source.size)
    rectangle = plan_placement(
        task,
        source.size,
        seed=settings.seed,
        area_fraction=settings.area_fraction,
        minimum_distance_px=settings.minimum_distance_px,
    )
    identity = str(task.get("edit_id", task.get("item_id", "")))
    derived_seed = int(hashlib.sha256(f"{settings.seed}:{identity}".encode()).hexdigest()[:16], 16)
    generated = _apply_engine(source, rectangle, settings.engine, seed=derived_seed)
    metrics = image_metrics(source, generated, target)
    errors: list[str] = []
    if metrics["changed_pixels"] == 0:
        errors.append("source_and_output_identical")
    if metrics["target_overlap_pixels"]:
        errors.append("target_overlap")
    fraction = float(metrics["pixel_difference_area_fraction"])
    if not settings.minimum_changed_fraction <= fraction <= settings.maximum_changed_fraction:
        errors.append("perturbation_area_outside_contract")
    if errors:
        raise GenerationError("; ".join(errors))
    output = Path(output_path)
    if output.exists():
        with Image.open(output) as current:
            current.load()
            if np.array_equal(np.asarray(current), np.asarray(generated)):
                status = "EXISTING_VALID_OUTPUT"
            else:
                raise GenerationError(f"conflicting existing output: {output}")
    else:
        _atomic_image(output, generated)
        status = "GENERATED"
    return {
        "schema": "certvic.cvpr.generated_control.v1",
        "status": status,
        "edit_id": identity,
        "item_id": str(task.get("item_id", identity)),
        "engine": settings.engine,
        "engine_version": ENGINE_VERSION,
        "seed": settings.seed,
        "derived_seed": derived_seed,
        "placement_xyxy": list(rectangle),
        "parameters": {
            "area_fraction": settings.area_fraction,
            "minimum_distance_px": settings.minimum_distance_px,
        },
        "source_image_path": str(source_path),
        "output_image_path": str(output),
        "source_sha256": sha256_file(source_path),
        "output_sha256": sha256_file(output),
        "metrics": metrics,
        "paper_evidence": False,
    }


def inpainting_capability(model_path: str | Path | None) -> dict[str, Any]:
    if not model_path:
        return {"available": False, "blocker": "LOCAL_INPAINTING_SNAPSHOT_NOT_SUPPLIED"}
    path = Path(model_path)
    if not path.is_dir():
        return {"available": False, "blocker": "LOCAL_INPAINTING_SNAPSHOT_NOT_FOUND"}
    try:
        import diffusers  # noqa: F401
    except ImportError:
        return {"available": False, "blocker": "DIFFUSERS_DEPENDENCY_NOT_INSTALLED"}
    return {"available": True, "model_path": str(path), "offline_only": True}


def generate_inpaint_one(
    task: dict[str, Any],
    output_path: str | Path,
    settings: GenerationSettings,
    *,
    model_path: str | Path,
    snapshot_manifest: str | Path,
    snapshot_manifest_sha256: str,
    prompt: str = "subtle neutral background texture",
) -> dict[str, Any]:
    """Run a local-only diffusion inpaint branch when its snapshot is explicitly supplied."""
    capability = inpainting_capability(model_path)
    if not capability["available"]:
        raise GenerationError(str(capability["blocker"]))
    manifest_path = Path(snapshot_manifest)
    if not manifest_path.is_file() or sha256_file(manifest_path) != snapshot_manifest_sha256:
        raise GenerationError("inpainting snapshot manifest is missing or hash-mismatched")
    snapshot = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = snapshot.get("files")
    if not isinstance(files, dict) or not files:
        raise GenerationError("inpainting snapshot manifest has no file inventory")
    root = Path(model_path)
    observed_files = {
        path.relative_to(root).as_posix() for path in root.rglob("*")
        if path.is_file() and path.resolve() != manifest_path.resolve()
    }
    if observed_files != set(files):
        raise GenerationError("inpainting snapshot file inventory is not exact")
    for relative, record in files.items():
        path = root / relative
        expected = record.get("sha256") if isinstance(record, dict) else record
        if not path.is_file() or sha256_file(path) != expected:
            raise GenerationError(f"inpainting snapshot verification failed: {relative}")
    source_value = task.get("source_image_path", task.get("image_path"))
    source_path = Path(str(source_value or ""))
    if not source_path.is_file():
        raise GenerationError(f"missing source image: {source_path}")
    with Image.open(source_path) as opened:
        opened.load()
        source = opened.convert("RGB")
    target = _target_mask(task, source.size)
    rectangle = plan_placement(
        task,
        source.size,
        seed=settings.seed,
        area_fraction=settings.area_fraction,
        minimum_distance_px=settings.minimum_distance_px,
    )
    mask = Image.new("L", source.size, 0)
    mask_array = np.asarray(mask).copy()
    x0, y0, x1, y1 = rectangle
    mask_array[y0:y1, x0:x1] = 255
    mask = Image.fromarray(mask_array, mode="L")
    try:
        import torch
        from diffusers import AutoPipelineForInpainting
    except ImportError as exc:
        raise GenerationError("DIFFUSERS_DEPENDENCY_NOT_INSTALLED") from exc
    if not torch.cuda.is_available():
        raise GenerationError("CUDA_REQUIRED_FOR_OPTIONAL_INPAINTING")
    derived_seed = int(hashlib.sha256(
        f"{settings.seed}:{task.get('edit_id', task.get('item_id'))}:inpaint".encode()
    ).hexdigest()[:16], 16)
    pipeline = AutoPipelineForInpainting.from_pretrained(
        str(root), local_files_only=True, torch_dtype=torch.float16,
    ).to("cuda:0")
    try:
        with torch.inference_mode():
            generated = pipeline(
                prompt=prompt,
                image=source,
                mask_image=mask,
                generator=torch.Generator(device="cuda:0").manual_seed(derived_seed),
                num_inference_steps=int(task.get("inpaint_steps", 20)),
                guidance_scale=float(task.get("inpaint_guidance_scale", 5.0)),
            ).images[0].convert("RGB")
    except Exception as exc:
        if "out of memory" in str(exc).lower():
            torch.cuda.empty_cache()
            raise GenerationError("OPTIONAL_INPAINTING_OOM_RETRY_WITH_SINGLE_ITEM") from exc
        raise
    finally:
        del pipeline
        torch.cuda.empty_cache()
    metrics = image_metrics(source, generated, target)
    if metrics["target_overlap_pixels"]:
        raise GenerationError("optional inpainting changed target pixels")
    fraction = float(metrics["pixel_difference_area_fraction"])
    if not settings.minimum_changed_fraction <= fraction <= settings.maximum_changed_fraction:
        raise GenerationError("optional inpainting perturbation area outside contract")
    output = Path(output_path)
    if output.exists():
        with Image.open(output) as current:
            current.load()
            if not np.array_equal(np.asarray(current.convert("RGB")), np.asarray(generated)):
                raise GenerationError(f"conflicting existing output: {output}")
        status = "EXISTING_VALID_OUTPUT"
    else:
        _atomic_image(output, generated)
        status = "GENERATED"
    return {
        "schema": "certvic.cvpr.generated_control.v1",
        "status": status,
        "edit_id": str(task.get("edit_id", task.get("item_id"))),
        "engine": "offline_diffusers_inpainting",
        "engine_version": ENGINE_VERSION,
        "seed": settings.seed,
        "derived_seed": derived_seed,
        "placement_xyxy": list(rectangle),
        "source_sha256": sha256_file(source_path),
        "output_sha256": sha256_file(output),
        "snapshot_manifest_sha256": snapshot_manifest_sha256,
        "offline_only": True,
        "metrics": metrics,
        "paper_evidence": False,
    }


def run_generation(
    tasks: Iterable[dict[str, Any]],
    out_dir: str | Path,
    settings: GenerationSettings,
    *,
    max_items: int | None,
    allow_full_run: bool,
    dry_run: bool,
) -> dict[str, Any]:
    rows = list(tasks)
    if max_items is not None and max_items < 1:
        raise GenerationError("max_items must be positive")
    if not dry_run and max_items is None and not allow_full_run:
        raise GenerationError("choose --max-items for a bounded run or --allow-full-run explicitly")
    selected = rows if max_items is None else rows[:max_items]
    mode = "DRY_RUN" if dry_run else ("BOUNDED_SMOKE" if max_items is not None else "EXPLICIT_FULL_RUN")
    out = Path(out_dir)
    if dry_run:
        return {"status": "DRY_RUN", "mode": mode, "planned": len(selected), "paper_evidence": False}
    generated: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for task in selected:
        identity = str(task.get("edit_id", task.get("item_id", "missing-id")))
        try:
            generated.append(generate_one(task, out / "images" / f"{identity}.png", settings))
        except GenerationError as exc:
            failures.append({"edit_id": identity, "error": str(exc)})
    manifest = {
        "schema": "certvic.cvpr.generation_run.v1",
        "status": "COMPLETE" if not failures else "COMPLETE_WITH_REJECTIONS",
        "mode": mode,
        "planned": len(selected),
        "generated": len(generated),
        "rejected": len(failures),
        "settings": settings.__dict__,
        "rows": generated,
        "failures": failures,
        "paper_evidence": False,
    }
    _atomic_json(out / "generation_manifest.json", manifest)
    return manifest


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic CertVIC control images")
    parser.add_argument("--task-manifest", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--engine", choices=(*DETERMINISTIC_ENGINES, "offline_diffusers_inpainting"), required=True
    )
    parser.add_argument("--inpaint-model-path")
    parser.add_argument("--inpaint-snapshot-manifest")
    parser.add_argument("--inpaint-snapshot-manifest-sha256")
    parser.add_argument("--seed", type=int, default=12013)
    parser.add_argument("--area-fraction", type=float, default=0.01)
    parser.add_argument("--minimum-distance-px", type=int, default=75)
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--allow-full-run", action="store_true")
    parser.add_argument("--resume", action="store_true",
                        help="revalidate and reuse byte-identical existing outputs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    tasks = _read_jsonl(Path(args.task_manifest))
    settings = GenerationSettings(
        engine=args.engine,
        seed=args.seed,
        area_fraction=args.area_fraction,
        minimum_distance_px=args.minimum_distance_px,
    )
    if args.engine == "offline_diffusers_inpainting":
        if not args.dry_run and args.max_items is None and not args.allow_full_run:
            raise GenerationError(
                "choose --max-items for a bounded run or --allow-full-run explicitly"
            )
        if not all((args.inpaint_model_path, args.inpaint_snapshot_manifest,
                    args.inpaint_snapshot_manifest_sha256)):
            raise GenerationError("optional inpainting requires its local path and manifest contract")
        selected = tasks if args.max_items is None else tasks[:args.max_items]
        if args.dry_run:
            result = {"status": "DRY_RUN", "planned": len(selected), "paper_evidence": False}
        else:
            out = Path(args.out_dir)
            rows = [generate_inpaint_one(
                task,
                out / "images" / f"{task.get('edit_id', task.get('item_id'))}.png",
                settings,
                model_path=args.inpaint_model_path,
                snapshot_manifest=args.inpaint_snapshot_manifest,
                snapshot_manifest_sha256=args.inpaint_snapshot_manifest_sha256,
            ) for task in selected]
            result = {"status": "COMPLETE", "mode": "BOUNDED_SMOKE" if args.max_items else
                      "EXPLICIT_FULL_RUN", "planned": len(selected), "generated": len(rows),
                      "rows": rows, "paper_evidence": False}
            _atomic_json(out / "generation_manifest.json", result)
    else:
        result = run_generation(
            tasks,
            args.out_dir,
            settings,
            max_items=args.max_items,
            allow_full_run=args.allow_full_run,
            dry_run=args.dry_run,
        )
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, sort_keys=True))
    return 0 if not result.get("failures") else 2


if __name__ == "__main__":
    raise SystemExit(main())
