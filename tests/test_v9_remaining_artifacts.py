from __future__ import annotations

import csv
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
V9 = ROOT / "data/results/main_real_200/v9_mega_upgrade"


def test_main500_blocked_artifacts_do_not_create_results():
    planning = json.loads((ROOT / "data/results/main_500/planning/main500_planning_blocked.json").read_text())
    assert planning["status"] == "BLOCKED_MAIN500_GATE_NOT_GO"
    assert planning["paper_evidence"] is False
    certification = json.loads((ROOT / "data/results/main_500/certification/main500_results.json").read_text())
    assert certification["status"] == "BLOCKED_MISSING_MAIN500_VLM_OUTPUTS"
    assert certification["paper_evidence"] is False
    quality = json.loads((ROOT / "data/results/main_500/quality/main500_quality_report.json").read_text())
    detectability = json.loads((ROOT / "data/results/main_500/detectability/main500_detectability_report.json").read_text())
    assert quality["status"] == "BLOCKED_MISSING_DIFFUSION_OUTPUTS"
    assert detectability["status"] == "BLOCKED_MISSING_DIFFUSION_OUTPUTS"


def test_blank_main500_human_review_refuses_apply_and_iaa():
    for name in ["main500_review_sheet.csv", "rater1_sheet.csv", "rater2_sheet.csv"]:
        rows = list(csv.DictReader((ROOT / "data/annotations/main500_human_review" / name).open()))
        assert rows == []
    apply_proc = subprocess.run(
        [sys.executable, "scripts/apply_main500_human_review.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    iaa_proc = subprocess.run(
        [sys.executable, "scripts/compute_main500_iaa.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert apply_proc.returncode == 2
    assert iaa_proc.returncode == 2


def test_gated_notebooks_are_nbformat_valid_and_result_free():
    names = [
        "notebooks/kaggle/main500_diffusion_T4x2.ipynb",
        "notebooks/kaggle/main500_qwen2_5_vl_7b_T4x2.ipynb",
        "notebooks/kaggle/main500_internvl_8b_T4x2.ipynb",
        "notebooks/kaggle/main500_llava_onevision_7b_T4x2.ipynb",
        "notebooks/kaggle/second_domain_mini_diffusion_T4x2.ipynb",
        "notebooks/kaggle/second_domain_mini_vlm_T4x2.ipynb",
    ]
    for name in names:
        nb = nbformat.read(ROOT / name, as_version=4)
        text = "\n".join(cell["source"] for cell in nb["cells"])
        assert nb["nbformat"] == 4
        assert "/Users/" not in text
        assert "CUDA_VISIBLE_DEVICES=0" in text
        assert "CUDA_VISIBLE_DEVICES=1" in text
        assert "input validation" in text.lower()
        assert "estimated runtime" in text.lower()
        assert "Do not create this zip until real GPU outputs exist." in text


def test_diagnostic_statistical_reviewer_and_scorecard_reports_are_guarded():
    for raw in [
        "polarity_deep_report.json",
        "mechanism_deep_report.json",
        "statistical_power_lock.json",
        "failure_taxonomy_final.json",
        "v9_reviewer_attack_results.json",
        "cvpr_readiness_scorecard_v9.json",
    ]:
        data = json.loads((V9 / raw).read_text())
        assert data.get("paper_evidence") is False
    score = json.loads((V9 / "cvpr_readiness_scorecard_v9.json").read_text())
    assert score["recommendation"] == "HOLD_FOR_SPURIOUS_V2"


def test_v9_paper_and_release_package_exist_without_forbidden_payloads():
    compile_status = json.loads((V9 / "paper_compile_v9_status.json").read_text())
    assert compile_status["status"] == "PASS"
    assert (ROOT / "paper/main_v9.pdf").exists()
    manifest = json.loads((ROOT / "dist/certvic_v9_artifact_manifest.json").read_text())
    assert manifest["paper_evidence"] is False
    assert "paper/main_v9.pdf" in manifest["files"]
    release_zip = ROOT / "dist/certvic_v9_release_candidate.zip"
    assert release_zip.exists()
    with zipfile.ZipFile(release_zip) as zf:
        names = zf.namelist()
        text_payload = b"\n".join(
            zf.read(name)
            for name in names
            if name.endswith((".md", ".json", ".csv", ".tex", ".txt"))
        )
    assert not any(name.endswith(".DS_Store") for name in names)
    assert not any(name.lower().endswith((".pt", ".pth", ".safetensors", ".ckpt", ".bin")) for name in names)
    assert b"/Users/" not in text_payload
