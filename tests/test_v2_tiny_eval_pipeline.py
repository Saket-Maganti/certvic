"""Tests for the V2 tiny eval + scoring path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from certvic.data.smoke_fixtures import generate_smoke_tasks
from certvic.io import write_jsonl
from certvic.pipeline.run_tiny_eval import TinyEvalError, run_tiny_eval

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = str(REPO_ROOT / "configs" / "smoke.yaml")


def _reviewed_tasks(tmp_path, status="HUMAN_REVIEWED_NON_EVIDENCE"):
    tasks = generate_smoke_tasks(tmp_path / "smoke", n_items=8)
    rows = []
    for task in tasks:
        dumped = task.model_dump(mode="json")
        dumped["metadata"]["evidence_status"] = status
        rows.append(dumped)
    path = tmp_path / "reviewed_tasks.jsonl"
    write_jsonl(path, rows)
    return path


def test_requires_max_items_unless_full_run(tmp_path):
    tasks = _reviewed_tasks(tmp_path)
    with pytest.raises(TinyEvalError, match="max_items is required"):
        run_tiny_eval(CONFIG, str(tasks), "mock_inconsistent", str(tmp_path / "out"), "r1", allow_mock_smoke=True)


def test_mock_blocked_for_evidence_path(tmp_path):
    tasks = _reviewed_tasks(tmp_path)
    with pytest.raises(TinyEvalError, match="mock providers are blocked"):
        run_tiny_eval(CONFIG, str(tasks), "mock_inconsistent", str(tmp_path / "out"), "r1", max_items=8)


def test_unreviewed_tasks_blocked_on_evidence_path(tmp_path):
    tasks = _reviewed_tasks(tmp_path, status="GENERATED_EDIT_ONLY")
    # Non-mock provider would be required; here we assert the status gate fires
    # before any model is constructed by using a non-mock provider name path.
    with pytest.raises(TinyEvalError):
        run_tiny_eval(CONFIG, str(tasks), "text_only_baseline", str(tmp_path / "out"), "r1", max_items=8)


def test_mock_smoke_run_completes_non_evidence(tmp_path):
    tasks = _reviewed_tasks(tmp_path)
    summary = run_tiny_eval(CONFIG, str(tasks), "mock_inconsistent", str(tmp_path / "out"), "r1", max_items=8, allow_mock_smoke=True)
    assert summary["evidence_status"] == "MOCK_SMOKE_NON_EVIDENCE"
    assert summary["is_evidence_path"] is False
    # A mock/smoke run can never be certified.
    assert summary["certified"] is False
    assert summary["raw_outputs_preserved"] is True
    assert summary["n_scores"] > 0
    out = tmp_path / "out"
    assert (out / "predictions.jsonl").exists()
    assert (out / "pair_scores.jsonl").exists()
    assert (out / "metrics_summary.json").exists()
    assert (out / "stage_status.json").exists()


def test_metrics_summary_has_certification_block(tmp_path):
    tasks = _reviewed_tasks(tmp_path)
    run_tiny_eval(CONFIG, str(tasks), "mock_inconsistent", str(tmp_path / "out"), "r1", max_items=8, allow_mock_smoke=True)
    payload = json.loads((tmp_path / "out" / "metrics_summary.json").read_text())
    assert "metrics" in payload and "certification" in payload
    assert payload["certification_policy_decision"]["policy_passed"] is False  # smoke data is blocked
