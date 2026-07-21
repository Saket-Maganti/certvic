"""Deterministic mock VLM providers for smoke tests.

All providers in this module are MOCK_ONLY and non-evidence. They are designed
to exercise scoring, parsing, and audit gates before any real data/model run.
"""

from __future__ import annotations

import random
from pathlib import Path

from certvic.schema import ImageVariant, TaskItem


class MockProvider:
    provider_type = "mock"
    local_only = True
    cost_policy = "zero_cost_mock_only"
    evidence_status = "MOCK_ONLY"
    non_evidence = True

    def __init__(self, variant: str = "perfect", seed: int = 0):
        self.variant = variant
        self.provider_name = f"mock_{variant}"
        self.model_name = f"mock-{variant}"
        self.model_version = "v1.1"
        self.seed = seed
        self._tasks: dict[str, TaskItem] = {}

    def set_task_context(self, tasks: list[TaskItem]) -> None:
        self._tasks = {task.item_id: task for task in tasks}

    def answer(self, image_path: str, prompt: str) -> str:
        item_id, image_variant = self._infer_item_and_variant(image_path)
        task = self._tasks.get(item_id)
        if self.variant in {"random", "random_seeded"}:
            rng = random.Random(f"{self.seed}:{image_path}:{prompt}")
            return rng.choice(["yes", "no"])
        if self.variant == "parser_fail":
            return "yes and no"
        if self.variant == "always_yes":
            return "yes"
        if self.variant == "always_no":
            return "no"
        if task is None:
            return "yes"
        if self.variant == "perfect":
            return task.answer_original if image_variant == ImageVariant.ORIGINAL.value else task.answer_edited
        if self.variant == "inconsistent":
            return task.answer_original
        if self.variant == "spurious_flip":
            if image_variant == ImageVariant.ORIGINAL.value:
                return task.answer_original
            if task.required_change == "no_change":
                return _flip_yes_no(task.answer_original)
            return task.answer_edited
        raise ValueError(f"Unknown mock provider variant: {self.variant}")

    @staticmethod
    def _infer_item_and_variant(image_path: str) -> tuple[str, str]:
        stem = Path(image_path).stem
        if stem.endswith("_orig"):
            return stem.removesuffix("_orig"), ImageVariant.ORIGINAL.value
        if stem.endswith("_var"):
            return stem.removesuffix("_var"), ImageVariant.EDITED.value
        if "edited" in stem:
            return stem.split("_edited")[0], ImageVariant.EDITED.value
        return stem.split("_original")[0], ImageVariant.ORIGINAL.value


def _flip_yes_no(answer: str) -> str:
    if answer == "yes":
        return "no"
    if answer == "no":
        return "yes"
    return answer
