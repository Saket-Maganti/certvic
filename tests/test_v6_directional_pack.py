"""Tests for the V6 directional-correction pack."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from certvic.commands.generate_real_run_commands import write_command_bundle
from certvic.io import write_json, write_jsonl
from certvic.paper.identity_audit import audit_identity
from certvic.reporting.naive_vs_validity_gated import compare as compare_naive_valid
from certvic.review.cvpr_bar_checker import check_bar
from certvic.validity.filter_scores import filter_scores
from certvic.validity.load_bearing import analyze_load_bearing
from certvic.validation.detectability_gate import evaluate_gate
from certvic.validation.directional_language_guard import scan_directional_language
from certvic.v6.final_directional_audit import run_audit as run_v6_audit


def _scores(path: Path) -> Path:
    write_jsonl(
        path,
        [
            {
                "run_id": "r",
                "item_id": "i1",
                "provider_name": "mock",
                "model_name": "mock",
                "task_family": "support",
                "domain": "fixture",
                "original_correct": True,
                "edited_correct": False,
                "consistent": False,
                "required_change": "change",
                "parse_ok": True,
                "metadata": {"evidence_status": "MOCK_ONLY"},
            },
            {
                "run_id": "r",
                "item_id": "i2",
                "provider_name": "mock",
                "model_name": "mock",
                "task_family": "support",
                "domain": "fixture",
                "original_correct": True,
                "edited_correct": True,
                "consistent": True,
                "required_change": "change",
                "parse_ok": True,
                "metadata": {"evidence_status": "MOCK_ONLY"},
            },
        ],
    )
    return path


def _certs(path: Path) -> Path:
    write_jsonl(
        path,
        [
            {
                "item_id": "i1",
                "quality_gate_status": "pass",
                "detectability_status": "fail",
                "visual_review_status": "pass",
                "human_answerability_status": "pass",
                "single_factor_status": "pass",
                "photorealism_status": "pass",
                "leakage_status": "pass",
                "evidence_eligible_candidate": False,
                "blocking_reasons": ["detectability_status:fail"],
                "warnings": [],
            },
            {
                "item_id": "i2",
                "quality_gate_status": "pass",
                "detectability_status": "pass",
                "visual_review_status": "pass",
                "human_answerability_status": "pass",
                "single_factor_status": "pass",
                "photorealism_status": "pass",
                "leakage_status": "pass",
                "evidence_eligible_candidate": True,
                "blocking_reasons": [],
                "warnings": [],
            },
        ],
    )
    return path


def test_validity_filter_rejects_missing_or_failed_certificates(tmp_path):
    scores = _scores(tmp_path / "scores.jsonl")
    certs = _certs(tmp_path / "certs.jsonl")
    result = filter_scores(str(scores), str(certs), str(tmp_path / "valid.jsonl"), str(tmp_path / "rejected.jsonl"))
    assert result["n_valid"] == 1
    assert result["n_rejected"] == 1
    rejected = [json.loads(line) for line in (tmp_path / "rejected.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rejected[0]["metadata"]["validity_filter"]["rejection_reasons"]


def test_load_bearing_analysis_detects_gap_shift_and_blocks_claims(tmp_path):
    scores = _scores(tmp_path / "scores.jsonl")
    certs = _certs(tmp_path / "certs.jsonl")
    result = analyze_load_bearing(str(scores), str(certs), material_gap_shift=0.01)
    assert result["certificate_is_load_bearing"] is True
    assert result["analysis_status"] == "NON_EVIDENCE_ANALYSIS_ONLY"
    assert result["stages"][0]["intervention_consistency_gap"] != result["stages"][-1]["intervention_consistency_gap"]


def test_naive_vs_validity_gated_summarizes_rejections(tmp_path):
    scores = _scores(tmp_path / "scores.jsonl")
    certs = _certs(tmp_path / "certs.jsonl")
    filter_scores(str(scores), str(certs), str(tmp_path / "valid.jsonl"), str(tmp_path / "rejected.jsonl"))
    result = compare_naive_valid(str(scores), str(tmp_path / "valid.jsonl"), str(certs))
    assert result["validity_gated"]["n"] == 1
    assert result["rejection_distribution"]["detectability_status:fail"] == 1
    assert result["claim_status"] == "NO_CERTIFIED_CLAIMS_EMITTED"


def test_detectability_gate_thresholds_and_quality_override():
    quality = {"passed": True}
    assert evaluate_gate({"classifier": {"auc": 0.55}, "n_items": 20}, quality)["status"] == "GO"
    assert evaluate_gate({"classifier": {"auc": 0.65}, "n_items": 20}, quality)["status"] == "CONDITIONAL"
    assert evaluate_gate({"classifier": {"auc": 0.90}, "n_items": 20}, quality)["status"] == "NO_GO"
    assert evaluate_gate(None, quality)["status"] == "NO_GO"
    result = evaluate_gate({"classifier": {"auc": 0.55}, "n_items": 20}, {"passed": False})
    assert result["status"] == "NO_GO"
    assert "quality_gate_not_passed" in result["blockers"]


def test_staged_command_bundle_is_guarded(tmp_path):
    manifest = write_command_bundle("tiny_pilot", str(tmp_path / "commands"), staged_only=True)
    text = (tmp_path / "commands" / "commands.sh").read_text(encoding="utf-8")
    assert "Refusing to run all stages" in text
    assert "CERTVIC_RUN_ALL_DANGEROUS_STAGES" in text
    for name in (
        "01_cpu_readiness.sh",
        "02_dry_run_only.sh",
        "03_generate_edits_only.sh",
        "04_detectability_gate_only.sh",
        "05_vlm_eval_only_AFTER_GATES.sh",
    ):
        assert (tmp_path / "commands" / "commands" / "tiny_pilot" / name).exists()
    assert manifest["staged_only"] is True


def test_paper_identity_and_directional_language_pass_current_repo():
    assert audit_identity("paper")["passed"] is True
    assert scan_directional_language(["paper", "docs/V6_FULL_PACK_REPORT.md"])["passed"] is True


def test_cvpr_bar_checker_fails_closed_without_detectability(tmp_path):
    write_json(
        tmp_path / "cvpr_bar_metrics.json",
        {
            "reviewed_item_count": 200,
            "model_count": 3,
            "human_iaa": 0.8,
            "main_figure_present": True,
            "main_table_present": True,
        },
    )
    result = check_bar(str(tmp_path))
    assert result["passed"] is False
    assert result["highest_bar"] == "none"


def test_v6_final_audit_current_repo_shape():
    result = run_v6_audit()
    assert result["downloads_attempted"] is False
    assert result["gpu_jobs_run"] is False
    assert result["vlm_inference_run"] is False


def test_v6_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
