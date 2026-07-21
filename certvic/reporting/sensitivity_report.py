"""Render V4 statistical sensitivity markdown."""

from __future__ import annotations

from certvic.io import read_json


def render_sensitivity_report(summary_json: str) -> str:
    summary = read_json(summary_json)
    return "\n".join(
        [
            "# Statistical Sensitivity Report",
            "",
            "Sensitivity tables are descriptive. Bootstrap summaries are never certification.",
            f"Scores: `{summary['scores']}`",
            f"N: {summary['n_scores']}",
            f"Consistency rate: {summary['consistent_rate']}",
            f"CS status: {summary['confidence_sequence_status']}",
            f"Non-evidence blocked: {summary['non_evidence_blocked']}",
            "",
        ]
    )
