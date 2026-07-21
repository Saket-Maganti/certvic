"""Tests for the V2.5 reviewer attack harness."""

from __future__ import annotations

from certvic.v2.reviewer_attack_harness import (
    ATTACKS,
    render_report,
    run_reviewer_attack_harness,
)


def test_all_blocking_defenses_are_tooling_ready():
    result = run_reviewer_attack_harness()
    assert result["passed"] is True, result["blocking_unready"]
    assert result["blocking_unready"] == []
    assert result["n_blocking_ready"] == result["n_blocking"]


def test_every_attack_has_a_classification():
    for attack in ATTACKS:
        assert attack["kind"] in {"blocking", "enhancement"}
        assert callable(attack["fn"])


def test_optional_stopping_defense_is_live():
    result = run_reviewer_attack_harness()
    row = next(r for r in result["attacks"] if r["id"] == "optional_stopping_invalidates")
    assert row["tooling_ready"] is True
    assert "Type-I" in row["note"]


def test_report_renders():
    text = render_report(run_reviewer_attack_harness())
    assert "Reviewer Attack Harness" in text
    assert "blocking" in text
