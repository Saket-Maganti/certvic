from __future__ import annotations

import ast
import csv
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from certvic.cvpr.kaggle_bundle import verify_bundle
from certvic.cvpr.kagglefiles_pack import (
    ACTIVE_PROFILE,
    INPUT_FOLDERS,
    KagglefilesPackError,
    build_operator_pack,
    identify_kaggle_return,
    import_kaggle_return,
    snapshot_provisioning_notebook,
    verify_pack,
)


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "kagglefiles"


def _rows(root: Path = PACK) -> list[dict[str, str]]:
    with (root / "RUN_ORDER.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _notebook_text(path: Path) -> tuple[dict, str]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    text = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    return notebook, text


def _write_small_return(path: Path, *, profile: str = ACTIVE_PROFILE) -> None:
    environment = json.dumps({
        "schema": "certvic.cvpr.smoke_artifact.v1",
        "passed": True,
        "runtime_profile_id": profile,
        "paper_evidence": False,
    }, sort_keys=True).encode() + b"\n"
    validation = json.dumps({
        "schema": "certvic.cvpr.smoke_artifact.v1",
        "stage": "00A",
        "passed": True,
        "paper_evidence": False,
    }, sort_keys=True).encode() + b"\n"
    seed = b'{"schema":"certvic.kaggle.seed_manifest.v1","paper_evidence":false}\n'
    members = {
        "00A_environment.json": environment,
        "00A_environment_validation.json": validation,
        "seed_manifest.json": seed,
    }
    members["hash_manifest.json"] = json.dumps({
        "schema": "certvic.cvpr.smoke_hash_manifest.v1",
        "files": {
            name: hashlib.sha256(payload).hexdigest()
            for name, payload in members.items()
        },
    }, sort_keys=True).encode() + b"\n"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted(members.items()):
            archive.writestr(name, payload)


def test_exact_root_shape_and_required_runbook_set() -> None:
    assert sorted(path.name for path in PACK.iterdir() if path.is_dir()) == ["inputs", "runbooks"]
    rows = _rows()
    assert len(rows) == 23
    names = [row["runbook"] for row in rows]
    assert len(names) == len(set(names))
    assert "00C1_certvic_mock_adapter_smoke.ipynb" not in names
    assert not any(token in name.lower() for name in names for token in (
        "deprecated", "historical", "spurious_v2", "v11", "parameterized", "mock"
    ))
    assert {path.name for path in PACK.glob("runbooks/**/*.ipynb")} == set(names)


def test_every_runbook_maps_to_one_existing_input_stage_and_canonical_output() -> None:
    for row in _rows():
        assert (PACK / row["runbook_path"]).is_file()
        assert (PACK / row["matching_input_folder"]).is_dir()
        assert row["readiness"] in {
            "READY_NOW", "WAITING_FOR_PRI_RETURN", "WAITING_FOR_PRIOR_RETURN",
            "WAITING_FOR_EXTERNAL_BYTES", "WAITING_FOR_HUMAN_REVIEW",
            "CONDITIONAL_NOT_AUTHORIZED",
        }
        notebook = json.loads((PACK / row["runbook_path"]).read_text())
        text = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
        assert row["expected_output"] in text


def test_input_stages_are_truthful_and_all_present_zips_verify() -> None:
    assert tuple(sorted(path.name for path in (PACK / "inputs").iterdir())) == INPUT_FOLDERS
    observed_zips = []
    for stage in INPUT_FOLDERS:
        folder = PACK / "inputs" / stage
        status = json.loads((folder / "STATUS.json").read_text())
        assert (folder / "UPLOAD_THESE_FILES.md").is_file()
        if not status["required_files_present"]:
            assert (folder / "NOT_READY.md").is_file()
        for path in folder.glob("*.zip"):
            observed_zips.append(path)
            assert path.stat().st_size > 0
            assert verify_bundle(path)["passed"] is True
    assert {path.name for path in observed_zips} == {
        "certvic_code_bundle.zip",
        "certvic_configs_bundle.zip",
        "certvic_execution_tools_bundle.zip",
    }
    assert not (PACK / "inputs/01_CP312_WHEELHOUSE/certvic_offline_wheelhouse.zip").exists()


def test_all_notebooks_are_cleared_python_and_have_no_active_placeholders() -> None:
    for path in PACK.glob("runbooks/**/*.ipynb"):
        notebook, text = _notebook_text(path)
        assert "REQUIRED_USER_FILL" not in text
        assert not any(cell.get("outputs") or cell.get("execution_count") is not None
                       for cell in notebook["cells"] if cell["cell_type"] == "code")
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]), filename=f"{path.name}:cell-{index}")


def test_cp312_and_c2_portability_are_active() -> None:
    start = (PACK / "START_HERE.md").read_text()
    assert start.startswith(
        "OPEN ONLY THIS FOLDER FOR KAGGLE EXECUTION.\n"
        "DO NOT NAVIGATE THE REST OF THE REPOSITORY.\n"
    )
    assert "BUILD_CP312_WHEELHOUSE" in start
    assert ACTIVE_PROFILE in start
    for provider in ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"):
        payload = snapshot_provisioning_notebook(provider)
        text = payload.decode()
        assert "CONTENT_AUTHENTICATED_ANY_LOCATION" in text
        assert "CERTVIC_DISCOVERY_02_AMBIGUOUS_DISTINCT_CONTENT" in text
        assert "observed_dataset_folder" in text and "observed_archive_name" in text
        assert "Accelerator OFF" in text and "Internet ON" in text
        assert f"PROVIDER = '{provider}'" in text


def test_permission_checks_precede_gpu_and_worker_in_smoke_and_scientific_runbooks() -> None:
    for row in _rows():
        if row["stage"] not in {"REAL_MODEL_SMOKE", "EVALUATION"}:
            continue
        _, text = _notebook_text(PACK / row["runbook_path"])
        permission = text.find("verify_provider_permission(")
        environment = text.find("prepare_offline_environment(")
        worker = text.find('"-m", "certvic.cvpr.worker"')
        assert min(permission, environment, worker) >= 0
        assert permission < environment < worker


def test_pack_manifest_checksums_and_security_boundary() -> None:
    result = verify_pack(PACK)
    assert result["passed"] is True, result["errors"]
    manifest = json.loads((PACK / "PACK_MANIFEST.json").read_text())
    assert manifest["active_runtime_profile"] == ACTIVE_PROFILE
    assert manifest["human_gate_status"]["genuine_human_reviewed_true_count"] == 0
    assert manifest["Main_authorization"]["execution_allowed"] is False
    assert manifest["second_domain_authorization"]["execution_allowed"] is False
    assert all(row["paper_evidence"] is False for row in manifest["files"])
    text = "\n".join(
        path.read_text(errors="ignore")
        for path in PACK.rglob("*") if path.is_file() and path.suffix != ".zip"
    )
    assert "AKIA" not in text
    assert '"api_token"' not in text and '"kaggle_key"' not in text


def test_refresh_is_byte_deterministic_in_an_isolated_pack(tmp_path: Path) -> None:
    pack = tmp_path / "kagglefiles"
    first = build_operator_pack(pack, rebuild_common=False)
    before = {
        path.relative_to(pack).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in pack.rglob("*") if path.is_file()
    }
    second = build_operator_pack(pack, rebuild_common=False)
    after = {
        path.relative_to(pack).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in pack.rglob("*") if path.is_file()
    }
    assert before == after
    assert first["deterministic_portion_sha256"] == second["deterministic_portion_sha256"]


def test_return_importer_dry_run_profile_and_replay_guards(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    good = tmp_path / "anything.without-canonical-name"
    _write_small_return(good)
    identity = identify_kaggle_return(good, pack_root=pack)
    assert identity["return_type"] == "00A_ENVIRONMENT"
    assert identity["canonical_filename"] == "00A_environment_bundle.zip"
    dry = import_kaggle_return(good, pack_root=pack, dry_run=True)
    assert dry["status"] == "DRY_RUN_AUTHENTICATED_NOT_IMPORTED"

    wrong = tmp_path / "wrong-profile.zip"
    _write_small_return(wrong, profile="kaggle_cp310_legacy")
    with pytest.raises(KagglefilesPackError, match="wrong or missing runtime profile"):
        identify_kaggle_return(wrong, pack_root=pack)

    (pack / ".IMPORTED_RETURNS.json").write_text(json.dumps({
        "schema": "certvic.kagglefiles.imported_returns.v1",
        "returns": {identity["sha256"]: {"return_type": "00A_ENVIRONMENT"}},
    }))
    with pytest.raises(KagglefilesPackError, match="replayed return"):
        import_kaggle_return(good, pack_root=pack, dry_run=True)
