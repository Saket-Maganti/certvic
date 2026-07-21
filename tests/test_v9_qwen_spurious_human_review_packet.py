from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data/annotations/v9_qwen_spurious_human_review"
V9 = ROOT / "data/results/main_real_200/v9_mega_upgrade"


def test_review_sheet_exists_with_blank_human_columns():
    sheet = ANN / "qwen_failed_12_human_review.csv"
    assert sheet.exists()
    rows = list(csv.DictReader(sheet.open()))
    assert len(rows) == 12
    human_cols = [
        "human_valid_control",
        "human_failure_cause",
        "human_notes",
        "human_reviewer_id",
        "human_review_timestamp",
    ]
    for row in rows:
        assert row["codex_prelim_label"].startswith("CODEX_PRELIM_")
        assert all(row[col] == "" for col in human_cols)


def test_manifest_marks_packet_pending_not_evidence():
    manifest = json.loads((ANN / "qwen_failed_12_human_review_manifest.json").read_text())
    assert manifest["n_items"] == 12
    assert manifest["human_fields_prefilled"] is False
    assert manifest["paper_evidence"] is False
    assert manifest["status"] == "PENDING_REAL_HUMAN_REVIEW"


def test_apply_script_refuses_blank_review_sheet():
    out_json = V9 / "qwen_spurious_human_review_apply_report.json"
    result = subprocess.run(
        [sys.executable, "scripts/apply_v9_qwen_spurious_human_review.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    report = json.loads(out_json.read_text())
    assert report["status"] == "BLOCKED_BLANK_HUMAN_REVIEW"
    assert report["paper_evidence"] is False
    assert report["canonical_results_changed"] is False
    assert report["raw_gate"]["flipped"] == 12
    assert report["raw_gate"]["n_items"] == 94
