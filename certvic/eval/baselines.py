"""Baseline helpers."""

from __future__ import annotations

from collections import Counter

from certvic.schema import TaskItem


def majority_answer(tasks: list[TaskItem]) -> str:
    counts = Counter()
    for task in tasks:
        counts[task.answer_original] += 1
        counts[task.answer_edited] += 1
    if not counts:
        return "yes"
    return counts.most_common(1)[0][0]
