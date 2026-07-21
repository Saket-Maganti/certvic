"""Tests for V7 failure taxonomy + gallery."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from certvic.io import read_json

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "build_failure_taxonomy_gallery", REPO / "scripts/build_failure_taxonomy_gallery.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

GAL = REPO / "data/results/main_real_200/failure_gallery/gallery.json"


def test_gallery_non_evidence_and_91_items():
    g = read_json(GAL)
    assert g["paper_evidence"] is False
    assert g["n_reviewed_items"] == 91


def test_every_example_has_required_fields_and_three_model_answers():
    g = read_json(GAL)
    for cat, blk in g["categories"].items():
        assert "selection_criteria" in blk and "selection_rule" in blk
        for ex in blk["examples"]:
            for field in ("original_image_path", "edited_image_path", "target_object",
                          "edit_type", "question", "expected_original_answer",
                          "expected_edited_answer", "edited_sha256", "model_answers",
                          "visual_review_status"):
                assert field in ex, (cat, field)
            assert ex["visual_review_status"] == "approved"  # no unreviewed headline items
            assert set(ex["model_answers"]) == {"qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"}


def test_selection_is_deterministic_lowest_item_id():
    g = read_json(GAL)
    for cat, blk in g["categories"].items():
        ids = [e["item_id"] for e in blk["examples"]]
        assert ids == sorted(ids)  # deterministic order, no hand-picking


def test_llava_only_update_examples_match_definition():
    g = read_json(GAL)
    for ex in g["categories"]["llava_only_update"]["examples"]:
        ma = ex["model_answers"]
        assert ma["llava_onevision_7b"]["edited_correct"] is True
        assert ma["qwen2_5_vl_7b"]["edited_correct"] is False
        assert ma["internvl_8b"]["edited_correct"] is False


def test_polarity_category_is_pending_not_fabricated():
    g = read_json(GAL)
    pol = g["categories"]["prompt_polarity_sensitive"]
    assert pol["examples"] == []
    assert pol["status"] == "pending_ablation_predictions"
