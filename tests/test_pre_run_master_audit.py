"""Tests for the V2.7 pre-run master audit."""

from __future__ import annotations

from certvic.v2.pre_run_master_audit import render_report, run_pre_run_master_audit


def test_master_audit_clears_when_all_components_pass():
    result = run_pre_run_master_audit(validity_trials=400, validity_n=150)
    assert result["passed"] is True, [c for c in result["components"] if not c["passed"]]
    assert result["cleared_for_real_runs"] is True
    component_names = {c["component"] for c in result["components"]}
    assert {
        "v2_full_system_audit",
        "reviewer_attack_harness",
        "paper_numbers_guard",
        "anytime_validity_lab",
    } <= component_names


def test_master_audit_no_models_or_downloads():
    result = run_pre_run_master_audit(validity_trials=400, validity_n=150)
    assert result["evidence_claims_made"] is False
    assert result["downloads_attempted"] is False
    assert result["vlm_inference_run"] is False


def test_master_audit_report_renders():
    text = render_report(run_pre_run_master_audit(validity_trials=400, validity_n=150))
    assert "Pre-Run Master Audit" in text
    assert "real runs" in text
