"""Authenticated, name-independent discovery for CertVIC runtime inputs.

Kaggle account names, dataset titles, mount folders, archive names, and notebook
names are operational provenance only.  This module classifies candidates from
small authenticated manifests, fully verifies only candidates relevant to the
requested role, deduplicates mirrors by content identity, and fails closed when
distinct valid content remains.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from certvic.cvpr.kaggle_bundle import HASH_SCHEMA, SCHEMA, canonical_json, verify_bundle


ERROR_NOT_FOUND = "CERTVIC_DISCOVERY_01_REQUIRED_ROLE_NOT_FOUND"
ERROR_AMBIGUOUS = "CERTVIC_DISCOVERY_02_AMBIGUOUS_DISTINCT_CONTENT"
ERROR_AUTHENTICATION = "CERTVIC_DISCOVERY_03_CONTENT_AUTHENTICATION_FAILED"
DISCOVERY_POLICY = "CONTENT_AUTHENTICATED_ANY_LOCATION"
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")

ROLE_BUNDLE_TYPES: dict[str, tuple[str, ...]] = {
    "CODE": ("CODE",),
    "CONFIGS": ("CONFIGS",),
    "EXECUTION_TOOLS": ("EXECUTION_TOOLS",),
    "OFFLINE_LINUX_WHEELHOUSE": ("OFFLINE_LINUX_WHEELHOUSE",),
    "MODEL_SNAPSHOT": ("MODEL_SNAPSHOT", "SYNTHETIC_MODEL_SNAPSHOT_PROOF"),
    "REAL_TWO_ITEM_SMOKE": (
        "REAL_TWO_ITEM_SMOKE_INPUT", "SYNTHETIC_TWO_ITEM_SMOKE_PROOF",
    ),
    "PRE_SMOKE_PERMISSIONS": ("PRE_SMOKE_PERMISSIONS",),
    "CONFIRMATORY_GENERATION_INPUT": ("CONFIRMATORY_GENERATION_INPUT",),
    "GENERATION_INPUT": (
        "CONFIRMATORY_GENERATION_INPUT",
        "MAIN_GENERATION_INPUT",
        "COCO_GENERATION_INPUT",
    ),
    "SCIENTIFIC_PROVIDER_INPUT": (
        "CONFIRMATORY_SCIENTIFIC_PROVIDER_INPUT",
        "MAIN_SCIENTIFIC_PROVIDER_INPUT",
        "COCO_SCIENTIFIC_PROVIDER_INPUT",
    ),
    "SYNTHETIC_VALIDATION": ("SYNTHETIC_VALIDATION",),
    # Compatibility roles used only by the non-evidence synthetic route suite.
    # Keeping them explicit preserves the fail-closed public role allowlist.
    "SYNTHETIC_ZERO_EDIT_MOUNT": ("SYNTHETIC_ZERO_EDIT_MOUNT",),
    "TEST": ("TEST",),
    "TASK_BUNDLE": (),
    "CANONICAL_RETURN": (),
}

ROLE_OVERRIDE_ENV = {
    "CODE": "CERTVIC_EXPECTED_CONTENT_ID_CODE",
    "CONFIGS": "CERTVIC_EXPECTED_CONTENT_ID_CONFIGS",
    "EXECUTION_TOOLS": "CERTVIC_EXPECTED_CONTENT_ID_TOOLS",
    "OFFLINE_LINUX_WHEELHOUSE": "CERTVIC_EXPECTED_CONTENT_ID_WHEELHOUSE",
    "MODEL_SNAPSHOT": "CERTVIC_EXPECTED_CONTENT_ID_SNAPSHOT",
    "REAL_TWO_ITEM_SMOKE": "CERTVIC_EXPECTED_CONTENT_ID_TASKS",
    "TASK_BUNDLE": "CERTVIC_EXPECTED_CONTENT_ID_TASKS",
    "PRE_SMOKE_PERMISSIONS": "CERTVIC_EXPECTED_CONTENT_ID_PERMISSIONS",
    "SCIENTIFIC_PROVIDER_INPUT": "CERTVIC_EXPECTED_CONTENT_ID_PERMISSIONS",
}

OPERATIONAL_MANIFEST_FIELDS = {
    "builder_command",
    "created_time",
    "expected_kaggle_dataset_slug",
    "mount_path",
    "required_notebook",
    "validation_command",
}


class ContentDiscoveryError(RuntimeError):
    """A required authenticated input is missing, ambiguous, or tampered."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative(name: str) -> str:
    normalized = name.replace("\\", "/")
    value = PurePosixPath(normalized)
    if (
        not normalized
        or normalized != name
        or normalized.endswith("/")
        or value.is_absolute()
        or ".." in value.parts
        or "." in value.parts
        or normalized.startswith("~")
        or "\x00" in normalized
    ):
        raise ContentDiscoveryError(f"{ERROR_AUTHENTICATION}: unsafe member {name!r}")
    return value.as_posix()


def _regular_zip_member(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return not info.is_dir() and not stat.S_ISLNK(mode) and (not mode or stat.S_ISREG(mode))


def _roots(values: Iterable[str | Path] | str | Path | None) -> list[Path]:
    if values is None:
        configured = os.environ.get("CERTVIC_INPUT_ROOTS", "")
        raw: list[str | Path] = (
            [value for value in configured.split(os.pathsep) if value]
            if configured
            else ["/kaggle/input", "/kaggle/working"]
        )
    elif isinstance(values, (str, Path)):
        raw = [value for value in str(values).split(os.pathsep) if value]
    else:
        raw = list(values)
    result: list[Path] = []
    seen: set[str] = set()
    for value in raw:
        path = Path(value).expanduser().resolve()
        key = os.path.normcase(path.as_posix())
        if key not in seen and path.is_dir() and not path.is_symlink():
            seen.add(key)
            result.append(path)
    return sorted(result, key=lambda path: os.path.normcase(path.as_posix()))


def _observed(candidate: Path, roots: list[Path]) -> tuple[str, str]:
    for root in roots:
        try:
            relative = candidate.resolve().relative_to(root)
        except ValueError:
            continue
        first = relative.parts[0] if relative.parts else "."
        return root.as_posix(), (root / first).as_posix() if first != "." else root.as_posix()
    return candidate.parent.as_posix(), candidate.parent.as_posix()


def _zip_magic(path: Path) -> bool:
    try:
        if path.is_symlink() or not path.is_file():
            return False
        with path.open("rb") as handle:
            return handle.read(4) in ZIP_MAGICS
    except OSError:
        return False


def _small_json(payload: bytes, label: str) -> dict[str, Any]:
    if len(payload) > MAX_MANIFEST_BYTES:
        raise ContentDiscoveryError(f"{ERROR_AUTHENTICATION}: oversized {label}")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContentDiscoveryError(f"{ERROR_AUTHENTICATION}: malformed {label}: {error}") from error
    if not isinstance(value, dict):
        raise ContentDiscoveryError(f"{ERROR_AUTHENTICATION}: {label} must be an object")
    return value


def _archive_probe(path: Path) -> dict[str, Any] | None:
    try:
        with zipfile.ZipFile(path) as archive:
            try:
                info = archive.getinfo("bundle_manifest.json")
            except KeyError:
                return None
            if info.file_size > MAX_MANIFEST_BYTES:
                raise ContentDiscoveryError(
                    f"{ERROR_AUTHENTICATION}: oversized bundle manifest at {path}"
                )
            manifest = _small_json(archive.read(info), "bundle_manifest.json")
            return manifest if manifest.get("schema") == SCHEMA else None
    except ContentDiscoveryError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError):
        return None


def _directory_probe(path: Path) -> dict[str, Any] | None:
    marker = path / "bundle_manifest.json"
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > MAX_MANIFEST_BYTES:
        return None
    try:
        manifest = _small_json(marker.read_bytes(), "bundle_manifest.json")
    except (OSError, ContentDiscoveryError):
        return None
    return manifest if manifest.get("schema") == SCHEMA else None


def _role_matches(role: str, manifest: Mapping[str, Any]) -> bool:
    bundle_type = str(manifest.get("bundle_type", ""))
    return bundle_type in ROLE_BUNDLE_TYPES.get(role, ())


def _metadata_matches(
    manifest: Mapping[str, Any],
    *,
    provider: str | None,
    study: str | None,
    stage: str | None,
) -> tuple[bool, str | None]:
    for field, expected in (("provider", provider), ("study", study), ("stage", stage)):
        if expected is not None and manifest.get(field) != expected:
            return False, f"{field} mismatch: expected={expected!r} observed={manifest.get(field)!r}"
    return True, None


def _semantic_identity(manifest: Mapping[str, Any], hash_files: Mapping[str, Any]) -> str:
    scientific_manifest = {
        key: value for key, value in manifest.items() if key not in OPERATIONAL_MANIFEST_FIELDS
    }
    scientific_files = {
        name: record
        for name, record in hash_files.items()
        if name not in {"README.md", "bundle_manifest.json"}
    }
    return hashlib.sha256(canonical_json({
        "manifest": scientific_manifest,
        "files": scientific_files,
    })).hexdigest()


def _directory_verification(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    hashes: dict[str, Any] = {}
    observed: dict[str, Path] = {}
    try:
        for member in path.rglob("*"):
            relative = member.relative_to(path).as_posix()
            mode = member.lstat().st_mode
            if member.is_symlink() or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                errors.append(f"unsafe extracted member: {relative}")
            elif stat.S_ISREG(mode):
                observed[relative] = member
        manifest = _small_json((path / "bundle_manifest.json").read_bytes(), "bundle_manifest.json")
        hashes = _small_json((path / "hash_manifest.json").read_bytes(), "hash_manifest.json")
        if manifest.get("schema") != SCHEMA:
            errors.append("bundle schema mismatch")
        if hashes.get("schema") != HASH_SCHEMA:
            errors.append("hash manifest schema mismatch")
        declared = manifest.get("files")
        hash_files = hashes.get("files")
        if not isinstance(declared, dict) or not isinstance(hash_files, dict):
            errors.append("manifest file inventories must be mappings")
            declared, hash_files = {}, {}
        expected = set(hash_files) | {"hash_manifest.json"}
        if set(observed) != expected:
            errors.append(
                "extracted file universe mismatch: "
                f"missing={sorted(expected - set(observed))} extra={sorted(set(observed) - expected)}"
            )
        if set(declared) != set(observed) - {"bundle_manifest.json", "hash_manifest.json"}:
            errors.append("bundle manifest payload file list mismatch")
        verified_records: dict[str, dict[str, Any]] = {}
        for name, record in hash_files.items():
            member = observed.get(name)
            if member is None:
                continue
            actual = {"size": member.stat().st_size, "sha256": _sha256_file(member)}
            verified_records[name] = actual
            if actual != record:
                errors.append(f"hash manifest mismatch: {name}")
        for name, record in declared.items():
            if verified_records.get(name) != record:
                errors.append(f"bundle manifest mismatch: {name}")
    except (OSError, KeyError, ContentDiscoveryError) as error:
        errors.append(str(error))
    return {
        "passed": not errors,
        "errors": errors,
        "bundle_manifest": manifest,
        "hash_manifest": hashes,
        "manifest_sha256": (
            _sha256_file(path / "bundle_manifest.json")
            if (path / "bundle_manifest.json").is_file()
            else None
        ),
        "verified_file_count": len(observed),
        "verified_total_bytes": sum(member.stat().st_size for member in observed.values()),
    }


def _archive_authentication(path: Path) -> dict[str, Any]:
    verified = verify_bundle(path)
    hashes: dict[str, Any] = {}
    manifest_sha256: str | None = None
    if verified["passed"]:
        with zipfile.ZipFile(path) as archive:
            manifest_bytes = archive.read("bundle_manifest.json")
            manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
            hashes = _small_json(archive.read("hash_manifest.json"), "hash_manifest.json")
            total = sum(info.file_size for info in archive.infolist())
    else:
        total = 0
    return {
        **verified,
        "hash_manifest": hashes,
        "manifest_sha256": manifest_sha256,
        "verified_file_count": verified.get("member_count", 0),
        "verified_total_bytes": total,
    }


def _materialization_base(value: str | Path | None) -> Path:
    if value is not None:
        return Path(value).resolve()
    configured = os.environ.get("CERTVIC_MATERIALIZED_ROOT")
    if configured:
        return Path(configured).resolve()
    kaggle = Path("/kaggle/working")
    if kaggle.is_dir() and os.access(kaggle, os.W_OK):
        return kaggle / "certvic_authenticated_inputs"
    return Path(tempfile.gettempdir()) / "certvic_authenticated_inputs"


def _extract_archive(path: Path, destination: Path) -> Path:
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir():
            raise ContentDiscoveryError(
                f"{ERROR_AUTHENTICATION}: unsafe materialization destination {destination}"
            )
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [_safe_relative(info.filename) for info in infos]
            if len(names) != len(set(names)):
                raise ContentDiscoveryError(
                    f"{ERROR_AUTHENTICATION}: duplicate archive members"
                )
            if archive.testzip() is not None:
                raise ContentDiscoveryError(f"{ERROR_AUTHENTICATION}: corrupt archive")
            for info, name in zip(infos, names, strict=True):
                if not _regular_zip_member(info):
                    raise ContentDiscoveryError(
                        f"{ERROR_AUTHENTICATION}: unsafe archive member {name}"
                    )
                output = (destination / name).resolve()
                try:
                    output.relative_to(destination)
                except ValueError as error:
                    raise ContentDiscoveryError(
                        f"{ERROR_AUTHENTICATION}: traversal member {name}"
                    ) from error
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, output.open("xb") as sink:
                    shutil.copyfileobj(source, sink, length=1024 * 1024)
        checked = _directory_verification(destination)
        if not checked["passed"]:
            raise ContentDiscoveryError(
                f"{ERROR_AUTHENTICATION}: extracted authentication failed: {checked['errors']}"
            )
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return destination


def _identity_override(role: str, expected_identity: str | Mapping[str, Any] | None) -> Any:
    if expected_identity is not None:
        return expected_identity
    variable = ROLE_OVERRIDE_ENV.get(role)
    return os.environ.get(variable) if variable else None


def _override_matches(candidate: Mapping[str, Any], expected: Any) -> bool:
    if expected is None or expected == "":
        return True
    if isinstance(expected, str):
        return candidate.get("content_identity_sha256") == expected.lower()
    if isinstance(expected, Mapping):
        manifest = candidate.get("bundle_manifest", {})
        return all(
            candidate.get(key, manifest.get(key) if isinstance(manifest, Mapping) else None)
            == value
            for key, value in expected.items()
        )
    return False


def _candidate_paths(roots: list[Path]) -> tuple[list[Path], list[Path], dict[str, int]]:
    archives: list[Path] = []
    directories: list[Path] = []
    stats = {"regular_files_probed": 0, "zip_candidates": 0, "manifest_directories": 0}
    seen_archives: set[str] = set()
    seen_directories: set[str] = set()
    for root in roots:
        for current, directory_names, file_names in os.walk(root, followlinks=False):
            base = Path(current)
            directory_names[:] = sorted(
                name for name in directory_names if not (base / name).is_symlink()
            )
            if (
                "bundle_manifest.json" in file_names and "hash_manifest.json" in file_names
            ) or "task_bundle_manifest.json" in file_names:
                key = os.path.normcase(base.resolve().as_posix())
                if key not in seen_directories:
                    seen_directories.add(key)
                    directories.append(base.resolve())
                    stats["manifest_directories"] += 1
            for name in sorted(file_names):
                path = base / name
                if path.is_symlink() or not path.is_file():
                    continue
                stats["regular_files_probed"] += 1
                if _zip_magic(path):
                    key = os.path.normcase(path.resolve().as_posix())
                    if key not in seen_archives:
                        seen_archives.add(key)
                        archives.append(path.resolve())
                        stats["zip_candidates"] += 1
    return sorted(archives), sorted(directories), stats


def _task_bundle_directory(path: Path) -> dict[str, Any] | None:
    marker = path / "task_bundle_manifest.json"
    if marker.is_symlink() or not marker.is_file():
        return None
    try:
        manifest = _small_json(marker.read_bytes(), "task_bundle_manifest.json")
    except (OSError, ContentDiscoveryError):
        return None
    if manifest.get("schema") != "certvic.cvpr.task_bundle.v1":
        return None
    for member in path.rglob("*"):
        mode = member.lstat().st_mode
        if member.is_symlink() or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise ContentDiscoveryError(
                f"{ERROR_AUTHENTICATION}: unsafe task bundle member"
            )
    try:
        from certvic.cvpr.task_bundle import verify_bundle as verify_task_bundle

        verified = verify_task_bundle(path, marker)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ContentDiscoveryError(
            f"{ERROR_AUTHENTICATION}: task bundle authentication failed: {error}"
        ) from error
    return {
        "manifest": manifest,
        "content_identity_sha256": verified["bundle_hash"],
        "manifest_sha256": _sha256_file(marker),
        "verified_file_count": int(verified["files"]) + 1,
        "verified_total_bytes": sum(
            member.stat().st_size for member in path.rglob("*") if member.is_file()
        ),
    }


def _return_hash_record(record: Any) -> tuple[int | None, str | None]:
    if isinstance(record, str):
        return None, record
    if isinstance(record, Mapping):
        return (
            int(record["size"]) if record.get("size") is not None else None,
            str(record.get("sha256")) if record.get("sha256") is not None else None,
        )
    return None, None


def _canonical_return_archive(path: Path) -> dict[str, Any] | None:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [_safe_relative(info.filename) for info in infos]
            if "hash_manifest.json" not in names or "bundle_manifest.json" in names:
                return None
            if len(names) != len(set(names)) or archive.testzip() is not None:
                raise ContentDiscoveryError(
                    f"{ERROR_AUTHENTICATION}: invalid canonical return archive"
                )
            if any(not _regular_zip_member(info) for info in infos):
                raise ContentDiscoveryError(
                    f"{ERROR_AUTHENTICATION}: unsafe canonical return member"
                )
            hashes = _small_json(archive.read("hash_manifest.json"), "hash_manifest.json")
            records = hashes.get("files")
            if not isinstance(records, Mapping):
                return None
            if set(names) != set(records) | {"hash_manifest.json"}:
                raise ContentDiscoveryError(
                    f"{ERROR_AUTHENTICATION}: canonical return file universe mismatch"
                )
            normalized: dict[str, dict[str, Any]] = {}
            for name, record in records.items():
                payload = archive.read(name)
                expected_size, expected_hash = _return_hash_record(record)
                observed_hash = hashlib.sha256(payload).hexdigest()
                if expected_hash != observed_hash or (
                    expected_size is not None and expected_size != len(payload)
                ):
                    raise ContentDiscoveryError(
                        f"{ERROR_AUTHENTICATION}: canonical return hash mismatch {name}"
                    )
                normalized[name] = {"size": len(payload), "sha256": observed_hash}
            runtime: dict[str, Any] = {}
            for name in ("runtime_manifest.json", "run_contract.json"):
                if name in names:
                    runtime = _small_json(archive.read(name), name)
                    break
            identity = hashlib.sha256(canonical_json(normalized)).hexdigest()
            return {
                "manifest": runtime,
                "content_identity_sha256": identity,
                "manifest_sha256": hashlib.sha256(
                    canonical_json(runtime) if runtime else canonical_json(normalized)
                ).hexdigest(),
                "verified_file_count": len(names),
                "verified_total_bytes": sum(info.file_size for info in infos),
                "archive_sha256": _sha256_file(path),
            }
    except ContentDiscoveryError:
        raise
    except (OSError, zipfile.BadZipFile, KeyError, RuntimeError):
        return None


def _discover_special(
    role: str,
    *,
    archives: list[Path],
    directories: list[Path],
    roots: list[Path],
    provider: str | None,
    study: str | None,
    stage: str | None,
    override: Any,
    materialization_root: str | Path | None,
    probe_stats: dict[str, int],
) -> dict[str, Any] | None:
    valid: list[dict[str, Any]] = []
    failures: list[str] = []
    if role == "TASK_BUNDLE":
        for path in directories:
            try:
                result = _task_bundle_directory(path)
            except ContentDiscoveryError as error:
                failures.append(f"{path}: {error}")
                continue
            if result is None:
                continue
            manifest = result["manifest"]
            if study is not None and manifest.get("study") != study:
                failures.append(f"{path}: study mismatch")
                continue
            observed_mount, observed_folder = _observed(path, roots)
            valid.append({
                "role": role,
                "provider": None,
                "study": manifest.get("study"),
                "stage": "task_bundle",
                "representation": "extracted_directory",
                "discovered_path": path.as_posix(),
                "materialized_root": path.as_posix(),
                "bundle_schema": manifest.get("schema"),
                "manifest_sha256": result["manifest_sha256"],
                "content_identity_sha256": result["content_identity_sha256"],
                "archive_sha256": None,
                "verified_file_count": result["verified_file_count"],
                "verified_total_bytes": result["verified_total_bytes"],
                "observed_mount": observed_mount,
                "observed_dataset_folder": observed_folder,
                "bundle_manifest": manifest,
                "paper_evidence": False,
            })
    elif role == "CANONICAL_RETURN":
        for path in archives:
            try:
                result = _canonical_return_archive(path)
            except ContentDiscoveryError as error:
                failures.append(f"{path}: {error}")
                continue
            if result is None:
                continue
            manifest = result["manifest"]
            metadata_ok, reason = _metadata_matches(
                manifest, provider=provider, study=study, stage=stage
            )
            if not metadata_ok:
                failures.append(f"{path}: {reason}")
                continue
            observed_mount, observed_folder = _observed(path, roots)
            candidate = {
                "role": role,
                "provider": manifest.get("provider"),
                "study": manifest.get("study"),
                "stage": manifest.get("stage"),
                "representation": "zip_archive",
                "discovered_path": path.as_posix(),
                "materialized_root": path.parent.as_posix(),
                "bundle_schema": manifest.get("schema"),
                "manifest_sha256": result["manifest_sha256"],
                "content_identity_sha256": result["content_identity_sha256"],
                "archive_sha256": result["archive_sha256"],
                "verified_file_count": result["verified_file_count"],
                "verified_total_bytes": result["verified_total_bytes"],
                "observed_mount": observed_mount,
                "observed_dataset_folder": observed_folder,
                "bundle_manifest": manifest,
                "paper_evidence": False,
            }
            valid.append(candidate)
    else:
        return None
    authenticated = list(valid)
    valid = [row for row in valid if _override_matches(row, override)]
    if not valid:
        if authenticated and override is not None and override != "":
            raise ContentDiscoveryError(
                f"{ERROR_AUTHENTICATION}: role={role} expected content identity mismatch"
            )
        if failures:
            raise ContentDiscoveryError(f"{ERROR_AUTHENTICATION}: role={role} failures={failures}")
        raise ContentDiscoveryError(f"{ERROR_NOT_FOUND}: role={role}")
    identities = {row["content_identity_sha256"] for row in valid}
    if len(identities) != 1:
        raise ContentDiscoveryError(
            f"{ERROR_AMBIGUOUS}: role={role} candidates="
            f"{[(row['content_identity_sha256'], row['discovered_path']) for row in valid]}"
        )
    selected = min(valid, key=lambda row: os.path.normcase(row["discovered_path"]))
    mirrors = sorted({row["discovered_path"] for row in valid})
    selected.update({
        "schema": "certvic.cvpr.authenticated_content_discovery.v1",
        "discovery_policy": DISCOVERY_POLICY,
        "owner_binding_required": False,
        "filename_binding_required": False,
        "path_binding_required": False,
        "accepted_representations": ["zip_archive", "extracted_directory"],
        "mirrors": mirrors,
        "mirror_count": len(mirrors),
        "probe_stats": probe_stats,
    })
    return selected


def discover_authenticated_input(
    role: str,
    provider: str | None = None,
    study: str | None = None,
    stage: str | None = None,
    roots: Iterable[str | Path] | str | Path | None = None,
    expected_identity: str | Mapping[str, Any] | None = None,
    *,
    materialization_root: str | Path | None = None,
) -> dict[str, Any]:
    """Discover and materialize exactly one authenticated content identity."""
    normalized_role = role.upper()
    if normalized_role not in ROLE_BUNDLE_TYPES:
        raise ValueError(f"unsupported authenticated input role: {role}")
    search_roots = _roots(roots)
    if not search_roots:
        raise ContentDiscoveryError(
            f"{ERROR_NOT_FOUND}: role={normalized_role} roots=[]"
        )
    override = _identity_override(normalized_role, expected_identity)
    archives, directories, probe_stats = _candidate_paths(search_roots)
    special = _discover_special(
        normalized_role,
        archives=archives,
        directories=directories,
        roots=search_roots,
        provider=provider,
        study=study,
        stage=stage,
        override=override,
        materialization_root=materialization_root,
        probe_stats=probe_stats,
    )
    if special is not None:
        return special
    valid: list[dict[str, Any]] = []
    failures: list[str] = []

    for representation, paths in (("zip_archive", archives), ("extracted_directory", directories)):
        for path in paths:
            try:
                manifest = _archive_probe(path) if representation == "zip_archive" else _directory_probe(path)
            except ContentDiscoveryError as error:
                failures.append(f"{path}: {error}")
                continue
            if manifest is None or not _role_matches(normalized_role, manifest):
                continue
            metadata_ok, reason = _metadata_matches(
                manifest, provider=provider, study=study, stage=stage
            )
            if not metadata_ok:
                failures.append(f"{path}: {reason}")
                continue
            authentication = (
                _archive_authentication(path)
                if representation == "zip_archive"
                else _directory_verification(path)
            )
            if not authentication["passed"]:
                failures.append(f"{path}: {authentication['errors']}")
                continue
            authenticated_manifest = authentication["bundle_manifest"]
            hash_files = authentication["hash_manifest"].get("files", {})
            identity = _semantic_identity(authenticated_manifest, hash_files)
            observed_mount, observed_folder = _observed(path, search_roots)
            candidate = {
                "role": normalized_role,
                "provider": authenticated_manifest.get("provider"),
                "study": authenticated_manifest.get("study"),
                "stage": authenticated_manifest.get("stage"),
                "representation": representation,
                "discovered_path": path.as_posix(),
                "bundle_schema": authenticated_manifest.get("schema"),
                "manifest_sha256": authentication["manifest_sha256"],
                "content_identity_sha256": identity,
                "archive_sha256": authentication.get("sha256"),
                "verified_file_count": authentication["verified_file_count"],
                "verified_total_bytes": authentication["verified_total_bytes"],
                "observed_mount": observed_mount,
                "observed_dataset_folder": observed_folder,
                "bundle_manifest": authenticated_manifest,
                "paper_evidence": False,
            }
            if not _override_matches(candidate, override):
                failures.append(f"{path}: expected content identity override mismatch")
                continue
            valid.append(candidate)

    if not valid:
        if failures:
            raise ContentDiscoveryError(
                f"{ERROR_AUTHENTICATION}: role={normalized_role} failures={failures}"
            )
        raise ContentDiscoveryError(
            f"{ERROR_NOT_FOUND}: role={normalized_role} roots={[path.as_posix() for path in search_roots]}"
        )
    identities = {row["content_identity_sha256"] for row in valid}
    if len(identities) != 1:
        summary = sorted(
            (row["content_identity_sha256"], row["discovered_path"]) for row in valid
        )
        raise ContentDiscoveryError(
            f"{ERROR_AMBIGUOUS}: role={normalized_role} candidates={summary}"
        )
    mirrors = sorted(
        {row["discovered_path"] for row in valid}, key=lambda value: os.path.normcase(value)
    )
    selected = min(valid, key=lambda row: os.path.normcase(row["discovered_path"]))
    identity = selected["content_identity_sha256"]
    if selected["representation"] == "zip_archive":
        destination = _materialization_base(materialization_root) / f"{normalized_role.lower()}_{identity[:16]}"
        selected["materialized_root"] = _extract_archive(
            Path(selected["discovered_path"]), destination
        ).as_posix()
    else:
        selected["materialized_root"] = selected["discovered_path"]
    selected.update({
        "schema": "certvic.cvpr.authenticated_content_discovery.v1",
        "discovery_policy": DISCOVERY_POLICY,
        "owner_binding_required": False,
        "filename_binding_required": False,
        "path_binding_required": False,
        "accepted_representations": ["zip_archive", "extracted_directory"],
        "mirrors": mirrors,
        "mirror_count": len(mirrors),
        "probe_stats": probe_stats,
    })
    return selected


def role_for_bundle_type(bundle_type: str) -> str:
    """Map a canonical outer bundle type to its public discovery role."""
    for role, types in ROLE_BUNDLE_TYPES.items():
        if bundle_type in types:
            return role
    raise ValueError(f"no authenticated discovery role for bundle type: {bundle_type}")


def authenticate_content_path(
    path: str | Path,
    role: str,
    *,
    provider: str | None = None,
    study: str | None = None,
    stage: str | None = None,
) -> str:
    """Return the semantic identity of one exact canonical bundle path.

    This is used while issuing permissions from already selected local files. It
    deliberately authenticates bytes and manifest metadata without using the
    filename or searching neighboring paths.
    """
    normalized_role = role.upper()
    if normalized_role not in ROLE_BUNDLE_TYPES or normalized_role in {
        "TASK_BUNDLE", "CANONICAL_RETURN"
    }:
        raise ValueError(f"unsupported canonical bundle identity role: {role}")
    candidate = Path(path).resolve()
    if candidate.name == "bundle_manifest.json":
        candidate = candidate.parent
    representation = "zip_archive" if candidate.is_file() else "extracted_directory"
    manifest = (
        _archive_probe(candidate)
        if representation == "zip_archive"
        else _directory_probe(candidate)
    )
    if manifest is None or not _role_matches(normalized_role, manifest):
        raise ContentDiscoveryError(
            f"{ERROR_AUTHENTICATION}: role={normalized_role} candidate classification failed"
        )
    metadata_ok, reason = _metadata_matches(
        manifest, provider=provider, study=study, stage=stage
    )
    if not metadata_ok:
        raise ContentDiscoveryError(f"{ERROR_AUTHENTICATION}: {reason}")
    authentication = (
        _archive_authentication(candidate)
        if representation == "zip_archive"
        else _directory_verification(candidate)
    )
    if not authentication["passed"]:
        raise ContentDiscoveryError(
            f"{ERROR_AUTHENTICATION}: candidate authentication failed: "
            f"{authentication['errors']}"
        )
    return _semantic_identity(
        authentication["bundle_manifest"],
        authentication["hash_manifest"].get("files", {}),
    )


def resolve_content_bound_roles(
    root: str | Path,
    role_sha256: Mapping[str, str],
) -> dict[str, str]:
    """Resolve authenticated inner role files by digest, never by filename."""
    base = Path(root).resolve()
    expected = {str(role): str(digest).lower() for role, digest in role_sha256.items()}
    wanted = set(expected.values())
    matches: dict[str, list[Path]] = {digest: [] for digest in wanted}
    for path in base.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        digest = _sha256_file(path)
        if digest in matches:
            matches[digest].append(path.resolve())
    code_digest = expected.get("code_bundle")
    if code_digest and not matches[code_digest]:
        for path in base.rglob("*"):
            if not _zip_magic(path):
                continue
            try:
                identity = authenticate_content_path(path, "CODE")
            except (ContentDiscoveryError, OSError, ValueError):
                continue
            if identity == code_digest:
                matches[code_digest].append(path.resolve())
    resolved: dict[str, str] = {}
    for role, digest in sorted(expected.items()):
        candidates = sorted(set(matches[digest]))
        if not candidates:
            raise ContentDiscoveryError(
                f"{ERROR_AUTHENTICATION}: bound inner role missing: {role}"
            )
        resolved[role] = candidates[0].as_posix()
    return resolved
