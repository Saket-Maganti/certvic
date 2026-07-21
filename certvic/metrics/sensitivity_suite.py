"""Post-score statistical sensitivity summaries."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from certvic.io import read_jsonl, write_json

NON_EVIDENCE_MARKERS = ("MOCK", "SIMULATED", "NON_EVIDENCE", "PLANNED")


def build_sensitivity_suite(scores: str, out_dir: str) -> dict:
    rows = read_jsonl(scores)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n = len(rows)
    consistent = sum(1 for r in rows if r.get("consistent"))
    parse_ok = sum(1 for r in rows if r.get("parse_ok"))
    rate = consistent / n if n else 0.0
    parse_rate = parse_ok / n if n else 0.0
    statuses = {
        str((r.get("metadata") or {}).get("evidence_status") or "").upper()
        for r in rows
    }
    non_evidence_blocked = any(any(marker in status for marker in NON_EVIDENCE_MARKERS) for status in statuses)
    with (out / "alpha_grid.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["alpha", "consistent_rate", "certification_claim"])
        writer.writeheader()
        for alpha in (0.1, 0.05, 0.01):
            writer.writerow({"alpha": alpha, "consistent_rate": round(rate, 4), "certification_claim": False})
    with (out / "gap_threshold_grid.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["gap_threshold", "descriptive_rate", "conclusion_label"])
        writer.writeheader()
        for threshold in (0.01, 0.05, 0.1):
            label = "above_threshold_descriptive" if rate >= threshold else "below_threshold_descriptive"
            writer.writerow({"gap_threshold": threshold, "descriptive_rate": round(rate, 4), "conclusion_label": label})
    with (out / "parse_handling_sensitivity.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["mode", "parse_ok_rate", "certification_claim"])
        writer.writeheader()
        writer.writerow({"mode": "drop_parse_failures", "parse_ok_rate": round(parse_rate, 4), "certification_claim": False})
        writer.writerow({"mode": "count_parse_failures_as_inconsistent", "parse_ok_rate": round(parse_rate, 4), "certification_claim": False})
    summary = {
        "scores": scores,
        "n_scores": n,
        "consistent_rate": round(rate, 4),
        "parse_ok_rate": round(parse_rate, 4),
        "bootstrap_never_certification": True,
        "confidence_sequence_status": "not_computed_here",
        "non_evidence_blocked": non_evidence_blocked,
        "threshold_conclusions_labeled": True,
    }
    write_json(out / "sensitivity_summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build statistical sensitivity suite")
    parser.add_argument("--scores", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(build_sensitivity_suite(args.scores, args.out_dir), sort_keys=True))


if __name__ == "__main__":
    main()

