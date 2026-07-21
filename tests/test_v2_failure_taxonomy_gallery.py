"""Tests for the V2 failure taxonomy and gallery."""

from __future__ import annotations

import json

from certvic.io import write_jsonl
from certvic.reporting.failure_gallery_v2 import build_failure_gallery_v2
from certvic.reporting.failure_taxonomy import TAXONOMY, classify_failure


def test_taxonomy_has_ten_types():
    assert len(TAXONOMY) == 10
    assert "missed_required_change" in TAXONOMY
    assert "spurious_flip_on_control" in TAXONOMY


def test_classify_missed_required_change_and_inertia():
    score = {"item_id": "i0", "required_change": "change", "task_family": "support_stability",
             "parse_ok": True, "original_correct": True, "edited_correct": False, "consistent": False}
    po = {"parsed_answer": "yes", "parse_ok": True, "parse_confidence": 1.0}
    pe = {"parsed_answer": "yes", "parse_ok": True, "parse_confidence": 1.0}
    cls = classify_failure(score, po, pe, edit_type="remove")
    assert cls["primary"] == "missed_required_change"
    assert "answer_inertia" in cls["applicable"]


def test_classify_spurious_flip_on_control():
    score = {"item_id": "i1", "required_change": "no_change", "task_family": "control_irrelevant",
             "parse_ok": True, "original_correct": True, "edited_correct": False, "consistent": False}
    po = {"parsed_answer": "yes", "parse_ok": True, "parse_confidence": 1.0}
    pe = {"parsed_answer": "no", "parse_ok": True, "parse_confidence": 1.0}
    cls = classify_failure(score, po, pe, edit_type="control_irrelevant")
    assert cls["primary"] == "spurious_flip_on_control"


def test_classify_parse_failure():
    score = {"item_id": "i2", "required_change": "change", "task_family": "support_stability",
             "parse_ok": False, "original_correct": False, "edited_correct": False, "consistent": False}
    cls = classify_failure(score, {"parse_ok": False, "parse_confidence": 0.0}, {"parse_ok": False, "parse_confidence": 0.0})
    assert cls["primary"] == "parse_failure"


def test_manual_override():
    score = {"item_id": "i3", "required_change": "change", "task_family": "support_stability",
             "parse_ok": True, "original_correct": True, "edited_correct": True, "consistent": True}
    cls = classify_failure(score, {}, {}, overrides={"i3": "ambiguous_item"})
    assert cls["primary"] == "ambiguous_item"
    assert cls["source"] == "manual_override"


def test_consistent_correct_item_is_not_a_failure():
    score = {"item_id": "ok", "required_change": "change", "task_family": "support_stability",
             "parse_ok": True, "original_correct": True, "edited_correct": True, "consistent": True}
    po = {"parsed_answer": "yes", "parse_ok": True, "parse_confidence": 1.0}
    pe = {"parsed_answer": "no", "parse_ok": True, "parse_confidence": 1.0}
    cls = classify_failure(score, po, pe, edit_type="remove")
    assert cls["is_failure"] is False


def test_build_gallery_outputs(tmp_path):
    tasks = [{"item_id": "i0", "task_family": "support_stability", "edit_type": "remove",
              "original_image_path": str(tmp_path / "o.png"), "edited_image_path": str(tmp_path / "e.png"),
              "license_category": "pointer_only"}]
    preds = [
        {"item_id": "i0", "image_variant": "original", "parsed_answer": "yes", "parse_ok": True, "parse_confidence": 1.0, "prompt": "q", "raw_output": "yes"},
        {"item_id": "i0", "image_variant": "edited", "parsed_answer": "yes", "parse_ok": True, "parse_confidence": 1.0, "prompt": "q", "raw_output": "yes"},
    ]
    scores = [{"item_id": "i0", "task_family": "support_stability", "domain": "household",
               "required_change": "change", "parse_ok": True, "original_correct": True, "edited_correct": False, "consistent": False}]
    write_jsonl(tmp_path / "tasks.jsonl", tasks)
    write_jsonl(tmp_path / "preds.jsonl", preds)
    write_jsonl(tmp_path / "scores.jsonl", scores)
    out = tmp_path / "gallery"
    summary = build_failure_gallery_v2(str(tmp_path / "tasks.jsonl"), str(tmp_path / "preds.jsonl"), str(tmp_path / "scores.jsonl"), str(out))
    assert summary["n_failures"] == 1
    assert summary["pixels_copied"] is False
    for name in ["failure_gallery.jsonl", "failure_taxonomy_summary.csv", "failure_gallery.md", "local_gallery.html", "paper_candidate_failures.jsonl", "failure_gallery_summary.json"]:
        assert (out / name).exists(), name
    entry = json.loads((out / "failure_gallery.jsonl").read_text().splitlines()[0])
    assert "no deployment or causal" in entry["paper_caption"]
