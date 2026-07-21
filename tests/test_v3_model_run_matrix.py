"""Tests for the V3 model run orchestration matrix (prompt 08)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from certvic.eval import model_matrix, run_matrix_planner, run_status

PROVIDERS = ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]


def test_build_matrix_dimensions():
    m = model_matrix.build_matrix("data/manifests/tasks.jsonl", PROVIDERS, max_items=200, num_shards=4)
    assert m["n_cells"] == len(PROVIDERS) * 1 * 4
    assert m["vlm_inference_run"] is False
    assert m["evidence_claims_made"] is False
    # Each cell has a resumable command with shard + max-items flags.
    c = m["cells"][0]
    assert "--num-shards 4" in c["command"]
    assert "--max-items 200" in c["command"]
    assert "--shard-index" in c["command"]
    assert c["expected_output_path"].endswith(".jsonl")
    assert len(c["expected_sidecars"]) == 3


def test_prompt_variants_multiply_cells():
    m = model_matrix.build_matrix("t.jsonl", ["qwen2_5_vl_7b"], num_shards=2, prompt_variants=["default", "terse"])
    assert m["n_cells"] == 1 * 2 * 2


def test_paid_provider_rejected(monkeypatch):
    monkeypatch.setattr(model_matrix, "PAID_PROVIDER_NAMES", {"gpt4v_paid"})
    with pytest.raises(ValueError, match="paid"):
        model_matrix.build_matrix("t.jsonl", ["gpt4v_paid"], num_shards=1)


def test_evidence_eligibility_flagged():
    m = model_matrix.build_matrix("t.jsonl", ["qwen2_5_vl_7b", "mock_inconsistent"], num_shards=1)
    summaries = m["provider_summaries"]
    assert summaries["qwen2_5_vl_7b"]["evidence_eligible"] is True
    assert summaries["mock_inconsistent"]["evidence_eligible"] is False


def test_memory_estimate_4bit():
    m = model_matrix.build_matrix("t.jsonl", ["qwen2_5_vl_7b"], num_shards=1)
    mem = m["provider_summaries"]["qwen2_5_vl_7b"]["memory_estimate"]
    assert mem["expected_gpu_memory_gb"] > 0
    assert mem["expected_gpu_memory_gb_4bit"] < mem["expected_gpu_memory_gb"]


def test_invalid_shards_and_empty_providers():
    with pytest.raises(ValueError):
        model_matrix.build_matrix("t.jsonl", PROVIDERS, num_shards=0)
    with pytest.raises(ValueError):
        model_matrix.build_matrix("t.jsonl", [], num_shards=2)


def test_planner_writes_artifacts(tmp_path):
    out = tmp_path / "matrix"
    m = model_matrix.build_matrix("t.jsonl", PROVIDERS, num_shards=2)
    paths = run_matrix_planner.write_matrix(m, str(out))
    for p in paths.values():
        assert Path(p).exists()
    assert "run_eval" in Path(paths["commands"]).read_text(encoding="utf-8")
    assert "Model Run Matrix" in Path(paths["report"]).read_text(encoding="utf-8")


def test_run_status_detects_missing_and_completed(tmp_path):
    # Build a matrix rooted under tmp_path so we can create some outputs.
    pred_root = tmp_path / "preds"
    m = model_matrix.build_matrix("t.jsonl", ["qwen2_5_vl_7b"], num_shards=2, pred_root=str(pred_root))
    matrix_path = tmp_path / "run_matrix.json"
    matrix_path.write_text(json.dumps(m), encoding="utf-8")

    # Complete the first cell: write predictions + all sidecars.
    cell0 = m["cells"][0]
    out0 = Path(cell0["expected_output_path"])
    out0.parent.mkdir(parents=True, exist_ok=True)
    out0.write_text('{"x": 1}\n{"x": 2}\n', encoding="utf-8")
    for sc in cell0["expected_sidecars"]:
        Path(sc).write_text("{}", encoding="utf-8")

    result = run_status.run_status(str(matrix_path), str(pred_root))
    assert result["n_cells"] == 2
    assert result["n_completed"] == 1
    assert result["n_missing"] == 1
    assert result["all_complete"] is False
    # Missing cell carries a resume command.
    assert len(result["resume_commands"]) == 1
    assert "run_eval" in result["resume_commands"][0]


def test_run_status_partial_output_without_sidecars_is_missing(tmp_path):
    pred_root = tmp_path / "preds"
    m = model_matrix.build_matrix("t.jsonl", ["qwen2_5_vl_7b"], num_shards=1, pred_root=str(pred_root))
    matrix_path = tmp_path / "m.json"
    matrix_path.write_text(json.dumps(m), encoding="utf-8")
    cell = m["cells"][0]
    out = Path(cell["expected_output_path"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('{"x": 1}\n', encoding="utf-8")  # predictions but no sidecars
    result = run_status.run_status(str(matrix_path), str(pred_root))
    assert result["cells"][0]["status"] == "missing"


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
