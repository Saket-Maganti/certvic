"""Prompt and path leakage checks."""

from __future__ import annotations

import re
from pathlib import Path

from certvic.schema.task import TaskItem

FORBIDDEN_PROMPT_TERMS = [
    "removed",
    "occluded",
    "displaced",
    "edited",
    "changed",
    "unsupported",
    "fall",
    "falls",
    "unsafe",
    "answer",
    "label",
    "ground_truth",
    "ground truth",
]

FORBIDDEN_FILENAME_TERMS = [
    "removed",
    "occluded",
    "displaced",
    "edited",
    "changed",
    "unsupported",
    "falls",
    "unsafe",
    "answer",
    "label",
    "ground_truth",
    "ground truth",
]


def _term_found(text: str, term: str) -> bool:
    pattern = r"(?<![a-z0-9_])" + re.escape(term.lower()) + r"(?![a-z0-9_])"
    return re.search(pattern, text.lower()) is not None


def check_prompt_no_leakage(prompt: str, answers: list[str] | None = None) -> list[str]:
    warnings = [f"prompt contains forbidden leakage term: {term}" for term in FORBIDDEN_PROMPT_TERMS if _term_found(prompt, term)]
    for answer in answers or []:
        if answer and answer.lower() not in {"yes", "no"} and _term_found(prompt, answer):
            warnings.append(f"prompt contains expected answer token: {answer}")
    return warnings


def check_path_no_leakage(path: str) -> list[str]:
    name = re.sub(r"[_\-.]+", " ", Path(path).name.lower())
    return [f"path contains forbidden leakage term: {term}" for term in FORBIDDEN_FILENAME_TERMS if _term_found(name, term)]


def validate_task_no_leakage(task: TaskItem) -> list[str]:
    warnings: list[str] = []
    answers = [task.answer_original, task.answer_edited]
    warnings.extend(check_prompt_no_leakage(task.question_original, answers=answers))
    warnings.extend(check_prompt_no_leakage(task.question_edited, answers=answers))
    warnings.extend(check_path_no_leakage(task.original_image_path))
    warnings.extend(check_path_no_leakage(task.edited_image_path))
    return warnings
