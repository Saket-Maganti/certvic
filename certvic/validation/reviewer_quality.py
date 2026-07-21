"""Reviewer reliability, sentinel, and fatigue checks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from certvic.io import write_json
from certvic.validation.sentinel_items import sentinel_summary


def _anon(reviewer: str) -> str:
    return "reviewer_" + hashlib.sha256(reviewer.encode("utf-8")).hexdigest()[:8]


def analyze_reviewer_quality(ratings: str, out_dir: str) -> dict:
    with Path(ratings).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_item: dict[str, list[dict]] = defaultdict(list)
    counts: Counter = Counter()
    for row in rows:
        by_item[str(row.get("item_id"))].append(row)
        counts[_anon(str(row.get("reviewer_id", "")))] += 1
    disagreements = []
    for item_id, bucket in by_item.items():
        values = {row.get("single_factor_valid") for row in bucket if row.get("single_factor_valid")}
        if len(values) > 1:
            disagreements.append(item_id)
    fatigue = [reviewer for reviewer, count in counts.items() if count > 200]
    summary = {
        "ratings": ratings,
        "n_rows": len(rows),
        "reviewer_counts": dict(counts),
        "reviewers_anonymized": True,
        "paid_annotation_required": False,
        "disagreements": disagreements,
        "fatigue_warnings": fatigue,
        "sentinel_summary": sentinel_summary(rows),
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "reviewer_quality_summary.json", summary)
    (out / "reviewer_quality_report.md").write_text(
        "# Reviewer Quality\n\nDisagreements and optional sentinels are surfaced for adjudication.\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Analyze reviewer quality")
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    result = analyze_reviewer_quality(args.ratings, args.out_dir)
    print(json.dumps({"out_dir": args.out_dir, "n_rows": result["n_rows"]}, sort_keys=True))


if __name__ == "__main__":
    main()

