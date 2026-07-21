"""Audit that the paper is complete except empirical result values."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.validation.paper_numbers_guard import verify_paper

REQUIRED_SECTIONS = (
    "01_intro.tex",
    "02_related.tex",
    "03_method.tex",
    "04_experiments.tex",
    "05_results.tex",
    "06_limitations.tex",
    "07_conclusion.tex",
)
EXPECTED_ARTIFACTS = (
    "data/results/pair_scores.jsonl",
    "data/results/v2_report/main_results_table.csv",
    "data/results/claim_ledger.json",
)


def audit_result_free_paper(paper_dir: str) -> dict:
    root = Path(paper_dir)
    missing_sections = [name for name in REQUIRED_SECTIONS if not (root / "sections" / name).exists()]
    text = "\n".join(
        (root / "sections" / name).read_text(encoding="utf-8")
        for name in REQUIRED_SECTIONS
        if (root / "sections" / name).exists()
    )
    disallowed_todo = [
        line.strip()
        for line in text.splitlines()
        if "TODO" in line and "[RESULT REQUIRED]" not in line
    ]
    results_text = (root / "sections/05_results.tex").read_text(encoding="utf-8")
    placeholder_artifacts = [artifact for artifact in EXPECTED_ARTIFACTS if artifact in results_text]
    guard = verify_paper(repo_root=root.parent if root.name == "paper" else Path("."))
    limitations_present = "limitation" in text.lower()
    contributions_cautious = "deployment safety" not in text.lower() and "all vlms" not in text.lower()
    return {
        "missing_sections": missing_sections,
        "disallowed_todo": disallowed_todo,
        "paper_number_guard": guard,
        "limitations_present": limitations_present,
        "contributions_cautious": contributions_cautious,
        "placeholder_artifacts": placeholder_artifacts,
        "passed": (
            not missing_sections
            and not disallowed_todo
            and guard.get("passed")
            and limitations_present
            and contributions_cautious
            and len(placeholder_artifacts) >= 2
        ),
    }


def render_report(result: dict) -> str:
    return "\n".join(
        [
            "# Result-Free Paper Completeness Audit",
            "",
            f"Passed: {result['passed']}",
            f"Missing sections: {result['missing_sections']}",
            f"Disallowed TODOs: {result['disallowed_todo']}",
            f"Limitations present: {result['limitations_present']}",
            f"Placeholder artifacts: {result['placeholder_artifacts']}",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit result-free paper completeness")
    parser.add_argument("--paper-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_result_free_paper(args.paper_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()

