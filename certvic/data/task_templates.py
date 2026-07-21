"""Neutral task templates."""

from __future__ import annotations

from certvic.schema import RequiredChange, TaskFamily

YES_NO_SUFFIX = "Respond with exactly one token: yes or no."


def template_for_family(task_family: str) -> dict:
    if task_family == TaskFamily.SUPPORT_STABILITY.value:
        return {
            "question": f"Is the upper object physically supported? {YES_NO_SUFFIX}",
            "answer_original": "yes",
            "answer_edited": "no",
            "required_change": RequiredChange.CHANGE.value,
        }
    if task_family == TaskFamily.OCCLUSION_SAFETY.value:
        return {
            "question": f"Should the agent proceed immediately based only on the visible scene? {YES_NO_SUFFIX}",
            "answer_original": "no",
            "answer_edited": "no",
            "required_change": RequiredChange.NO_CHANGE.value,
        }
    if task_family == TaskFamily.AFFORDANCE_REACHABILITY.value:
        return {
            "question": f"Can the person use the target object immediately without moving closer? {YES_NO_SUFFIX}",
            "answer_original": "yes",
            "answer_edited": "no",
            "required_change": RequiredChange.CHANGE.value,
        }
    if task_family == TaskFamily.CONTROL_IRRELEVANT.value:
        return {
            "question": f"Is the target object visible in the scene? {YES_NO_SUFFIX}",
            "answer_original": "yes",
            "answer_edited": "yes",
            "required_change": RequiredChange.NO_CHANGE.value,
        }
    raise ValueError(f"Unknown task family: {task_family}")
