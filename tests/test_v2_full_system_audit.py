"""Tests for the V2 full system audit."""

from __future__ import annotations

from pathlib import Path

from certvic.v2 import full_audit

REPO_ROOT = Path(__file__).resolve().parents[1]


def _failed(result):
    return "; ".join(f"{c['name']}: {c.get('errors') or c.get('missing') or c.get('hits')}" for c in result["checks"] if not c["passed"])


def test_full_audit_passes_on_repo():
    result = full_audit.run_full_audit(REPO_ROOT)
    assert result["passed"], _failed(result)
    assert result["n_passed"] == result["n_checks"]
    assert result["vlm_inference_run"] is False


def test_full_audit_has_expected_checks():
    result = full_audit.run_full_audit(REPO_ROOT)
    names = {c["name"] for c in result["checks"]}
    assert {
        "v1_handoffs_exist", "v2_handoffs_exist", "v2_configs_exist", "runbooks_exist",
        "v2_commands_import", "no_paid_provider_enabled", "no_forbidden_claims",
        "no_fake_paper_results", "baseline_audit_passes",
    } <= names


def test_all_v2_command_modules_import():
    result = full_audit.run_full_audit(REPO_ROOT)
    cmd = next(c for c in result["checks"] if c["name"] == "v2_commands_import")
    assert cmd["passed"], cmd.get("errors")


def test_empty_repo_fails(tmp_path):
    result = full_audit.run_full_audit(tmp_path)
    assert result["passed"] is False


def test_render_report():
    result = full_audit.run_full_audit(REPO_ROOT)
    report = full_audit.render_report(result)
    assert "V2 Full System Audit Report" in report
    assert "PASS" in report
