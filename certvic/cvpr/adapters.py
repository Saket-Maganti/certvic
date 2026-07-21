"""Lazy, offline VLM adapters with a shared lifecycle and provenance contract."""

from __future__ import annotations

import gc
import hashlib
import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from PIL import Image


class AdapterError(RuntimeError):
    pass


def deterministic_config_hash(config: dict[str, Any]) -> str:
    safe = {key: value for key, value in config.items() if key not in {"output_dir"}}
    payload = (json.dumps(safe, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


class BaseAdapter(ABC):
    provider: str

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.model: Any = None
        self.processor: Any = None
        self._prepared = False

    @abstractmethod
    def prepare(self) -> dict[str, Any]:
        """Load a verified local snapshot without network access."""

    @abstractmethod
    def generate_one(self, image_path: str, prompt: str) -> str:
        """Generate one deterministic response."""

    def generate_batch(self, requests: list[tuple[str, str]]) -> list[str]:
        """Provider-safe fallback; concrete adapters override with real tensor batching."""
        return [self.generate_one(image, prompt) for image, prompt in requests]

    def release(self) -> None:
        self.model = None
        self.processor = None
        self._prepared = False
        gc.collect()
        torch = sys.modules.get("torch")
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()

    def capability_report(self) -> dict[str, Any]:
        report: dict[str, Any] = {
            "provider": self.provider,
            "prepared": self._prepared,
            "supports_batch": True,
            "offline_only": True,
            "config_sha256": deterministic_config_hash(self.config),
        }
        torch = sys.modules.get("torch")
        if torch is not None:
            report.update({
                "cuda_available": bool(torch.cuda.is_available()),
                "gpu_count": int(torch.cuda.device_count()),
                "bfloat16_supported": bool(
                    torch.cuda.is_available() and torch.cuda.is_bf16_supported()
                ),
                "float16_policy": "REQUIRED_ON_T4",
            })
        else:
            report["torch_status"] = "NOT_LOADED"
        return report

    def provenance_manifest(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model_id": self.config["model_id"],
            "model_commit": self.config["model_commit"],
            "processor_commit": self.config["processor_commit"],
            "model_snapshot_manifest_hash": self.config.get("model_snapshot_manifest_hash"),
            "generation_parameters": self.config["generation_parameters"],
            "config_sha256": deterministic_config_hash(self.config),
            "offline_only": True,
        }

    def answer(self, image_path: str, prompt: str) -> str:
        """Compatibility alias for older callers."""
        return self.generate_one(image_path, prompt)


class QwenAdapter(BaseAdapter):
    provider = "qwen2_5_vl_7b"

    def prepare(self) -> dict[str, Any]:
        import torch
        from transformers import AutoProcessor, BitsAndBytesConfig

        try:
            from transformers import Qwen2_5_VLForConditionalGeneration as Model
        except ImportError:
            from transformers import AutoModelForImageTextToText as Model
        quantization = None
        if str(self.config.get("quantization", "nf4_4bit")).startswith("nf4"):
            quantization = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        self.model = Model.from_pretrained(
            self.config["model_path"],
            device_map={"": 0},
            quantization_config=quantization,
            torch_dtype=torch.float16 if quantization is None else None,
            low_cpu_mem_usage=True,
            local_files_only=True,
        ).eval()
        self.processor = AutoProcessor.from_pretrained(
            self.config.get("processor_path", self.config["model_path"]),
            max_pixels=int(self.config.get("max_pixels", 768 * 768)),
            local_files_only=True,
        )
        self._prepared = True
        return self.capability_report()

    def _inputs(self, requests: list[tuple[str, str]]) -> Any:
        images = [Image.open(path).convert("RGB") for path, _ in requests]
        texts = []
        for image, (_, prompt) in zip(images, requests, strict=True):
            messages = [{"role": "user", "content": [
                {"type": "image", "image": image}, {"type": "text", "text": prompt}
            ]}]
            texts.append(self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            ))
        return images, self.processor(
            text=texts, images=images, padding=True, return_tensors="pt"
        ).to(self.model.device)

    def generate_batch(self, requests: list[tuple[str, str]]) -> list[str]:
        import torch

        if not self._prepared:
            raise AdapterError("adapter is not prepared")
        images, inputs = self._inputs(requests)
        try:
            with torch.inference_mode():
                output = self.model.generate(**inputs, **self.config["generation_parameters"])
            offsets = inputs.input_ids.shape[1]
            return [self.processor.decode(row[offsets:], skip_special_tokens=True).strip()
                    for row in output]
        finally:
            for image in images:
                image.close()

    def generate_one(self, image_path: str, prompt: str) -> str:
        return self.generate_batch([(image_path, prompt)])[0]


def dynamic_preprocess(
    image: Image.Image,
    *,
    image_size: int = 448,
    min_num: int = 1,
    max_num: int = 12,
    use_thumbnail: bool = True,
) -> list[Image.Image]:
    """InternVL dynamic tiling contract used by supported remote-code revisions."""
    width, height = image.size
    aspect = width / height
    ratios = sorted({(i, j) for n in range(min_num, max_num + 1)
                     for i in range(1, n + 1) for j in range(1, n + 1)
                     if min_num <= i * j <= max_num}, key=lambda value: value[0] * value[1])

    def score(ratio: tuple[int, int]) -> tuple[float, int]:
        return abs(aspect - ratio[0] / ratio[1]), ratio[0] * ratio[1]

    columns, rows = min(ratios, key=score)
    resized = image.resize((image_size * columns, image_size * rows), Image.Resampling.BICUBIC)
    blocks = [resized.crop((
        (index % columns) * image_size,
        (index // columns) * image_size,
        (index % columns + 1) * image_size,
        (index // columns + 1) * image_size,
    )) for index in range(columns * rows)]
    if use_thumbnail and len(blocks) > 1:
        blocks.append(image.resize((image_size, image_size), Image.Resampling.BICUBIC))
    return blocks


def internvl_t4_strategy(config: dict[str, Any]) -> dict[str, Any]:
    """Return the frozen single-worker T4 policy for InternVL2-8B."""
    quantization = str(config.get("quantization", "nf4_4bit"))
    max_patches = int(config.get("max_patches", 6))
    if quantization != "nf4_4bit":
        raise AdapterError("InternVL2-8B on one 16 GiB T4 requires the frozen NF4 policy")
    if not 1 <= max_patches <= 6:
        raise AdapterError("InternVL T4 max_patches must be within the frozen 1..6 bound")
    return {
        "device_map": {"": 0},
        "dtype": "float16",
        "quantization": "nf4_4bit",
        "max_patches": max_patches,
        "thumbnail": True,
        "worker_topology": "one_process_per_visible_t4",
        "real_model_proof_status": "REQUIRES_00C2_KAGGLE_SMOKE",
    }


class InternVLAdapter(BaseAdapter):
    provider = "internvl_8b"

    def prepare(self) -> dict[str, Any]:
        import torch
        from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig

        strategy = internvl_t4_strategy(self.config)
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        self.model = AutoModel.from_pretrained(
            self.config["model_path"],
            device_map=strategy["device_map"],
            quantization_config=quantization,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
            local_files_only=True,
        ).eval()
        self.processor = AutoTokenizer.from_pretrained(
            self.config.get("processor_path", self.config["model_path"]),
            trust_remote_code=True,
            use_fast=False,
            local_files_only=True,
        )
        self._prepared = True
        report = self.capability_report()
        report.update({"dynamic_tiling": True, "image_size": 448,
                       "maximum_patches": strategy["max_patches"] + 1,
                       "t4_strategy": strategy})
        return report

    def _pixels(self, image_path: str) -> Any:
        import torch
        import torchvision.transforms as transforms
        from torchvision.transforms.functional import InterpolationMode

        transform = transforms.Compose([
            transforms.Resize((448, 448), interpolation=InterpolationMode.BICUBIC),
            transforms.ToTensor(),
            transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
        ])
        with Image.open(image_path) as image:
            tiles = dynamic_preprocess(
                image.convert("RGB"), max_num=int(self.config.get("max_patches", 6))
            )
        return torch.stack([transform(tile) for tile in tiles]).to(
            device="cuda:0", dtype=torch.float16
        )

    def generate_one(self, image_path: str, prompt: str) -> str:
        import torch

        if not self._prepared:
            raise AdapterError("adapter is not prepared")
        pixels = self._pixels(image_path)
        try:
            with torch.inference_mode():
                result = self.model.chat(
                    self.processor,
                    pixels,
                    "<image>\n" + prompt,
                    self.config["generation_parameters"],
                )
            return str(result).strip()
        finally:
            del pixels

    def generate_batch(self, requests: list[tuple[str, str]]) -> list[str]:
        import torch

        if not self._prepared:
            raise AdapterError("adapter is not prepared")
        if not hasattr(self.model, "batch_chat") or len(requests) == 1:
            return [self.generate_one(image, prompt) for image, prompt in requests]
        tensors = [self._pixels(image) for image, _ in requests]
        counts = [tensor.shape[0] for tensor in tensors]
        pixels = torch.cat(tensors, dim=0)
        questions = ["<image>\n" + prompt for _, prompt in requests]
        try:
            with torch.inference_mode():
                outputs = self.model.batch_chat(
                    self.processor,
                    pixels,
                    num_patches_list=counts,
                    questions=questions,
                    generation_config=self.config["generation_parameters"],
                )
            return [str(value).strip() for value in outputs]
        finally:
            del pixels, tensors


class LlavaAdapter(BaseAdapter):
    provider = "llava_onevision_7b"

    def prepare(self) -> dict[str, Any]:
        import torch
        from transformers import AutoProcessor, BitsAndBytesConfig
        from transformers import LlavaOnevisionForConditionalGeneration

        quantization = None
        if str(self.config.get("quantization", "nf4_4bit")).startswith("nf4"):
            quantization = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        self.processor = AutoProcessor.from_pretrained(
            self.config.get("processor_path", self.config["model_path"]),
            local_files_only=True,
        )
        self.model = LlavaOnevisionForConditionalGeneration.from_pretrained(
            self.config["model_path"],
            device_map={"": 0},
            quantization_config=quantization,
            torch_dtype=torch.float16 if quantization is None else None,
            low_cpu_mem_usage=True,
            local_files_only=True,
        ).eval()
        self._prepared = True
        return self.capability_report()

    def generate_batch(self, requests: list[tuple[str, str]]) -> list[str]:
        import torch

        if not self._prepared:
            raise AdapterError("adapter is not prepared")
        images = [Image.open(path).convert("RGB") for path, _ in requests]
        texts = []
        for _, prompt in requests:
            conversation = [{"role": "user", "content": [
                {"type": "image"}, {"type": "text", "text": prompt}
            ]}]
            texts.append(self.processor.apply_chat_template(
                conversation, add_generation_prompt=True
            ))
        inputs = self.processor(images=images, text=texts, padding=True, return_tensors="pt").to(
            self.model.device
        )
        try:
            with torch.inference_mode():
                output = self.model.generate(
                    **inputs,
                    pad_token_id=self.processor.tokenizer.eos_token_id,
                    **self.config["generation_parameters"],
                )
            offset = inputs["input_ids"].shape[1]
            return [self.processor.decode(row[offset:], skip_special_tokens=True).strip()
                    for row in output]
        finally:
            for image in images:
                image.close()

    def generate_one(self, image_path: str, prompt: str) -> str:
        return self.generate_batch([(image_path, prompt)])[0]


def load_adapter(provider: str, config: dict[str, Any]) -> BaseAdapter:
    for key in (
        "model_path",
        "model_id",
        "model_commit",
        "processor_commit",
        "generation_parameters",
    ):
        if key not in config:
            raise ValueError(f"runtime config missing {key}")
    if not Path(config["model_path"]).exists():
        raise ValueError("mounted immutable model snapshot does not exist")
    adapters = {
        "qwen2_5_vl_7b": QwenAdapter,
        "internvl_8b": InternVLAdapter,
        "llava_onevision_7b": LlavaAdapter,
    }
    try:
        return adapters[provider](config)
    except KeyError as exc:
        raise ValueError(f"unsupported CVPR provider: {provider}") from exc
