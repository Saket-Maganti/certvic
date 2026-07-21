"""Tests for the V3 Kaggle/Colab free-compute packager (prompt 03)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from certvic.compute import colab_packager, job_bundle, kaggle_packager


def _read_manifest(out_dir) -> dict:
    return json.loads((Path(out_dir) / "manifest.json").read_text(encoding="utf-8"))


def test_all_job_types_build(tmp_path):
    for job in job_bundle.JOB_TYPES:
        out = tmp_path / job
        manifest = kaggle_packager.package(job, "configs/real_pilot_ade20k.yaml", str(out))
        assert manifest["job"] == job
        assert manifest["safe"] is True
        assert manifest["evidence_status"] == "JOB_PLANNED_ONLY"
        # Required files present.
        for name in ("README.md", "commands.sh", "preflight.sh", "expected_inputs.md", "expected_outputs.md", "ZERO_COST_POLICY.txt", "manifest.json"):
            assert (out / name).exists()


def test_unknown_job_rejected(tmp_path):
    with pytest.raises(ValueError):
        job_bundle.build_bundle("nope", config="configs/smoke.yaml", out_dir=str(tmp_path / "x"))


def test_bundle_is_not_executed_and_marks_non_evidence(tmp_path):
    out = tmp_path / "vlm_tiny"
    manifest = kaggle_packager.package("vlm_tiny", "configs/tiny_reviewed_eval.yaml", str(out))
    assert manifest["executed"] is False
    assert manifest["paid_services"] is False
    assert manifest["evidence_claims_made"] is False
    assert manifest["downloads_attempted"] is False


def test_paths_anonymized_by_default(tmp_path):
    # Even if a private path leaks into config text, anonymization scrubs it.
    out = tmp_path / "b"
    private = f"{Path.home()}/secret_dataset/ade20k"
    manifest = job_bundle.build_bundle("diffusion_tiny", config=private, out_dir=str(out))
    text = (out / "README.md").read_text(encoding="utf-8") + (out / "commands.sh").read_text(encoding="utf-8")
    assert str(Path.home()) not in text
    assert "/secret_dataset/" not in text
    assert manifest["anonymized"] is True


def test_no_anonymize_flag_keeps_paths(tmp_path):
    out = tmp_path / "b2"
    cfg = "configs/real_pilot_ade20k.yaml"  # repo-relative, safe to keep
    manifest = job_bundle.build_bundle("reports_only", config=cfg, out_dir=str(out), anonymize_paths=False)
    assert manifest["anonymized"] is False


def test_forbidden_marker_scan_blocks_bundle(tmp_path, monkeypatch):
    # Inject a forbidden marker into a spec to prove the safety scan triggers.
    real_specs = job_bundle._job_specs

    def poisoned(config, scale):
        specs = real_specs(config, scale)
        specs["reports_only"]["commands"].append("export OPENAI_API_KEY=sk-leakedtoken")
        return specs

    monkeypatch.setattr(job_bundle, "_job_specs", poisoned)
    with pytest.raises(ValueError, match="forbidden"):
        job_bundle.build_bundle("reports_only", config="configs/smoke.yaml", out_dir=str(tmp_path / "p"))


def test_reports_only_is_cpu_job(tmp_path):
    manifest = colab_packager.package("reports_only", "configs/smoke.yaml", str(tmp_path / "r"))
    assert manifest["heavy_gpu_required"] is False
    assert manifest["platform"] == "colab"


def test_kaggle_and_colab_notes_differ(tmp_path):
    k = tmp_path / "k"
    c = tmp_path / "c"
    kaggle_packager.package("vlm_tiny", "configs/tiny_reviewed_eval.yaml", str(k))
    colab_packager.package("vlm_tiny", "configs/tiny_reviewed_eval.yaml", str(c))
    kt = (k / "README.md").read_text(encoding="utf-8")
    ct = (c / "README.md").read_text(encoding="utf-8")
    assert "/kaggle/working" in kt and "/content" in ct


def test_resume_instructions_present(tmp_path):
    out = tmp_path / "v200"
    kaggle_packager.package("vlm_200", "configs/kaggle_open_vlm.yaml", str(out))
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "Resume" in readme and "resume" in readme.lower()


def test_file_hashes_recorded(tmp_path):
    out = tmp_path / "h"
    manifest = kaggle_packager.package("ablations", "configs/tiny_reviewed_eval.yaml", str(out), scale=200)
    assert set(manifest["file_hashes"]) == set(manifest["files"])
    assert all(isinstance(v, str) and len(v) == 64 for v in manifest["file_hashes"].values())


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
