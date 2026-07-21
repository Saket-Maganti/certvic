"""Task manifest checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from certvic.data.license_policy import release_mode_for_source
from certvic.io import read_jsonl
from certvic.schema import TaskItem
from certvic.validation.leakage import validate_task_no_leakage


def check_task_manifest(path: str, strict: bool = False) -> dict:
    rows = read_jsonl(path)
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for idx, row in enumerate(rows):
        try:
            task = TaskItem.model_validate(row)
        except ValidationError as exc:
            errors.append(f"row {idx}: schema error: {exc}")
            continue
        if task.item_id in seen:
            errors.append(f"duplicate item_id: {task.item_id}")
        seen.add(task.item_id)
        leak_warnings = validate_task_no_leakage(task)
        if leak_warnings:
            (errors if strict else warnings).extend([f"{task.item_id}: {msg}" for msg in leak_warnings])
        if task.split in {"smoke", "local"}:
            for image_path in [task.original_image_path, task.edited_image_path]:
                if not Path(image_path).exists():
                    errors.append(f"{task.item_id}: missing local image path {image_path}")
            if task.mask and not Path(task.mask.mask_path).exists():
                errors.append(f"{task.item_id}: missing mask path {task.mask.mask_path}")
        if release_mode_for_source(task.source) == "blocked_until_verified" and task.split != "smoke":
            errors.append(f"{task.item_id}: source blocked until license verification")
        for field in ["task_hash", "source_hash", "edit_hash", "schema_version"]:
            if field not in task.metadata:
                errors.append(f"{task.item_id}: missing metadata.{field}")
    return {"passed": not errors, "n": len(rows), "errors": errors, "warnings": warnings}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    result = check_task_manifest(args.tasks, strict=args.strict)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
