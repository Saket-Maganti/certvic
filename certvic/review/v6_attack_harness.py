"""Reviewer attack harness for the V6 direction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import write_json

ATTACKS = [
    ("just_another_benchmark", "This is just another benchmark.", "Show validity gating, item certificates, and naive-vs-gated shifts."),
    ("edits_are_artifacts", "Edits are detectable artifacts.", "Detectability AUC must pass before VLM inference."),
    ("certificate_over_engineered", "The item certificate is over-engineered.", "Report whether certificate gating changes admissible evidence and the measured gap."),
    ("cs_unnecessary", "Confidence sequences are unnecessary.", "Tie optional stopping and small-budget evaluation to the native CS implementation."),
    ("open_only_weak", "Open-only models are weak.", "Scope claims to open VLMs actually run and present frontier comparisons as non-core future work."),
    ("no_mechanism", "The paper has no mechanism.", "Use diagnostic prompt/intervention probes as exploratory mechanism evidence."),
    ("small_scale", "Scale is too small.", "Use the CVPR bar checker and stop/scale decisions after the tiny pilot."),
    ("human_validation_subjective", "Human validation is too subjective.", "Report review overlap, IAA, answerability, and certificate pass rates."),
    ("detectability_probe_weak", "The detectability probe is too weak.", "Block if AUC is high and require stronger edits/probes before VLM runs."),
    ("ambiguous_answer_keys", "Answer keys are ambiguous.", "Answerability and single-factor gates reject ambiguous items."),
]


def build_attacks() -> dict:
    rows = [
        {
            "id": attack_id,
            "attack": attack,
            "required_empirical_defense": defense,
            "blocker_if_missing": True,
        }
        for attack_id, attack, defense in ATTACKS
    ]
    return {
        "harness": "v6_reviewer_attacks",
        "attacks": rows,
        "n_attacks": len(rows),
        "passed": all(row["required_empirical_defense"] for row in rows),
        "evidence_status": "REVIEWER_ATTACK_PLAN_NON_EVIDENCE",
    }


def render_markdown(result: dict) -> str:
    lines = ["# V6 Reviewer Attacks for the New Direction", "", "| Attack | Required defense |", "| --- | --- |"]
    for row in result["attacks"]:
        lines.append(f"| {row['attack']} | {row['required_empirical_defense']} |")
    lines.append("")
    return "\n".join(lines)


def write_attacks(out: str, json_out: str) -> dict:
    result = build_attacks()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(render_markdown(result), encoding="utf-8")
    write_json(json_out, result)
    return {"out": out, "json_out": json_out, "passed": result["passed"]}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build V6 reviewer attack harness")
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_attacks(args.out, args.json_out), sort_keys=True))


if __name__ == "__main__":
    main()
