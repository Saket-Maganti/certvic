"""Convert rich materialized/reviewed eval-task rows into strict TaskItem manifests.

`materialize_tasks` emits a review-friendly preview schema (flat `source_id`/`edit_id`
plus quality/review fields); `run_eval` / `run_tiny_eval` load the strict `TaskItem`
schema (nested `source` + `edit`, `extra="forbid"`). This projects the former onto the
latter so the evidence run can actually load the tasks. CPU-only, no evidence claims.
"""

from __future__ import annotations

import argparse
import json

from certvic.io import read_jsonl
from certvic.schema import TaskItem
from certvic.schema.edit import EditSpec
from certvic.schema.source import SourceImageRecord


def to_task_item(row: dict) -> TaskItem:
    source = SourceImageRecord(
        source_id=row["source_id"],
        source_name="ADE20K",
        license_category="pointer_only",
    )
    edit = EditSpec(
        edit_id=row["edit_id"],
        source_id=row["source_id"],
        edit_type=row["edit_type"],
        task_family=row["task_family"],
        domain=row["domain"],
        expected_effect=row["expected_effect"],
    )
    meta = dict(row.get("metadata") or {})
    meta.setdefault("evidence_status", row.get("evidence_status", "HUMAN_REVIEWED_NON_EVIDENCE"))
    return TaskItem(
        item_id=row["item_id"],
        source=source,
        edit=edit,
        original_image_path=row["original_image_path"],
        edited_image_path=row["edited_image_path"],
        question_original=row["question_original"],
        question_edited=row["question_edited"],
        answer_original=row["answer_original"],
        answer_edited=row["answer_edited"],
        required_change=row["required_change"],
        answer_format=row["answer_format"],
        task_family=row["task_family"],
        domain=row["domain"],
        split=row["split"],
        metadata=meta,
    )


def convert_file(in_path: str, out_path: str) -> dict:
    rows = read_jsonl(in_path)
    items: list[TaskItem] = []
    skipped: list[dict] = []
    for r in rows:
        try:
            items.append(to_task_item(r))
        except Exception as exc:
            skipped.append({"item_id": r.get("item_id"), "error": f"{type(exc).__name__}: {exc}"})
    with open(out_path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(it.model_dump_json() + "\n")
    return {
        "in": in_path,
        "out": out_path,
        "converted": len(items),
        "skipped": len(skipped),
        "skipped_detail": skipped[:5],
        "evidence_claims_made": False,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Convert reviewed eval tasks into a strict TaskItem manifest")
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", dest="out_path", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(convert_file(args.in_path, args.out_path), sort_keys=True))


if __name__ == "__main__":
    main()
