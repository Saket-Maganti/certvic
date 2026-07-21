"""Tests for V7 second-rater export + IAA computation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


export_mod = _load("export_second_rater_review", "scripts/export_second_rater_review.py")
iaa_mod = _load("compute_review_iaa", "scripts/compute_review_iaa.py")

SHEET = REPO / "data/results/main_real_200/review_iaa/second_rater_review_sheet.csv"


def test_export_sheet_is_blinded_and_leakage_free():
    rows = iaa_mod._read_csv(SHEET)
    assert len(rows) == 91
    header = set(rows[0].keys())
    # No model outcome / first-rater label columns may leak in.
    for forbidden in ("model_fail_count", "keep_for_eval_rater1", "photorealistic", "consistent"):
        assert forbidden not in header
    # human fields blank on export
    for r in rows:
        assert r["photorealism"] == "" and r["keep_for_eval"] == "" and r["reviewer_id"] == ""


def test_compute_reports_pending_when_second_rater_blank():
    rows = iaa_mod._read_csv(SHEET)
    rater1 = iaa_mod._read_csv(REPO / "data/results/main_real_200/visual_review_completed.csv")
    result = iaa_mod.compute(rater1, rows)
    assert result["status"] == "second_rater_pending"
    assert result["two_rater"] is None
    assert result["paper_evidence"] is False
    # rater 1 reviewed all 103 input tasks; 91 were kept for eval.
    assert result["single_rater_preliminary"]["n_items"] == 103
    assert result["single_rater_preliminary"]["keep_for_eval_pass"] == 91


def test_two_rater_kappa_on_synthetic_completed_sheet():
    rater1 = [
        {"item_id": "a", "photorealistic": "1", "single_factor": "1", "prompt_answerable": "1",
         "required_change_unambiguous": "1", "keep_for_eval": "1", "reviewer_id": "r1"},
        {"item_id": "b", "photorealistic": "1", "single_factor": "0", "prompt_answerable": "1",
         "required_change_unambiguous": "1", "keep_for_eval": "1", "reviewer_id": "r1"},
        {"item_id": "c", "photorealistic": "0", "single_factor": "1", "prompt_answerable": "0",
         "required_change_unambiguous": "0", "keep_for_eval": "0", "reviewer_id": "r1"},
    ]
    rater2 = [
        {"item_id": "a", "photorealism": "yes", "single_factor": "yes", "answerability": "yes",
         "required_answer_change_unambiguous": "yes", "keep_for_eval": "yes",
         "target_absent_after_edit": "no", "reviewer_id": "r2"},
        {"item_id": "b", "photorealism": "yes", "single_factor": "yes", "answerability": "yes",
         "required_answer_change_unambiguous": "yes", "keep_for_eval": "no",  # gate disagreement
         "target_absent_after_edit": "yes", "reviewer_id": "r2"},
        {"item_id": "c", "photorealism": "no", "single_factor": "yes", "answerability": "no",
         "required_answer_change_unambiguous": "no", "keep_for_eval": "no",
         "target_absent_after_edit": "uncertain", "reviewer_id": "r2"},
    ]
    result = iaa_mod.compute(rater1, rater2)
    assert result["status"] == "two_rater_computed"
    assert result["n_joined_items"] == 3
    pf = result["two_rater"]["per_field"]
    # photorealism: rater1 yes,yes,no vs rater2 yes,yes,no -> perfect agreement
    assert pf["photorealism"]["percent_agreement"] == 1.0
    # one gate disagreement on item b
    assert result["two_rater"]["n_gate_disagreements"] == 1
    assert "b" in result["two_rater"]["exclusion_sensitivity_item_ids"]


def test_export_refuses_when_reviewed_missing(tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        export_mod.build(tmp_path / "nope.jsonl", tmp_path / "out")
