"""Regression tests for the V8 post-newruns upgrade artifacts."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from certvic.v7.spurious_control_integration import check_readiness, integrate

ROOT = Path(__file__).resolve().parents[1]
V8 = ROOT / "data/results/main_real_200/v8_upgrade"
PROVIDERS = {"qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"}
RUNS = {"spurious", "perception_scaled", "polarity", "mechanism"}


def test_build_v8_upgrade_is_idempotent_and_result_nonproducing():
    proc = subprocess.run(
        [sys.executable, "scripts/build_v8_upgrade.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    assert summary["status"] == "complete"
    assert summary["produced_model_results_by_this_script"] is False
    assert summary["spurious_all_provider_gate_pass"] is False


def test_canonical_prediction_manifest_has_all_expected_real_outputs():
    manifest = json.loads((V8 / "canonical_prediction_manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["paper_evidence"] is False
    assert manifest["produced_model_results_by_this_script"] is False
    assert set(manifest["entries"]) == {f"{p}__{r}" for p in PROVIDERS for r in RUNS}
    for entry in manifest["entries"].values():
        assert entry["status"] == "complete"
        assert entry["validation"]["row_count_ok"] is True
        assert entry["validation"]["provider_ok"] is True
        assert entry["validation"]["n_duplicate_ids"] == 0
    qwen_pol = manifest["entries"]["qwen2_5_vl_7b__polarity"]
    assert qwen_pol["source_kind"] == "zip_member"
    assert qwen_pol["validation"]["n_rows"] == 728


def test_spurious_gate_is_answered_but_failed_for_qwen_only():
    report = json.loads((V8 / "spurious_specificity_control_report.json").read_text())
    assert report["status"] == "blocked_failed_gate"
    assert report["paper_evidence"] is False
    assert report["all_provider_gate_pass"] is False
    assert report["providers"]["qwen2_5_vl_7b"]["spurious_flip_rate"] == 0.1277
    assert report["providers"]["qwen2_5_vl_7b"]["gate_pass"] is False
    assert report["providers"]["internvl_8b"]["gate_pass"] is True
    assert report["providers"]["llava_onevision_7b"]["gate_pass"] is True
    detect = report["detectability_quality"]["json_reports"][0]["data"]
    assert detect["n_items"] == 94
    assert detect["n_skipped"] == 0
    assert detect["artifact_risk"] is False


def test_v7_spurious_integration_uses_real_predictions_without_promoting_evidence():
    readiness = check_readiness(ROOT)
    assert readiness["ready"] is False
    assert readiness["present"]["quality_detectability_report"] is True
    assert all(readiness["present"]["predictions_per_provider"].values())
    assert readiness["present"]["human_visual_review_complete"] is False
    status = integrate(ROOT)
    assert status["status"] == "blocked"
    assert status["specificity_status"] == "blocked"
    assert status["paper_evidence"] is False
    assert any("human visual review" in item for item in status["missing"])


def test_scaled_polarity_and_mechanism_reports_are_complete_but_non_evidence():
    scaled = json.loads((V8 / "scaled_perception_control_report.json").read_text())
    polarity = json.loads((V8 / "polarity_ablation_report.json").read_text())
    mechanism = json.loads((V8 / "mechanism_probe_report.json").read_text())
    assert scaled["status"] == "complete"
    assert all(scaled["providers"][p]["n"] == 369 for p in PROVIDERS)
    assert polarity["status"] == "complete"
    assert polarity["schema"] == "certvic.v8.polarity_ablation_report.v2"
    assert polarity["task_manifest_audit"]["valid"] is True
    assert all(polarity["providers"][p]["n_rows"] == 728 for p in PROVIDERS)
    assert all(polarity["providers"][p]["gold_source"] == "current_task_manifest" for p in PROVIDERS)
    assert all(polarity["providers"][p]["n_missing_task_gold"] == 0 for p in PROVIDERS)
    assert all(polarity["providers"][p]["raw_metadata_gold_mismatches"] > 0 for p in PROVIDERS)
    assert polarity["providers"]["qwen2_5_vl_7b"]["families"]["positive"]["row_accuracy"] == 0.6154
    assert polarity["providers"]["qwen2_5_vl_7b"]["families"]["negative"]["row_accuracy"] == 0.544
    assert mechanism["status"] == "complete"
    assert all(mechanism["providers"][p]["n_rows"] == 364 for p in PROVIDERS)
    assert "original_vs_edited" in mechanism["spec_blocked_families_excluded"]
    assert not any(x["paper_evidence"] for x in (scaled, polarity, mechanism))


def test_v8_human_exports_are_blank_and_portable():
    for path in [
        ROOT / "data/annotations/v8_residual_cue_audit/residual_cue_audit_sheet.csv",
        ROOT / "data/annotations/v8_second_rater_iaa/second_rater_review_sheet.csv",
    ]:
        text = path.read_text()
        assert "/Users/" not in text
        rows = list(csv.DictReader(text.splitlines()))
        assert rows
        human_cols = [c for c in rows[0] if c in {"notes", "reviewer_id", "keep_for_eval", "residual_target_visible"}]
        assert human_cols
        assert all(row[col] == "" for row in rows for col in human_cols)


def test_v8_final_policy_and_task_ledger_keep_scale_blocked():
    handoff = json.loads((V8 / "v8_final_handoff.json").read_text())
    scorecard = json.loads((V8 / "CVPR_READINESS_SCORECARD_V8.json").read_text())
    ledger = json.loads((V8 / "v8_task_ledger.json").read_text())
    assert handoff["produced_model_results_by_this_script"] is False
    assert handoff["ingested_existing_kaggle_predictions"] is True
    assert handoff["spurious_control_ready"] is False
    assert scorecard["ready"] is False
    assert "spurious specificity gate failed" in scorecard["blocking_conditions"]
    assert {t["id"] for t in ledger["tasks"]} == {f"V8_{i:02d}" for i in range(23)}
    assert all(t["paper_evidence"] is False for t in ledger["tasks"])
