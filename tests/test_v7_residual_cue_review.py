"""Tests for V7 residual-cue review export + summarizer."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


export_mod = _load("export_residual_cue_review", "scripts/export_residual_cue_review.py")
apply_mod = _load("apply_residual_cue_review", "scripts/apply_residual_cue_review.py")


def test_exported_sheet_has_blank_human_fields():
    sheet = REPO / "data/results/main_real_200/residual_cue_review/residual_cue_review_sheet.csv"
    rows = apply_mod.read_sheet(sheet)
    assert len(rows) == 91
    for r in rows:
        assert r["residual_target_visible"] == ""
        assert r["human_absence_confident"] == ""
        assert r["reviewer_id"] == ""
        assert r["model_fail_count"] in {"0", "1", "2", "3"}


def test_model_fail_count_matches_canonical_pair_scores_for_qwen():
    """The Qwen column of model_fail_count must equal canonical edited_correct=False."""
    import json
    reviewed = [json.loads(line) for line in open(
        REPO / "data/results/main_real_200/pilot_eval_tasks_reviewed_v2.jsonl") if line.strip()]
    info = export_mod.compute_model_fail(reviewed)
    ps = {json.loads(line)["item_id"]: json.loads(line) for line in open(
        REPO / "data/results/main_real_200/pair_scores_v2.jsonl") if line.strip()}
    for iid, d in info.items():
        if iid in ps:
            qwen_fail = d["per_model"]["qwen2_5_vl_7b"] == "fail"
            assert qwen_fail == (ps[iid]["edited_correct"] is False)


def test_blank_sheet_summarizes_as_review_pending():
    sheet = REPO / "data/results/main_real_200/residual_cue_review/residual_cue_review_sheet.csv"
    rows = apply_mod.read_sheet(sheet)
    summary = apply_mod.summarize(rows)
    assert summary["status"] == "review_pending"
    assert summary["n_reviewed"] == 0
    assert summary["residual_cue_rate"] is None
    assert summary["canonical_unchanged"] is True


def test_validate_rows_flags_bad_enum_and_missing_reviewer():
    rows = [
        {"residual_target_visible": "maybe", "residual_type": "", "human_absence_confident": "",
         "reviewer_id": "r1", "model_fail_count": "3", "edit_type": "remove", "item_id": "a"},
        {"residual_target_visible": "yes", "residual_type": "shadow", "human_absence_confident": "yes",
         "reviewer_id": "", "model_fail_count": "2", "edit_type": "remove", "item_id": "b"},
    ]
    v = apply_mod.validate_rows(rows)
    fields = {x["field"] for x in v}
    assert "residual_target_visible" in fields  # "maybe" invalid
    assert "reviewer_id" in fields              # blank reviewer on a reviewed row


def test_summarizer_computes_rates_on_synthetic_completed_sheet():
    rows = [
        # absent-confident, no residual, 3 models fail -> clean strong-evidence row
        {"item_id": "a", "edit_type": "remove", "model_fail_count": "3",
         "residual_target_visible": "no", "residual_type": "none",
         "human_absence_confident": "yes", "reviewer_id": "r1"},
        # residual visible (shadow), 1 model fails
        {"item_id": "b", "edit_type": "displace", "model_fail_count": "1",
         "residual_target_visible": "yes", "residual_type": "shadow",
         "human_absence_confident": "no", "reviewer_id": "r1"},
        # uncertain -> excluded from residual rate
        {"item_id": "c", "edit_type": "occlude", "model_fail_count": "2",
         "residual_target_visible": "uncertain", "residual_type": "other",
         "human_absence_confident": "uncertain", "reviewer_id": "r1"},
        # unreviewed -> excluded entirely
        {"item_id": "d", "edit_type": "remove", "model_fail_count": "0",
         "residual_target_visible": "", "residual_type": "", "human_absence_confident": "",
         "reviewer_id": ""},
    ]
    s = apply_mod.summarize(rows)
    assert s["status"] == "summarized"
    assert s["n_reviewed"] == 3
    assert s["n_unreviewed_excluded"] == 1
    assert s["n_uncertain_excluded_from_strong_claims"] == 1
    assert s["residual_cue_rate"] == 0.5  # 1 yes of {yes,no} = 1/2
    assert s["alternate_clean_subset"]["n"] == 1
    assert s["alternate_clean_subset"]["mean_model_fail_rate"] == 1.0  # 3/3
