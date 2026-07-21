"""Tests for the V3 final pre-real-run audit (prompt 19)."""

from __future__ import annotations

import json
import sys

from certvic.v3 import final_pre_real_run_audit as fa


def test_audit_passes_on_real_repo():
    result = fa.run_final_audit()
    assert result["passed"] is True, result["blockers"]
    assert result["n_passed"] == result["n_checks"]
    assert result["evidence_claims_made"] is False
    assert result["vlm_inference_run"] is False


def test_all_modules_import_check():
    result = fa.run_final_audit()
    mod_check = next(c for c in result["checks"] if c["name"] == "v3_modules_import")
    assert mod_check["passed"] is True
    assert mod_check["checked"] == len(fa.V3_COMMAND_MODULES)


def test_no_fake_results_and_guard_pass():
    result = fa.run_final_audit()
    by_name = {c["name"]: c for c in result["checks"]}
    assert by_name["no_fake_paper_results"]["passed"] is True
    assert by_name["paper_number_guard_passes"]["passed"] is True
    assert by_name["no_paid_providers"]["passed"] is True
    assert by_name["non_evidence_statuses_blocked"]["passed"] is True


def test_composed_audits_pass():
    result = fa.run_final_audit()
    by_name = {c["name"]: c for c in result["checks"]}
    assert by_name["security_privacy_audit_passes"]["passed"] is True
    assert by_name["reproduction_scripts_audit_passes"]["passed"] is True
    assert by_name["v2_full_audit_passes"]["passed"] is True
    assert by_name["related_work_no_fabrication"]["passed"] is True


def test_guidance_says_stop_building_when_passed():
    result = fa.run_final_audit()
    assert "STOP building" in result["guidance"]
    assert "run_tiny_pilot" in result["next_real_run_command"]


def test_blocker_path_guidance(tmp_path):
    # Empty repo root -> modules still import (installed pkg) but docs missing -> fail.
    result = fa.run_final_audit(repo_root=str(tmp_path))
    assert result["passed"] is False
    assert "DO NOT start real runs" in result["guidance"]
    assert result["blockers"]


def test_cli_writes_report_and_json(tmp_path):
    out = tmp_path / "report.md"
    js = tmp_path / "audit.json"
    fa.main(["--out", str(out), "--json-out", str(js)])  # passes -> no SystemExit
    assert out.exists() and js.exists()
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["passed"] is True
    assert "V3 Final Pre-Real-Run Audit" in out.read_text(encoding="utf-8")


def test_report_renders_next_command():
    result = fa.run_final_audit()
    md = fa.render_report(result)
    assert "Next real-run command" in md
    assert "main_study_dry_run" in md


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
