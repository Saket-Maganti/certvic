from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from certvic.cvpr.kaggle_bundle import build_bundle
from certvic.cvpr.notebook_bootstrap import NotebookBootstrapError, materialize_dataset
from certvic.cvpr.notebook_builder import NOTEBOOKS, build_suite, expected_return_zip


ZERO_EDIT = dict(NOTEBOOKS)


@pytest.mark.parametrize("name", sorted(ZERO_EDIT))
def test_zero_edit_notebook_has_no_runtime_placeholders_and_valid_python(
    tmp_path: Path, name: str
) -> None:
    build_suite(tmp_path)
    stage, provider = ZERO_EDIT[name]
    notebook = json.loads((tmp_path / name).read_text(encoding="utf-8"))
    text = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    assert "REQUIRED_USER_FILL" not in text
    assert notebook["metadata"]["certvic"]["zero_edit"] is True
    assert expected_return_zip(name, stage, provider) in text
    assert "discover_authenticated_input" in text
    assert "CONTENT_AUTHENTICATED_ANY_LOCATION" in text
    assert "CERTVIC_DISCOVERY_02_AMBIGUOUS_DISTINCT_CONTENT" in text
    assert "HF_HUB_OFFLINE" in text and "PIP_NO_INDEX" in text
    assert all(
        cell.get("execution_count") is None and not cell.get("outputs")
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]), filename=f"{name}:cell-{index}")


def test_zero_edit_accelerator_and_permission_order(tmp_path: Path) -> None:
    build_suite(tmp_path)
    for name, (stage, _provider) in ZERO_EDIT.items():
        notebook = json.loads((tmp_path / name).read_text(encoding="utf-8"))
        text = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
        if stage in {"code_smoke", "snapshot_smoke"}:
            assert "EXPECTED_GPUS = 0" in text
            assert "KAGGLE_ZERO_EDIT_CPU_ACCELERATOR_MUST_BE_OFF" in text
        else:
            assert "EXPECTED_GPUS = 2" in text
        if stage == "real_model_smoke":
            assert '"REAL_TWO_ITEM_SMOKE"' in text
            assert '"PRE_SMOKE_PERMISSIONS"' in text
            assert text.index("verify_provider_permission(") < text.index(
                "hardware = hardware_report()"
            ) < text.index("certvic.cvpr.worker")


def test_fixture_mount_uses_content_discovery_and_safe_extraction_flow(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "kaggle" / "input"
    specs = (
        ("certvic/certvic-code", "certvic_code_bundle.zip", "CODE"),
        ("certvic/certvic-configs", "certvic_configs_bundle.zip", "CONFIGS"),
        (
            "certvic/certvic-execution-tools",
            "certvic_execution_tools_bundle.zip",
            "EXECUTION_TOOLS",
        ),
        (
            "certvic/certvic-offline-wheelhouse",
            "certvic_offline_wheelhouse.zip",
            "OFFLINE_LINUX_WHEELHOUSE",
        ),
    )
    for index, (slug, _filename, bundle_type) in enumerate(specs):
        filename = ("payload.dat", "opaque", "anything.bin", "wheels.random")[index]
        mount = input_root / f"unrelated-account-title-{index}" / "nested"
        mount.mkdir(parents=True)
        build_bundle(
            mount / filename,
            {f"fixture/{bundle_type.lower()}.json": b'{"synthetic_fixture": true}\n'},
            bundle_type=bundle_type,
            study="synthetic",
            stage="zero_edit_mount_proof",
            provider=None,
            required_notebook="ZERO_EDIT_FIXTURE_ONLY",
            dataset_slug=slug,
            mount_path=f"/kaggle/input/{slug.split('/', 1)[1]}",
            external_dependency_status="SYNTHETIC_FIXTURE",
            evidence_class="SYNTHETIC_FIXTURE",
            builder_command="pytest",
            readme="Synthetic zero-edit mount proof.",
        )
        materialized = materialize_dataset(
            slug=slug,
            filename=filename,
            expected_type=bundle_type,
            input_root=input_root,
            destination=tmp_path / "kaggle" / "working" / bundle_type.lower(),
        )
        assert materialized["slug"] == slug
        assert Path(materialized["root"]).is_dir()
    with pytest.raises(
        NotebookBootstrapError,
        match="CERTVIC_DISCOVERY_01_REQUIRED_ROLE_NOT_FOUND.*MODEL_SNAPSHOT",
    ):
        materialize_dataset(
            slug="certvic/qwen2-5-vl-7b-snapshot",
            filename="qwen2_5_vl_7b_snapshot.zip",
            expected_type="MODEL_SNAPSHOT",
            input_root=input_root,
            destination=tmp_path / "missing",
        )
