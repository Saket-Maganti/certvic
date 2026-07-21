"""Caption-only baseline stub."""

from __future__ import annotations

from pathlib import Path


class CaptionOnlyBaselineProvider:
    provider_name = "caption_only_baseline"
    provider_type = "baseline"
    model_name = "caption-only-stub"
    model_version = "v1"
    local_only = True
    cost_policy = "zero_cost_baseline"

    def __init__(self, caption_file: str | None = None):
        self.caption_file = caption_file
        self.available = bool(caption_file and Path(caption_file).exists())

    def answer(self, image_path: str, prompt: str) -> str:
        if not self.available:
            return "UNAVAILABLE"
        return "yes"
