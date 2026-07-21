"""Generate model cards for planned/open-local providers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.providers.registry import PAID_PROVIDER_NAMES, provider_metadata


def build_model_card(provider: str) -> dict:
    meta = provider_metadata(provider)
    unknown = provider not in {"qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"}
    paid = provider in PAID_PROVIDER_NAMES
    return {
        "provider": provider,
        "model_id": meta.get("model_family", provider),
        "license_status": "user_verified_required",
        "open_local_free_status": meta.get("cost_status"),
        "expected_memory_gb": meta.get("expected_gpu_memory_gb"),
        "quantization": "4-bit supported" if meta.get("supports_4bit") else "not declared",
        "prompt_settings": "CertVIC prompt suite, recorded per run",
        "limitations": ["adapter scaffold until real run", "no frontier or paid-provider claims"],
        "paid_provider_flagged": paid,
        "unknown_provider_flagged": unknown,
        "missing_license_flagged": True,
        "evidence_status": "MODEL_CARD_ONLY",
    }


def render_model_card(card: dict) -> str:
    lines = [
        f"# Model Card: {card['provider']}",
        "",
        f"- Model id/family: {card['model_id']}",
        f"- License/status: {card['license_status']}",
        f"- Open/local/free status: {card['open_local_free_status']}",
        f"- Expected memory: {card['expected_memory_gb']} GB",
        f"- Quantization: {card['quantization']}",
        f"- Prompt settings: {card['prompt_settings']}",
        "",
        "Limitations:",
        *[f"- {item}" for item in card["limitations"]],
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write a CertVIC model card")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    card = build_model_card(args.provider)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_model_card(card), encoding="utf-8")
    print(json.dumps({"out": args.out, "provider": args.provider, "unknown": card["unknown_provider_flagged"]}, sort_keys=True))


if __name__ == "__main__":
    main()

