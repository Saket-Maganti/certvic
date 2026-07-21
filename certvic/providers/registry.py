"""Provider registry."""

from __future__ import annotations

from certvic.providers.caption_only import CaptionOnlyBaselineProvider
from certvic.providers.free_tier_reference import FreeTierReferenceStub
from certvic.providers.internvl import InternVLProvider
from certvic.providers.llava_onevision import LlavaOneVisionProvider
from certvic.providers.mock import MockProvider
from certvic.providers.qwen_vl import QwenVLProvider
from certvic.providers.random_baseline import MajorityBaselineProvider, RandomBaselineProvider
from certvic.providers.text_only import TextOnlyBaselineProvider

PAID_PROVIDER_NAMES: set[str] = set()

# Static metadata for zero-cost provider planning. tested_status is conservative:
# adapters remain scaffolds until a real run is recorded.
PROVIDER_METADATA: dict[str, dict] = {
    "qwen2_5_vl_7b": {
        "model_family": "qwen2_5_vl",
        "expected_gpu_memory_gb": 16,
        "supports_4bit": True,
        "supports_batching": True,
        "tested_status": "adapter_scaffold",
        "cost_status": "zero_cost_open_local",
        "provider_type": "open_local",
    },
    "internvl_8b": {
        "model_family": "internvl",
        "expected_gpu_memory_gb": 18,
        "supports_4bit": True,
        "supports_batching": True,
        "tested_status": "adapter_scaffold",
        "cost_status": "zero_cost_open_local",
        "provider_type": "open_local",
    },
    "llava_onevision_7b": {
        "model_family": "llava_onevision",
        "expected_gpu_memory_gb": 16,
        "supports_4bit": True,
        "supports_batching": False,
        "tested_status": "adapter_scaffold",
        "cost_status": "zero_cost_open_local",
        "provider_type": "open_local",
    },
    "free_tier_reference_stub": {
        "model_family": "free_tier_reference",
        "expected_gpu_memory_gb": 0,
        "supports_4bit": False,
        "supports_batching": False,
        "tested_status": "disabled_non_core",
        "cost_status": "free_tier_reference_only",
        "provider_type": "free_tier_reference",
    },
}

OPEN_LOCAL_PROVIDERS = {"qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"}
MOCK_PROVIDER_PREFIX = "mock"


def provider_metadata(name: str) -> dict:
    if name in PROVIDER_METADATA:
        return {"provider_name": name, **PROVIDER_METADATA[name]}
    if name.startswith(MOCK_PROVIDER_PREFIX):
        return {"provider_name": name, "model_family": "mock", "provider_type": "mock", "cost_status": "zero_cost_mock", "tested_status": "deterministic_mock", "expected_gpu_memory_gb": 0, "supports_4bit": False, "supports_batching": False}
    return {"provider_name": name, "model_family": "baseline", "provider_type": "baseline", "cost_status": "zero_cost_baseline", "tested_status": "baseline", "expected_gpu_memory_gb": 0, "supports_4bit": False, "supports_batching": False}


def is_evidence_eligible_provider(name: str) -> bool:
    """Only non-mock, non-paid, open-local providers can produce evidence."""
    return name in OPEN_LOCAL_PROVIDERS and name not in PAID_PROVIDER_NAMES


def get_provider(name: str, config: dict | None = None):
    config = config or {}
    if name == "mock_perfect":
        return MockProvider("perfect", seed=int(config.get("seed", 0)))
    if name == "mock_inconsistent":
        return MockProvider("inconsistent", seed=int(config.get("seed", 0)))
    if name == "mock_spurious_flip":
        return MockProvider("spurious_flip", seed=int(config.get("seed", 0)))
    if name == "mock_parser_fail":
        return MockProvider("parser_fail", seed=int(config.get("seed", 0)))
    if name == "mock_always_yes":
        return MockProvider("always_yes", seed=int(config.get("seed", 0)))
    if name == "mock_always_no":
        return MockProvider("always_no", seed=int(config.get("seed", 0)))
    if name == "mock_random_seeded":
        return MockProvider("random_seeded", seed=int(config.get("seed", 0)))
    if name == "mock_random":
        return MockProvider("random", seed=int(config.get("seed", 0)))
    if name == "random_baseline":
        return RandomBaselineProvider(seed=int(config.get("seed", 0)))
    if name == "majority_baseline":
        return MajorityBaselineProvider(majority_answer=config.get("majority_answer", "yes"))
    if name == "text_only_baseline":
        return TextOnlyBaselineProvider(seed=int(config.get("seed", 0)))
    if name == "caption_only_baseline":
        return CaptionOnlyBaselineProvider(caption_file=config.get("caption_file"))
    if name == "qwen2_5_vl_7b":
        return QwenVLProvider(config)
    if name == "internvl_8b":
        return InternVLProvider(config)
    if name == "llava_onevision_7b":
        return LlavaOneVisionProvider(config)
    if name == "free_tier_reference_stub":
        return FreeTierReferenceStub(config)
    raise ValueError(f"Unknown provider: {name}")


def available_provider_names() -> list[str]:
    return [
        "mock_perfect",
        "mock_inconsistent",
        "mock_spurious_flip",
        "mock_parser_fail",
        "mock_always_yes",
        "mock_always_no",
        "mock_random_seeded",
        "mock_random",
        "random_baseline",
        "majority_baseline",
        "text_only_baseline",
        "caption_only_baseline",
        "qwen2_5_vl_7b",
        "internvl_8b",
        "llava_onevision_7b",
        "free_tier_reference_stub",
    ]
