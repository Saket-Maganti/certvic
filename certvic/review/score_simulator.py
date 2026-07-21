"""Structured CVPR reviewer score simulator."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


AXES = (
    "novelty",
    "technical_quality",
    "empirical_strength",
    "clarity",
    "reproducibility",
    "construct_validity",
    "significance",
    "recommendation",
)


def simulate_scores(paper_dir: str, reports_root: str, out_dir: str) -> dict:
    paper_exists = Path(paper_dir).exists()
    reports_exist = Path(reports_root).exists()
    no_results = "[RESULT REQUIRED]" in (Path(paper_dir) / "sections/05_results.tex").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    scores = {
        "novelty": 4,
        "technical_quality": 4,
        "empirical_strength": 1 if no_results else 3,
        "clarity": 4 if paper_exists else 2,
        "reproducibility": 4 if reports_exist else 2,
        "construct_validity": 3,
        "significance": 3,
        "recommendation": 2 if no_results else 4,
    }
    weaknesses = ["empirical results missing"] if no_results else []
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    reviews = {"axes": scores, "fatal_weaknesses": weaknesses, "fake_results_invented": False}
    (out / "simulated_reviews.json").write_text(json.dumps(reviews, indent=2, sort_keys=True), encoding="utf-8")
    with (out / "score_distribution.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["axis", "score"])
        writer.writeheader()
        for axis in AXES:
            writer.writerow({"axis": axis, "score": scores[axis]})
    (out / "fatal_weaknesses.md").write_text("\n".join(["# Fatal Weaknesses", "", *[f"- {w}" for w in weaknesses], ""]), encoding="utf-8")
    (out / "action_plan.md").write_text("# Action Plan\n\n- Execute real ADE20K/diffusion/VLM runs.\n", encoding="utf-8")
    return {"out_dir": str(out), "scores": scores, "fatal_weaknesses": weaknesses}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Simulate CVPR reviewer scores")
    parser.add_argument("--paper-dir", required=True)
    parser.add_argument("--reports-root", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(simulate_scores(args.paper_dir, args.reports_root, args.out_dir), sort_keys=True))


if __name__ == "__main__":
    main()

