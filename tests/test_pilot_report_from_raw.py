"""Tests for the pilot report builder: provenance refusal gates + scoring helpers.

CPU-local, no heavy deps, no network. Covers the safety-critical behavior:
fabricated/missing/tampered raw predictions must be refused, and the control /
update-rate math must be exact.
"""

from __future__ import annotations

import json

import pytest

from scripts.build_multimodel_summary import build_summary
from scripts.pilot_report_from_raw import (
    _source_generated_utc,
    control_accuracy,
    ingest_raw,
    positive_presence_subset,
    sha256,
    spurious_flip,
    update_rate,
    verify_provider,
)


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def test_ingest_refuses_missing_raw(tmp_path):
    with pytest.raises(SystemExit, match="not found"):
        ingest_raw("presence", tmp_path / "nope.jsonl", tmp_path / "ingest", None)


def test_ingest_refuses_hash_mismatch(tmp_path):
    raw = _write_jsonl(tmp_path / "raw.jsonl", [{"a": 1}])
    with pytest.raises(SystemExit, match="sha256 mismatch"):
        ingest_raw("presence", raw, tmp_path / "ingest", {"presence": "deadbeef"})


def test_ingest_succeeds_and_locks_hash(tmp_path):
    raw = _write_jsonl(tmp_path / "raw.jsonl", [{"a": 1}, {"a": 2}])
    digest = sha256(raw)
    info = ingest_raw("presence", raw, tmp_path / "ingest", {"presence": digest})
    assert info["sha256"] == digest
    assert info["n_records"] == 2
    assert (tmp_path / "ingest" / "presence__raw.jsonl").exists()


def test_report_timestamp_is_derived_from_sources_not_wall_clock(tmp_path):
    first = _write_jsonl(
        tmp_path / "first.jsonl",
        [{"timestamp_utc": "2026-07-01T00:00:00+00:00"}],
    )
    second = _write_jsonl(
        tmp_path / "second.jsonl",
        [{"timestamp_utc": "2026-07-02T00:00:00+00:00"}],
    )
    artifacts = [{"ingested_path": str(first)}, {"ingested_path": str(second)}]
    assert _source_generated_utc(artifacts) == "2026-07-02T00:00:00+00:00"


def test_update_rate_counts_non_updates(tmp_path):
    preds = _write_jsonl(
        tmp_path / "p.jsonl",
        [
            {"item_id": "a", "image_variant": "original", "parsed_answer": "yes"},
            {"item_id": "a", "image_variant": "edited", "parsed_answer": "yes"},  # same -> no update
            {"item_id": "b", "image_variant": "original", "parsed_answer": "yes"},
            {"item_id": "b", "image_variant": "edited", "parsed_answer": "no"},  # updated
        ],
    )
    out = update_rate(preds)
    assert out == {"n_items": 2, "same_answer": 1, "updated_answer": 1, "non_update_rate": 0.5}


def _qwen_preds(path):
    return _write_jsonl(
        path,
        [
            {"item_id": "x", "image_variant": "original", "parsed_answer": "yes", "provider_name": "qwen2_5_vl_7b"},
            {"item_id": "x", "image_variant": "edited", "parsed_answer": "no", "provider_name": "qwen2_5_vl_7b"},
        ],
    )


def test_verify_provider_refuses_mislabeled_model(tmp_path):
    preds = _qwen_preds(tmp_path / "p.jsonl")
    # Filing Qwen predictions under an InternVL label must fail.
    with pytest.raises(SystemExit, match="provider mismatch"):
        verify_provider("presence", preds, "internvl_8b")


def test_verify_provider_accepts_matching_model(tmp_path):
    preds = _qwen_preds(tmp_path / "p.jsonl")
    verify_provider("presence", preds, "qwen2_5_vl_7b")  # no raise


def test_ingest_refuses_provider_mismatch(tmp_path):
    preds = _qwen_preds(tmp_path / "p.jsonl")
    with pytest.raises(SystemExit, match="provider mismatch"):
        ingest_raw("presence", preds, tmp_path / "ingest", None, provider="llava_onevision_7b")


def test_multimodel_summary_marks_unrun_models_null(tmp_path):
    # Only Qwen has a real report; InternVL/LLaVA must appear as not_run with NO numbers.
    rep = tmp_path / "pilot_report"
    rep.mkdir()
    (rep / "pilot_result.json").write_text(json.dumps({
        "provider": "qwen2_5_vl_7b",
        "model": "Qwen/Qwen2.5-VL-7B-Instruct",
        "presence_intervention": {
            "summary": {"n": 91, "original_accuracy": 0.9231, "consistency_rate": 0.1758,
                        "intervention_consistency_gap": 0.7473},
            "certification": {"lower_bound": 0.364, "upper_bound": 1.0, "certified": True},
        },
        "absent_object_control": {"absent_correct": 60, "absent_n": 60, "present_correct": 50, "present_n": 60},
    }), encoding="utf-8")

    summary = build_summary(tmp_path)
    rows = {r["provider"]: r for r in summary["models"]}
    assert summary["n_run"] == 1
    assert rows["qwen2_5_vl_7b"]["status"] == "run" and rows["qwen2_5_vl_7b"]["gap"] == 0.7473
    for absent in ("internvl_8b", "llava_onevision_7b"):
        assert rows[absent]["status"] == "not_run"
        # Critically: unrun models carry NO metrics copied from Qwen.
        assert rows[absent]["gap"] is None
        assert rows[absent]["original_accuracy"] is None
        assert rows[absent]["certified"] is None


def test_spurious_flip_rate_and_gate(tmp_path):
    preds = _write_jsonl(
        tmp_path / "sp.jsonl",
        [
            {"item_id": "a", "image_variant": "original", "parsed_answer": "yes"},
            {"item_id": "a", "image_variant": "edited", "parsed_answer": "yes"},   # stable -> no flip
            {"item_id": "b", "image_variant": "original", "parsed_answer": "yes"},
            {"item_id": "b", "image_variant": "edited", "parsed_answer": "no"},    # flip (yes->no)
            {"item_id": "c", "image_variant": "original", "parsed_answer": "no"},
            {"item_id": "c", "image_variant": "edited", "parsed_answer": "no"},
        ],
    )
    out = spurious_flip(preds)
    assert out["n_items"] == 3 and out["flipped"] == 1
    assert out["spurious_flip_rate"] == round(1 / 3, 4)
    assert out["yes_to_no_flips"] == 1 and out["yes_items"] == 2
    assert out["gate_pass"] is False  # 0.333 > 0.10


def test_positive_subset_drops_negated_questions(tmp_path):
    tasks = _write_jsonl(
        tmp_path / "tasks.jsonl",
        [
            {"item_id": "p1", "question_original": "Is there a clearly visible table?",
             "answer_original": "yes", "answer_edited": "no", "required_change": "change"},
            {"item_id": "n1", "question_original": "Is the sofa absent or not clearly visible?",
             "answer_original": "no", "answer_edited": "yes", "required_change": "change"},
        ],
    )
    preds = _write_jsonl(
        tmp_path / "p.jsonl",
        [
            {"item_id": "p1", "image_variant": "original", "parsed_answer": "yes"},  # correct
            {"item_id": "p1", "image_variant": "edited", "parsed_answer": "yes"},    # did not update
            {"item_id": "n1", "image_variant": "original", "parsed_answer": "no"},
            {"item_id": "n1", "image_variant": "edited", "parsed_answer": "no"},
        ],
    )
    out = positive_presence_subset(tasks, preds)
    assert out["n"] == 1  # only the positive item
    assert out["original_accuracy"] == 1.0 and out["consistency_rate"] == 0.0 and out["gap"] == 1.0


def test_control_accuracy_splits_present_absent(tmp_path):
    gold = _write_jsonl(
        tmp_path / "gold.jsonl",
        [
            {"item_id": "ctrl_table_pos_1", "answer_original": "yes"},
            {"item_id": "ctrl_table_neg_1", "answer_original": "no"},
            {"item_id": "ctrl_sofa_neg_2", "answer_original": "no"},
        ],
    )
    preds = _write_jsonl(
        tmp_path / "preds.jsonl",
        [
            {"item_id": "ctrl_table_pos_1", "image_variant": "original", "parsed_answer": "yes"},  # correct present
            {"item_id": "ctrl_table_neg_1", "image_variant": "original", "parsed_answer": "no"},  # correct absent
            {"item_id": "ctrl_sofa_neg_2", "image_variant": "original", "parsed_answer": "yes"},  # wrong absent
        ],
    )
    out = control_accuracy(gold, preds)
    assert out["present_correct"] == 1 and out["present_n"] == 1
    assert out["absent_correct"] == 1 and out["absent_n"] == 2
    assert out["absent_accuracy"] == 0.5
    assert out["n"] == 3
