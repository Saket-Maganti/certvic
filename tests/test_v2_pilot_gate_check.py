"""Tests for the V2 pilot gate checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from certvic.pipeline.pilot_gate_check import GATE_STAGES, run_gate_check

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = str(REPO_ROOT / "configs" / "real_pilot_ade20k.yaml")


def test_all_gate_stages_defined():
    assert GATE_STAGES == [
        "before_edit_generation", "before_visual_review", "before_vlm", "before_claims", "before_release",
    ]


def test_unknown_stage_raises():
    with pytest.raises(ValueError):
        run_gate_check("nonsense", CONFIG, repo_root=str(REPO_ROOT))


def test_before_release_passes_on_repo():
    # Release-stage prerequisites (configs + docs) exist in the repo.
    result = run_gate_check("before_release", CONFIG, repo_root=str(REPO_ROOT))
    assert result["passed"] is True
    assert result["evidence_status"] == "GATE_CHECK_NON_EVIDENCE"


def test_before_claims_passes_on_repo():
    result = run_gate_check("before_claims", CONFIG, repo_root=str(REPO_ROOT))
    assert result["passed"] is True


def test_before_edit_generation_blocks_without_manifests(tmp_path):
    # Empty repo root -> manifests absent -> gate blocks.
    result = run_gate_check("before_edit_generation", CONFIG, repo_root=str(tmp_path))
    assert result["passed"] is False
    assert "source_manifest_present" in result["blocking"]


def test_gate_writes_json(tmp_path):
    out = tmp_path / "gate.json"
    from certvic.pipeline.pilot_gate_check import main

    main(["--stage", "before_release", "--config", CONFIG, "--repo-root", str(REPO_ROOT), "--out", str(out)])
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["stage"] == "before_release"
