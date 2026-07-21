"""Interpret future ablation reports with cautious language."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def interpret_ablation_report(ablation_report: str) -> dict:
    data = {}
    path = Path(ablation_report)
    if path.is_file() and path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    text_only = float(data.get("text_only_rate", 0.0) or 0.0)
    parser_sensitivity = float(data.get("parser_sensitivity", 0.0) or 0.0)
    control_flips = float(data.get("control_spurious_flip_rate", 0.0) or 0.0)
    warnings: list[str] = []
    blocked = False
    if text_only > 0.5:
        warnings.append("text_only_high_construct_threat")
    if parser_sensitivity > 0.1:
        warnings.append("parser_sensitivity_claim_threat")
    if control_flips > 0.1:
        warnings.append("control_flips_block_claims")
        blocked = True
    draft = "Ablations are interpreted cautiously and remain descriptive unless claim gates pass."
    if not warnings:
        draft = "Ablations are directionally consistent with the main analysis, subject to claim gates."
    return {
        "ablation_report": ablation_report,
        "warnings": warnings,
        "claims_blocked": blocked,
        "draft": draft,
        "unsupported_claims": False,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Draft cautious ablation interpretation")
    parser.add_argument("--ablation-report", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = interpret_ablation_report(args.ablation_report)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("# Ablation Interpretation Draft\n\n" + result["draft"] + "\n", encoding="utf-8")
    print(json.dumps({"out": args.out, "warnings": result["warnings"], "claims_blocked": result["claims_blocked"]}, sort_keys=True))


if __name__ == "__main__":
    main()

