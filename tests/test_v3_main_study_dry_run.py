"""Tests for the V3 main study dry-run orchestrator (prompt 18)."""

from __future__ import annotations

import json
import sys

from certvic.pipeline import main_study_dry_run, main_study_plan


def test_stage_plan_ordered_and_gated():
    stages = main_study_plan.stage_plan(200)
    ids = [s["id"] for s in stages]
    # Core ordering: edits before review before vlm before scoring before report.
    assert ids.index("edit_generation") < ids.index("visual_review")
    assert ids.index("visual_review") < ids.index("vlm_inference")
    assert ids.index("vlm_inference") < ids.index("scoring")
    assert ids.index("scoring") < ids.index("report")
    # Gates attached at the right stages.
    gated = {s["gate_after"] for s in stages if s.get("gate_after")}
    assert {"before_edit_generation", "before_visual_review", "before_vlm", "before_claims", "before_release"} <= gated


def test_build_main_study_plan_scale_and_flags():
    plan = main_study_plan.build_main_study_plan(2000)
    assert plan["scale"] == 2000
    assert plan["n_gpu_stages"] >= 2
    assert plan["executed"] is False
    assert plan["vlm_inference_run"] is False
    assert plan["evidence_claims_made"] is False
    assert plan["runtime_estimate"]["total_gpu_hours"] > 0


def test_required_inputs_include_dataset_root_and_weights():
    plan = main_study_plan.build_main_study_plan(200)
    joined = " ".join(plan["required_inputs"])
    assert "ADE20K_ROOT" in joined
    assert "WEIGHTS" in joined or "WEIGHTS_DIR" in joined


def test_gate_sequence_brackets_with_audits():
    gates = [g["gate"] for g in main_study_plan.gate_sequence()]
    assert gates[0] == "pre_run_master_audit"
    assert "final_pre_real_run_audit" in gates
    assert "security_privacy_audit" in gates


def test_dry_run_writes_seven_artifacts(tmp_path):
    plan = main_study_dry_run.write_dry_run(200, str(tmp_path / "dry200"))
    expected = {"stage_plan.json", "commands.sh", "required_inputs.md", "expected_outputs.md",
                "gate_sequence.md", "runtime_estimates.md", "report.md"}
    assert set(plan["files"]) == expected
    for name in expected:
        assert (tmp_path / "dry200" / name).exists()
    # commands.sh embeds gates after gated stages.
    cmds = (tmp_path / "dry200" / "commands.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in cmds
    assert "GATE: before_vlm" in cmds
    assert "run_eval" in cmds or "run_matrix_planner" in cmds


def test_dry_run_no_execution_markers(tmp_path):
    main_study_dry_run.write_dry_run(2000, str(tmp_path / "dry2000"))
    data = json.loads((tmp_path / "dry2000" / "stage_plan.json").read_text(encoding="utf-8"))
    assert data["executed"] is False
    assert data["downloads_attempted"] is False
    report = (tmp_path / "dry2000" / "report.md").read_text(encoding="utf-8")
    assert "No GPU/VLM jobs executed" in report


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
