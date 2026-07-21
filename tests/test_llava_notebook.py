"""Static checks on the self-download LLaVA-OneVision Kaggle notebook.

CPU-local, no heavy deps, no network. Mirrors the InternVL notebook guarantees with the
LLaVA-OneVision specifics (native transformers model + processor, not remote-code .chat()).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "notebooks/kaggle/certvic_llava_ov_T4_eval_SELF_DOWNLOAD.ipynb"


def _load():
    nb = json.loads(NB.read_text())
    src = "\n".join(
        c["source"] if isinstance(c["source"], str) else "".join(c["source"]) for c in nb["cells"]
    )
    return nb, src


def test_notebook_exists_and_valid():
    assert NB.exists(), f"missing notebook {NB}"
    nb, _ = _load()
    assert nb["nbformat"] == 4 and len(nb["cells"]) >= 8


def test_code_cells_compile():
    nb, _ = _load()
    for c in nb["cells"]:
        if c["cell_type"] == "code":
            ast.parse(c["source"] if isinstance(c["source"], str) else "".join(c["source"]))


def test_self_download_no_weights_input():
    _, src = _load()
    assert "snapshot_download" in src
    assert "llava-hf/llava-onevision-qwen2-7b-ov-hf" in src
    assert "/kaggle/working/hf_models/llava-ov-7b" in src
    assert "WEIGHTS" not in src
    assert "/kaggle/input/llava" not in src.lower()


def test_no_machine_local_paths():
    _, src = _load()
    assert "/Users/" not in src


def test_native_llava_api_and_transformers_pin():
    _, src = _load()
    assert "transformers==4.49.0" in src  # has LlavaOnevision, pre-4.50 churn
    assert "LlavaOnevisionForConditionalGeneration" in src
    assert "apply_chat_template" in src  # processor-based, not remote-code .chat()


def test_bf16_multigpu_default_no_bitsandbytes():
    _, src = _load()
    assert 'device_map="auto"' in src
    assert "load_in_8bit" not in src
    assert "bitsandbytes>=0.45.0" in src  # single-GPU 4-bit fallback only


def test_flat_to_taskitem_projection():
    _, src = _load()
    assert "EditSpec" in src and "SourceImageRecord" in src and "TaskItem(" in src
    assert "'source' not in rows[0]" in src


def test_gates_provider_and_outputs():
    _, src = _load()
    assert "provider='llava_onevision_7b'" in src or "llava_onevision_7b" in src
    assert "evidence_run=True" in src and "strict_leakage=True" in src
    assert "main200_llava_onevision_7b_presence" in src and "main200_llava_onevision_7b_control" in src
    assert "pred_llava_onevision_7b_presence_merged.jsonl" in src
    assert "pred_llava_onevision_7b_control_merged.jsonl" in src
