"""Text-only baseline provider."""

from __future__ import annotations

import random


class TextOnlyBaselineProvider:
    provider_name = "text_only_baseline"
    provider_type = "baseline"
    model_name = "text-only-heuristic"
    model_version = "v1"
    local_only = True
    cost_policy = "zero_cost_baseline"

    def __init__(self, seed: int = 0):
        self.seed = seed
        self.seen_image_paths: list[str] = []

    def answer(self, image_path: str, prompt: str) -> str:
        self.seen_image_paths.append(image_path)
        return random.Random(f"{self.seed}:{prompt}").choice(["yes", "no"])
