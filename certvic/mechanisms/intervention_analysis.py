"""Analyze whether a diagnostic intervention moves the decision-update gap."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import read_jsonl, write_json
from certvic.validity.load_bearing import score_gap


def _parse_failure(rows: list[dict]) -> float | None:
    if not rows:
        return None
    return sum(1 for row in rows if not bool(row.get("parse_ok", True))) / len(rows)


def _non_evidence(rows: list[dict]) -> bool:
    joined = " ".join(str((row.get("metadata") or {}).get("evidence_status", "unknown")).lower() for row in rows)
    return any(token in joined for token in ("mock", "smoke", "simulated", "planned", "unknown"))


def analyze_intervention(baseline_path: str, intervention_path: str) -> dict:
    baseline = read_jsonl(baseline_path)
    intervention = read_jsonl(intervention_path)
    b_gap = score_gap(baseline)
    i_gap = score_gap(intervention)
    gap_delta = None
    if b_gap["intervention_consistency_gap"] is not None and i_gap["intervention_consistency_gap"] is not None:
        gap_delta = i_gap["intervention_consistency_gap"] - b_gap["intervention_consistency_gap"]
    parse_delta = None
    if _parse_failure(baseline) is not None and _parse_failure(intervention) is not None:
        parse_delta = _parse_failure(intervention) - _parse_failure(baseline)
    consistency_delta = None
    if b_gap["consistency_rate"] is not None and i_gap["consistency_rate"] is not None:
        consistency_delta = i_gap["consistency_rate"] - b_gap["consistency_rate"]
    flags: list[str] = []
    if parse_delta is not None and parse_delta > 0.05:
        flags.append("intervention_increased_parse_failures")
    if gap_delta is not None and gap_delta < 0:
        flags.append("intervention_reduced_gap")
    if gap_delta is not None and gap_delta > 0:
        flags.append("intervention_increased_gap")
    if _non_evidence(baseline + intervention):
        flags.append("exploratory_only_non_evidence_inputs")
    return {
        "analysis": "intervention_that_moves_the_gap",
        "baseline": b_gap,
        "intervention": i_gap,
        "gap_delta": gap_delta,
        "parse_delta": parse_delta,
        "consistency_delta": consistency_delta,
        "caution_flags": sorted(flags),
        "claim_status": "EXPLORATORY_ONLY_UNLESS_PREREGISTERED_AND_CLAIM_GATED",
    }


def render_markdown(result: dict) -> str:
    return "\n".join(
        [
            "# Intervention Analysis",
            "",
            f"Gap delta: {result['gap_delta']}",
            f"Parse delta: {result['parse_delta']}",
            f"Consistency delta: {result['consistency_delta']}",
            "",
            "Caution flags:",
            *[f"- {flag}" for flag in result["caution_flags"]],
            "",
            "This analysis is exploratory unless the intervention was preregistered and real evidence passes claim gates.",
            "",
        ]
    )


def write_analysis(baseline: str, intervention: str, out_dir: str) -> dict:
    result = analyze_intervention(baseline, intervention)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "intervention_analysis_summary.json", result)
    (out / "intervention_analysis_report.md").write_text(render_markdown(result), encoding="utf-8")
    return {"out_dir": str(out), "passed": True, "claim_status": result["claim_status"]}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Analyze gap movement under a diagnostic intervention")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--intervention", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_analysis(args.baseline, args.intervention, args.out_dir), sort_keys=True))


if __name__ == "__main__":
    main()
