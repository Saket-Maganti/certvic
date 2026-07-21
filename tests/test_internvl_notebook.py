"""Static checks on the self-download InternVL Kaggle notebook.

CPU-local, no heavy deps, no network: validate the notebook is well-formed and that its
guarantees hold (self-download, no weights input, pinned transformers, gates intact, no
machine-local paths). No model is run here.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

NB = Path(__file__).resolve().parents[1] / "notebooks/kaggle/certvic_internvl_T4_eval_SELF_DOWNLOAD.ipynb"


def _load():
    nb = json.loads(NB.read_text())
    src = "\n".join(
        c["source"] if isinstance(c["source"], str) else "".join(c["source"]) for c in nb["cells"]
    )
    return nb, src


def test_notebook_exists_and_valid():
    assert NB.exists(), f"missing notebook {NB}"
    nb, _ = _load()
    assert nb["nbformat"] == 4
    assert len(nb["cells"]) >= 8


def test_code_cells_compile():
    nb, _ = _load()
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] == "code":
            src = c["source"] if isinstance(c["source"], str) else "".join(c["source"])
            ast.parse(src)  # raises SyntaxError on bad cell


def test_self_download_present():
    _, src = _load()
    assert "snapshot_download" in src
    assert "OpenGVLab/InternVL2-8B" in src
    assert "/kaggle/working/hf_models/internvl2-8b" in src  # runtime cache path


def test_no_weights_input_required():
    _, src = _load()
    assert "WEIGHTS" not in src  # the WEIGHTS config variable is removed
    assert "/kaggle/input/internvl" not in src.lower()  # no attached weights dataset


def test_pinned_compatible_transformers():
    _, src = _load()
    assert "transformers==4.37.2" in src  # avoids all_tied_weights_keys / GenerationMixin break


def test_no_broken_bitsandbytes_and_bf16_multigpu():
    _, src = _load()
    # The broken 0.43.x pin (triton.ops / missing CUDA 12.8 binary) must be gone.
    assert "bitsandbytes==0.43.1" not in src
    # Default path is bf16 sharded across GPUs (no bitsandbytes); 8-bit single-GPU load removed.
    assert "split_model" in src and "device_map=split_model()" in src
    assert "load_in_8bit=True" not in src
    # Single-GPU fallback installs a current bitsandbytes on demand.
    assert "bitsandbytes>=0.45.0" in src


def test_no_machine_local_paths():
    _, src = _load()
    assert "/Users/" not in src


def test_projects_flat_tasks_to_taskitem_schema():
    # run_eval needs the strict nested TaskItem schema; the presence bundle ships the flat
    # reviewed schema. The notebook must project it (and pass the already-nested control through).
    _, src = _load()
    assert "EditSpec" in src and "SourceImageRecord" in src and "TaskItem(" in src
    assert "'source' not in rows[0]" in src  # convert-only-if-flat guard


def test_gates_and_provider_intact():
    _, src = _load()
    assert "internvl_8b" in src
    assert "evidence_run=True" in src
    assert "strict_leakage=True" in src
    assert "main200_internvl_8b_presence" in src
    assert "main200_internvl_8b_control" in src


def test_outputs_named_as_expected():
    _, src = _load()
    assert "pred_internvl_8b_presence_merged.jsonl" in src
    assert "pred_internvl_8b_control_merged.jsonl" in src
    assert "internvl_preds.zip" in src


@pytest.mark.parametrize("needle", ["build_transform", "dynamic_preprocess", "load_image", "model.chat"])
def test_official_internvl_helpers(needle):
    _, src = _load()
    assert needle in src
