"""Deterministic, portable, and fail-closed Kaggle input bundle format.

The format deliberately keeps metadata outside the scientific payload.  ``bundle_manifest.json``
describes every payload member (including ``README.md``), while ``hash_manifest.json`` binds that
manifest and every described member.  The hash manifest cannot hash itself, so it is the sole
permitted member not listed in its own mapping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


SCHEMA = "certvic.kaggle.bundle.v1"
HASH_SCHEMA = "certvic.kaggle.hash_manifest.v1"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
REQUIRED_MEMBERS = {"README.md", "bundle_manifest.json", "hash_manifest.json"}
RESERVED_MEMBERS = {"bundle_manifest.json", "hash_manifest.json"}
HOST_PATH = re.compile(
    rb"(?:/" + b"Users" + rb"/[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*|/"
    + b"home" + rb"/[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*|"
    + rb"[A-Za-z]:\\" + b"Users" + rb"\\[A-Za-z0-9][A-Za-z0-9._-]*\\"
    + rb"[A-Za-z0-9][A-Za-z0-9._-]*)"
)


class KaggleBundleError(ValueError):
    """The bundle is unsafe, incomplete, or inconsistent with its manifest."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _safe_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.endswith("/")
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or normalized.startswith("~")
        or "\x00" in normalized
    ):
        raise KaggleBundleError(f"unsafe archive member: {name!r}")
    return path.as_posix()


def _portable_payload(name: str, payload: bytes) -> None:
    suffix = PurePosixPath(name).suffix.lower()
    textual = suffix in {
        ".csv", ".ini", ".ipynb", ".json", ".jsonl", ".lock", ".md", ".py", ".sh",
        ".toml", ".txt", ".yaml", ".yml",
    }
    if textual and HOST_PATH.search(payload):
        raise KaggleBundleError(f"host-specific absolute path in {name}")


def _payload(value: bytes | bytearray | str | Path) -> bytes:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    source = Path(value)
    if source.is_symlink():
        raise KaggleBundleError(f"symlink inputs are prohibited: {source}")
    if not source.is_file():
        raise KaggleBundleError(f"bundle input is not a regular file: {source}")
    return source.read_bytes()


def _entry(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256_bytes(payload)}


def _source(value: bytes | bytearray | str | Path) -> bytes | Path:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    path = Path(value)
    if path.is_symlink():
        raise KaggleBundleError(f"symlink inputs are prohibited: {path}")
    if not path.is_file():
        raise KaggleBundleError(f"bundle input is not a regular file: {path}")
    return path


def _source_entry(value: bytes | Path) -> dict[str, Any]:
    if isinstance(value, bytes):
        return _entry(value)
    return {"size": value.stat().st_size, "sha256": sha256_file(value)}


def _portable_source(name: str, value: bytes | Path) -> None:
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in {
        ".csv", ".ini", ".ipynb", ".json", ".jsonl", ".lock", ".md", ".py", ".sh",
        ".toml", ".txt", ".yaml", ".yml",
    }:
        return
    payload = value if isinstance(value, bytes) else value.read_bytes()
    _portable_payload(name, payload)


def build_bundle(
    output: str | Path,
    files: Mapping[str, bytes | bytearray | str | Path],
    *,
    bundle_type: str,
    study: str,
    stage: str,
    provider: str | None,
    required_notebook: str,
    dataset_slug: str,
    mount_path: str,
    external_dependency_status: str,
    evidence_class: str,
    builder_command: str,
    validation_command: str | None = None,
    readme: str,
    extra_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a byte-reproducible v1 archive and return its immutable identity."""
    if not dataset_slug or "/" not in dataset_slug:
        raise KaggleBundleError("expected Kaggle dataset slug must be owner/dataset")
    if not mount_path.startswith("/kaggle/input/"):
        raise KaggleBundleError("mount path must be below /kaggle/input")
    # Keep large wheel/model files as paths.  Reading 16 GB checkpoints into a
    # Python mapping made the otherwise-correct snapshot builder non-executable.
    members: dict[str, bytes | Path] = {}
    for raw_name, value in files.items():
        name = _safe_name(raw_name)
        if name in RESERVED_MEMBERS or name in members:
            raise KaggleBundleError(f"reserved or duplicate member: {name}")
        payload = _source(value)
        _portable_source(name, payload)
        members[name] = payload
    members["README.md"] = readme.rstrip().encode("utf-8") + b"\n"
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "bundle_type": bundle_type,
        "study": study,
        "stage": stage,
        "provider": provider,
        "created_time": "1980-01-01T00:00:00Z",
        "deterministic_build": True,
        "files": {name: _source_entry(payload) for name, payload in sorted(members.items())},
        "required_notebook": required_notebook,
        "expected_kaggle_dataset_slug": dataset_slug,
        "mount_path": mount_path,
        "external_dependency_status": external_dependency_status,
        "evidence_class": evidence_class,
        "builder_command": builder_command,
        "validation_command": validation_command or (
            f"python3 -m certvic.cvpr.kaggle_bundle verify {Path(output).as_posix()}"
        ),
        "paper_evidence": False,
    }
    if extra_manifest:
        collisions = set(manifest) & set(extra_manifest)
        if collisions:
            raise KaggleBundleError(f"extra manifest fields collide: {sorted(collisions)}")
        manifest.update(extra_manifest)
    manifest_bytes = canonical_json(manifest)
    members["bundle_manifest.json"] = manifest_bytes
    hash_manifest = {
        "schema": HASH_SCHEMA,
        "algorithm": "sha256",
        "files": {name: _source_entry(payload) for name, payload in sorted(members.items())},
        "paper_evidence": False,
    }
    members["hash_manifest.json"] = canonical_json(hash_manifest)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as raw:
        with zipfile.ZipFile(
            raw, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            for name, payload in sorted(members.items()):
                info = zipfile.ZipInfo(name, FIXED_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                if isinstance(payload, Path):
                    with payload.open("rb") as source, archive.open(info, "w") as destination_member:
                        shutil.copyfileobj(source, destination_member, length=1024 * 1024)
                else:
                    archive.writestr(
                        info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
                    )
    verification = verify_bundle(destination)
    if not verification["passed"]:
        raise KaggleBundleError(f"new bundle failed self-verification: {verification['errors']}")
    return {
        "path": destination.as_posix(),
        "size": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "member_count": len(members),
        "manifest": manifest,
        "passed": True,
    }


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)


def _archive_entry(archive: zipfile.ZipFile, name: str) -> tuple[dict[str, Any], bool]:
    digest = hashlib.sha256()
    size = 0
    textual = PurePosixPath(name).suffix.lower() in {
        ".csv", ".ini", ".ipynb", ".json", ".jsonl", ".lock", ".md", ".py", ".sh",
        ".toml", ".txt", ".yaml", ".yml",
    }
    portable = True
    tail = b""
    with archive.open(name) as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
            if textual:
                window = tail + block
                if HOST_PATH.search(window):
                    portable = False
                tail = window[-512:]
    return {"size": size, "sha256": digest.hexdigest()}, portable


def verify_bundle(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    hash_manifest: dict[str, Any] = {}
    try:
        with zipfile.ZipFile(source) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                errors.append("duplicate archive members")
            for info in infos:
                try:
                    _safe_name(info.filename)
                except KaggleBundleError as error:
                    errors.append(str(error))
                if info.is_dir():
                    errors.append(f"directory entries are prohibited: {info.filename}")
                if _is_symlink(info):
                    errors.append(f"symlink archive member: {info.filename}")
                if info.date_time != FIXED_TIME:
                    errors.append(f"non-deterministic timestamp: {info.filename}")
            if REQUIRED_MEMBERS - set(names):
                errors.append(f"required members missing: {sorted(REQUIRED_MEMBERS - set(names))}")
            try:
                manifest = json.loads(archive.read("bundle_manifest.json"))
                hash_manifest = json.loads(archive.read("hash_manifest.json"))
            except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as error:
                errors.append(f"invalid metadata: {error}")
            if manifest.get("schema") != SCHEMA:
                errors.append("bundle schema mismatch")
            if hash_manifest.get("schema") != HASH_SCHEMA:
                errors.append("hash manifest schema mismatch")
            declared = manifest.get("files")
            hashes = hash_manifest.get("files")
            if not isinstance(declared, dict):
                errors.append("bundle manifest files must be a mapping")
                declared = {}
            if not isinstance(hashes, dict):
                errors.append("hash manifest files must be a mapping")
                hashes = {}
            expected_names = set(hashes) | {"hash_manifest.json"}
            if set(names) != expected_names:
                errors.append(
                    "unexpected or unmanifested files: "
                    f"missing={sorted(expected_names - set(names))}, "
                    f"extra={sorted(set(names) - expected_names)}"
                )
            if set(declared) != set(names) - RESERVED_MEMBERS:
                errors.append("bundle manifest payload file list mismatch")
            observed_records: dict[str, dict[str, Any]] = {}
            for name, record in hashes.items():
                try:
                    observed, portable = _archive_entry(archive, name)
                    observed_records[name] = observed
                except (KeyError, OSError, RuntimeError, zipfile.BadZipFile) as error:
                    errors.append(f"cannot read archive member {name}: {error}")
                    continue
                if not isinstance(record, dict) or record != observed:
                    errors.append(f"hash manifest mismatch: {name}")
                if not portable:
                    errors.append(f"host-specific absolute path in {name}")
            for name, record in declared.items():
                if not isinstance(record, dict) or record != observed_records.get(name):
                    errors.append(f"bundle manifest mismatch: {name}")
    except (OSError, zipfile.BadZipFile) as error:
        errors.append(f"invalid ZIP: {error}")
        names = []
    return {
        "schema": "certvic.kaggle.bundle.verification.v1",
        "path": source.as_posix(),
        "passed": not errors,
        "errors": errors,
        "sha256": sha256_file(source) if source.is_file() else None,
        "size": source.stat().st_size if source.is_file() else None,
        "member_count": len(names),
        "bundle_manifest": manifest,
        "paper_evidence": False,
    }


def inspect_bundle(path: str | Path) -> dict[str, Any]:
    result = verify_bundle(path)
    return {
        "path": result["path"],
        "passed": result["passed"],
        "errors": result["errors"],
        "sha256": result["sha256"],
        "size": result["size"],
        "member_count": result["member_count"],
        "manifest": result["bundle_manifest"],
    }


def diff_bundles(left: str | Path, right: str | Path) -> dict[str, Any]:
    a = verify_bundle(left)
    b = verify_bundle(right)
    a_files = a.get("bundle_manifest", {}).get("files", {})
    b_files = b.get("bundle_manifest", {}).get("files", {})
    return {
        "schema": "certvic.kaggle.bundle.diff.v1",
        "identical_bytes": a.get("sha256") == b.get("sha256"),
        "left_valid": a["passed"],
        "right_valid": b["passed"],
        "added": sorted(set(b_files) - set(a_files)),
        "removed": sorted(set(a_files) - set(b_files)),
        "changed": sorted(
            name for name in set(a_files) & set(b_files) if a_files[name] != b_files[name]
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("verify", "inspect"):
        sub = subparsers.add_parser(command)
        sub.add_argument("zip")
    diff = subparsers.add_parser("diff")
    diff.add_argument("left")
    diff.add_argument("right")
    args = parser.parse_args(argv)
    if args.command == "verify":
        result = verify_bundle(args.zip)
    elif args.command == "inspect":
        result = inspect_bundle(args.zip)
    else:
        result = diff_bundles(args.left, args.right)
    print(json.dumps(result, indent=2, sort_keys=True))
    passed = result.get("passed", result.get("left_valid") and result.get("right_valid"))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
