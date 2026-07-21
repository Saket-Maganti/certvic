"""Tests for the V3 failure-mode playbooks + diagnosis (prompt 17)."""

from __future__ import annotations

import sys
from pathlib import Path

from certvic.io import write_json
from certvic.playbooks import diagnose_failure


def test_all_playbook_docs_exist():
    pb = Path("docs/playbooks")
    for _title, fname in diagnose_failure.PLAYBOOKS.values():
        assert (pb / fname).exists(), fname
    assert (pb / "README.md").exists()


def test_no_report_present(tmp_path):
    result = diagnose_failure.diagnose(str(tmp_path))
    assert result["report_present"] is False
    assert result["healthy"] is False
    md = diagnose_failure.render_report(result)
    assert "No report artifacts found" in md


def test_healthy_report_no_symptoms(tmp_path):
    write_json(tmp_path / "summary.json", {
        "overall": {"original_accuracy": 0.9, "spurious_flip_rate": 0.0, "parse_failure_rate": 0.0,
                    "intervention_consistency_gap": 0.3, "consistency_rate": 0.6},
    })
    write_json(tmp_path / "claim_ledger.json", [{"claim_id": "c1", "certification_status": "certified", "safe": True}])
    result = diagnose_failure.diagnose(str(tmp_path))
    assert result["n_symptoms"] == 0
    assert result["healthy"] is True


def test_detects_low_quality_pass(tmp_path):
    write_json(tmp_path / "edit_generation_summary.json", {"quality_passed": 2, "quality_failed": 8, "generated": 10})
    result = diagnose_failure.diagnose(str(tmp_path))
    symptoms = {s["symptom"] for s in result["symptoms"]}
    assert "low_quality_pass" in symptoms
    pb = {s["symptom"]: s["playbook"] for s in result["symptoms"]}
    assert pb["low_quality_pass"].endswith("EDIT_REALISM_FAILURE.md")


def test_detects_high_detectability(tmp_path):
    write_json(tmp_path / "detectability_summary.json", {"classifier": {"auc": 0.97}, "artifact_risk": True})
    result = diagnose_failure.diagnose(str(tmp_path))
    assert "high_detectability" in {s["symptom"] for s in result["symptoms"]}


def test_detects_high_parse_failure(tmp_path):
    write_json(tmp_path / "triage_summary.json", {"provider_stats": [{"parse_ok_rate": 0.5}]})
    result = diagnose_failure.diagnose(str(tmp_path))
    assert "high_parse_failure" in {s["symptom"] for s in result["symptoms"]}


def test_detects_control_flip_and_low_accuracy(tmp_path):
    write_json(tmp_path / "summary.json", {
        "overall": {"original_accuracy": 0.4, "spurious_flip_rate": 0.5},
    })
    result = diagnose_failure.diagnose(str(tmp_path))
    symptoms = {s["symptom"] for s in result["symptoms"]}
    assert "high_control_flip" in symptoms
    assert "low_original_accuracy" in symptoms


def test_detects_gpu_preflight_failure(tmp_path):
    write_json(tmp_path / "vlm_preflight.json", {"ready": False, "blocking_failures": ["local_weights_present"]})
    result = diagnose_failure.diagnose(str(tmp_path))
    assert "gpu_preflight_failure" in {s["symptom"] for s in result["symptoms"]}


def test_no_certified_gap_when_summary_but_no_certified_claim(tmp_path):
    write_json(tmp_path / "summary.json", {"overall": {"original_accuracy": 0.9, "spurious_flip_rate": 0.0}})
    result = diagnose_failure.diagnose(str(tmp_path))
    assert "no_certified_gap" in {s["symptom"] for s in result["symptoms"]}


def test_report_lists_all_playbooks(tmp_path):
    result = diagnose_failure.diagnose(str(tmp_path))
    md = diagnose_failure.render_report(result)
    assert "All playbooks" in md
    assert "EDIT_REALISM_FAILURE.md" in md


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
