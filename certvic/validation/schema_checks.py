"""Schema validation helpers."""

from __future__ import annotations

from pydantic import ValidationError

from certvic.schema import TaskItem
from certvic.validation.leakage import validate_task_no_leakage


def validate_task_record(record: dict, strict_leakage: bool = True) -> list[str]:
    warnings: list[str] = []
    try:
        task = TaskItem.model_validate(record)
    except ValidationError as exc:
        return [f"schema_error: {exc}"]
    warnings.extend(validate_task_no_leakage(task))
    if strict_leakage and warnings:
        return warnings
    return warnings
