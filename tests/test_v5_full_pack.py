"""Integration tests for the V5 final infrastructure pack."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from certvic.analysis.analysis_plan_lock import build_analysis_plan_lock
from certvic.analysis.preregistration import validate_analysis_plan
from certvic.cards.eval_card import build_eval_card
from certvic.cards.model_card import build_model_card
from certvic.contracts.result_contracts import validate_contracts
from certvic.experiments.registry import validate_registry
from certvic.paper.ethics_audit import audit_ethics
from certvic.paper.figure_manifest_audit import audit_figure_manifest
from certvic.paper.result_free_completeness_audit import audit_result_free_paper
from certvic.paper.table_manifest_audit import audit_table_manifest
from certvic.paper.theory_audit import audit_theory
from certvic.planning.deadline_plan import build_critical_path
from certvic.reporting.ablation_interpreter import interpret_ablation_report
from certvic.reporting.certification_interpreter import interpret_certification
from certvic.reporting.edit_realism_scorecard import build_scorecard
from certvic.review.response_bank import TOPICS, write_response_bank
from certvic.review.score_simulator import simulate_scores
from certvic.submission.package_plan import build_package_plan
from certvic.validity.item_certificate import build_certificates
from certvic.validation.answerability import write_answerability_sheet
from certvic.validation.claim_language_guard import scan_claim_language
from certvic.validation.edit_realism_rubric import RUBRIC_FIELDS
from certvic.validation.rater_calibration import calibrate_raters
from certvic.validation.rater_training import write_rater_training
from certvic.v5.all_commands_smoke import run_smoke
from certvic.v5.cvpr_ready_except_results_audit import run_audit


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def test_v5_item_certificates_are_deterministic_and_block_failures(tmp_path):
    tasks = tmp_path / "tasks.jsonl"
    edits = tmp_path / "edits.jsonl"
    review = tmp_path / "review.json"
    _jsonl(
        tasks,
        [
            {
                "item_id": "i1",
                "source_id": "s1",
                "edit_id": "e1",
                "task_family": "support_stability",
                "domain": "household",
                "metadata": {"leakage_status": "pass", "detectability_status": "pass"},
            },
            {
                "item_id": "i2",
                "source_id": "s2",
                "edit_id": "e2",
                "task_family": "support_stability",
                "domain": "household",
                "metadata": {"leakage_status": "fail"},
            },
        ],
    )
    _jsonl(edits, [{"edit_id": "e1", "quality_gate_status": "pass"}, {"edit_id": "e2", "quality_gate_status": "fail"}])
    review.write_text(
        json.dumps(
            {
                "items": [
                    {"item_id": "i1", "visual_review_status": "pass", "human_answerability_status": "pass", "single_factor_status": "pass", "photorealism_status": "pass"},
                    {"item_id": "i2", "visual_review_status": "pass", "human_answerability_status": "pass", "single_factor_status": "pass", "photorealism_status": "pass"},
                ]
            }
        ),
        encoding="utf-8",
    )
    first = build_certificates(str(tasks), str(edits), str(review), str(tmp_path / "certs.jsonl"), str(tmp_path / "report"))
    content_1 = (tmp_path / "certs.jsonl").read_text(encoding="utf-8")
    build_certificates(str(tasks), str(edits), str(review), str(tmp_path / "certs.jsonl"), str(tmp_path / "report"))
    content_2 = (tmp_path / "certs.jsonl").read_text(encoding="utf-8")
    assert first["n_candidate_eligible"] == 1
    assert "quality_gate_status:fail" in first["blocking_reasons"]
    assert content_1 == content_2


def test_v5_analysis_plan_lock_and_theory_paper_audits(tmp_path):
    result = build_analysis_plan_lock("configs/certification_policy.yaml", str(tmp_path / "lock.md"), str(tmp_path / "lock.json"))
    assert result["passed"] is True
    assert result["analysis_plan_hash"]
    bad_plan = {"primary_estimand": "exploratory subgroup", "frozen_before_results": False}
    assert validate_analysis_plan(bad_plan)
    assert audit_theory("paper")["passed"] is True
    assert audit_result_free_paper("paper")["passed"] is True
    assert audit_ethics("paper")["passed"] is True


def test_v5_rater_training_calibration_realism_and_answerability(tmp_path):
    assert write_rater_training(str(tmp_path / "training"))["guide_generated"] is True
    ratings = tmp_path / "ratings.csv"
    gold = tmp_path / "gold.csv"
    with ratings.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id", "reviewer_id", "single_factor_valid", *RUBRIC_FIELDS])
        writer.writeheader()
        writer.writerow({"item_id": "i1", "reviewer_id": "r1", "single_factor_valid": "yes", **{field: "pass" for field in RUBRIC_FIELDS}})
        writer.writerow({"item_id": "i2", "reviewer_id": "r1", "single_factor_valid": "no", **{field: "uncertain" for field in RUBRIC_FIELDS}})
    with gold.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id", "gold_single_factor_valid"])
        writer.writeheader()
        writer.writerow({"item_id": "i1", "gold_single_factor_valid": "yes"})
        writer.writerow({"item_id": "i2", "gold_single_factor_valid": "yes"})
    calibration = calibrate_raters(str(ratings), str(gold), str(tmp_path / "cal"))
    scorecard = build_scorecard(str(ratings), str(tmp_path / "scorecard"))
    assert calibration["low_calibration_raters"] == ["r1"]
    assert scorecard["item_status"]["i2"]["uncertain_heavy"] is True
    tasks = tmp_path / "tasks.jsonl"
    _jsonl(tasks, [{"item_id": "i1"}])
    sheet = write_answerability_sheet(str(tasks), str(tmp_path / "answerability.csv"))
    assert sheet["contains_model_outputs"] is False


def test_v5_cards_registry_contracts_claim_guard_and_review_sim(tmp_path):
    assert build_model_card("qwen2_5_vl_7b")["missing_license_flagged"] is True
    assert build_model_card("unknown_provider")["unknown_provider_flagged"] is True
    assert build_eval_card(str(tmp_path / "missing"))["claim_status"] == "incomplete_eval_card_no_evidence"
    assert validate_registry("configs/experiments.yaml")["passed"] is True
    contracts = validate_contracts("configs/result_contracts.yaml", "data/results")
    assert contracts["passed"] is False  # smoke contracts are explicitly not evidence.
    safe_doc = tmp_path / "safe.md"
    safe_doc.write_text("CertVIC reports controlled intervention consistency with RESULT REQUIRED placeholders.", encoding="utf-8")
    bad_doc = tmp_path / "bad.md"
    bad_doc.write_text("This first to prove claim is not allowed.", encoding="utf-8")
    assert scan_claim_language([str(safe_doc)])["passed"] is True
    assert scan_claim_language([str(bad_doc)])["passed"] is False
    sim = simulate_scores("paper", "data/results", str(tmp_path / "scores"))
    assert sim["scores"]["empirical_strength"] == 1
    assert "empirical results missing" in sim["fatal_weaknesses"]


def test_v5_manifests_response_interpreters_package_and_deadline(tmp_path):
    assert audit_figure_manifest("paper/figure_manifest.yaml", "paper")["passed"] is True
    assert audit_table_manifest("paper/table_manifest.yaml")["passed"] is True
    bank = write_response_bank(str(tmp_path / "responses.md"))
    assert set(bank["topics"]) == set(TOPICS)
    ablation = tmp_path / "ablation.json"
    ablation.write_text(json.dumps({"text_only_rate": 0.9, "control_spurious_flip_rate": 0.2}), encoding="utf-8")
    assert interpret_ablation_report(str(ablation))["claims_blocked"] is True
    cert = tmp_path / "cert.json"
    ledger = tmp_path / "ledger.json"
    cert.write_text(json.dumps({"confidence_sequence": {"available": False}, "bootstrap_only": True}), encoding="utf-8")
    ledger.write_text(json.dumps({"entries": [{"evidence_status": "MOCK_ONLY"}]}), encoding="utf-8")
    assert interpret_certification(str(cert), str(ledger))["eligible"] is False
    package = build_package_plan("paper", str(tmp_path / "package"))
    deadline = build_critical_path("2026-11-15")
    assert "model/eval cards" in package["components"]
    assert deadline["buffer_days"] >= 0


def test_v5_audit_prompt_pack_and_smoke_harness():
    prompt_dir = Path("docs/audit_prompts")
    prompts = sorted(prompt_dir.glob("[0-9][0-9]_*.md"))
    assert len(prompts) == 10
    for prompt in prompts:
        text = prompt.read_text(encoding="utf-8")
        assert "Do not fabricate evidence" in text
        assert "Expected output" in text
    smoke = run_smoke("data/results/v5_test_smoke.json")
    assert smoke["passed"] is True
    assert smoke["skipped_unsafe"]


def test_v5_cvpr_ready_audit_current_repo_shape():
    result = run_audit()
    assert result["downloads_attempted"] is False
    assert result["gpu_required"] is False
    assert result["vlm_inference_run"] is False


def test_v5_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
