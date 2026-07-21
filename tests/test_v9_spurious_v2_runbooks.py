from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

import nbformat
import pytest

from scripts.validate_t4x2_notebooks import validate


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = {
    "notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb": "qwen2_5_vl_7b",
    "notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb": "internvl_8b",
    "notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb": "llava_onevision_7b",
}
FORBIDDEN_TEXT = re.compile(r"(fake|mock)[_-]?(prediction|preds?|results?)", re.I)


@pytest.fixture(scope="module", autouse=True)
def _ensure_spurious_v2_dist_docs():
    if not (ROOT / "dist/kaggle_remaining_runs/SPURIOUS_V2_INPUTS_MATRIX.md").exists():
        subprocess.run(
            [sys.executable, "scripts/build_spurious_v2_control.py"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )


def _nb_text(path: Path) -> tuple[dict, str]:
    nb = nbformat.read(path, as_version=4)
    text = "\n".join(
        cell["source"] if isinstance(cell["source"], str) else "".join(cell["source"])
        for cell in nb["cells"]
    )
    return nb, text


def test_spurious_v2_notebooks_are_valid_and_safe():
    for raw, provider in NOTEBOOKS.items():
        nb, text = _nb_text(ROOT / raw)
        assert nb["nbformat"] == 4
        assert sum(len(cell.get("outputs", [])) for cell in nb["cells"] if cell["cell_type"] == "code") == 0
        assert "/Users/" not in text
        assert not FORBIDDEN_TEXT.search(text)
        assert f'PROVIDER = "{provider}"' in text
        assert 'RUN_TAG = "spurious_v2"' in text
        assert "CUDA_VISIBLE_DEVICES" in text
        assert "CUDA_VISIBLE_DEVICES=0" in text
        assert "CUDA_VISIBLE_DEVICES=1" in text
        assert "single-GPU fallback" in text
        assert 'merged_name = f"pred_{PROVIDER}_{RUN_TAG}_merged.jsonl"' in text
        assert 'f"{PROVIDER}_{RUN_TAG}_preds.zip"' in text
        assert 'f"summary_{PROVIDER}_{RUN_TAG}.json"' in text
        assert 'f"runtime_manifest_{PROVIDER}_{RUN_TAG}.json"' in text
        assert "parse_ok_rate" in text
        assert "certvic.eval.run_eval" in text
        assert "ovlm.OpenVLMProvider.answer" in text
        assert "subprocess.Popen" in text
        assert "Launching two parallel GPU workers" in text
        assert "prediction key mismatch" in text
        assert "certification-critical parse failures block packaging" in text
        assert "certvic.v11.spurious_v2.kaggle_output_manifest.v3" in text
        assert "merged_predictions_sha256" in text
        assert "task_file_sha256" in text
        assert 'run_prefix = "v9" if RUN_TAG == "spurious_v2" else "remaining"' in text
        assert 'evidence_run=(RUN_TAG != "spurious_v2")' in text
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                ast.parse(cell["source"])


def test_spurious_v2_runbook_docs_match_notebook_outputs():
    runbook = (ROOT / "docs/runbooks/KAGGLE_SPURIOUS_V2_T4X2_RUNBOOK.md").read_text()
    inputs = (ROOT / "dist/kaggle_remaining_runs/SPURIOUS_V2_INPUTS_MATRIX.md").read_text()
    ingest = (ROOT / "dist/kaggle_remaining_runs/SPURIOUS_V2_LOCAL_INGEST_COMMANDS.md").read_text()
    all_docs = "\n".join([runbook, inputs, ingest])
    assert "certvic_spurious_v2_control.zip" in all_docs
    assert "certvic_kaggle_main200_bundle.zip" in all_docs
    assert "pred_<provider>_spurious_v2_merged.jsonl" in all_docs
    assert "<provider>_spurious_v2_preds.zip" in all_docs
    assert "scripts/import_v9_spurious_v2_outputs.py" in all_docs
    assert "T4x2" in all_docs
    assert "paper_evidence=false" in all_docs


def test_cpu_static_validator_passes_all_runnable_t4x2_vlm_notebooks():
    result = validate()
    assert result["mode"] == "CPU_STATIC_ONLY_NOTEBOOKS_NOT_EXECUTED"
    assert result["n_notebooks"] == 6
    assert result["passed"], result


def test_cpu_static_validator_catches_broken_parallel_launch(tmp_path):
    source = ROOT / "notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb"
    nb = nbformat.read(source, as_version=4)
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.source = cell.source.replace("subprocess.Popen", "subprocess.run")
    broken = tmp_path / source.name
    nbformat.write(nb, broken)
    result = validate([broken])
    assert result["passed"] is False
    assert any("parallel subprocess launch" in error for error in result["notebooks"][0]["errors"])
