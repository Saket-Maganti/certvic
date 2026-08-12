#!/usr/bin/env python3
"""Reconcile authenticated first-wave state and gate CertVIC's real smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

sys.dont_write_bytecode = True
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.cvpr.content_discovery import (  # noqa: E402
    ContentDiscoveryError,
    authenticate_content_path,
)
from certvic.cvpr.kaggle_bundle import build_bundle, verify_bundle  # noqa: E402
from certvic.cvpr.reconcile_provider_permissions import (  # noqa: E402
    ProviderPermissionError,
    create_matrix_authorization,
    derive_provider_permission,
    verify_matrix_authorization,
    verify_provider_permission,
)
from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes  # noqa: E402
from certvic.cvpr.run_contract import build_run_contract  # noqa: E402
from certvic.cvpr.smoke_input_builder import (  # noqa: E402
    SmokeInputBuilderError,
    build_smoke_bundle,
)
from local_operator.runtime_materializer import (  # noqa: E402
    ACTIVE_PROFILE,
    RuntimeMaterializationError,
    inspect_runtime_archive,
)


PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
MATRIX_SCHEMA = "certvic.local_operator.00b_matrix_complete.v1"
PERMISSIONS_SCHEMA = "certvic.local_operator.pre_smoke_provider_permissions.v1"
EXPECTED_CODE_IDENTITY = (
    "79d7fe9bc7f3778811071afdd1242241127ebaa182ac29cb092af87c13eacf33"
)
CANONICAL_PROMPT_TEMPLATE_HASH = hashlib.sha256(b"{prompt}\n").hexdigest()


class PreSmokeOperatorError(ValueError):
    """Local pre-smoke state is incomplete, conflicting, or unauthenticated."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and HASH_PATTERN.fullmatch(value) is not None


def _load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise PreSmokeOperatorError(f"required JSON is missing or unsafe: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PreSmokeOperatorError(f"required JSON is invalid: {path}") from error
    if not isinstance(value, dict):
        raise PreSmokeOperatorError(f"required JSON is not an object: {path}")
    return value


def _atomic_write_exact(path: Path, payload: bytes) -> bool:
    """Write once atomically; accept an exact replay and reject conflicting bytes."""
    if path.is_symlink():
        raise PreSmokeOperatorError(f"refusing symlink destination: {path}")
    if path.exists():
        if not path.is_file() or path.read_bytes() != payload:
            raise PreSmokeOperatorError(
                f"conflicting pre-existing bytes rejected: {path}"
            )
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise PreSmokeOperatorError(f"path is outside repository: {path}") from error


def _ledger(root: Path) -> dict[str, Any]:
    value = _load_json(root / "kagglefiles/.IMPORTED_RETURNS.json")
    if (
        value.get("schema") != "certvic.kagglefiles.imported_returns.v1"
        or not isinstance(value.get("returns"), dict)
    ):
        raise PreSmokeOperatorError("imported-return replay ledger is invalid")
    return value


def _authenticated_runtime_row(
    root: Path,
    *,
    provider: str | None,
) -> dict[str, Any]:
    stem = (
        "00A_environment"
        if provider is None
        else f"00B_{provider}_snapshot"
    )
    archive = root / f"data/runtime/{stem}_bundle.zip"
    record_path = root / f"data/runtime/{stem}.json"
    try:
        plan = inspect_runtime_archive(archive, pack_root=root / "kagglefiles")
    except RuntimeMaterializationError as error:
        raise PreSmokeOperatorError(str(error)) from error
    if (
        record_path.is_symlink()
        or not record_path.is_file()
        or record_path.read_bytes() != plan.member_bytes
    ):
        raise PreSmokeOperatorError(
            f"materialized runtime bytes differ from authenticated member: {record_path}"
        )
    record = _load_json(record_path)
    if (
        record.get("passed") is not True
        or record.get("runtime_profile_id") != ACTIVE_PROFILE
        or record.get("paper_evidence") is not False
    ):
        raise PreSmokeOperatorError(f"runtime contract rejected: {record_path}")
    expected_provider = provider or "all"
    if record.get("provider", "all") != expected_provider:
        raise PreSmokeOperatorError(f"runtime provider mismatch: {record_path}")
    ledger = _ledger(root)
    imported = ledger["returns"].get(plan.archive_sha256)
    expected_materialization = {
        "schema": "certvic.kagglefiles.runtime_materialization.v1",
        "source_archive_sha256": plan.archive_sha256,
        "source_archive_size": plan.archive_size,
        "authenticated_member": plan.member_name,
        "authenticated_member_sha256": plan.member_sha256,
        "canonical_destination": _relative(record_path, root),
        "runtime_profile_id": ACTIVE_PROFILE,
        "provider": expected_provider,
        "paper_evidence": False,
    }
    if (
        not isinstance(imported, dict)
        or imported.get("return_type") != plan.return_type
        or imported.get("canonical_destination") != _relative(archive, root)
        or imported.get("paper_evidence") is not False
        or imported.get("materialization") != expected_materialization
    ):
        raise PreSmokeOperatorError(
            f"runtime provenance/replay ledger mismatch: {archive.name}"
        )
    return {
        "record": record,
        "runtime_record": _relative(record_path, root),
        "runtime_record_sha256": plan.member_sha256,
        "source_archive": _relative(archive, root),
        "source_archive_sha256": plan.archive_sha256,
        "source_archive_size": plan.archive_size,
        "authenticated_member": plan.member_name,
        "authenticated_member_sha256": plan.member_sha256,
    }


def verify_authenticated_runtime_state(
    root: str | Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    project = Path(root).resolve()
    environment = _authenticated_runtime_row(project, provider=None)
    code_bundle = project / "kagglefiles/inputs/00_COMMON/certvic_code_bundle.zip"
    try:
        code_identity = authenticate_content_path(code_bundle, "CODE")
    except (ContentDiscoveryError, OSError) as error:
        raise PreSmokeOperatorError(f"CODE authentication failed: {error}") from error
    if (
        code_identity != EXPECTED_CODE_IDENTITY
        or environment["record"].get("code_bundle_hash") != code_identity
    ):
        raise PreSmokeOperatorError("authenticated 00A/CODE identity is not active C8")
    snapshots = {
        provider: _authenticated_runtime_row(project, provider=provider)
        for provider in PROVIDERS
    }
    if {row["record"]["provider"] for row in snapshots.values()} != set(PROVIDERS):
        raise PreSmokeOperatorError("authenticated 00B providers are not distinct")
    return {
        "environment": environment,
        "snapshots": snapshots,
        "code_content_identity_sha256": code_identity,
        "code_archive_sha256": _sha256_file(code_bundle),
        "runtime_profile_id": ACTIVE_PROFILE,
        "paper_evidence": False,
    }


def matrix_payload(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Construct the canonical matrix from authenticated record/provenance rows."""
    if len(rows) != len(PROVIDERS):
        raise PreSmokeOperatorError("00B matrix requires exactly three providers")
    providers = [row.get("provider") for row in rows]
    if len(set(providers)) != len(providers) or set(providers) != set(PROVIDERS):
        raise PreSmokeOperatorError("00B matrix provider set is wrong or duplicated")
    profiles = {row.get("runtime_profile_id") for row in rows}
    if profiles != {ACTIVE_PROFILE}:
        raise PreSmokeOperatorError("00B matrix mixes or uses the wrong runtime profile")
    normalized: list[dict[str, Any]] = []
    required_hashes = (
        "runtime_record_sha256",
        "source_archive_sha256",
        "authenticated_member_sha256",
        "runtime_profile_hash",
        "snapshot_content_identity_sha256",
        "snapshot_root_hash",
    )
    for row in rows:
        provider = str(row["provider"])
        if row.get("passed") is not True:
            raise PreSmokeOperatorError(f"failed 00B provider rejected: {provider}")
        if row.get("paper_evidence") is not False:
            raise PreSmokeOperatorError(f"00B paper evidence must remain false: {provider}")
        invalid = [name for name in required_hashes if not _valid_hash(row.get(name))]
        if invalid:
            raise PreSmokeOperatorError(
                f"00B provenance/identity hashes are invalid for {provider}: {invalid}"
            )
        if row["runtime_record_sha256"] != row["authenticated_member_sha256"]:
            raise PreSmokeOperatorError(
                f"00B materialized/member hash mismatch: {provider}"
            )
        expected_member = f"00B_{provider}_snapshot.json"
        if row.get("authenticated_member") != expected_member:
            raise PreSmokeOperatorError(f"00B authenticated member mismatch: {provider}")
        normalized.append(dict(row))
    normalized.sort(key=lambda row: PROVIDERS.index(str(row["provider"])))
    base = {
        "schema": MATRIX_SCHEMA,
        "status": "AUTHENTICATED_00B_MATRIX_COMPLETE",
        "providers": list(PROVIDERS),
        "runtime_profile_id": ACTIVE_PROFILE,
        "rows": normalized,
        "source_model_snapshot_archives_required_locally": False,
        "paper_evidence": False,
    }
    base["matrix_identity_sha256"] = _sha256_bytes(_canonical_bytes(base))
    return base


def derive_00b_matrix(
    root: str | Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    authenticated = verify_authenticated_runtime_state(root)
    rows: list[dict[str, Any]] = []
    for provider in PROVIDERS:
        provenance = authenticated["snapshots"][provider]
        record = provenance["record"]
        rows.append({
            "provider": provider,
            "passed": record["passed"],
            "runtime_profile_id": record["runtime_profile_id"],
            "runtime_profile_hash": record["runtime_profile_hash"],
            "snapshot_content_identity_sha256": record[
                "snapshot_content_identity_sha256"
            ],
            "snapshot_root_hash": record["snapshot_root_hash"],
            "model_id": record["model_id"],
            "model_revision": record["model_commit"],
            "processor_model_contract": record["expected_architecture"],
            "paper_evidence": False,
            **{
                key: provenance[key]
                for key in (
                    "runtime_record",
                    "runtime_record_sha256",
                    "source_archive",
                    "source_archive_sha256",
                    "source_archive_size",
                    "authenticated_member",
                    "authenticated_member_sha256",
                )
            },
        })
    return matrix_payload(rows)


def create_00b_matrix(
    root: str | Path = REPOSITORY_ROOT,
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    project = Path(root).resolve()
    destination = (
        Path(output).resolve()
        if output is not None
        else project / "data/runtime/00B_matrix_complete.json"
    )
    payload = derive_00b_matrix(project)
    created = _atomic_write_exact(destination, _json_bytes(payload))
    return {
        **payload,
        "artifact": _relative(destination, project),
        "created": created,
        "idempotent": not created,
    }


def verify_00b_matrix(
    root: str | Path = REPOSITORY_ROOT,
    *,
    path: str | Path | None = None,
) -> dict[str, Any]:
    project = Path(root).resolve()
    source = (
        Path(path).resolve()
        if path is not None
        else project / "data/runtime/00B_matrix_complete.json"
    )
    observed = _load_json(source)
    expected = derive_00b_matrix(project)
    if observed != expected or source.read_bytes() != _json_bytes(expected):
        raise PreSmokeOperatorError("00B matrix bytes differ from authenticated inputs")
    return observed


def _zip_json_members(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            values = {}
            for basename in (
                "tasks.jsonl",
                "task_bundle_manifest.json",
                "smoke_contract.json",
                "licensing_metadata.json",
                "validation_report.json",
            ):
                matches = [
                    candidate
                    for candidate in archive.namelist()
                    if PurePosixPath(candidate).name == basename
                ]
                if len(matches) != 1:
                    raise PreSmokeOperatorError(
                        f"real smoke bundle member missing/duplicated: {basename}"
                    )
                name = matches[0]
                payload = archive.read(name)
                if basename.endswith(".jsonl"):
                    values[basename] = [
                        json.loads(line)
                        for line in payload.decode("utf-8").splitlines()
                        if line
                    ]
                    values[f"{basename}:sha256"] = _sha256_bytes(payload)
                else:
                    values[basename] = json.loads(payload)
                    values[f"{basename}:sha256"] = _sha256_bytes(payload)
            return values
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        raise PreSmokeOperatorError(f"real smoke bundle is unreadable: {error}") from error


def verify_real_smoke_bundle(
    root: str | Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    project = Path(root).resolve()
    tasks_path = project / "local_inputs/smoke/real_smoke_tasks.jsonl"
    bundle = project / "kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip"
    if (
        tasks_path.is_symlink()
        or not tasks_path.is_file()
        or bundle.is_symlink()
        or not bundle.is_file()
    ):
        raise PreSmokeOperatorError("two genuine real smoke items/bundle are absent")
    verification = verify_bundle(bundle)
    if not verification["passed"]:
        raise PreSmokeOperatorError(
            f"real smoke canonical bundle verification failed: {verification['errors']}"
        )
    manifest = verification["bundle_manifest"]
    if (
        manifest.get("bundle_type") != "REAL_TWO_ITEM_SMOKE_INPUT"
        or manifest.get("synthetic_fixture") is not False
        or manifest.get("evidence_class") != "REAL_MODEL_SMOKE_NON_EVIDENCE"
    ):
        raise PreSmokeOperatorError("real smoke bundle type/evidence boundary mismatch")
    members = _zip_json_members(bundle)
    rows = members["tasks.jsonl"]
    if len(rows) != 2 or len({row.get("item_id") for row in rows}) != 2:
        raise PreSmokeOperatorError("real smoke bundle is not exactly two unique items")
    byte_hashes: list[str] = []
    for row in rows:
        if (
            row.get("license_eligible") is not True
            or not str(row.get("license_id", "")).strip()
            or row.get("synthetic_fixture") is not False
            or row.get("paper_evidence") is not False
            or not _valid_hash(row.get("prompt_template_hash"))
            or not str(row.get("parser_version", "")).strip()
            or not _valid_hash(row.get("run_contract_hash"))
        ):
            raise PreSmokeOperatorError(
                f"real smoke task contract is incomplete: {row.get('item_id')}"
            )
        for field in ("original_image_sha256", "edited_image_sha256"):
            if not _valid_hash(row.get(field)):
                raise PreSmokeOperatorError(
                    f"real smoke task asset hash is invalid: {field}"
                )
            byte_hashes.append(row[field])
        if row.get("mask_sha256") is not None:
            if not _valid_hash(row["mask_sha256"]):
                raise PreSmokeOperatorError("real smoke mask hash is invalid")
            byte_hashes.append(row["mask_sha256"])
    if len(byte_hashes) != len(set(byte_hashes)):
        raise PreSmokeOperatorError("real smoke bundle contains duplicate asset bytes")
    task_bundle = members["task_bundle_manifest.json"]
    contract = members["smoke_contract.json"]
    validation = members["validation_report.json"]
    if (
        task_bundle.get("schema") != "certvic.cvpr.task_bundle.v1"
        or task_bundle.get("task_count") != 2
        or task_bundle.get("paper_evidence") is not False
        or contract.get("use_real_model") is not True
        or contract.get("providers") != list(PROVIDERS)
        or validation.get("passed") is not True
        or validation.get("paper_evidence") is not False
    ):
        raise PreSmokeOperatorError("real smoke verification contract is not genuine")
    return {
        "path": _relative(bundle, project),
        "archive_sha256": _sha256_file(bundle),
        "content_identity_sha256": authenticate_content_path(
            bundle, "REAL_TWO_ITEM_SMOKE"
        ),
        "rows": rows,
        "members": members,
        "paper_evidence": False,
    }


def _historical_manifests(project: Path, task_manifest: Path) -> list[Path]:
    return [
        path
        for path in sorted((project / "data").rglob("*.jsonl"))
        if path.resolve() != task_manifest.resolve()
        and "synthetic" not in path.as_posix().lower()
    ]


def build_real_smoke_if_present(
    root: str | Path = REPOSITORY_ROOT,
) -> dict[str, Any] | None:
    project = Path(root).resolve()
    tasks = project / "local_inputs/smoke/real_smoke_tasks.jsonl"
    if not tasks.is_file() or tasks.is_symlink():
        return None
    output = project / "kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip"
    try:
        build_smoke_bundle(
            tasks,
            output=output,
            historical_manifests=_historical_manifests(project, tasks),
        )
    except SmokeInputBuilderError as error:
        raise PreSmokeOperatorError(str(error)) from error
    return verify_real_smoke_bundle(project)


def _permission_sources(
    authenticated: Mapping[str, Any],
    matrix: Mapping[str, Any],
    smoke: Mapping[str, Any],
) -> dict[str, Any]:
    rows = smoke["rows"]
    prompt_hashes = {row["prompt_template_hash"] for row in rows}
    parser_versions = {row["parser_version"] for row in rows}
    if len(prompt_hashes) != 1 or len(parser_versions) != 1:
        raise PreSmokeOperatorError(
            "real smoke items must share one prompt-template and parser identity"
        )
    if prompt_hashes != {CANONICAL_PROMPT_TEMPLATE_HASH} or parser_versions != {
        "certvic.parse.v2"
    }:
        raise PreSmokeOperatorError(
            "real smoke prompt/parser identity differs from the frozen 00C2 notebooks"
        )
    members = smoke["members"]
    item_ids = sorted(str(row["item_id"]) for row in rows)
    edited_hashes = sorted(str(row["edited_image_sha256"]) for row in rows)
    return {
        "prompt_hash": next(iter(prompt_hashes)),
        "parser_version": next(iter(parser_versions)),
        "task_manifest_sha256": sha256_bytes(canonical_json_bytes(rows)),
        "task_universe_sha256": _sha256_bytes(_canonical_bytes(item_ids)),
        "edited_image_hashes_hash": _sha256_bytes(_canonical_bytes(edited_hashes)),
        "final_task_manifest_hash": members["tasks.jsonl:sha256"],
        "review_hash": members["licensing_metadata.json:sha256"],
        "detectability_hash": members["validation_report.json:sha256"],
        "smoke_contract_hash": members["smoke_contract.json:sha256"],
        "task_bundle_manifest_hash": members["task_bundle_manifest.json:sha256"],
        "task_bundle_hash": members["task_bundle_manifest.json"]["bundle_hash"],
        "environment_hash": authenticated["environment"]["record"]["environment_lock_hash"],
        "model_registry_hash": matrix["matrix_identity_sha256"],
    }


def _provider_run_contract(
    provider: str,
    authenticated: Mapping[str, Any],
    sources: Mapping[str, Any],
) -> dict[str, Any]:
    record = authenticated["snapshots"][provider]["record"]
    environment = authenticated["environment"]["record"]
    return build_run_contract(
        {
            "study": "pre_smoke",
            "runtime_class": "REAL_MODEL_SMOKE",
            "provider": provider,
            "model_id": record["model_id"],
            "processor_id": record["processor_id"],
            "model_commit": record["model_commit"],
            "processor_commit": record["processor_commit"],
            "model_snapshot_manifest_hash": record["snapshot_manifest_file_sha256"],
            "processor_snapshot_manifest_hash": record["snapshot_manifest_file_sha256"],
            "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
            "snapshot_contract": "UNIFIED_SNAPSHOT",
            "environment_lock_hash": environment["environment_lock_hash"],
            "runtime_profile_id": ACTIVE_PROFILE,
            "runtime_profile_hash": environment["runtime_profile_hash"],
            "wheelhouse_content_identity_sha256": environment[
                "wheelhouse_content_identity_sha256"
            ],
            "prompt_template_id": "certification_yes_no_v1",
            "prompt_template_hash": sources["prompt_hash"],
            "parser_version": sources["parser_version"],
            "output_schema": "certvic.cvpr.output.v2",
            "run_tag": f"00C2_{provider}_real_model_two_item_smoke",
            "code_bundle_hash": authenticated["code_content_identity_sha256"],
            "seed": 12013,
            "generation_parameters": {"do_sample": False, "max_new_tokens": 8},
        },
        task_manifest_sha256=sources["task_manifest_sha256"],
        strict=True,
    )


def generate_pre_smoke_permissions(
    root: str | Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    """Issue only three single-use REAL_MODEL_SMOKE permissions."""
    project = Path(root).resolve()
    authenticated = verify_authenticated_runtime_state(project)
    matrix_complete = verify_00b_matrix(project)
    smoke = verify_real_smoke_bundle(project)
    sources = _permission_sources(authenticated, matrix_complete, smoke)
    parent_path = project / "data/runtime/pre_smoke_matrix_authorization.json"
    children_path = project / "data/runtime/pre_smoke_provider_permissions.json"
    package_path = (
        project
        / "kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip"
    )
    if parent_path.exists() or children_path.exists() or package_path.exists():
        return verify_pre_smoke_permissions(project)
    environment = authenticated["environment"]["record"]
    parent = create_matrix_authorization(
        study="pre_smoke",
        task_bundle_hash=sources["task_bundle_hash"],
        final_task_manifest_hash=sources["final_task_manifest_hash"],
        task_universe_sha256=sources["task_universe_sha256"],
        edited_image_hashes_hash=sources["edited_image_hashes_hash"],
        review_hash=sources["review_hash"],
        detectability_hash=sources["detectability_hash"],
        environment_hash=sources["environment_hash"],
        model_registry_hash=sources["model_registry_hash"],
        providers=list(PROVIDERS),
        code_hash=authenticated["code_content_identity_sha256"],
        prompt_template_hash=sources["prompt_hash"],
        output_schema="certvic.cvpr.real_model_smoke_output.v1",
        runtime_profile_id=ACTIVE_PROFILE,
        runtime_profile_hash=environment["runtime_profile_hash"],
        wheelhouse_content_identity_sha256=environment[
            "wheelhouse_content_identity_sha256"
        ],
        issued_at=datetime.now(timezone.utc),
        validity_hours=168,
    )
    rows_by_provider = {
        row["provider"]: row for row in matrix_complete["rows"]
    }
    environment_lock_file_sha256 = _sha256_file(
        project / "configs/runtime/kaggle_t4x2_environment.lock.json"
    )
    model_registry_file_sha256 = _sha256_file(
        project / "configs/models/certvic_immutable_model_registry.json"
    )
    children: dict[str, dict[str, Any]] = {}
    for provider in PROVIDERS:
        row = rows_by_provider[provider]
        run_contract = _provider_run_contract(provider, authenticated, sources)
        snapshot_record = authenticated["snapshots"][provider]["record"]
        active_input_hashes = {
            "task_bundle_manifest": sources["task_bundle_manifest_hash"],
            "freeze_manifest": sources["task_bundle_manifest_hash"],
            "final_review": sources["review_hash"],
            "smoke_gate": sources["detectability_hash"],
            "environment_lock": environment_lock_file_sha256,
            "model_registry": model_registry_file_sha256,
            "snapshot_manifest": snapshot_record["snapshot_manifest_file_sha256"],
            "code_bundle": authenticated["code_content_identity_sha256"],
            "study_config": sources["smoke_contract_hash"],
            "matrix_authorization": _sha256_bytes(_json_bytes(parent)),
        }
        active_scalars = {
            "schema_version": parent["output_schema"],
            "provider": provider,
            "run_tag": f"00C2_{provider}_real_model_two_item_smoke",
            "prompt_template_hash": sources["prompt_hash"],
            "runtime_profile_id": ACTIVE_PROFILE,
            "runtime_profile_hash": environment["runtime_profile_hash"],
            "wheelhouse_content_identity_sha256": environment[
                "wheelhouse_content_identity_sha256"
            ],
        }
        nonce = _sha256_bytes(
            f"{parent['matrix_authorization_id']}:{provider}:single-use".encode()
        )
        children[provider] = derive_provider_permission(
            parent,
            provider=provider,
            model_id=row["model_id"],
            model_revision=row["model_revision"],
            snapshot_hash=row["snapshot_content_identity_sha256"],
            snapshot_root_hash=row["snapshot_root_hash"],
            environment_hash=sources["environment_hash"],
            task_bundle_hash=sources["task_bundle_hash"],
            run_tag=active_scalars["run_tag"],
            code_hash=authenticated["code_content_identity_sha256"],
            parser_version=sources["parser_version"],
            processor_model_contract=row["processor_model_contract"],
            active_input_hashes=active_input_hashes,
            active_scalars=active_scalars,
            runtime_class="REAL_MODEL_SMOKE",
            run_contract_hash=run_contract["run_contract_hash"],
            prompt_template_hash=sources["prompt_hash"],
            nonce=nonce,
        )
    aggregate = {
        "schema": PERMISSIONS_SCHEMA,
        "parent_matrix_authorization_id": parent["matrix_authorization_id"],
        "providers": list(PROVIDERS),
        "permissions": children,
        "execution_allowed": True,
        "authorized_execution": "TWO_ITEM_REAL_MODEL_SMOKE_ONLY",
        "scientific_execution_allowed": False,
        "confirmatory_execution_allowed": False,
        "main_execution_allowed": False,
        "coco_execution_allowed": False,
        "paper_evidence": False,
    }
    _atomic_write_exact(parent_path, _json_bytes(parent))
    _atomic_write_exact(children_path, _json_bytes(aggregate))
    with tempfile.TemporaryDirectory(prefix="certvic_pre_smoke_") as temporary:
        temporary_zip = Path(temporary) / package_path.name
        files: dict[str, bytes] = {
            "authorization/pre_smoke_matrix_authorization.json": _json_bytes(parent),
            "authorization/pre_smoke_provider_permissions.json": _json_bytes(aggregate),
        }
        for provider, child in children.items():
            files[f"authorization/{provider}_permission.json"] = _json_bytes(child)
        build_bundle(
            temporary_zip,
            files,
            bundle_type="PRE_SMOKE_PERMISSIONS",
            study="pre_smoke",
            stage="authorization",
            provider=None,
            required_notebook="ALL_3_PROVIDER_SPECIFIC_00C2_NOTEBOOKS",
            dataset_slug="certvic/certvic-pre-smoke-permissions",
            mount_path="/kaggle/input/certvic-pre-smoke-permissions",
            external_dependency_status="UPSTREAM_NON_EVIDENCE_ARTIFACTS_VERIFIED",
            evidence_class="REAL_MODEL_SMOKE_AUTHORIZATION_ONLY",
            builder_command="python3 local_operator/pre_smoke_operator.py authorize",
            readme=(
                "# CertVIC pre-smoke permissions\n\nOnly the two-item real-model "
                "smoke is authorized. Scientific execution remains prohibited."
            ),
        )
        _atomic_write_exact(package_path, temporary_zip.read_bytes())
    return verify_pre_smoke_permissions(project)


def verify_pre_smoke_permissions(
    root: str | Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    project = Path(root).resolve()
    parent_path = project / "data/runtime/pre_smoke_matrix_authorization.json"
    children_path = project / "data/runtime/pre_smoke_provider_permissions.json"
    package_path = (
        project
        / "kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip"
    )
    matrix_complete = verify_00b_matrix(project)
    authenticated = verify_authenticated_runtime_state(project)
    smoke = verify_real_smoke_bundle(project)
    sources = _permission_sources(authenticated, matrix_complete, smoke)
    try:
        parent = verify_matrix_authorization(parent_path)
    except (ProviderPermissionError, OSError, json.JSONDecodeError) as error:
        raise PreSmokeOperatorError(f"pre-smoke parent rejected: {error}") from error
    expected_parent = {
        "study": "pre_smoke",
        "providers": sorted(PROVIDERS),
        "task_bundle_hash": sources["task_bundle_hash"],
        "environment_hash": sources["environment_hash"],
        "model_registry_hash": sources["model_registry_hash"],
        "code_hash": authenticated["code_content_identity_sha256"],
        "prompt_template_hash": sources["prompt_hash"],
        "runtime_profile_id": ACTIVE_PROFILE,
        "paper_evidence": False,
    }
    for key, expected in expected_parent.items():
        if parent.get(key) != expected:
            raise PreSmokeOperatorError(f"pre-smoke parent binding mismatch: {key}")
    aggregate = _load_json(children_path)
    if (
        aggregate.get("schema") != PERMISSIONS_SCHEMA
        or aggregate.get("providers") != list(PROVIDERS)
        or set(aggregate.get("permissions", {})) != set(PROVIDERS)
        or aggregate.get("execution_allowed") is not True
        or aggregate.get("authorized_execution")
        != "TWO_ITEM_REAL_MODEL_SMOKE_ONLY"
        or any(
            aggregate.get(field) is not False
            for field in (
                "scientific_execution_allowed",
                "confirmatory_execution_allowed",
                "main_execution_allowed",
                "coco_execution_allowed",
                "paper_evidence",
            )
        )
    ):
        raise PreSmokeOperatorError("pre-smoke aggregate authorization is unsafe")
    nonces: set[str] = set()
    for provider in PROVIDERS:
        try:
            child = verify_provider_permission(
                aggregate["permissions"][provider],
                matrix=parent,
                expected_provider=provider,
            )
        except ProviderPermissionError as error:
            raise PreSmokeOperatorError(
                f"pre-smoke provider permission rejected: {provider}: {error}"
            ) from error
        expected_contract = _provider_run_contract(provider, authenticated, sources)
        if (
            child.get("runtime_class") != "REAL_MODEL_SMOKE"
            or child.get("parser_version") != sources["parser_version"]
            or child.get("run_contract_hash") != expected_contract["run_contract_hash"]
            or child.get("paper_evidence") is not False
        ):
            raise PreSmokeOperatorError(
                f"pre-smoke provider semantic binding mismatch: {provider}"
            )
        nonces.add(child["one_run_nonce"])
    if len(nonces) != len(PROVIDERS):
        raise PreSmokeOperatorError("provider permissions do not have distinct nonces")
    package = verify_bundle(package_path)
    if (
        not package["passed"]
        or package["bundle_manifest"].get("bundle_type")
        != "PRE_SMOKE_PERMISSIONS"
    ):
        raise PreSmokeOperatorError("pre-smoke permission ZIP verification failed")
    return {
        "matrix_authorization": _relative(parent_path, project),
        "provider_permissions": _relative(children_path, project),
        "permission_bundle": _relative(package_path, project),
        "providers": list(PROVIDERS),
        "execution_allowed": True,
        "scientific_execution_allowed": False,
        "confirmatory_execution_allowed": False,
        "main_execution_allowed": False,
        "coco_execution_allowed": False,
        "paper_evidence": False,
    }


def operator_status(
    root: str | Path = REPOSITORY_ROOT,
) -> dict[str, Any]:
    project = Path(root).resolve()
    result: dict[str, Any] = {
        "schema": "certvic.local_operator.pre_smoke_status.v1",
        "operator_state": "BLOCKED",
        "local_failures": 0,
        "00A": "INCOMPLETE",
        "00B": "INCOMPLETE",
        "00B_matrix_complete": "ABSENT",
        "real_smoke_bundle": "ABSENT",
        "pre_smoke_permissions": "ABSENT",
        "00C2": "NOT_AUTHORIZED",
        "paper_evidence": False,
        "legacy_graph_discrepancy": (
            "The canonical doctor/run graph advances from provider JSON presence "
            "and retains legacy generic paths; this operator gate additionally "
            "verifies provenance, matrix, real bytes, and permissions."
        ),
        "blockers": [],
    }
    try:
        verify_authenticated_runtime_state(project)
        result["00A"] = "COMPLETE"
        result["00B"] = "COMPLETE"
        verify_00b_matrix(project)
        result["00B_matrix_complete"] = "VERIFIED"
    except PreSmokeOperatorError as error:
        result["local_failures"] = 1
        result["blockers"].append(str(error))
        return result
    try:
        verify_real_smoke_bundle(project)
        result["real_smoke_bundle"] = "VERIFIED"
    except PreSmokeOperatorError as error:
        permission_paths = (
            project / "data/runtime/pre_smoke_matrix_authorization.json",
            project / "data/runtime/pre_smoke_provider_permissions.json",
            project
            / "kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip",
        )
        if any(path.exists() for path in permission_paths):
            result["local_failures"] = 1
            result["blockers"].append(
                "permission artifacts exist without a verified real smoke bundle"
            )
            return result
        result["operator_state"] = "READY_FOR_REAL_SMOKE_INPUTS"
        result["preparation_status"] = (
            "BLOCKED_BY_TWO_REAL_LICENSED_SMOKE_ITEMS"
        )
        result["blockers"].append(str(error))
        return result
    try:
        verify_pre_smoke_permissions(project)
        result["pre_smoke_permissions"] = "VERIFIED"
    except PreSmokeOperatorError as error:
        permission_paths = (
            project / "data/runtime/pre_smoke_matrix_authorization.json",
            project / "data/runtime/pre_smoke_provider_permissions.json",
            project
            / "kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip",
        )
        if any(path.exists() for path in permission_paths):
            result["local_failures"] = 1
            result["blockers"].append(str(error))
            return result
        result["operator_state"] = "READY_FOR_PRE_SMOKE_AUTHORIZATION"
        result["blockers"].append(str(error))
        return result
    result["operator_state"] = "READY_FOR_00C2"
    result["00C2"] = "AUTHORIZED_TWO_ITEM_REAL_MODEL_SMOKE_ONLY"
    return result


def prepare(root: str | Path = REPOSITORY_ROOT) -> dict[str, Any]:
    project = Path(root).resolve()
    create_00b_matrix(project)
    smoke = build_real_smoke_if_present(project)
    if smoke is not None:
        generate_pre_smoke_permissions(project)
    return operator_status(project)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("prepare", "reconcile-00b", "authorize", "status"),
        nargs="?",
        default="status",
    )
    parser.add_argument("--root", default=str(REPOSITORY_ROOT))
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.root)
        elif args.command == "reconcile-00b":
            result = create_00b_matrix(args.root)
        elif args.command == "authorize":
            result = generate_pre_smoke_permissions(args.root)
        else:
            result = operator_status(args.root)
    except (PreSmokeOperatorError, OSError) as error:
        result = {
            "operator_state": "BLOCKED",
            "local_failures": 1,
            "error": str(error),
            "00C2": "NOT_AUTHORIZED",
            "paper_evidence": False,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("local_failures", 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
