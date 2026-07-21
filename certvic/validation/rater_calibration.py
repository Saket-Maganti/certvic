"""Compute rater calibration against gold labels."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from certvic.io import write_json


def calibrate_raters(ratings: str, gold: str, out_dir: str, *, threshold: float = 0.8) -> dict:
    with Path(gold).open("r", encoding="utf-8", newline="") as handle:
        gold_rows = {row["item_id"]: row for row in csv.DictReader(handle)}
    by_rater: dict[str, list[bool]] = defaultdict(list)
    with Path(ratings).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            item_gold = gold_rows.get(row.get("item_id", ""))
            if not item_gold:
                continue
            expected = str(item_gold.get("gold_single_factor_valid", "")).lower()
            observed = str(row.get("single_factor_valid", "")).lower()
            by_rater[str(row.get("reviewer_id", "unknown"))].append(expected == observed)
    rater_status = {}
    for rater, values in by_rater.items():
        accuracy = sum(values) / len(values) if values else 0.0
        rater_status[rater] = {
            "n": len(values),
            "accuracy": round(accuracy, 4),
            "approved": accuracy >= threshold,
        }
    summary = {
        "ratings": ratings,
        "gold": gold,
        "threshold": threshold,
        "rater_status": rater_status,
        "low_calibration_raters": [r for r, row in rater_status.items() if not row["approved"]],
        "paid_annotation": False,
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "calibration_report.json", summary)
    (out / "calibration_report.md").write_text(
        "# Rater Calibration\n\n"
        f"Approved raters: {sum(1 for row in rater_status.values() if row['approved'])}\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compute rater calibration")
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args(argv)
    result = calibrate_raters(args.ratings, args.gold, args.out_dir, threshold=args.threshold)
    print(json.dumps({"out_dir": args.out_dir, "low_calibration_raters": result["low_calibration_raters"]}, sort_keys=True))


if __name__ == "__main__":
    main()

