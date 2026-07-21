"""Tests for V7 mechanism-probe task generation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from certvic.io import read_jsonl, read_json

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "build_mechanism_probe_tasks", REPO / "scripts/build_mechanism_probe_tasks.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

PROBE_ROOT = REPO / "data/results/main_real_200/mechanism_probes"


def test_summary_marks_probes_non_evidence():
    top = read_json(PROBE_ROOT / "summary.json")
    assert top["evidence_status"] == "MECHANISM_PROBE_NON_EVIDENCE"
    assert top["paper_evidence"] is False
    assert top["n_reviewed_items"] == 91


def test_runnable_families_have_91_tasks_and_distinct_run_labels():
    labels = set()
    for family in ("object_list", "region_focused", "two_step", "context_suppression"):
        tasks = read_jsonl(PROBE_ROOT / family / "tasks.jsonl")
        assert len(tasks) == 91, family
        for t in tasks:
            assert t["evidence_status"] == "MECHANISM_PROBE_NON_EVIDENCE"
            assert t["vlm_inference_run"] is False
            # every task traces to a reviewed item
            assert t["item_id"] and t["edit_id"] and t["source_id"]
            # scoring spec, never a result
            assert "gold_post_edit_answer" in t["scoring"]
            # Every mechanism prompt asks positive target visibility on an edit
            # whose target is intended absent/hidden, independent of the source
            # task's alternating wording.
            assert t["scoring"]["gold_post_edit_answer"] == "no"
            assert t["scoring"]["gold_semantics"] == "positive_target_visibility"
            assert t["scoring"]["source_question_polarity"] in {"positive", "negative"}
            assert "flag_condition" in t["scoring"]
        labels.add(tasks[0]["run_label"])
    assert len(labels) == 4  # distinct run labels per family


def test_region_probe_carries_bbox_crop_spec():
    tasks = read_jsonl(PROBE_ROOT / "region_focused" / "tasks.jsonl")
    with_bbox = [t for t in tasks if t.get("crop_status") == "bbox_available"]
    assert with_bbox
    for t in with_bbox:
        bbox = t["crop_spec"]["bbox_xyxy"]
        assert len(bbox) == 4
        assert t["crop_spec"]["applies_to"] == "edited_image_path"


def test_forced_comparison_family_is_blocked_not_faked():
    spec = read_json(PROBE_ROOT / "original_vs_edited" / "SPEC_BLOCKED.json")
    assert spec["status"] == "blocked"
    assert "interface_change_required" in spec
    assert not (PROBE_ROOT / "original_vs_edited" / "tasks.jsonl").exists()


def test_generator_refuses_when_reviewed_missing(tmp_path):
    with pytest.raises(SystemExit):
        mod.build(tmp_path / "nope.jsonl")


def test_negative_source_gold_is_normalized_for_positive_mechanism_prompt():
    item = {
        "question_edited": "Is the chair absent or not clearly visible in the image?",
        "answer_edited": "yes",
        "question_object": "chair",
    }
    assert mod.item_positive_presence_gold(item, "edited") == "no"
