"""Build edit realism scorecards from visual-review ratings."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from certvic.io import write_json
from certvic.validation.edit_realism_rubric import RUBRIC_FIELDS, rubric_template


def build_scorecard(ratings: str, out_dir: str) -> dict:
    rows: list[dict]
    with Path(ratings).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    item_status: dict[str, dict] = {}
    for row in rows:
        item_id = str(row.get("item_id"))
        values = [str(row.get(field, "")).lower() for field in RUBRIC_FIELDS]
        major_fail = any(value in {"fail", "major"} for value in values)
        uncertain = sum(1 for value in values if value == "uncertain")
        item_status[item_id] = {
            "passed": not major_fail and uncertain < 3,
            "major_artifact_blocks": major_fail,
            "uncertain_heavy": uncertain >= 3,
        }
    counts = Counter("pass" if row["passed"] else "fail" for row in item_status.values())
    summary = {
        "ratings": ratings,
        "rubric": rubric_template(),
        "n_items": len(item_status),
        "status_counts": dict(counts),
        "item_status": item_status,
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "edit_realism_scorecard.json", summary)
    (out / "edit_realism_scorecard.md").write_text(
        "# Edit Realism Scorecard\n\nMajor artifacts block item eligibility.\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build edit realism scorecard")
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    result = build_scorecard(args.ratings, args.out_dir)
    print(json.dumps({"out_dir": args.out_dir, "n_items": result["n_items"]}, sort_keys=True))


if __name__ == "__main__":
    main()

