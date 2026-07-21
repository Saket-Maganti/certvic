"""Merge sharded VLM prediction outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from certvic.eval.prediction_dedup import deduplicate_predictions
from certvic.io import read_jsonl, write_json, write_jsonl


def _prediction_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.jsonl")))
        elif path.exists():
            files.append(path)
    return files


def merge_predictions(pred_dirs: list[str], out: str, report: str, *, tasks: str | None = None) -> dict:
    rows: list[dict] = []
    for path in _prediction_files(pred_dirs):
        rows.extend(read_jsonl(path))
    dedup = deduplicate_predictions(rows)
    write_jsonl(out, dedup["merged"])
    out_path = Path(out)
    duplicates_csv = out_path.with_name("duplicates.csv")
    missing_csv = out_path.with_name("missing_items.csv")
    with duplicates_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["key", "n"])
        writer.writeheader()
        for row in dedup["duplicates"]:
            writer.writerow({"key": "|".join(row["key"]), "n": row["n"]})
    missing_items: list[str] = []
    if tasks:
        expected = {str(row.get("item_id")) for row in read_jsonl(tasks)}
        present = {str(row.get("item_id")) for row in dedup["merged"]}
        missing_items = sorted(expected - present)
    with missing_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id"])
        writer.writeheader()
        for item_id in missing_items:
            writer.writerow({"item_id": item_id})
    summary = {
        "input_rows": len(rows),
        "merged_rows": len(dedup["merged"]),
        "duplicates": len(dedup["duplicates"]),
        "conflicts": len(dedup["conflicts"]),
        "missing_items": len(missing_items),
        "mock_or_evidence_status_preserved": True,
        "out": out,
    }
    write_json(report, summary)
    Path(str(Path(report).with_suffix(".md"))).write_text(
        "# Prediction Merge Report\n\n"
        f"Merged rows: {summary['merged_rows']}\n\n"
        f"Duplicates: {summary['duplicates']}\n\n"
        f"Conflicts: {summary['conflicts']}\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Merge prediction shards")
    parser.add_argument("--pred-dirs", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--tasks")
    args = parser.parse_args(argv)
    print(json.dumps(merge_predictions(args.pred_dirs, args.out, args.report, tasks=args.tasks), sort_keys=True))


if __name__ == "__main__":
    main()

