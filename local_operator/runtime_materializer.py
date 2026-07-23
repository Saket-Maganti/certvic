#!/usr/bin/env python3
"""Materialize authenticated first-wave records from imported runtime ZIPs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

sys.dont_write_bytecode = True
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.cvpr.content_discovery import (  # noqa: E402
    ContentDiscoveryError,
    authenticate_content_path,
)


ACTIVE_PROFILE = "kaggle_cp312_2026_07"
MAX_ARCHIVE_MEMBERS = 32
MAX_MEMBER_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")


class RuntimeMaterializationError(ValueError):
    """An imported runtime return cannot be safely materialized."""


@dataclass(frozen=True)
class RuntimeSpec:
    archive_name: str
    primary_name: str
    return_type: str
    provider: str | None


@dataclass(frozen=True)
class MaterializationPlan:
    archive_path: Path
    archive_sha256: str
    archive_size: int
    member_name: str
    member_bytes: bytes
    member_sha256: str
    destination: Path
    return_type: str
    provider: str | None


def _specifications() -> tuple[RuntimeSpec, ...]:
    return (
        RuntimeSpec(
            archive_name="00A_environment_bundle.zip",
            primary_name="00A_environment.json",
            return_type="00A_ENVIRONMENT",
            provider=None,
        ),
        *(
            RuntimeSpec(
                archive_name=f"00B_{provider}_snapshot_bundle.zip",
                primary_name=f"00B_{provider}_snapshot.json",
                return_type=f"00B_SNAPSHOT_SMOKE:{provider}",
                provider=provider,
            )
            for provider in PROVIDERS
        ),
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _atomic_write(path: Path, payload: bytes) -> None:
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


def _safe_member(info: zipfile.ZipInfo) -> str:
    name = info.filename
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    if (
        not name
        or normalized != name
        or normalized.endswith("/")
        or path.is_absolute()
        or path.as_posix() != normalized
        or "." in path.parts
        or ".." in path.parts
        or normalized.startswith("~")
        or "\x00" in normalized
        or info.is_dir()
        or file_type not in {0, stat.S_IFREG}
        or info.flag_bits & 0x1
    ):
        raise RuntimeMaterializationError(f"unsafe runtime return member: {name!r}")
    if info.file_size < 0 or info.file_size > MAX_MEMBER_BYTES:
        raise RuntimeMaterializationError(
            f"runtime return member exceeds size limit: {name!r}"
        )
    return path.as_posix()


def _read_authenticated_members(path: Path) -> dict[str, bytes]:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size == 0
        or path.stat().st_size > MAX_TOTAL_BYTES
    ):
        raise RuntimeMaterializationError("runtime return archive is missing or unsafe")
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_ARCHIVE_MEMBERS:
                raise RuntimeMaterializationError(
                    "runtime return archive member count is invalid"
                )
            names = [_safe_member(info) for info in infos]
            if len(names) != len(set(names)):
                raise RuntimeMaterializationError(
                    "runtime return archive contains duplicate members"
                )
            if sum(info.file_size for info in infos) > MAX_TOTAL_BYTES:
                raise RuntimeMaterializationError(
                    "runtime return archive exceeds extraction limit"
                )
            if archive.testzip() is not None:
                raise RuntimeMaterializationError("runtime return archive is corrupt")
            payloads = {
                name: archive.read(info)
                for name, info in zip(names, infos, strict=True)
            }
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        raise RuntimeMaterializationError(
            f"runtime return archive is unreadable or corrupt: {error}"
        ) from error

    manifest_bytes = payloads.get("hash_manifest.json")
    if manifest_bytes is None:
        raise RuntimeMaterializationError(
            "runtime return has no authenticated hash_manifest.json"
        )
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeMaterializationError(
            "runtime return hash manifest is malformed"
        ) from error
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema") != "certvic.cvpr.smoke_hash_manifest.v1"
    ):
        raise RuntimeMaterializationError("runtime return hash manifest schema mismatch")
    declared = manifest.get("files")
    if not isinstance(declared, dict) or not declared:
        raise RuntimeMaterializationError("runtime return hash manifest is empty")
    expected_names = set(payloads) - {"hash_manifest.json"}
    if set(declared) != expected_names:
        raise RuntimeMaterializationError(
            "runtime return hash manifest coverage mismatch"
        )
    for name, record in declared.items():
        digest = record.get("sha256") if isinstance(record, dict) else record
        if not isinstance(digest, str) or HASH_PATTERN.fullmatch(digest) is None:
            raise RuntimeMaterializationError(
                f"runtime return hash manifest has invalid digest: {name}"
            )
        if _sha256_bytes(payloads[name]) != digest:
            raise RuntimeMaterializationError(
                f"runtime return hash manifest mismatch: {name}"
            )
        if isinstance(record, dict) and record.get("size", len(payloads[name])) != len(
            payloads[name]
        ):
            raise RuntimeMaterializationError(
                f"runtime return hash manifest size mismatch: {name}"
            )
    return payloads


def _spec_for_archive(
    path: Path,
    *,
    expected_return_type: str | None = None,
) -> RuntimeSpec:
    for spec in _specifications():
        if (
            expected_return_type == spec.return_type
            if expected_return_type is not None
            else path.name == spec.archive_name
        ):
            return spec
    raise RuntimeMaterializationError(
        f"unsupported runtime return archive: {path.name}"
    )


def _primary_json(payloads: Mapping[str, bytes], spec: RuntimeSpec) -> dict[str, Any]:
    if spec.provider is None:
        candidates = [name for name in payloads if name == "00A_environment.json"]
    else:
        candidates = [
            name
            for name in payloads
            if re.fullmatch(r"00B_[a-z0-9_]+_snapshot\.json", name)
        ]
    if candidates != [spec.primary_name]:
        raise RuntimeMaterializationError(
            f"runtime return must contain exactly one primary member: {spec.primary_name}"
        )
    try:
        value = json.loads(payloads[spec.primary_name])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeMaterializationError(
            f"runtime primary member is malformed: {spec.primary_name}"
        ) from error
    if not isinstance(value, dict):
        raise RuntimeMaterializationError("runtime primary member must be an object")
    if value.get("passed") is not True:
        raise RuntimeMaterializationError("failed runtime return cannot be materialized")
    if value.get("runtime_profile_id") != ACTIVE_PROFILE:
        raise RuntimeMaterializationError("runtime return profile mismatch")
    if value.get("paper_evidence") is not False:
        raise RuntimeMaterializationError(
            "runtime return must remain paper_evidence=false"
        )
    if spec.provider is not None and value.get("provider") != spec.provider:
        raise RuntimeMaterializationError("runtime return provider mismatch")
    return value


def inspect_runtime_archive(
    archive_path: str | Path,
    *,
    pack_root: str | Path,
    expected_return_type: str | None = None,
) -> MaterializationPlan:
    """Fully authenticate one first-wave archive without writing output."""
    archive = Path(archive_path).resolve()
    pack = Path(pack_root).resolve()
    project = pack.parent
    spec = _spec_for_archive(
        archive,
        expected_return_type=expected_return_type,
    )
    payloads = _read_authenticated_members(archive)
    primary = _primary_json(payloads, spec)
    if spec.provider is None:
        code_bundle = pack / "inputs/00_COMMON/certvic_code_bundle.zip"
        try:
            current_code_identity = authenticate_content_path(code_bundle, "CODE")
        except (ContentDiscoveryError, OSError) as error:
            raise RuntimeMaterializationError(
                f"current CODE bundle authentication failed: {error}"
            ) from error
        if primary.get("code_bundle_hash") != current_code_identity:
            raise RuntimeMaterializationError(
                "00A runtime return is bound to a superseded CODE content identity"
            )
    member_bytes = payloads[spec.primary_name]
    return MaterializationPlan(
        archive_path=archive,
        archive_sha256=_sha256_file(archive),
        archive_size=archive.stat().st_size,
        member_name=spec.primary_name,
        member_bytes=member_bytes,
        member_sha256=_sha256_bytes(member_bytes),
        destination=project / "data/runtime" / spec.primary_name,
        return_type=spec.return_type,
        provider=spec.provider,
    )


def _load_import_ledger(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeMaterializationError(
            "imported-return ledger is missing or unsafe"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeMaterializationError(
            "imported-return ledger is missing or invalid"
        ) from error
    if not isinstance(value, dict) or not isinstance(value.get("returns"), dict):
        raise RuntimeMaterializationError("imported-return ledger structure is invalid")
    return value


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise RuntimeMaterializationError(
            "runtime materialization destination is outside the project"
        ) from error


def validate_materialization_destination(plan: MaterializationPlan) -> None:
    """Reject a conflicting canonical JSON before importing an archive."""
    if (
        plan.destination.is_symlink()
        or (
            plan.destination.exists()
            and (
                not plan.destination.is_file()
                or plan.destination.read_bytes() != plan.member_bytes
            )
        )
    ):
        raise RuntimeMaterializationError(
            f"canonical runtime JSON contains conflicting bytes: {plan.destination.name}"
        )


def materialize_runtime_archive(
    archive_path: str | Path,
    *,
    pack_root: str | Path,
) -> dict[str, Any]:
    """Materialize one imported archive exactly and update its replay ledger."""
    pack = Path(pack_root).resolve()
    project = pack.parent
    plan = inspect_runtime_archive(archive_path, pack_root=pack)
    archive_sha_before = plan.archive_sha256
    ledger_path = pack / ".IMPORTED_RETURNS.json"
    ledger = _load_import_ledger(ledger_path)
    record = ledger["returns"].get(plan.archive_sha256)
    archive_destination = _relative(plan.archive_path, project)
    if (
        not isinstance(record, dict)
        or record.get("return_type") != plan.return_type
        or record.get("canonical_destination") != archive_destination
        or record.get("paper_evidence") is not False
    ):
        raise RuntimeMaterializationError(
            "runtime archive is not the canonical authenticated imported return"
        )
    validate_materialization_destination(plan)
    materialization = {
        "schema": "certvic.kagglefiles.runtime_materialization.v1",
        "source_archive_sha256": plan.archive_sha256,
        "source_archive_size": plan.archive_size,
        "authenticated_member": plan.member_name,
        "authenticated_member_sha256": plan.member_sha256,
        "canonical_destination": _relative(plan.destination, project),
        "runtime_profile_id": ACTIVE_PROFILE,
        "provider": plan.provider or "all",
        "paper_evidence": False,
    }
    existing = record.get("materialization")
    if existing is not None and existing != materialization:
        raise RuntimeMaterializationError(
            "runtime materialization ledger contains conflicting provenance"
        )
    if not plan.destination.exists():
        _atomic_write(plan.destination, plan.member_bytes)
    if _sha256_file(plan.archive_path) != archive_sha_before:
        raise RuntimeMaterializationError(
            "authoritative runtime archive changed during materialization"
        )
    if record.get("materialization") != materialization:
        record["materialization"] = materialization
        _atomic_write(ledger_path, _json_bytes(ledger))
    return {
        **materialization,
        "status": "AUTHENTICATED_RUNTIME_RECORD_MATERIALIZED",
        "idempotent": plan.destination.read_bytes() == plan.member_bytes,
    }


def clean_operator_metadata(pack_root: str | Path) -> dict[str, int]:
    """Remove harmless platform/cache metadata from the operator pack."""
    root = Path(pack_root).resolve()
    removed_finder = 0
    removed_caches = 0
    if not root.is_dir():
        return {"ds_store_removed": 0, "pycache_removed": 0}
    for path in root.rglob(".DS_Store"):
        if path.is_file() and not path.is_symlink():
            path.unlink()
            removed_finder += 1
    for path in sorted(root.rglob("__pycache__"), reverse=True):
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
            removed_caches += 1
    return {
        "ds_store_removed": removed_finder,
        "pycache_removed": removed_caches,
    }


def materialize_imported_runtime_records(
    *,
    pack_root: str | Path,
) -> dict[str, Any]:
    """Backfill every currently imported 00A/00B canonical runtime record."""
    pack = Path(pack_root).resolve()
    runtime = pack.parent / "data/runtime"
    results = []
    for spec in _specifications():
        archive = runtime / spec.archive_name
        if archive.is_file():
            results.append(materialize_runtime_archive(archive, pack_root=pack))
    return {
        "schema": "certvic.kagglefiles.runtime_materialization_batch.v1",
        "status": "AUTHENTICATED_RUNTIME_MATERIALIZATION_COMPLETE",
        "materialized": len(results),
        "records": results,
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?")
    parser.add_argument(
        "--pack-root",
        default=str(REPOSITORY_ROOT / "kagglefiles"),
    )
    parser.add_argument("--clean-operator-metadata", action="store_true")
    args = parser.parse_args(argv)
    try:
        cleanup = (
            clean_operator_metadata(args.pack_root)
            if args.clean_operator_metadata
            else None
        )
        result = (
            materialize_runtime_archive(args.archive, pack_root=args.pack_root)
            if args.archive
            else materialize_imported_runtime_records(pack_root=args.pack_root)
        )
    except (RuntimeMaterializationError, OSError) as error:
        print(json.dumps({
            "status": "RUNTIME_MATERIALIZATION_REJECTED",
            "error": str(error),
            "paper_evidence": False,
        }, indent=2, sort_keys=True))
        return 2
    if cleanup is not None:
        result["operator_metadata_cleanup"] = cleanup
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
