"""Static validation for the remaining Kaggle/IPYNB runbook package.

CPU-local only: this rebuilds packaging artifacts, inspects notebooks and ZIP
contents, and checks that no prediction/result artifacts are created locally.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import nbformat
import pytest

from certvic.v7.spurious_control_integration import check_readiness
from scripts.build_remaining_kaggle_runbooks import _clean_owned_outputs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist/kaggle_remaining_runs"
TOP_ZIP = ROOT / "dist/certvic_remaining_kaggle_runbooks.zip"
KAGGLE_NB = ROOT / "notebooks/kaggle"
FAKE_PRED_RE = re.compile(r"(fake|mock|fixture)[_-]?(prediction|preds?|results?)", re.I)
WEIGHT_SUFFIXES = (".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".gguf")
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")
TEXT_SUFFIXES = (".jsonl", ".json", ".md", ".py", ".txt", ".yaml", ".yml", ".ipynb")
PRIVATE_POSIX = "/" + "Users/"
PRIVATE_WIN = "\\" + "Users" + "\\"

VLM_NOTEBOOKS = {
    "vlm_qwen2_5_vl_7b_T4x2_parallel.ipynb": "qwen2_5_vl_7b",
    "vlm_internvl_8b_T4x2_parallel.ipynb": "internvl_8b",
    "vlm_llava_onevision_7b_T4x2_parallel.ipynb": "llava_onevision_7b",
}


@pytest.fixture(scope="module")
def generated() -> Path:
    proc = subprocess.run(
        [sys.executable, "scripts/build_remaining_kaggle_runbooks.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    assert summary["produced_model_results"] is False
    assert summary["n_notebooks"] == 4
    assert summary["n_bundles"] == 4
    return OUT


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _nb_text(path: Path) -> tuple[dict, str]:
    nb = nbformat.read(path, as_version=4)
    text = "\n".join(
        c["source"] if isinstance(c["source"], str) else "".join(c["source"])
        for c in nb["cells"]
    )
    return nb, text


def _zip_text(z: zipfile.ZipFile) -> bytes:
    chunks = []
    for name in z.namelist():
        if name.endswith(TEXT_SUFFIXES):
            chunks.append(z.read(name))
    return b"\n".join(chunks)


def _bundle_rows(z: zipfile.ZipFile, task_name: str) -> list[dict]:
    return [json.loads(line) for line in z.read(task_name).splitlines()]


def _image_entries(z: zipfile.ZipFile) -> list[str]:
    return [name for name in z.namelist() if name.lower().endswith(IMAGE_SUFFIXES)]


def _referenced_images_are_present(z: zipfile.ZipFile, rows: list[dict]) -> bool:
    names = set(z.namelist())
    for row in rows:
        for key in ("original_image_path", "edited_image_path", "image_path"):
            raw = row.get(key)
            if not raw:
                continue
            base = Path(raw).name
            if base not in names and f"orig/{base}" not in names:
                return False
    return True


def test_cleanup_preserves_independently_owned_v2_artifacts(tmp_path: Path):
    out = tmp_path / "kaggle_remaining_runs"
    (out / "notebooks").mkdir(parents=True)
    v2 = out / "certvic_spurious_v2_control.zip"
    v2.write_bytes(b"independently-owned-v2")
    (out / "manifest.json").write_text("stale builder manifest")
    (out / "certvic_spurious_flip_control.zip").write_bytes(b"stale builder bundle")
    (out / "notebooks/vlm_qwen2_5_vl_7b_T4x2_parallel.ipynb").write_text("stale")

    _clean_owned_outputs(out)

    assert v2.read_bytes() == b"independently-owned-v2"
    assert not (out / "manifest.json").exists()
    assert not (out / "certvic_spurious_flip_control.zip").exists()
    assert not (out / "notebooks/vlm_qwen2_5_vl_7b_T4x2_parallel.ipynb").exists()


def test_manifest_and_top_package_exist_with_non_evidence_flags(generated: Path):
    manifest = json.loads((generated / "manifest.json").read_text())
    assert TOP_ZIP.exists()
    assert manifest["schema"] == "certvic.remaining_kaggle_runbooks.v2"
    assert manifest["produced_model_results"] is False
    assert manifest["paper_evidence"] is False
    assert len(manifest["notebooks"]) == 4
    assert len(manifest["bundles"]) == 4
    for entry in manifest["notebooks"]:
        assert _sha256(generated / entry["file"]) == entry["sha256"]
        assert _sha256(ROOT / entry["repo_file"]) == entry["sha256"]
    for entry in manifest["bundles"]:
        assert (generated / entry["bundle"]).exists()
        assert _sha256(generated / entry["bundle"]) == entry["sha256"]
    with zipfile.ZipFile(TOP_ZIP) as z:
        names = set(z.namelist())
    assert "kaggle_remaining_runs/manifest.json" in names
    assert "kaggle_remaining_runs/certvic_spurious_flip_control.zip" in names
    assert "kaggle_remaining_runs/certvic_spurious_v2_control.zip" not in names
    assert "kaggle_remaining_runs/SPURIOUS_V2_INPUTS_MATRIX.md" not in names
    assert "kaggle_remaining_runs/SPURIOUS_V2_LOCAL_INGEST_COMMANDS.md" not in names
    assert len(names) == 14
    assert not any("/bundles/" in name for name in names)
    assert not any(name.endswith(".DS_Store") for name in names)


def test_help_is_read_only(generated: Path):
    before = {
        path.relative_to(generated).as_posix(): _sha256(path)
        for path in sorted(generated.rglob("*"))
        if path.is_file()
    }
    proc = subprocess.run(
        [sys.executable, "scripts/build_remaining_kaggle_runbooks.py", "--help"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    after = {
        path.relative_to(generated).as_posix(): _sha256(path)
        for path in sorted(generated.rglob("*"))
        if path.is_file()
    }
    assert proc.returncode == 0
    assert "usage:" in proc.stdout
    assert after == before


def test_generation_is_checksum_stable(generated: Path):
    before_top = _sha256(TOP_ZIP)
    before_manifest = (generated / "manifest.json").read_text()
    subprocess.run(
        [sys.executable, "scripts/build_remaining_kaggle_runbooks.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert _sha256(TOP_ZIP) == before_top
    assert (generated / "manifest.json").read_text() == before_manifest


def test_vlm_notebooks_are_valid_t4x2_parallel_and_safe(generated: Path):
    for name, provider in VLM_NOTEBOOKS.items():
        nb, text = _nb_text(generated / "notebooks" / name)
        assert nb["nbformat"] == 4
        assert sum(len(c.get("outputs", [])) for c in nb["cells"] if c["cell_type"] == "code") == 0
        assert PRIVATE_POSIX not in text
        assert not FAKE_PRED_RE.search(text)
        assert f'PROVIDER = "{provider}"' in text
        assert "RUN_TAGS" in text
        for run_tag in ("spurious", "perception_scaled", "polarity", "mechanism"):
            assert run_tag in text
        assert "torch.cuda.device_count()" in text
        assert "CUDA_VISIBLE_DEVICES=0" in text
        assert "CUDA_VISIBLE_DEVICES=1" in text
        assert "single-GPU fallback" in text
        assert "pred_{PROVIDER}_{RUN_TAG}_shard{shard}.jsonl" in text
        assert "pred_{PROVIDER}_{RUN_TAG}_merged.jsonl" in text
        assert "pred_{PROVIDER}_{RUN_TAG}.jsonl" in text
        assert "log_{PROVIDER}_{RUN_TAG}_shard{shard}.txt" in text
        assert "summary_{PROVIDER}_{RUN_TAG}.json" in text
        assert "runtime_manifest_{PROVIDER}_{RUN_TAG}.json" in text
        assert "{PROVIDER}_{RUN_TAG}_preds.zip" in text
        assert "duplicate prediction id" in text
        assert "parse_ok_rate" in text
        assert "SPEC_BLOCKED" in text and "original_vs_edited" in text
        assert "snapshot_download" in text
        assert (KAGGLE_NB / name).exists()


def test_model_specific_notebook_requirements(generated: Path):
    qwen = _nb_text(generated / "notebooks/vlm_qwen2_5_vl_7b_T4x2_parallel.ipynb")[1]
    internvl = _nb_text(generated / "notebooks/vlm_internvl_8b_T4x2_parallel.ipynb")[1]
    llava = _nb_text(generated / "notebooks/vlm_llava_onevision_7b_T4x2_parallel.ipynb")[1]
    assert "/kaggle/working/hf_models/qwen2_5_vl_7b" in qwen
    assert "max_new_tokens=16" in qwen and "do_sample=False" in qwen
    assert "BitsAndBytesConfig" not in internvl
    assert "ALLOW_INTERNVL_TWO_WORKER" in internvl
    assert "shared T4x2 sequential mode" in internvl
    assert "device_map=\"auto\"" in internvl
    assert 'PROVIDER != "internvl_8b"' in internvl
    assert "image.thumbnail((384, 384))" in llava
    assert "image_grid_pinpoints = [[384, 384]]" in llava
    assert "pad_token_id" in llava
    assert "max_new_tokens=16" in llava and "do_sample=False" in llava


def test_diffusion_template_is_valid_t4x2_template(generated: Path):
    nb, text = _nb_text(generated / "notebooks/diffusion_main_scale_T4x2_TEMPLATE.ipynb")
    assert nb["nbformat"] == 4
    assert PRIVATE_POSIX not in text
    assert "CUDA_VISIBLE_DEVICES=0" in text
    assert "CUDA_VISIBLE_DEVICES=1" in text
    assert "single-GPU fallback" in text
    assert "generated_shard0.jsonl" in text
    assert "generated_shard1.jsonl" in text
    assert "diffusion_main_scale_T4x2_outputs.zip" in text
    assert "Template only" in text
    assert (KAGGLE_NB / "diffusion_main_scale_T4x2_TEMPLATE.ipynb").exists()


@pytest.mark.parametrize(
    ("bundle", "task_name", "n_rows", "n_images", "families", "nested"),
    [
        ("certvic_spurious_flip_control.zip", "pilot_eval_tasks_reviewed.jsonl", 94, 188, None, True),
        ("certvic_perception_control_scaled.zip", "pilot_eval_tasks_reviewed.jsonl", 369, 738, None, True),
        (
            "certvic_mechanism_probes.zip",
            "tasks.jsonl",
            364,
            182,
            {"context_suppression", "object_list", "region_focused", "two_step"},
            False,
        ),
        (
            "certvic_polarity_ablations.zip",
            "tasks.jsonl",
            728,
            182,
            {"negative", "pixel_only", "positive", "short"},
            False,
        ),
    ],
)
def test_bundle_contents_are_portable_manifested_and_result_free(
    generated: Path,
    bundle: str,
    task_name: str,
    n_rows: int,
    n_images: int,
    families: set[str] | None,
    nested: bool,
):
    with zipfile.ZipFile(generated / bundle) as z:
        names = z.namelist()
        rows = _bundle_rows(z, task_name)
        text = _zip_text(z)
        image_entries = _image_entries(z)
        manifest = json.loads(z.read("bundle_manifest.json"))
        referenced_images_present = _referenced_images_are_present(z, rows)
        for file_name, info in manifest["files"].items():
            assert file_name in names
            assert hashlib.sha256(z.read(file_name)).hexdigest() == info["sha256"]
    assert len(rows) == n_rows
    assert len(image_entries) == n_images
    assert manifest["produced_model_results"] is False
    assert manifest["paper_evidence"] is False
    assert manifest["contains_model_weights"] is False
    assert manifest["contains_predictions"] is False
    assert PRIVATE_POSIX.encode() not in text and PRIVATE_WIN.encode() not in text
    assert not FAKE_PRED_RE.search(text.decode("utf-8", errors="replace"))
    assert not any(name.lower().endswith(WEIGHT_SUFFIXES) for name in names)
    assert not any("prediction" in name.lower() or "pred_" in name.lower() for name in names)
    assert referenced_images_present
    assert ("source" in rows[0]) is nested
    if families is not None:
        observed = {row.get("probe_family") or row.get("ablation_family") for row in rows}
        assert observed == families
        assert "original_vs_edited" not in observed


def test_runbook_docs_cover_inputs_settings_outputs_runtime_and_ingest(generated: Path):
    required = [
        "README_RUN_ORDER.md",
        "RUN_TIME_ESTIMATES.md",
        "INPUTS_MATRIX.md",
        "OUTPUTS_MATRIX.md",
        "LOCAL_INGEST_COMMANDS.md",
        "manifest.json",
    ]
    for name in required:
        assert (generated / name).exists()
    all_docs = "\n".join((generated / name).read_text() for name in required if name.endswith(".md"))
    assert "GPU T4 x2" in all_docs
    assert "Internet: ON" in all_docs
    assert "self-download" in all_docs
    assert "single GPU" in all_docs and "T4x2" in all_docs
    assert "certvic.validation.edit_detectability" in all_docs
    assert "certvic.v7.spurious_control_integration" in all_docs
    assert "certvic.reporting.ablations" in all_docs
    assert "--pred-dir" in all_docs and "--out-dir" in all_docs
    assert "certvic.mechanisms.intervention_analysis" in all_docs
    assert "pred_<provider>_spurious_merged.jsonl" in all_docs
    assert "pred_<provider>_perception_scaled_merged.jsonl" in all_docs
    assert "pred_<provider>_mechanism.jsonl" in all_docs
    assert "pred_<provider>_polarity.jsonl" in all_docs
    assert "Main-500 diffusion" in all_docs and "~6-8 hr" in all_docs
    assert (ROOT / "docs/runbooks/KAGGLE_T4X2_PARALLEL_VLM_REMAINING_RUNS.md").exists()
    assert (ROOT / "docs/runbooks/KAGGLE_MAIN_SCALE_T4X2_TEMPLATE.md").exists()


def test_spurious_integration_remains_blocked_without_human_review(generated: Path):
    _ = generated
    status = check_readiness(ROOT)
    assert status["ready"] is False
    assert status["specificity_status"] == "blocked"
    assert status["present"]["control_task_manifest"] is True
    assert status["present"]["control_images"] is True
    assert status["present"]["quality_detectability_report"] is True
    assert all(status["present"]["predictions_per_provider"].values())
    assert status["present"]["human_visual_review_complete"] is False
