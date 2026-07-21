import pytest

from certvic.validation.claims import validate_certified_claim_eligibility, validate_claim_text


def test_claim_validation_catches_forbidden():
    assert validate_claim_text("This proves causal understanding.")


@pytest.mark.parametrize(
    "status",
    [
        "MACHINE_ASSISTED_PRELIMINARY",
        "HUMAN_REVIEW_PENDING",
        "PLANNED_NOT_EXECUTED",
        "SYNTHETIC_TEST_FIXTURE",
        "DIAGNOSTIC_ONLY",
        "DEPRECATED_OR_STALE",
        "UNKNOWN_REQUIRES_AUDIT",
        "UNKNOWN",
    ],
)
def test_mandated_non_evidence_classes_block_certified_claims(status):
    errors = validate_certified_claim_eligibility(
        {
            "confidence_sequence": {"available": True, "latest": {"lo": 0.2}},
            "lower_bound": 0.2,
        },
        claim_text="Bounded result for this run.",
        evidence_context={
            "splits": ["validation"],
            "evidence_statuses": [status],
            "provider_types": ["open_local"],
        },
    )
    assert any(status in error for error in errors)
