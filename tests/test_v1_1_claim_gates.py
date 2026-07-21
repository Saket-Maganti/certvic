from __future__ import annotations

from certvic.metrics.certification import certify_gap
from certvic.validation.claims import validate_certified_claim_eligibility


def _certification(lower=0.10, available=True):
    return {
        "confidence_sequence": {"available": available, "latest": {"lo": lower, "hi": 0.50}},
        "lower_bound": lower,
        "upper_bound": 0.50,
    }


def _context(**overrides):
    base = {
        "splits": ["pilot"],
        "evidence_statuses": ["REAL_PILOT"],
        "provider_types": ["open_local"],
        "has_synthetic_smoke_fixtures": False,
    }
    base.update(overrides)
    return base


def _errors(certification=None, context=None, claim_text="A narrow certified gap claim."):
    return validate_certified_claim_eligibility(
        certification or _certification(),
        claim_text=claim_text,
        evidence_context=context or _context(),
        threshold=0.05,
    )


def test_claim_gate_allows_only_valid_non_smoke_context():
    assert _errors() == []


def test_claim_gate_blocks_smoke_split():
    assert any("split is smoke" in err for err in _errors(context=_context(splits=["smoke"])))


def test_claim_gate_blocks_mock_only_evidence_status():
    assert any(
        "MOCK_ONLY" in err
        for err in _errors(context=_context(evidence_statuses=["MOCK_ONLY"]))
    )


def test_claim_gate_blocks_mock_provider_type():
    assert any("provider_type is mock" in err for err in _errors(context=_context(provider_types=["mock"])))


def test_claim_gate_blocks_synthetic_smoke_fixtures():
    assert any(
        "synthetic smoke fixtures" in err
        for err in _errors(context=_context(has_synthetic_smoke_fixtures=True))
    )


def test_claim_gate_blocks_unavailable_cs():
    assert any("CS unavailable" in err for err in _errors(certification=_certification(available=False)))


def test_claim_gate_blocks_lower_bound_below_threshold():
    assert any("does not exceed threshold" in err for err in _errors(certification=_certification(lower=0.01)))


def test_claim_gate_blocks_forbidden_wording():
    assert any("forbidden claim phrase" in err for err in _errors(claim_text="All VLMs fail."))


def test_certify_gap_without_evidence_context_is_not_certified():
    result = certify_gap([1, 1], [0, 0], allow_unavailable=True)
    assert not result["certified"]
    assert result["certification_gate_errors"]
