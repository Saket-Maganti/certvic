"""Regression tests for V8.1 Qwen spurious-control forensic artifacts."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from certvic.metrics.certification_policy import DEFAULT_POLICY


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/results/main_real_200/v8_1_qwen_spurious_forensics"


def test_builder_runs_and_preserves_real_qwen_failed_count():
    proc = subprocess.run(
        [sys.executable, "scripts/build_v8_1_qwen_spurious_forensics.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    assert summary["qwen_failed"] == 12
    assert summary["paper_evidence"] is False
    assert summary["geometry_mode"] in {
        "LOCAL_ADE_ANNOTATION_RECOMPUTE",
        "FROZEN_DERIVED_REAL_EVIDENCE_CACHE",
    }
    rows = list(csv.DictReader((OUT / "qwen_spurious_failed_12.csv").open()))
    assert len(rows) == 12
    assert {row["flipped"] for row in rows} == {"True"}
    all_rows = [
        json.loads(line)
        for line in (OUT / "qwen_spurious_all_items.jsonl").read_text().splitlines()
        if line
    ]
    assert len(all_rows) == 94
    assert all(row["target_bbox_xyxy"] is not None for row in all_rows)
    assert all(row["patch_object_bbox_distance_px"] is not None for row in all_rows)


def test_gallery_and_preliminary_labels_are_triage_not_human_validation():
    assert (OUT / "qwen_spurious_failed_12_gallery.html").exists()
    assert (OUT / "qwen_spurious_failed_12_gallery").is_dir()
    labels = json.loads((OUT / "qwen_spurious_failed_12_prelim_labels.json").read_text())
    assert labels["label_authority"] == "CODEX_PRELIMINARY_EVAL"
    assert labels["is_real_human_validation"] is False
    assert labels["human_validation_claimed"] is False
    assert len(labels["labels"]) == 12
    assert all(row["requires_real_human_review"] is True for row in labels["labels"])
    human_claim = (OUT / "human_claim.md").read_text().lower()
    assert "not real human review" in human_claim
    assert "do not replace real human validation" in human_claim


def test_recompute_scenarios_include_raw_and_best_case_with_raw_failure():
    scenarios = json.loads((OUT / "qwen_spurious_recompute_scenarios.json").read_text())["scenarios"]
    by_id = {row["scenario_id"]: row for row in scenarios}
    assert "A_RAW_GATE" in by_id
    assert "F_BEST_CASE_CODEX_PRELIMINARY_EXCLUSION" in by_id
    raw = by_id["A_RAW_GATE"]
    assert raw["n_total"] == 94
    assert raw["n_flips"] == 12
    assert raw["flip_rate"] == 0.1277
    assert raw["gate_pass"] is False
    assert raw["claim_valid"] is True
    assert not any(row["claim_valid"] and row["gate_pass"] for row in scenarios)


def test_threshold_and_paper_evidence_are_not_weakened():
    assert DEFAULT_POLICY["control_spurious_flip_max"] == 0.10
    v8_report = json.loads((ROOT / "data/results/main_real_200/v8_upgrade/spurious_specificity_control_report.json").read_text())
    assert v8_report["paper_evidence"] is False
    assert v8_report["providers"]["qwen2_5_vl_7b"]["gate_threshold"] == 0.1
    assert v8_report["providers"]["qwen2_5_vl_7b"]["gate_pass"] is False
    ledger = json.loads((OUT / "v8_1_task_ledger.json").read_text())
    assert ledger["paper_evidence"] is False
    assert ledger["thresholds"]["control_spurious_flip_max"] == 0.10
    assert all(task["paper_evidence"] is False for task in ledger["tasks"])


def test_claim_safe_summary_blocks_clean_all_model_specificity():
    summary = (OUT / "CLAIM_SAFE_SUMMARY.md").read_text().lower()
    assert "qwen fails" in summary
    assert "clean all-model specificity claim is blocked" in summary
    assert "all models pass specificity" not in summary
    assert "cvpr-ready" not in summary
    assert "paper_evidence=false" in summary


def test_parser_quality_v2_and_go_no_go_artifacts_exist():
    assert (OUT / "parser_provenance_audit.json").exists()
    assert (OUT / "PARSER_PROVENANCE_AUDIT.md").exists()
    assert (OUT / "spurious_control_quality_audit.csv").exists()
    assert (OUT / "SPURIOUS_CONTROL_QUALITY_AUDIT.md").exists()
    assert (OUT / "SPURIOUS_CONTROL_V2_DESIGN.md").exists()
    assert (ROOT / "commands/spurious_v2/build_spurious_v2.sh").exists()
    assert (OUT / "V8_1_GO_NO_GO.md").exists()
    go = json.loads((OUT / "v8_1_go_no_go.json").read_text())
    assert go["main500_should_start_now"] is False
    assert go["paper_evidence"] is False
    assert go["decision"] in {"GO_SPURIOUS_V2_FIRST", "GO_HUMAN_AUDIT_FIRST", "STOP_AND_REFRAME"}


def test_cross_model_comparison_shows_qwen_specific_failed_set():
    rows = list(csv.DictReader((OUT / "qwen_failed_items_cross_model_comparison.csv").open()))
    assert len(rows) == 12
    assert sum(row["only_qwen_flips"] == "True" for row in rows) == 12
    assert sum(row["all_three_flip"] == "True" for row in rows) == 0
