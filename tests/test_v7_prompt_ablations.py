"""Tests for V7 prompt-polarity ablation generation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from certvic.io import read_jsonl, read_json

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "build_prompt_ablation_tasks", REPO / "scripts/build_prompt_ablation_tasks.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

ABL = REPO / "data/results/main_real_200/prompt_ablations"


def test_polarity_validator_inverts_negated_form():
    assert mod.expected_gold("positive", "yes") == "yes"
    assert mod.expected_gold("positive", "no") == "no"
    assert mod.expected_gold("negative", "yes") == "no"   # present -> "absent?" = no
    assert mod.expected_gold("negative", "no") == "yes"   # absent  -> "absent?" = yes


def test_all_families_present_with_distinct_run_labels():
    top = read_json(ABL / "summary.json")
    assert top["polarity_validation"] == "passed"
    labels = {v["run_label"] for v in top["families"].values()}
    assert labels == {"abl_positive", "abl_negative", "abl_pixelonly", "abl_short"}
    for fam in top["families"].values():
        assert fam["n_tasks"] == 182  # 91 items x {original, edited}


def test_generated_negative_tasks_have_inverted_validated_gold():
    rows = read_jsonl(ABL / "negative" / "tasks.jsonl")
    assert rows
    for r in rows:
        assert "absent" in r["question"].lower()
        assert r["gold_answer"] == mod.expected_gold("negative", r["base_gold"])
        assert mod.validate_task(r) == []
        assert r["task_hash"]
        assert r["evidence_status"] == "PROMPT_ABLATION_NON_EVIDENCE"


def test_positive_form_preserves_base_gold():
    rows = read_jsonl(ABL / "positive" / "tasks.jsonl")
    for r in rows:
        assert r["gold_answer"] == r["base_gold"]


def test_uniform_prompt_gold_is_normalized_out_of_source_polarity():
    """Regression: 45 negated source items must not reverse ablation gold."""
    expected = {
        "positive": {"original": "yes", "edited": "no"},
        "pixel_only": {"original": "yes", "edited": "no"},
        "short": {"original": "yes", "edited": "no"},
        "negative": {"original": "no", "edited": "yes"},
    }
    for family, by_variant in expected.items():
        rows = read_jsonl(ABL / family / "tasks.jsonl")
        assert {r["source_question_polarity"] for r in rows} == {"positive", "negative"}
        for row in rows:
            assert row["gold_answer"] == by_variant[row["image_variant"]]


def test_source_negative_wording_is_inverted_before_ablation_polarity():
    item = {
        "question_original": "Is the table absent or not clearly visible in the image?",
        "answer_original": "no",
        "question_edited": "Is the table absent or not clearly visible in the image?",
        "answer_edited": "yes",
    }
    assert mod.item_positive_presence_gold(item, "original") == "yes"
    assert mod.item_positive_presence_gold(item, "edited") == "no"


def test_validate_task_flags_wrong_polarity_gold():
    bad = {"run_label": "abl_negative", "item_id": "x", "image_variant": "edited",
           "polarity": "negative", "base_gold": "no", "gold_answer": "no",  # should be "yes"
           "question": "Is the table absent from the image? Answer yes or no."}
    assert mod.validate_task(bad)  # non-empty -> error


def test_generator_refuses_when_reviewed_missing(tmp_path):
    with pytest.raises(SystemExit):
        mod.build(tmp_path / "nope.jsonl")
