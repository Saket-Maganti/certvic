"""Random and majority baselines."""

from __future__ import annotations

import random


class RandomBaselineProvider:
    provider_name = "random_baseline"
    provider_type = "baseline"
    model_name = "seeded-random"
    model_version = "v1"
    local_only = True
    cost_policy = "zero_cost_baseline"

    def __init__(self, seed: int = 0):
        self.seed = seed

    def answer(self, image_path: str, prompt: str) -> str:
        return random.Random(f"{self.seed}:{image_path}:{prompt}").choice(["yes", "no"])


class MajorityBaselineProvider:
    provider_name = "majority_baseline"
    provider_type = "baseline"
    model_name = "manifest-majority"
    model_version = "v1"
    local_only = True
    cost_policy = "zero_cost_baseline"

    def __init__(self, majority_answer: str = "yes"):
        self.majority_answer = majority_answer

    def answer(self, image_path: str, prompt: str) -> str:
        return self.majority_answer
