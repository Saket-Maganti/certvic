"""Tests for the V2 baseline audit."""

from __future__ import annotations

from pathlib import Path


from certvic.v2 import baseline_audit


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_baseline_audit_passes_on_repo():
    result = baseline_audit.run_baseline_audit(REPO_ROOT)
    assert result["passed"], _failed_checks(result)
    assert result["n_passed"] == result["n_checks"]
    assert result["evidence_claims_made"] is False
    assert result["downloads_attempted"] is False
    assert result["gpu_required"] is False


def test_all_expected_checks_present():
    result = baseline_audit.run_baseline_audit(REPO_ROOT)
    names = {check["name"] for check in result["checks"]}
    assert {
        "handoff_docs_exist",
        "core_command_modules_import",
        "schema_modules_import",
        "core_configs_exist",
        "no_paid_providers_enabled_by_default",
        "v1_5_non_evidence_statuses_recognized",
        "paper_contains_no_fake_results",
        "zero_cost_policy_exists",
        "no_forbidden_claim_phrases",
    } <= names


def test_missing_handoff_doc_fails(tmp_path):
    # An empty repo root must fail handoff/doc/config checks rather than pass silently.
    result = baseline_audit.run_baseline_audit(tmp_path)
    assert result["passed"] is False
    handoff = _check_by_name(result, "handoff_docs_exist")
    assert handoff["passed"] is False
    assert len(handoff["missing"]) == len(baseline_audit.HANDOFF_DOCS)


def test_paid_provider_names_empty_invariant():
    # The whole zero-cost story depends on this set staying empty.
    assert baseline_audit.PAID_PROVIDER_NAMES == set()
    result = baseline_audit.run_baseline_audit(REPO_ROOT)
    assert _check_by_name(result, "no_paid_providers_enabled_by_default")["passed"] is True


def test_config_enabling_paid_services_is_caught(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir()
    (cfg_dir / "smoke.yaml").write_text("paid_services_enabled: true\n", encoding="utf-8")
    monkeypatch.setattr(baseline_audit, "CORE_CONFIGS", ["configs/smoke.yaml"])
    check = baseline_audit._paid_providers_check(tmp_path)
    assert check["passed"] is False
    assert any("paid services" in err for err in check["errors"])


def test_forbidden_phrase_in_doc_is_caught(tmp_path, monkeypatch):
    doc = tmp_path / "paper" / "main.tex"
    doc.parent.mkdir(parents=True)
    doc.write_text("We show that all vlms fail catastrophically.", encoding="utf-8")
    monkeypatch.setattr(baseline_audit, "PAPER_AND_RESULT_DOCS", ["paper/main.tex"])
    check = baseline_audit._forbidden_claims_check(tmp_path)
    assert check["passed"] is False
    assert check["hits"]


def test_render_report_contains_status():
    result = baseline_audit.run_baseline_audit(REPO_ROOT)
    report = baseline_audit.render_report(result)
    assert "V2 Baseline Audit Report" in report
    assert "PASS" in report
    assert "02_V2_VISUAL_REVIEW_AND_APPROVAL_WORKFLOW" in report


def test_cli_writes_report(tmp_path):
    out = tmp_path / "report.md"
    json_out = tmp_path / "report.json"
    baseline_audit.main(["--out", str(out), "--json-out", str(json_out)])
    assert out.exists()
    assert json_out.exists()
    assert "V2 Baseline Audit Report" in out.read_text(encoding="utf-8")


def _check_by_name(result: dict, name: str) -> dict:
    return next(check for check in result["checks"] if check["name"] == name)


def _failed_checks(result: dict) -> str:
    return "; ".join(
        f"{check['name']}: {check.get('errors') or check.get('missing') or check}"
        for check in result["checks"]
        if not check["passed"]
    )
