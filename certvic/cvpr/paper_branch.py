"""Fail-closed paper outcome-branch activation gate."""

from __future__ import annotations

from typing import Any


def activate_paper_branch(
    *, study_import: dict[str, Any], final_inclusion: dict[str, Any],
    evidence_hashes_match: bool, intervals: dict[str, Any], claim_guard: dict[str, Any],
    requested_branch: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    if study_import.get("status") not in {"ATOMIC_MATRIX_PROMOTED", "IDEMPOTENT"}:
        blockers.append("study import is incomplete")
    if final_inclusion.get("status") != "FINAL_INCLUSION_VALIDATED":
        blockers.append("final adjudicated human inclusion is missing")
    if not evidence_hashes_match:
        blockers.append("evidence hashes do not match lineage")
    provider_intervals = intervals.get("providers", {})
    if not provider_intervals or any(
        value.get("primary_missing_as_failure", {}).get("pass") not in {True, False}
        for value in provider_intervals.values()
    ):
        blockers.append("primary intervals are incomplete or inconclusive")
    if claim_guard.get("passed") is not True:
        blockers.append("claim-language guard has not passed")
    return {
        "schema": "certvic.cvpr.paper_branch_gate.v1",
        "status": "PAPER_BRANCH_BLOCKED" if blockers else "PAPER_BRANCH_ACTIVATED",
        "requested_branch": requested_branch,
        "active_branch": None if blockers else requested_branch,
        "blockers": blockers,
        "paper_evidence": not blockers,
    }

