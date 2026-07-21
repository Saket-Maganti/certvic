"""Zero-cost policy validation."""

from __future__ import annotations

from pathlib import Path

import yaml

from certvic.providers.registry import PAID_PROVIDER_NAMES

SUSPICIOUS_MARKERS = [
    "openai",
    "anthropic",
    "billing",
    "stripe",
    "aws",
    "gcp",
    "azure",
    "runpod",
    "replicate",
    "together",
    "modal",
    "vast.ai",
    "lambda labs",
]


def validate_zero_cost_config(config_path: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    if config_path and Path(config_path).exists():
        data = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
        if data.get("paid_services_enabled") is True:
            errors.append("config enables paid services")
        provider = str(data.get("provider", "")).lower()
        if provider in PAID_PROVIDER_NAMES:
            errors.append(f"paid provider configured: {provider}")
        if data.get("enable_free_tier_reference") is True:
            warnings.append("free-tier reference enabled; verify genuinely free and reference-only")
    return {"passed": not errors, "errors": errors, "warnings": warnings}


def scan_text_for_paid_recommendations(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8").lower()
    errors = []
    for marker in SUSPICIOUS_MARKERS:
        if marker in text and "zero_cost_policy" not in str(path).lower():
            if "paid fallback" in text or "use paid" in text:
                errors.append(f"suspicious paid-service recommendation: {marker}")
    return {"passed": not errors, "errors": errors}
