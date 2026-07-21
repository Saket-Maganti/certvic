"""Materialize visually-approved tasks from a keep-list.

Approved tasks remain non-evidence (HUMAN_REVIEWED_NON_EVIDENCE); human review
validates quality only and never creates model evidence.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from certvic.io import read_jsonl, write_json, write_jsonl


def apply_visual_review(tasks_path: str, keep_list_path: str, out_path: str, summary_out: str) -> dict:
    tasks = read_jsonl(tasks_path)
    keep_ids = {line.strip() for line in Path(keep_list_path).read_text(encoding="utf-8").splitlines() if line.strip()}
    approved: list[dict] = []
    dropped = 0
    for task in tasks:
        item_id = str(task.get("item_id") or task.get("edit_id") or "")
        if item_id not in keep_ids:
            dropped += 1
            continue
        row = dict(task)
        row["visual_review_status"] = "approved"
        row["evidence_status"] = "HUMAN_REVIEWED_NON_EVIDENCE"
        metadata = dict(row.get("metadata") or {})
        metadata["visual_review_status"] = "approved"
        metadata["evidence_status"] = "HUMAN_REVIEWED_NON_EVIDENCE"
        row["metadata"] = metadata
        approved.append(row)

    write_jsonl(out_path, approved)
    summary = {
        "tasks_path": tasks_path,
        "keep_list_path": keep_list_path,
        "out": out_path,
        "input_tasks": len(tasks),
        "approved_tasks": len(approved),
        "dropped_tasks": dropped,
        "keep_ids": len(keep_ids),
        "by_task_family": dict(sorted(Counter(r.get("task_family") for r in approved).items())),
        "evidence_status": "HUMAN_REVIEWED_NON_EVIDENCE",
        "visual_review_status": "approved",
        "paper_evidence": False,
    }
    write_json(summary_out, summary)
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Materialize visually-approved (non-evidence) tasks")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--keep-list", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--summary-out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(apply_visual_review(args.tasks, args.keep_list, args.out, args.summary_out), sort_keys=True))


if __name__ == "__main__":
    main()
