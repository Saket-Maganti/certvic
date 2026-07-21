"""Create human answerability validation sheets."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from certvic.io import read_jsonl

ANSWERABILITY_COLUMNS = (
    "item_id",
    "original_answerable",
    "edited_answerable",
    "expected_change_unambiguous",
    "human_expected_original",
    "human_expected_edited",
    "agreement_with_manifest",
    "notes",
)


def write_answerability_sheet(tasks: str, out: str) -> dict:
    rows = read_jsonl(tasks)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with Path(out).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ANSWERABILITY_COLUMNS)
        writer.writeheader()
        for task in rows:
            writer.writerow({"item_id": task.get("item_id")})
    return {"tasks": tasks, "out": out, "n_items": len(rows), "contains_model_outputs": False}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write answerability review sheet")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_answerability_sheet(args.tasks, args.out), sort_keys=True))


if __name__ == "__main__":
    main()

