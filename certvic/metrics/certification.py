"""Certification gate logic."""

from __future__ import annotations

from certvic.metrics.confseq_wrappers import gap_cs
from certvic.validation.claims import validate_certified_claim_eligibility


def certify_gap(
    a,
    C,
    delta_threshold: float = 0.05,
    alpha: float = 0.05,
    allow_unavailable: bool = False,
    evidence_context: dict | None = None,
    claim_text: str | None = None,
) -> dict:
    cs = gap_cs(a, C, alpha=alpha, allow_unavailable=allow_unavailable)
    latest = cs.get("latest", {})
    lo = latest.get("lo")
    hi = latest.get("hi")
    cs_threshold_passed = bool(cs.get("available") and lo is not None and lo > delta_threshold)
    provisional = {
        "certified": cs_threshold_passed,
        "lower_bound": lo,
        "upper_bound": hi,
        "threshold": delta_threshold,
        "alpha": alpha,
        "confidence_sequence": cs,
    }
    default_claim_text = (
        f"Under the configured item order and anytime-valid CS, the intervention-consistency "
        f"gap lower bound exceeds {delta_threshold} at alpha={alpha} for this run."
    )
    gate_errors = validate_certified_claim_eligibility(
        provisional,
        claim_text=claim_text or default_claim_text,
        evidence_context=evidence_context,
        threshold=delta_threshold,
    )
    certified = cs_threshold_passed and not gate_errors
    statement = (
        default_claim_text
        if certified
        else "No certified intervention-consistency gap claim is available for this run."
    )
    return {
        "certified": certified,
        "cs_threshold_passed": cs_threshold_passed,
        "lower_bound": lo,
        "upper_bound": hi,
        "threshold": delta_threshold,
        "alpha": alpha,
        "confidence_sequence": cs,
        "certification_gate_errors": gate_errors,
        "statement": statement,
        "safe_claim": statement if certified else "Not certified; report descriptive smoke metrics only.",
    }
