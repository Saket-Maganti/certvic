from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import certvic.cvpr.doctor as doctor_module
from certvic.cvpr.content_discovery import authenticate_content_path
from certvic.cvpr.kaggle_bundle import build_bundle
from certvic.cvpr.kagglefiles_pack import (
    KagglefilesPackError,
    import_kaggle_return,
)
from certvic.cvpr.run_graph import graph_status, load_graph
from local_operator.runtime_materializer import (
    ACTIVE_PROFILE,
    RuntimeMaterializationError,
    clean_operator_metadata,
    inspect_runtime_archive,
    materialize_imported_runtime_records,
    materialize_runtime_archive,
)


ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")


def _code_bundle(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    build_bundle(
        path,
        {"certvic/fixture.py": b"runtime materializer fixture\n"},
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
    return authenticate_content_path(path, "CODE")


def _runtime_return(
    path: Path,
    *,
    provider: str | None = None,
    code_identity: str | None = None,
    profile: str = ACTIVE_PROFILE,
    passed: bool = True,
    paper_evidence: bool = False,
    declared_digest: str | None = None,
) -> bytes:
    primary_name = (
        "00A_environment.json"
        if provider is None
        else f"00B_{provider}_snapshot.json"
    )
    validation_name = primary_name.removesuffix(".json") + "_validation.json"
    primary = {
        "schema": "certvic.cvpr.smoke_artifact.v1",
        "stage": "00A" if provider is None else "00B",
        "provider": provider or "all",
        "passed": passed,
        "runtime_profile_id": profile,
        "paper_evidence": paper_evidence,
    }
    if provider is None:
        primary["code_bundle_hash"] = code_identity
    members = {
        primary_name: json.dumps(primary, indent=2, sort_keys=True).encode() + b"\n",
        validation_name: json.dumps({
            "schema": "certvic.cvpr.smoke_artifact.v1",
            "passed": True,
            "provider": provider or "all",
            "paper_evidence": False,
        }, sort_keys=True).encode() + b"\n",
        "seed_manifest.json": b'{"paper_evidence":false}\n',
    }
    hashes = {
        name: hashlib.sha256(payload).hexdigest()
        for name, payload in members.items()
    }
    if declared_digest is not None:
        hashes[primary_name] = declared_digest
    members["hash_manifest.json"] = json.dumps({
        "schema": "certvic.cvpr.smoke_hash_manifest.v1",
        "files": hashes,
    }, sort_keys=True).encode() + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted(members.items()):
            archive.writestr(name, payload)
    return members[primary_name]


def _project(tmp_path: Path) -> tuple[Path, Path, str]:
    project = tmp_path / "project"
    pack = project / "kagglefiles"
    identity = _code_bundle(
        pack / "inputs/00_COMMON/certvic_code_bundle.zip"
    )
    return project, pack, identity


def _record_import(pack: Path, archive: Path, return_type: str) -> str:
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    project = pack.parent
    ledger = {
        "schema": "certvic.kagglefiles.imported_returns.v1",
        "returns": {
            digest: {
                "return_type": return_type,
                "canonical_destination": archive.relative_to(project).as_posix(),
                "size": archive.stat().st_size,
                "paper_evidence": False,
            },
        },
    }
    (pack / ".IMPORTED_RETURNS.json").write_text(
        json.dumps(ledger),
        encoding="utf-8",
    )
    return digest


def test_authenticated_00a_materializes_exact_bytes_and_is_idempotent(
    tmp_path: Path,
) -> None:
    project, pack, code_identity = _project(tmp_path)
    archive = project / "data/runtime/00A_environment_bundle.zip"
    expected = _runtime_return(archive, code_identity=code_identity)
    digest = _record_import(pack, archive, "00A_ENVIRONMENT")

    first = materialize_runtime_archive(archive, pack_root=pack)
    second = materialize_runtime_archive(archive, pack_root=pack)

    destination = project / "data/runtime/00A_environment.json"
    assert destination.read_bytes() == expected
    assert first == second
    assert first["source_archive_sha256"] == digest
    assert first["authenticated_member_sha256"] == hashlib.sha256(expected).hexdigest()
    assert first["paper_evidence"] is False
    ledger = json.loads((pack / ".IMPORTED_RETURNS.json").read_text())
    assert ledger["returns"][digest]["materialization"] == {
        key: value
        for key, value in first.items()
        if key not in {"status", "idempotent"}
    }


def test_already_imported_00a_backfills_and_replay_stays_rejected(
    tmp_path: Path,
) -> None:
    project, pack, code_identity = _project(tmp_path)
    source = tmp_path / "downloaded-00A.zip"
    expected = _runtime_return(source, code_identity=code_identity)
    imported = import_kaggle_return(source, pack_root=pack)
    destination = Path(imported["destination"])
    assert not (project / "data/runtime/00A_environment.json").exists()

    result = materialize_imported_runtime_records(pack_root=pack)

    assert result["materialized"] == 1
    assert (project / "data/runtime/00A_environment.json").read_bytes() == expected
    assert destination.read_bytes() == source.read_bytes()
    with pytest.raises(KagglefilesPackError, match="replayed return"):
        import_kaggle_return(source, pack_root=pack, dry_run=True)


def test_operator_import_materializes_arbitrarily_named_00a(
    tmp_path: Path,
) -> None:
    project, pack, code_identity = _project(tmp_path)
    source = tmp_path / "download-with-arbitrary-name.bin"
    expected = _runtime_return(source, code_identity=code_identity)

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "kagglefiles/import_kaggle_return.py"),
            str(source),
            "--pack-root",
            str(pack),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert (project / "data/runtime/00A_environment.json").read_bytes() == expected
    assert (
        project / "data/runtime/00A_environment_bundle.zip"
    ).read_bytes() == source.read_bytes()


def test_conflicting_existing_canonical_json_is_rejected(tmp_path: Path) -> None:
    project, pack, code_identity = _project(tmp_path)
    archive = project / "data/runtime/00A_environment_bundle.zip"
    _runtime_return(archive, code_identity=code_identity)
    _record_import(pack, archive, "00A_ENVIRONMENT")
    destination = project / "data/runtime/00A_environment.json"
    destination.write_bytes(b"conflicting authenticated-looking bytes\n")

    with pytest.raises(RuntimeMaterializationError, match="conflicting bytes"):
        materialize_runtime_archive(archive, pack_root=pack)


def test_corrupt_and_hash_mismatched_archives_are_rejected(tmp_path: Path) -> None:
    _, pack, code_identity = _project(tmp_path)
    corrupt = tmp_path / "00A_environment_bundle.zip"
    corrupt.write_bytes(b"not a ZIP")
    with pytest.raises(RuntimeMaterializationError, match="corrupt"):
        inspect_runtime_archive(corrupt, pack_root=pack)

    mismatched = tmp_path / "nested/00A_environment_bundle.zip"
    _runtime_return(
        mismatched,
        code_identity=code_identity,
        declared_digest="0" * 64,
    )
    with pytest.raises(RuntimeMaterializationError, match="hash manifest mismatch"):
        inspect_runtime_archive(mismatched, pack_root=pack)


@pytest.mark.parametrize("attack", ["traversal", "duplicate", "symlink", "fifo"])
def test_unsafe_archive_members_are_rejected(
    tmp_path: Path,
    attack: str,
) -> None:
    _, pack, code_identity = _project(tmp_path)
    archive_path = tmp_path / "00A_environment_bundle.zip"
    _runtime_return(archive_path, code_identity=code_identity)
    with zipfile.ZipFile(archive_path, "a") as archive:
        if attack == "traversal":
            archive.writestr("../escape.json", b"{}\n")
        elif attack == "duplicate":
            archive.writestr("00A_environment.json", b"{}\n")
        else:
            info = zipfile.ZipInfo(f"{attack}.member")
            info.create_system = 3
            kind = stat.S_IFLNK if attack == "symlink" else stat.S_IFIFO
            info.external_attr = (kind | 0o644) << 16
            archive.writestr(info, b"target")

    with pytest.raises(RuntimeMaterializationError, match="unsafe|duplicate"):
        inspect_runtime_archive(archive_path, pack_root=pack)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"code_identity": "f" * 64}, "superseded CODE"),
        ({"profile": "kaggle_cp310_legacy"}, "profile mismatch"),
        ({"passed": False}, "failed runtime return"),
        ({"paper_evidence": True}, "paper_evidence=false"),
    ],
)
def test_00a_runtime_contract_failures_are_rejected(
    tmp_path: Path,
    overrides: dict[str, object],
    message: str,
) -> None:
    _, pack, code_identity = _project(tmp_path)
    archive = tmp_path / "00A_environment_bundle.zip"
    options = {"code_identity": code_identity, **overrides}
    _runtime_return(archive, **options)

    with pytest.raises(RuntimeMaterializationError, match=message):
        inspect_runtime_archive(archive, pack_root=pack)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_each_00b_provider_materializes_to_doctor_path(
    tmp_path: Path,
    provider: str,
) -> None:
    project, pack, _ = _project(tmp_path)
    archive = (
        project
        / "data/runtime"
        / f"00B_{provider}_snapshot_bundle.zip"
    )
    expected = _runtime_return(archive, provider=provider)
    _record_import(pack, archive, f"00B_SNAPSHOT_SMOKE:{provider}")

    result = materialize_runtime_archive(archive, pack_root=pack)

    destination = project / "data/runtime" / f"00B_{provider}_snapshot.json"
    assert destination.read_bytes() == expected
    assert result["provider"] == provider
    assert result["paper_evidence"] is False


def test_wrong_00b_provider_is_rejected(tmp_path: Path) -> None:
    _, pack, _ = _project(tmp_path)
    archive = tmp_path / "00B_qwen2_5_vl_7b_snapshot_bundle.zip"
    _runtime_return(archive, provider="internvl_8b")

    with pytest.raises(RuntimeMaterializationError, match="exactly one primary"):
        inspect_runtime_archive(archive, pack_root=pack)


def test_backfill_advances_doctor_and_run_graph(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, pack, code_identity = _project(tmp_path)
    archive = project / "data/runtime/00A_environment_bundle.zip"
    _runtime_return(archive, code_identity=code_identity)
    _record_import(pack, archive, "00A_ENVIRONMENT")
    for entry in doctor_module.REQUIRED_LOCAL:
        path = project / entry
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        else:
            path.mkdir(parents=True, exist_ok=True)
    study = project / "configs/studies/specificity_confirmatory_cvpr.yaml"
    study.write_text(
        "paper_evidence: false\nexecution_allowed: false\nexecution:\n"
        "  expected_providers: [qwen2_5_vl_7b, internvl_8b, llava_onevision_7b]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        doctor_module,
        "_notebook_check",
        lambda root: {
            "count": 20,
            "expected_count": 20,
            "invalid": [],
            "code_cells_with_outputs": 0,
            "passed": True,
        },
    )
    monkeypatch.setattr(
        doctor_module,
        "_multi_account_portability_check",
        lambda root: {"passed": True},
    )
    monkeypatch.setattr(doctor_module, "unresolved_freeze_fields", lambda value: [])
    import certvic.cvpr.protocol_authority as protocol_authority

    monkeypatch.setattr(
        protocol_authority,
        "validate_authority",
        lambda root: {"passed": True, "errors": []},
    )
    assert doctor_module.diagnose(project)["state"] == "READY_FOR_00A"

    materialize_runtime_archive(archive, pack_root=pack)

    assert doctor_module.diagnose(project)["state"] == "READY_FOR_00B"
    (project / "reports/max_ceiling_upgrade").mkdir(parents=True, exist_ok=True)
    (project / "reports/max_ceiling_upgrade/doctor.json").touch()
    (project / "kaggle_uploads/01_wheelhouse").mkdir(parents=True, exist_ok=True)
    (project / "kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip").touch()
    (project / "kaggle_uploads/02_snapshots").mkdir(parents=True, exist_ok=True)
    for name in (
        "qwen2_5_vl_7b_snapshot.zip",
        "internvl2_8b_snapshot.zip",
        "llava_onevision_7b_snapshot.zip",
    ):
        (project / "kaggle_uploads/02_snapshots" / name).touch()
    notebook = project / "notebooks/kaggle/cvpr/00B_certvic_model_snapshot_smoke.ipynb"
    notebook.parent.mkdir(parents=True, exist_ok=True)
    notebook.touch()
    graph = load_graph(ROOT / "configs/execution/certvic_run_graph.yaml")
    status = graph_status(graph, project)
    rows = {row["id"]: row for row in status["nodes"]}
    assert rows["run_00a"]["status"] == "COMPLETE"
    assert rows["run_00b"]["status"] == "READY"
    assert rows["run_00c2"]["status"] == "BLOCKED"


def test_operator_metadata_cleanup_removes_ds_store_and_pycache(
    tmp_path: Path,
) -> None:
    pack = tmp_path / "kagglefiles"
    cache = pack / "nested/__pycache__"
    cache.mkdir(parents=True)
    (pack / ".DS_Store").write_bytes(b"finder")
    (cache / "cached.pyc").write_bytes(b"bytecode")

    result = clean_operator_metadata(pack)

    assert result == {"ds_store_removed": 1, "pycache_removed": 1}
    assert not (pack / ".DS_Store").exists()
    assert not cache.exists()
