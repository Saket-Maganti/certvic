"""Tests for the V4 real-run command generator (prompt 01)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from certvic.commands import command_manifest
from certvic.commands.generate_real_run_commands import write_command_bundle


def test_all_stages_write_expected_artifacts(tmp_path):
    for stage in command_manifest.SUPPORTED_STAGES:
        out = tmp_path / stage
        manifest = write_command_bundle(stage, str(out))
        assert manifest["stage"] == stage
        assert manifest["safety"]["executed"] is False
        assert manifest["safety"]["planned_artifacts_evidence_status"] == "RUN_COMMANDS_PLANNED_ONLY"
        for name in (
            "commands.sh",
            "commands.md",
            "command_manifest.json",
            "expected_inputs.md",
            "expected_outputs.md",
            "resume_notes.md",
        ):
            assert (out / name).exists()


def test_commands_include_max_items_resume_and_safety_flags(tmp_path):
    out = tmp_path / "tiny"
    write_command_bundle("tiny_pilot", str(out))
    text = (out / "commands.sh").read_text(encoding="utf-8")
    assert "--max-items 20" in text
    assert "--resume" in text
    assert "--dry-run" in text
    assert "--strict-leakage" in text
    assert "--evidence-run" in text
    assert "--overwrite" not in text


def test_generation_does_not_execute_real_run(tmp_path):
    out = tmp_path / "main"
    manifest = write_command_bundle("main_200", str(out))
    data = json.loads((out / "command_manifest.json").read_text(encoding="utf-8"))
    assert manifest["safety"]["downloads_attempted"] is False
    assert manifest["safety"]["vlm_inference_run"] is False
    assert data["safety"]["gpu_required_for_generation"] is False
    assert not (out / "stage_status.json").exists()
    assert not (out / "pair_scores.jsonl").exists()


def test_paid_providers_rejected(tmp_path):
    with pytest.raises(ValueError, match="paid or non-core providers"):
        write_command_bundle("tiny_pilot", str(tmp_path / "bad"), providers=["openai_gpt4o"])


def test_non_core_free_tier_reference_rejected(tmp_path):
    with pytest.raises(ValueError, match="paid or non-core providers"):
        write_command_bundle(
            "tiny_pilot",
            str(tmp_path / "bad_ref"),
            providers=["free_tier_reference_stub"],
        )


def test_absolute_private_paths_parameterized(tmp_path):
    private_root = str(Path.home() / "private" / "ADE20K")
    private_cache = str(Path.home() / "private" / "weights")
    out = tmp_path / "paths"
    write_command_bundle(
        "main_200",
        str(out),
        ade20k_root=private_root,
        model_cache_root=private_cache,
    )
    combined = "\n".join(
        (out / name).read_text(encoding="utf-8")
        for name in ("commands.sh", "commands.md", "command_manifest.json", "expected_inputs.md")
    )
    assert private_root not in combined
    assert private_cache not in combined
    assert "<ADE20K_ROOT>" in combined
    assert "<MODEL_CACHE_ROOT>" in combined


def test_stage_metadata_represents_all_required_stages():
    assert set(command_manifest.SUPPORTED_STAGES) == {"tiny_pilot", "main_200", "full_2000"}
    for stage in command_manifest.SUPPORTED_STAGES:
        manifest = command_manifest.build_command_manifest(stage)
        assert manifest["n_commands"] >= 10
        assert manifest["max_items"] > 0
        assert manifest["command_manifest_sha256"]


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
