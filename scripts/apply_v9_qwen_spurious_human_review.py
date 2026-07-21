from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/annotations/v9_qwen_spurious_human_review/qwen_failed_12_human_review.csv"
DEFAULT_OUT_JSON = ROOT / "data/results/main_real_200/v9_mega_upgrade/qwen_spurious_human_review_apply_report.json"
DEFAULT_OUT_MD = ROOT / "data/results/main_real_200/v9_mega_upgrade/QWEN_SPURIOUS_HUMAN_REVIEW_APPLY_REPORT.md"
SPURIOUS_REPORT = ROOT / "data/results/main_real_200/v8_upgrade/spurious_specificity_control_report.json"

VALID_CAUSES = {
    "VALID_IRRELEVANT_CONTROL",
    "PATCH_TOO_SALIENT",
    "PATCH_NEAR_TARGET",
    "OBJECT_REGION_AFFECTED",
    "PROMPT_AMBIGUOUS",
    "PARSE_ERROR",
    "IMAGE_MISMATCH",
    "UNSURE",
}

OBJECTIVE_EXCLUSION_CAUSES = {
    "PATCH_TOO_SALIENT",
    "PATCH_NEAR_TARGET",
    "OBJECT_REGION_AFFECTED",
    "PROMPT_AMBIGUOUS",
    "PARSE_ERROR",
    "IMAGE_MISMATCH",
}


def _write_report(report: dict, out_json: Path, out_md: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    out_md.write_text(
        "# Qwen Spurious Human Review Apply Report\n\n"
        f"- Status: `{report['status']}`\n"
        f"- Paper evidence: `{str(report['paper_evidence']).lower()}`\n"
        f"- Canonical results changed: `{str(report['canonical_results_changed']).lower()}`\n"
        f"- Raw Qwen gate: `{report['raw_gate']['flipped']}/{report['raw_gate']['n_items']} = {report['raw_gate']['rate']}`\n"
        f"- Adjusted gate after objective exclusions: `{report.get('adjusted_gate', {}).get('flipped', 'NA')}/"
        f"{report.get('adjusted_gate', {}).get('n_items', 'NA')}`\n\n"
        "## Blockers\n\n"
        + "".join(f"- {blocker}\n" for blocker in report.get("blockers", []))
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply completed V9 Qwen spurious human review sheet.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    with SPURIOUS_REPORT.open() as f:
        spurious = json.load(f)
    qwen = spurious["providers"]["qwen2_5_vl_7b"]
    raw_gate = {
        "flipped": qwen["flipped"],
        "n_items": qwen["n_items"],
        "rate": qwen["spurious_flip_rate"],
        "gate_pass": qwen["gate_pass"],
        "threshold": qwen["gate_threshold"],
    }

    rows = list(csv.DictReader(args.input.open()))
    required_human = [
        "human_valid_control",
        "human_failure_cause",
        "human_notes",
        "human_reviewer_id",
        "human_review_timestamp",
    ]
    blank_rows = [
        row["item_id"]
        for row in rows
        if any(not str(row.get(col, "")).strip() for col in required_human)
    ]
    invalid = [
        {"item_id": row["item_id"], "human_failure_cause": row.get("human_failure_cause", "")}
        for row in rows
        if row.get("human_failure_cause", "").strip()
        and row.get("human_failure_cause", "").strip() not in VALID_CAUSES
    ]
    valid_control_values = {"TRUE", "FALSE", "UNSURE"}
    invalid_validity = [
        {"item_id": row["item_id"], "human_valid_control": row.get("human_valid_control", "")}
        for row in rows
        if row.get("human_valid_control", "").strip()
        and row.get("human_valid_control", "").strip().upper() not in valid_control_values
    ]

    report = {
        "schema": "certvic.v9.qwen_spurious_human_review_apply_report.v1",
        "input": str(args.input.relative_to(ROOT)),
        "n_rows": len(rows),
        "raw_gate": raw_gate,
        "blank_rows": blank_rows,
        "invalid_failure_causes": invalid,
        "invalid_human_valid_control": invalid_validity,
        "paper_evidence": False,
        "canonical_results_changed": False,
        "blockers": [],
    }

    if blank_rows:
        report["status"] = "BLOCKED_BLANK_HUMAN_REVIEW"
        report["blockers"].append("At least one required human review field is blank.")
        _write_report(report, args.out_json, args.out_md)
        return 2
    if invalid or invalid_validity:
        report["status"] = "FAILED_INVALID_HUMAN_REVIEW_SHEET"
        report["blockers"].append("Human review sheet has invalid labels.")
        _write_report(report, args.out_json, args.out_md)
        return 1

    objective_exclusions = [
        row
        for row in rows
        if row["human_valid_control"].strip().upper() == "FALSE"
        and row["human_failure_cause"].strip() in OBJECTIVE_EXCLUSION_CAUSES
    ]
    subjective_exclusions = [
        row
        for row in rows
        if row["human_valid_control"].strip().upper() != "TRUE"
        and row["human_failure_cause"].strip() not in OBJECTIVE_EXCLUSION_CAUSES
    ]
    adjusted_n = raw_gate["n_items"] - len(objective_exclusions)
    adjusted_flips = raw_gate["flipped"] - len(objective_exclusions)
    adjusted_rate = adjusted_flips / adjusted_n if adjusted_n else None
    report.update(
        {
            "status": "DONE_HUMAN_REVIEW_APPLIED_TO_SEPARATE_REPORT",
            "objective_exclusions": [row["item_id"] for row in objective_exclusions],
            "subjective_exclusions": [row["item_id"] for row in subjective_exclusions],
            "adjusted_gate": {
                "flipped": adjusted_flips,
                "n_items": adjusted_n,
                "rate": adjusted_rate,
                "threshold": raw_gate["threshold"],
                "gate_pass": adjusted_rate is not None and adjusted_rate <= raw_gate["threshold"],
            },
            "blockers": ["Canonical results are not changed automatically by this script."],
        }
    )
    _write_report(report, args.out_json, args.out_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
