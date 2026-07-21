"""Compare multiple scored model runs descriptively."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from certvic.io import read_jsonl, write_json
from certvic.reporting.model_rankings import rank_models


def _score_files(root: str) -> list[Path]:
    path = Path(root)
    if path.is_file():
        return [path]
    return sorted(path.rglob("*.jsonl")) if path.exists() else []


def build_model_comparison(score_dirs: str, out_dir: str) -> dict:
    rows: list[dict] = []
    for path in _score_files(score_dirs):
        rows.extend(read_jsonl(path))
    rankings = rank_models(rows)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "model_rankings.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["model", "n", "consistency_rate", "parse_ok_rate", "ranking_type"])
        writer.writeheader()
        writer.writerows(rankings)
    summary = {
        "score_dirs": score_dirs,
        "n_scores": len(rows),
        "n_models": len(rankings),
        "rankings": rankings,
        "significance_claims_made": False,
        "descriptive_vs_certified_separated": True,
        "parse_failures_included": True,
    }
    write_json(out / "comparison_summary.json", summary)
    (out / "comparison_report.md").write_text(
        "# Model Comparison\n\nDescriptive comparison only; no significance or certification overclaim.\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build model comparison tables")
    parser.add_argument("--score-dirs", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(build_model_comparison(args.score_dirs, args.out_dir), sort_keys=True))


if __name__ == "__main__":
    main()

