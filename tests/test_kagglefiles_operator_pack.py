from __future__ import annotations

import ast
import csv
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

import certvic.cvpr.kagglefiles_pack as kagglefiles_pack_module
from certvic.cvpr.content_discovery import authenticate_content_path
from certvic.cvpr.kaggle_bundle import build_bundle, verify_bundle
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
KNOWN_C7_CODE_CONTENT_IDENTITY = (
    "bd645b467af1a19859159d3bef3d06da39d8b87a942ec4a87038d4ffc9ec37d7"
)
KNOWN_C7_CODE_ARCHIVE_SHA256 = (
    "ef7fe5bd0d971e0d6ef232b9c231864f690839c7e368bad4ff78415ec982e908"
)
KNOWN_C7_00A_ARCHIVE_SHA256 = (
    "91d84926ac44195977889ede036df15e0b577278826b5f1142e77e1a66e71a05"
)


def _rows(root: Path = PACK) -> list[dict[str, str]]:
    with (root / "RUN_ORDER.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _notebook_text(path: Path) -> tuple[dict, str]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    text = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
    return notebook, text


def _write_small_return(
    path: Path,
    *,
    profile: str = ACTIVE_PROFILE,
    marker: str = "",
    code_bundle_hash: str | None = None,
) -> None:
    environment = json.dumps({
        "schema": "certvic.cvpr.smoke_artifact.v1",
        "passed": True,
        "runtime_profile_id": profile,
        "fixture_marker": marker,
        "paper_evidence": False,
    }, sort_keys=True).encode() + b"\n"
    if code_bundle_hash is not None:
        environment_value = json.loads(environment)
        environment_value["code_bundle_hash"] = code_bundle_hash
        environment = json.dumps(environment_value, sort_keys=True).encode() + b"\n"
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


def _write_code_bundle(path: Path, *, payload: bytes = b"current code\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    build_bundle(
        path,
        {"certvic/fixture.py": payload},
        bundle_type="CODE",
        study="all",
        stage="bootstrap",
        provider=None,
        required_notebook="00A.ipynb",
        dataset_slug="fixture/code",
        mount_path="/kaggle/input/code",
        external_dependency_status="SYNTHETIC_FIXTURE",
        evidence_class="SYNTHETIC_FIXTURE",
        builder_command="pytest",
        validation_command="pytest",
        readme="Synthetic CODE fixture.",
    )
    return path


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
        assert "representation" in text and "discovered_path" in text
        assert "early_verify_archive" in text and "early_verify_directory" in text
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
    assert Path(identity["destination"]) == tmp_path / "data/runtime/00A_environment_bundle.zip"
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


def test_return_importer_writes_portable_ledger_and_preserves_replay_guard(tmp_path: Path) -> None:
    project = tmp_path / "project"
    pack = project / "kagglefiles"
    pack.mkdir(parents=True)
    source = tmp_path / "00A-return.zip"
    _write_small_return(source)

    imported = import_kaggle_return(source, pack_root=pack)
    ledger = json.loads((pack / ".IMPORTED_RETURNS.json").read_text())
    record = ledger["returns"][imported["sha256"]]
    assert record["canonical_destination"] == "data/runtime/00A_environment_bundle.zip"
    assert str(project) not in json.dumps(ledger)
    assert Path(imported["destination"]).read_bytes() == source.read_bytes()

    with pytest.raises(KagglefilesPackError, match="replayed return"):
        import_kaggle_return(source, pack_root=pack, dry_run=True)


def test_return_importer_migrates_in_project_absolute_ledger_path(tmp_path: Path) -> None:
    project = tmp_path / "project"
    pack = project / "kagglefiles"
    pack.mkdir(parents=True)
    source = tmp_path / "00A-return.zip"
    _write_small_return(source)
    digest = hashlib.sha256(b"historical return").hexdigest()
    ledger_path = pack / ".IMPORTED_RETURNS.json"
    ledger_path.write_text(json.dumps({
        "schema": "certvic.kagglefiles.imported_returns.v1",
        "returns": {
            digest: {
                "return_type": "00A_ENVIRONMENT",
                "canonical_destination": str(project / "data/runtime/historical.zip"),
                "size": 19,
                "paper_evidence": False,
                "authenticated_code_bundle_sha256": "a" * 64,
                "current_code_bundle_sha256": "b" * 64,
            },
        },
    }))

    import_kaggle_return(source, pack_root=pack, dry_run=True)
    migrated = json.loads(ledger_path.read_text())
    assert set(migrated["returns"]) == {digest}
    assert (
        migrated["returns"][digest]["canonical_destination"]
        == "data/runtime/historical.zip"
    )
    record = migrated["returns"][digest]
    assert record["authenticated_code_content_identity_sha256"] == "a" * 64
    assert record["current_code_archive_sha256"] == "b" * 64
    assert "authenticated_code_bundle_sha256" not in record
    assert "current_code_bundle_sha256" not in record


def test_return_importer_rejects_out_of_project_ledger_path(tmp_path: Path) -> None:
    project = tmp_path / "project"
    pack = project / "kagglefiles"
    pack.mkdir(parents=True)
    source = tmp_path / "00A-return.zip"
    _write_small_return(source)
    ledger_path = pack / ".IMPORTED_RETURNS.json"
    original = {
        "schema": "certvic.kagglefiles.imported_returns.v1",
        "returns": {
            hashlib.sha256(b"historical return").hexdigest(): {
                "return_type": "00A_ENVIRONMENT",
                "canonical_destination": str(tmp_path / "outside.zip"),
                "size": 19,
                "paper_evidence": False,
            },
        },
    }
    ledger_path.write_text(json.dumps(original))

    with pytest.raises(KagglefilesPackError, match="outside the derived project root"):
        import_kaggle_return(source, pack_root=pack, dry_run=True)
    assert json.loads(ledger_path.read_text()) == original


def test_return_importer_rejects_conflicting_canonical_bytes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    pack = project / "kagglefiles"
    pack.mkdir(parents=True)
    source = tmp_path / "00A-return.zip"
    _write_small_return(source)
    destination = project / "data/runtime/00A_environment_bundle.zip"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"different authenticated return bytes")

    with pytest.raises(KagglefilesPackError, match="contains different bytes"):
        import_kaggle_return(source, pack_root=pack, dry_run=True)


def test_return_importer_archives_exact_superseded_destination(tmp_path: Path) -> None:
    project = tmp_path / "project"
    pack = project / "kagglefiles"
    pack.mkdir(parents=True)
    old_source = tmp_path / "old-00A.zip"
    new_source = tmp_path / "new-00A.zip"
    _write_small_return(old_source, marker="old")
    _write_small_return(new_source, marker="new")
    old_digest = hashlib.sha256(old_source.read_bytes()).hexdigest()
    destination = project / "data/runtime/00A_environment_bundle.zip"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(old_source.read_bytes())
    (pack / ".IMPORTED_RETURNS.json").write_text(json.dumps({
        "schema": "certvic.kagglefiles.imported_returns.v1",
        "returns": {
            old_digest: {
                "return_type": "00A_ENVIRONMENT",
                "canonical_destination": "data/runtime/00A_environment_bundle.zip",
                "size": old_source.stat().st_size,
                "gating_status": "SUPERSEDED_CODE_IDENTITY",
                "paper_evidence": False,
            },
        },
    }))

    imported = import_kaggle_return(new_source, pack_root=pack)
    history = (
        project
        / "data/runtime/superseded"
        / f"00A_environment_bundle.{old_digest}.zip"
    )
    assert history.read_bytes() == old_source.read_bytes()
    assert destination.read_bytes() == new_source.read_bytes()
    ledger = json.loads((pack / ".IMPORTED_RETURNS.json").read_text())
    assert ledger["returns"][old_digest]["canonical_destination"] == (
        f"data/runtime/superseded/00A_environment_bundle.{old_digest}.zip"
    )
    assert ledger["returns"][imported["sha256"]]["gating_status"] == "ACTIVE_CODE_IDENTITY"


def test_return_importer_rejects_superseded_00a_code_identity(tmp_path: Path) -> None:
    project = tmp_path / "project"
    pack = project / "kagglefiles"
    common = pack / "inputs/00_COMMON"
    common.mkdir(parents=True)
    code_bundle = common / "certvic_code_bundle.zip"
    _write_code_bundle(code_bundle)
    source = tmp_path / "stale-00A.zip"
    _write_small_return(source, code_bundle_hash=hashlib.sha256(b"old code").hexdigest())

    with pytest.raises(KagglefilesPackError, match="superseded CODE bundle identity"):
        import_kaggle_return(source, pack_root=pack, dry_run=True)


def test_00a_guard_uses_verified_code_content_identity(tmp_path: Path) -> None:
    project = tmp_path / "project"
    pack = project / "kagglefiles"
    code_bundle = _write_code_bundle(
        pack / "inputs/00_COMMON/certvic_code_bundle.zip"
    )
    content_identity = authenticate_content_path(code_bundle, "CODE")
    archive_sha256 = hashlib.sha256(code_bundle.read_bytes()).hexdigest()
    assert content_identity != archive_sha256

    source = tmp_path / "current-00A.zip"
    _write_small_return(source, code_bundle_hash=content_identity)
    imported = import_kaggle_return(source, pack_root=pack)

    assert imported["status"] == "AUTHENTICATED_RETURN_IMPORTED_UNCHANGED"
    assert imported["current_code_content_identity_sha256"] == content_identity
    assert imported["current_code_archive_sha256"] == archive_sha256
    ledger = json.loads((pack / ".IMPORTED_RETURNS.json").read_text())
    record = ledger["returns"][imported["sha256"]]
    assert record["gating_status"] == "ACTIVE_CODE_IDENTITY"
    assert record["authenticated_code_content_identity_sha256"] == content_identity
    assert record["current_code_content_identity_sha256"] == content_identity
    assert record["current_code_archive_sha256"] == archive_sha256


def test_00a_guard_rejects_corrupt_code_archive(tmp_path: Path) -> None:
    project = tmp_path / "project"
    pack = project / "kagglefiles"
    code_bundle = _write_code_bundle(
        pack / "inputs/00_COMMON/certvic_code_bundle.zip"
    )
    content_identity = authenticate_content_path(code_bundle, "CODE")
    with zipfile.ZipFile(code_bundle, "a") as archive:
        archive.writestr("certvic/fixture.py", b"corrupt replacement\n")

    source = tmp_path / "current-00A.zip"
    _write_small_return(source, code_bundle_hash=content_identity)
    with pytest.raises(
        KagglefilesPackError,
        match="CODE bundle failed authenticated content verification",
    ):
        import_kaggle_return(source, pack_root=pack, dry_run=True)


def test_00a_reconciliation_uses_content_identity_for_gating(tmp_path: Path) -> None:
    project = tmp_path / "project"
    pack = project / "kagglefiles"
    code_bundle = _write_code_bundle(
        pack / "inputs/00_COMMON/certvic_code_bundle.zip"
    )
    content_identity = authenticate_content_path(code_bundle, "CODE")
    archive_sha256 = hashlib.sha256(code_bundle.read_bytes()).hexdigest()
    current = project / "data/runtime/current.zip"
    old = project / "data/runtime/old.zip"
    current.parent.mkdir(parents=True)
    _write_small_return(current, code_bundle_hash=content_identity)
    _write_small_return(old, code_bundle_hash="c" * 64)
    current_digest = hashlib.sha256(current.read_bytes()).hexdigest()
    old_digest = hashlib.sha256(old.read_bytes()).hexdigest()
    ledger_path = pack / ".IMPORTED_RETURNS.json"
    ledger_path.write_text(json.dumps({
        "schema": "certvic.kagglefiles.imported_returns.v1",
        "returns": {
            current_digest: {
                "return_type": "00A_ENVIRONMENT",
                "canonical_destination": "data/runtime/current.zip",
            },
            old_digest: {
                "return_type": "00A_ENVIRONMENT",
                "canonical_destination": "data/runtime/old.zip",
            },
        },
    }))

    kagglefiles_pack_module._reconcile_imported_00a_gating(pack)

    records = json.loads(ledger_path.read_text())["returns"]
    assert records[current_digest]["gating_status"] == "ACTIVE_CODE_IDENTITY"
    assert records[old_digest]["gating_status"] == "SUPERSEDED_CODE_IDENTITY"
    for record in records.values():
        assert record["current_code_content_identity_sha256"] == content_identity
        assert record["current_code_archive_sha256"] == archive_sha256


def test_known_genuine_00a_metadata_uses_distinct_identity_domains(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    known_metadata = {
        "return_archive_sha256": KNOWN_C7_00A_ARCHIVE_SHA256,
        "code_content_identity_sha256": KNOWN_C7_CODE_CONTENT_IDENTITY,
        "code_archive_sha256": KNOWN_C7_CODE_ARCHIVE_SHA256,
    }
    assert known_metadata["code_content_identity_sha256"] != (
        known_metadata["code_archive_sha256"]
    )
    project = tmp_path / "project"
    pack = project / "kagglefiles"
    code_bundle = pack / "inputs/00_COMMON/certvic_code_bundle.zip"
    code_bundle.parent.mkdir(parents=True)
    code_bundle.write_bytes(b"copied current CODE archive metadata fixture")
    monkeypatch.setattr(
        kagglefiles_pack_module,
        "_code_bundle_identities",
        lambda path: (
            known_metadata["code_content_identity_sha256"],
            known_metadata["code_archive_sha256"],
        ),
    )
    source = tmp_path / "known-metadata-00A.zip"
    _write_small_return(
        source,
        code_bundle_hash=known_metadata["code_content_identity_sha256"],
    )

    result = import_kaggle_return(source, pack_root=pack, dry_run=True)

    assert result["status"] == "DRY_RUN_AUTHENTICATED_NOT_IMPORTED"
    assert result["current_code_content_identity_sha256"] == (
        known_metadata["code_content_identity_sha256"]
    )
    assert result["current_code_archive_sha256"] == (
        known_metadata["code_archive_sha256"]
    )


def test_real_import_ledger_contains_no_private_absolute_path() -> None:
    ledger_path = PACK / ".IMPORTED_RETURNS.json"
    if not ledger_path.exists():
        pytest.skip("no machine-local imported-return ledger in this checkout")
    text = ledger_path.read_text()
    assert all(prefix not in text for prefix in ("/Users/", "/home/", "/root/", "~"))
