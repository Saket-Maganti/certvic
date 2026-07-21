"""Tests for the V7 post-result reviewer-attack audit."""

from __future__ import annotations

from certvic.v7.post_result_reviewer_attack_audit import run_audit


def test_twelve_attacks_enumerated():
    r = run_audit(".")
    assert r["n_attacks"] == 12
    assert {a["id"] for a in r["attacks"]} == set(range(1, 13))
    assert r["evidence_claims_made"] is False


def test_specificity_is_blocked_high_severity():
    r = run_audit(".")
    a4 = next(a for a in r["attacks"] if a["id"] == 4)
    assert a4["status"] == "blocked"
    assert a4["severity"] == "high"
    assert any("control_irrelevant_report" in e for e in a4["artifact_evidence"])
    assert "gate did not pass" in a4["remaining_action"].lower()


def test_cross_model_and_mock_attacks_are_answered():
    r = run_audit(".")
    by = {a["id"]: a for a in r["attacks"]}
    assert by[9]["status"] == "answered"   # reproduced across 3 models
    assert by[11]["status"] == "answered"  # old reports mock-labeled / excluded
    assert by[10]["status"] == "answered"  # optional-stopping controlled
    # answered attacks must actually point at existing artifacts
    assert by[9]["artifact_evidence"]


def test_top_unresolved_leads_with_high_severity_blocker():
    r = run_audit(".")
    assert r["top_unresolved"], "there should be unresolved attacks"
    top = r["top_unresolved"][0]
    assert top["severity"] == "high"
    assert top["id"] == 4  # specificity


def test_status_is_artifact_driven_no_fabrication():
    r = run_audit(".")
    # Nothing is marked answered for arms whose predictions don't exist yet.
    by = {a["id"]: a for a in r["attacks"]}
    assert by[5]["status"] != "answered"  # second domain not executed
    assert by[6]["status"] != "answered"  # two-rater IAA not done
    assert by[7]["status"] != "answered"  # scale not executed
