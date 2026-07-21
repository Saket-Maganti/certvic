"""Tests for the V7 post-3-model final audit + stop conditions."""

from __future__ import annotations

from certvic.v7.v7_post3model_final_audit import (
    BUILD_IF_BLOCKED, DO_NOT_DO, RUN_NOW, WRITE_NOW, run_audit,
)


def test_ten_categories_present():
    r = run_audit(".")
    cats = {c["category"] for c in r["categories"]}
    assert len(cats) == 10
    for expected in ("canonical_result_artifacts", "multi_model_replication", "control_status",
                     "human_review_iaa", "scale_readiness", "second_domain_readiness",
                     "mechanism_probes", "statistical_validity", "paper_report_language",
                     "release_privacy_security"):
        assert expected in cats


def test_passing_categories_and_blocked_control():
    r = run_audit(".")
    st = r["category_status"]
    assert st["canonical_result_artifacts"] == "pass"
    assert st["multi_model_replication"] == "partial"
    assert st["statistical_validity"] == "pass"
    assert st["paper_report_language"] == "pass"
    assert st["control_status"] == "blocked"  # observed raw failure; human/confirmatory gate incomplete


def test_paper_grade_not_ready_is_harsh():
    r = run_audit(".")
    assert r["paper_grade_ready"] is False
    gate = r["paper_grade_gate"]
    assert gate["control_pass"] is False  # failed specificity gate -> cannot be paper-grade


def test_stop_build_policy_verdicts():
    r = run_audit(".")
    by_task = {s["task"]: s["verdict"] for s in r["stop_build_policy"]}
    assert by_task["More generic V7+ infrastructure"] == DO_NOT_DO
    assert by_task["Spurious-flip / control_irrelevant predictions + integration"] == RUN_NOW
    assert by_task["Paper pilot result + limitations section"] == WRITE_NOW
    assert by_task["More models beyond 3"] == BUILD_IF_BLOCKED


def test_next_action_is_specificity_control():
    r = run_audit(".")
    nxt = r["next_highest_leverage_action"].lower()
    assert "spurious" in nxt or "specificity" in nxt
    assert r["evidence_claims_made"] is False
