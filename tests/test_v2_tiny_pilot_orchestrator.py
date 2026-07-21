"""Tests for the V2 tiny real-pilot orchestrator using a synthetic ADE20K root."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from certvic.pipeline.run_tiny_pilot import run_tiny_pilot

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = str(REPO_ROOT / "configs" / "real_pilot_ade20k.yaml")


def _make_fake_ade20k(root: Path, n: int = 3) -> Path:
    img_dir = root / "images" / "training"
    ann_dir = root / "annotations" / "training"
    img_dir.mkdir(parents=True)
    ann_dir.mkdir(parents=True)
    rng = np.random.RandomState(0)
    for i in range(n):
        arr = rng.randint(0, 255, size=(48, 48, 3), dtype=np.uint8)
        Image.fromarray(arr).save(img_dir / f"img{i}.jpg")
        seg = np.zeros((48, 48), dtype=np.uint8)
        seg[10:30, 10:30] = 8  # label 8 = bed (eligible in the policy), ~0.17 area
        seg[34:40, 34:44] = 16  # label 16 = table
        Image.fromarray(seg, mode="L").save(ann_dir / f"img{i}.png")
    return root


def test_dry_run_inspects_and_lists_next_commands(tmp_path):
    root = _make_fake_ade20k(tmp_path / "ade")
    out = tmp_path / "out"
    summary = run_tiny_pilot(CONFIG, str(root), str(out), max_items=5, seed=0, dry_run=True)
    assert summary["dry_run"] is True
    assert summary["zero_cost_audit"]["vlm_inference_run"] is False
    # Dry run stops after label_policy_report and lists the remaining commands.
    assert "label_policy_report" in summary["stages_attempted"]
    assert "edit_generation" not in summary["stages_attempted"]
    assert summary["next_commands"]
    assert (out / "stage_status.json").exists()
    assert (out / "zero_cost_audit.json").exists()
    assert (out / "command_log.txt").exists()
    audit = json.loads((out / "zero_cost_audit.json").read_text())
    assert audit["vlm_inference_run"] is False
    assert audit["downloads_attempted"] is False


def test_full_pipeline_runs_all_stages(tmp_path):
    root = _make_fake_ade20k(tmp_path / "ade", n=4)
    out = tmp_path / "out"
    summary = run_tiny_pilot(CONFIG, str(root), str(out), max_items=4, seed=0, dry_run=False)
    expected = {
        "pilot_readiness", "manifests", "label_policy_report", "selection", "edit_planning",
        "task_preview", "pilot_plan_report", "edit_generation", "quality_report",
        "materialization", "visual_review_sheet",
    }
    assert expected.issubset(set(summary["stages_attempted"]))
    # No stage should have failed; all attempted stages complete.
    assert summary["stages_failed"] == [], summary["stages_failed"]
    assert (out / "pilot_generated_edits.jsonl").exists()
    assert (out / "visual_review_sheet.csv").exists()
    assert summary["evidence_status"] == "PIPELINE_NON_EVIDENCE"


def test_resume_skips_completed_stages(tmp_path):
    root = _make_fake_ade20k(tmp_path / "ade")
    out = tmp_path / "out"
    run_tiny_pilot(CONFIG, str(root), str(out), max_items=3, seed=0, dry_run=True)
    status1 = json.loads((out / "stage_status.json").read_text())
    # Second dry run reuses completed stages (no --force).
    run_tiny_pilot(CONFIG, str(root), str(out), max_items=3, seed=0, dry_run=True)
    status2 = json.loads((out / "stage_status.json").read_text())
    assert status1["stages"]["manifests"]["status"] == "completed"
    assert status2["stages"]["manifests"]["status"] == "completed"
