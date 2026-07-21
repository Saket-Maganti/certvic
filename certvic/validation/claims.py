"""Claim wording validation."""

from __future__ import annotations

FORBIDDEN_CLAIM_PHRASES = [
    "proves causal understanding",
    "vlms cannot reason causally",
    "safe for autonomous driving",
    "unsafe for deployment",
    "frontier models fail",
    "all vlms",
]

NON_EVIDENCE_STATUSES = {
    "CANDIDATE_ONLY",
    "DEPRECATED_OR_STALE",
    "DIAGNOSTIC_ONLY",
    "EDIT_READY_NON_EVIDENCE",
    "GENERATED_EDIT_ONLY",
    "HUMAN_REVIEW_PENDING",
    "MACHINE_ASSISTED_PRELIMINARY",
    "PLANNED_ONLY",
    "PLANNED_NOT_EXECUTED",
    "PREVIEW_ONLY",
    "NOT_GENERATED",
    "SIMULATED_ONLY",
    "SYNTHETIC_TEST_FIXTURE",
    "UNKNOWN",
    "UNKNOWN_REQUIRES_AUDIT",
}


def validate_claim_text(text: str, certified: bool = False, has_cs_lower_bound: bool = False) -> list[str]:
    lowered = text.lower()
    errors = [f"forbidden claim phrase: {phrase}" for phrase in FORBIDDEN_CLAIM_PHRASES if phrase in lowered]
    if certified and not has_cs_lower_bound:
        errors.append("certified claim lacks CS lower bound")
    return errors


def build_evidence_context(tasks=None, predictions=None, scores=None) -> dict:
    splits: set[str] = set()
    evidence_statuses: set[str] = set()
    provider_types: set[str] = set()
    synthetic_flags: list[bool] = []

    for task in tasks or []:
        splits.add(str(task.split))
        evidence_statuses.add(str(task.metadata.get("evidence_status", "UNKNOWN")))
        synthetic_flags.append(
            task.split == "smoke"
            or task.domain == "synthetic_sanity"
            or "synthetic smoke" in task.source.source_name.lower()
        )
    for pred in predictions or []:
        provider_types.add(str(pred.provider_type))
        evidence_statuses.add(str(pred.metadata.get("provider_evidence_status", "UNKNOWN")))
    for score in scores or []:
        metadata = score.metadata or {}
        if "split" in metadata:
            splits.add(str(metadata["split"]))
        if "evidence_status" in metadata:
            evidence_statuses.add(str(metadata["evidence_status"]))
        if "provider_type" in metadata:
            provider_types.add(str(metadata["provider_type"]))
        if "source_is_synthetic_smoke" in metadata:
            synthetic_flags.append(bool(metadata["source_is_synthetic_smoke"]))

    return {
        "splits": sorted(splits),
        "evidence_statuses": sorted(evidence_statuses),
        "provider_types": sorted(provider_types),
        "has_synthetic_smoke_fixtures": any(synthetic_flags),
    }


def validate_certified_claim_eligibility(
    certification: dict,
    claim_text: str,
    evidence_context: dict | None,
    threshold: float = 0.05,
) -> list[str]:
    errors: list[str] = []
    context = evidence_context or {}
    splits = set(context.get("splits") or [])
    evidence_statuses = {str(value).upper() for value in context.get("evidence_statuses") or []}
    provider_types = set(context.get("provider_types") or [])

    if not splits:
        errors.append("certified claim blocked: missing split evidence")
    if "smoke" in splits:
        errors.append("certified claim blocked: split is smoke")
    if not evidence_statuses:
        errors.append("certified claim blocked: missing evidence_status")
    if "MOCK_ONLY" in evidence_statuses:
        errors.append("certified claim blocked: evidence_status is MOCK_ONLY")
    for status in sorted(evidence_statuses & NON_EVIDENCE_STATUSES):
        errors.append(f"certified claim blocked: evidence_status is {status}")
    if not provider_types:
        errors.append("certified claim blocked: missing provider_type")
    if "mock" in provider_types:
        errors.append("certified claim blocked: provider_type is mock")
    if context.get("has_synthetic_smoke_fixtures"):
        errors.append("certified claim blocked: data are synthetic smoke fixtures")

    cs = certification.get("confidence_sequence") or {}
    latest = cs.get("latest") or {}
    lower_bound = certification.get("lower_bound", latest.get("lo"))
    if not cs.get("available"):
        errors.append("certified claim blocked: anytime-valid CS unavailable")
    if lower_bound is None:
        errors.append("certified claim blocked: missing CS lower bound")
    elif lower_bound <= threshold:
        errors.append("certified claim blocked: CS lower bound does not exceed threshold")

    errors.extend(
        validate_claim_text(
            claim_text,
            certified=True,
            has_cs_lower_bound=lower_bound is not None,
        )
    )
    return errors
