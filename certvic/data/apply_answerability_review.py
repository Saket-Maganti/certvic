"""Apply answerability ratings to task metadata."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from certvic.io import read_jsonl, write_jsonl


def apply_answerability_review(tasks: str, ratings: str, out: str) -> dict:
    task_rows = read_jsonl(tasks)
    with Path(ratings).open("r", encoding="utf-8", newline="") as handle:
        rating_by_id = {row["item_id"]: row for row in csv.DictReader(handle)}
    reviewed: list[dict] = []
    blocked = 0
    for task in task_rows:
        item_id = str(task.get("item_id"))
        rating = rating_by_id.get(item_id, {})
        disagreement = str(rating.get("agreement_with_manifest", "")).lower() in {"no", "false", "0"}
        answerable = all(
            str(rating.get(field, "")).lower() in {"yes", "true", "1"}
            for field in ("original_answerable", "edited_answerable", "expected_change_unambiguous")
        )
        metadata = dict(task.get("metadata") or {})
        metadata["human_answerability_status"] = "blocked" if disagreement or not answerable else "pass"
        metadata["evidence_status"] = metadata.get("evidence_status", "EDIT_READY_NON_EVIDENCE")
        if metadata["human_answerability_status"] != "pass":
            blocked += 1
        new_task = dict(task)
        new_task["metadata"] = metadata
        reviewed.append(new_task)
    write_jsonl(out, reviewed)
    return {"tasks": tasks, "ratings": ratings, "out": out, "n_tasks": len(reviewed), "blocked": blocked}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Apply answerability review")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(apply_answerability_review(args.tasks, args.ratings, args.out), sort_keys=True))


if __name__ == "__main__":
    main()
