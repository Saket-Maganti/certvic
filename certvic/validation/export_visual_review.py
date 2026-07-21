"""Export a visual-review sheet for generated edits / materialized tasks.

Human review validates edit/item quality only; it never produces model evidence.
The exported sheet contains NO model outputs or predictions.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

from certvic.io import read_jsonl

REVIEW_COLUMNS = [
    "item_id",
    "edit_id",
    "source_id",
    "task_family",
    "domain",
    "edit_type",
    "required_change",
    "original_image_path",
    "edited_image_path",
    "mask_id",
    "bbox",
    "quality_gate_status",
    "quality_warnings",
    "neutral_question",
    # Reviewer-filled (yes / no / uncertain):
    "photorealistic",
    "single_factor",
    "target_object_clear",
    "required_change_unambiguous",
    "prompt_answerable",
    "keep_for_eval",
    "notes",
    "reviewer_id",
]


def _join_key(row: dict) -> str:
    return str(row.get("edit_id") or row.get("item_id") or "")


def export_visual_review(tasks_path: str, generated_edits_path: str, out_path: str, max_items: int = 50, seed: int = 0) -> int:
    tasks = read_jsonl(tasks_path)
    edits_by_key: dict[str, dict] = {}
    if generated_edits_path and Path(generated_edits_path).exists():
        for edit in read_jsonl(generated_edits_path):
            edits_by_key[_join_key(edit)] = edit

    rng = random.Random(seed)
    rng.shuffle(tasks)
    tasks = tasks[:max_items]
    tasks.sort(key=lambda r: str(r.get("item_id") or r.get("edit_id") or ""))

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(out_path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        for task in tasks:
            edit = edits_by_key.get(_join_key(task), {})
            quality = edit.get("quality") or {}
            warnings = quality.get("warnings") or []
            writer.writerow(
                {
                    "item_id": task.get("item_id") or task.get("edit_id"),
                    "edit_id": task.get("edit_id") or edit.get("edit_id"),
                    "source_id": task.get("source_id") or edit.get("source_id"),
                    "task_family": task.get("task_family") or edit.get("task_family"),
                    "domain": task.get("domain") or edit.get("domain"),
                    "edit_type": task.get("edit_type") or edit.get("edit_type"),
                    "required_change": task.get("required_change") or edit.get("required_change"),
                    "original_image_path": task.get("original_image_path") or edit.get("original_image_path"),
                    "edited_image_path": task.get("edited_image_path") or edit.get("edited_image_path"),
                    "mask_id": task.get("mask_id") or edit.get("mask_id"),
                    "bbox": json.dumps(task.get("bbox") or edit.get("actual_params", {}).get("bbox")),
                    "quality_gate_status": edit.get("quality_gate_status") or task.get("quality_gate_status"),
                    "quality_warnings": "; ".join(str(w) for w in warnings),
                    "neutral_question": task.get("question_original") or task.get("neutral_question") or "",
                    "photorealistic": "",
                    "single_factor": "",
                    "target_object_clear": "",
                    "required_change_unambiguous": "",
                    "prompt_answerable": "",
                    "keep_for_eval": "",
                    "notes": "",
                    "reviewer_id": "",
                }
            )
    return len(tasks)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export a visual review sheet (no model outputs)")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--generated-edits", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-items", type=int, default=50)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    n = export_visual_review(args.tasks, args.generated_edits, args.out, max_items=args.max_items, seed=args.seed)
    print(json.dumps({"rows": n, "out": args.out, "contains_model_outputs": False}, sort_keys=True))


if __name__ == "__main__":
    main()
