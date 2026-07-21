"""Tests for the V2 visual review and approval workflow."""

from __future__ import annotations

import csv

from certvic.data.apply_visual_review import apply_visual_review
from certvic.io import read_jsonl, write_jsonl
from certvic.reporting.visual_review_report import build_visual_review_report
from certvic.validation.aggregate_visual_review import aggregate_visual_review
from certvic.validation.build_review_gallery import build_review_gallery
from certvic.validation.export_visual_review import REVIEW_COLUMNS, export_visual_review
from certvic.validation.iaa import field_iaa, normalize_rating


def _tasks(tmp_path):
    rows = [
        {"item_id": "t0", "edit_id": "e0", "source_id": "s0", "task_family": "support_stability",
         "domain": "household", "edit_type": "remove", "required_change": "change",
         "original_image_path": str(tmp_path / "o0.png"), "edited_image_path": str(tmp_path / "x0.png"),
         "mask_id": "m0", "bbox": [0, 0, 4, 4], "question_original": "Is the cup supported?"},
        {"item_id": "t1", "edit_id": "e1", "source_id": "s1", "task_family": "occlusion_safety",
         "domain": "driving", "edit_type": "occlude", "required_change": "no_change",
         "original_image_path": str(tmp_path / "o1.png"), "edited_image_path": str(tmp_path / "x1.png"),
         "mask_id": "m1", "bbox": [0, 0, 4, 4], "question_original": "Is the road clear?"},
    ]
    path = tmp_path / "tasks.jsonl"
    write_jsonl(path, rows)
    return path


def _edits(tmp_path):
    rows = [
        {"edit_id": "e0", "quality_gate_status": "pass", "quality": {"warnings": []}},
        {"edit_id": "e1", "quality_gate_status": "fail", "quality": {"warnings": ["mask area too small"]}},
    ]
    path = tmp_path / "edits.jsonl"
    write_jsonl(path, rows)
    return path


def test_export_sheet_has_columns_and_no_predictions(tmp_path):
    out = tmp_path / "sheet.csv"
    n = export_visual_review(str(_tasks(tmp_path)), str(_edits(tmp_path)), str(out), max_items=10, seed=0)
    assert n == 2
    reader = csv.DictReader(out.open(encoding="utf-8"))
    assert reader.fieldnames == REVIEW_COLUMNS
    text = out.read_text(encoding="utf-8").lower()
    for forbidden in ["prediction", "model_output", "parsed_answer"]:
        assert forbidden not in text


def test_normalize_and_field_iaa():
    assert normalize_rating("Y") == "yes"
    assert normalize_rating("") == "uncertain"
    two = field_iaa([["yes", "yes"], ["no", "yes"]])
    assert two["method"] == "cohens_kappa"
    three = field_iaa([["yes", "yes", "no"], ["yes", "yes", "yes"]])
    assert three["method"] == "majority_agreement"
    one = field_iaa([["yes"], ["no"]])
    assert one["single_rater_warning"] is True


def _ratings_csv(tmp_path):
    # t0 approved by 2/2; t1 majority-no on photorealistic -> drop.
    rows = [
        {"item_id": "t0", "reviewer_id": "r1", "photorealistic": "yes", "single_factor": "yes",
         "target_object_clear": "yes", "required_change_unambiguous": "yes", "prompt_answerable": "yes", "keep_for_eval": "yes"},
        {"item_id": "t0", "reviewer_id": "r2", "photorealistic": "yes", "single_factor": "yes",
         "target_object_clear": "yes", "required_change_unambiguous": "yes", "prompt_answerable": "yes", "keep_for_eval": "yes"},
        {"item_id": "t1", "reviewer_id": "r1", "photorealistic": "no", "single_factor": "no",
         "target_object_clear": "uncertain", "required_change_unambiguous": "no", "prompt_answerable": "no", "keep_for_eval": "no"},
        {"item_id": "t1", "reviewer_id": "r2", "photorealistic": "no", "single_factor": "yes",
         "target_object_clear": "uncertain", "required_change_unambiguous": "no", "prompt_answerable": "no", "keep_for_eval": "no"},
    ]
    path = tmp_path / "ratings.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_aggregate_keep_drop_and_iaa(tmp_path):
    summary = aggregate_visual_review(
        str(_ratings_csv(tmp_path)),
        str(tmp_path / "summary.json"),
        str(tmp_path / "keep.txt"),
        str(tmp_path / "drop.txt"),
    )
    assert summary["keep_items"] == ["t0"]
    assert summary["drop_items"] == ["t1"]
    assert "photorealistic" in summary["iaa"]
    assert (tmp_path / "keep.txt").read_text().strip() == "t0"


def test_apply_visual_review_sets_status(tmp_path):
    keep = tmp_path / "keep.txt"
    keep.write_text("t0\n", encoding="utf-8")
    summary = apply_visual_review(str(_tasks(tmp_path)), str(keep), str(tmp_path / "reviewed.jsonl"), str(tmp_path / "rev_summary.json"))
    assert summary["approved_tasks"] == 1
    rows = read_jsonl(tmp_path / "reviewed.jsonl")
    assert rows[0]["visual_review_status"] == "approved"
    assert rows[0]["evidence_status"] == "HUMAN_REVIEWED_NON_EVIDENCE"


def test_gallery_and_report(tmp_path):
    sheet = tmp_path / "sheet.csv"
    export_visual_review(str(_tasks(tmp_path)), str(_edits(tmp_path)), str(sheet), max_items=10, seed=0)
    gallery = build_review_gallery(str(sheet), str(tmp_path / "gallery"))
    assert gallery["pixels_copied"] is False
    assert (tmp_path / "gallery" / "index.html").exists()

    summary = aggregate_visual_review(str(_ratings_csv(tmp_path)), str(tmp_path / "summary.json"), str(tmp_path / "keep.txt"), str(tmp_path / "drop.txt"))
    apply_visual_review(str(_tasks(tmp_path)), str(tmp_path / "keep.txt"), str(tmp_path / "reviewed.jsonl"), str(tmp_path / "rev_summary.json"))
    report = build_visual_review_report(str(tmp_path / "summary.json"), str(tmp_path / "reviewed.jsonl"), str(tmp_path / "report"))
    assert report["evidence_status"] == "HUMAN_REVIEWED_NON_EVIDENCE"
    assert (tmp_path / "report" / "visual_review_report.md").exists()
    assert summary["n_items"] == 2
