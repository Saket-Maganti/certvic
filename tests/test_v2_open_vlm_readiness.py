"""Tests for V2 open-local VLM readiness, preflight, and metadata."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from certvic.data.smoke_fixtures import generate_smoke_tasks
from certvic.eval.run_eval import run_eval
from certvic.eval.vlm_preflight import environment_summary, vlm_preflight
from certvic.io import write_jsonl
from certvic.providers.registry import (
    PAID_PROVIDER_NAMES,
    is_evidence_eligible_provider,
    provider_metadata,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = str(REPO_ROOT / "configs" / "smoke.yaml")


def _tasks(tmp_path, status="HUMAN_REVIEWED_NON_EVIDENCE"):
    tasks = generate_smoke_tasks(tmp_path / "smoke", n_items=6)
    rows = []
    for t in tasks:
        d = t.model_dump(mode="json")
        d["metadata"]["evidence_status"] = status
        rows.append(d)
    path = tmp_path / "tasks.jsonl"
    write_jsonl(path, rows)
    return path


def test_provider_metadata_and_eligibility():
    qwen = provider_metadata("qwen2_5_vl_7b")
    assert qwen["cost_status"] == "zero_cost_open_local"
    assert qwen["supports_4bit"] is True
    assert is_evidence_eligible_provider("qwen2_5_vl_7b") is True
    assert is_evidence_eligible_provider("mock_inconsistent") is False
    assert is_evidence_eligible_provider("text_only_baseline") is False
    assert PAID_PROVIDER_NAMES == set()


def test_environment_summary_no_gpu_check():
    env = environment_summary(check_gpu=False)
    assert env["gpu_checked"] is False
    assert "torch_available" in env


def test_preflight_blocks_missing_manifest(tmp_path):
    result = vlm_preflight("qwen2_5_vl_7b", CONFIG, str(tmp_path / "missing.jsonl"))
    assert result["ready"] is False
    assert "task_manifest_exists" in result["blocking_failures"]


def test_preflight_passes_structural_checks(tmp_path):
    tasks = _tasks(tmp_path)
    out = tmp_path / "preflight.json"
    result = vlm_preflight("qwen2_5_vl_7b", CONFIG, str(tasks), out_path=str(out))
    assert out.exists()
    assert result["inference_run"] is False
    assert result["downloads_attempted"] is False
    names = {c["check"] for c in result["checks"]}
    assert {"task_manifest_exists", "images_exist", "zero_cost_policy", "memory_estimate"} <= names
    # mock check not requested; provider is evidence eligible
    assert any(c["check"] == "provider_evidence_eligible" and c["ok"] for c in result["checks"])


def test_runner_writes_sidecars(tmp_path):
    tasks = _tasks(tmp_path)
    out = tmp_path / "preds.jsonl"
    run_eval(CONFIG, str(tasks), str(out), "mock_inconsistent", "r1", max_items=4)
    assert Path(f"{out}.provider_metadata.json").exists()
    assert Path(f"{out}.environment.json").exists()
    meta = json.loads(Path(f"{out}.provider_metadata.json").read_text())
    assert meta["provider_name"] == "mock_inconsistent"


def test_evidence_run_blocks_mock(tmp_path):
    tasks = _tasks(tmp_path)
    with pytest.raises(ValueError, match="not an evidence-eligible"):
        run_eval(CONFIG, str(tasks), str(tmp_path / "p.jsonl"), "mock_inconsistent", "r1", max_items=4, evidence_run=True)


def test_evidence_run_blocks_unreviewed_tasks(tmp_path):
    tasks = _tasks(tmp_path, status="GENERATED_EDIT_ONLY")
    # qwen is evidence-eligible but tasks are not reviewed -> blocked before model load.
    with pytest.raises(ValueError, match="tasks must be reviewed"):
        run_eval(CONFIG, str(tasks), str(tmp_path / "p.jsonl"), "qwen2_5_vl_7b", "r1", max_items=4, evidence_run=True)
