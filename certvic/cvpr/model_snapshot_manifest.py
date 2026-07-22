"""Create and strictly verify immutable, offline model snapshot manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


COMMIT = re.compile(r"^[0-9a-f]{40}$")
MANIFEST_NAME = "certvic_model_snapshot_manifest.json"
PROCESSOR_FILES = {
    "tokenizer.json",
    "tokenizer_config.json",
    "processor_config.json",
    "preprocessor_config.json",
    "special_tokens_map.json",
    "chat_template.json",
}


class SnapshotManifestError(ValueError):
    pass


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot_files(root: Path) -> list[Path]:
    excluded_parts = {".cache", ".git", "__pycache__"}
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.name not in {MANIFEST_NAME, ".DS_Store"}
        and not excluded_parts.intersection(path.relative_to(root).parts)
        and not path.is_symlink()
    )


def _architecture(root: Path) -> tuple[list[str], str]:
    config_path = root / "config.json"
    if not config_path.is_file():
        raise SnapshotManifestError("snapshot is missing config.json")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotManifestError("snapshot config.json is invalid") from exc
    architectures = config.get("architectures", [])
    if not isinstance(architectures, list) or not architectures:
        raise SnapshotManifestError("config.json does not declare architectures")
    model_type = str(config.get("model_type", ""))
    if not model_type:
        raise SnapshotManifestError("config.json does not declare model_type")
    return [str(value) for value in architectures], model_type


def create_manifest(
    snapshot: str | Path,
    *,
    model_id: str,
    model_commit: str,
    processor_commit: str,
    expected_architecture: str,
    processor_id: str | None = None,
) -> dict[str, Any]:
    root = Path(snapshot).resolve()
    if not root.is_dir():
        raise SnapshotManifestError(f"snapshot directory does not exist: {root}")
    if not COMMIT.fullmatch(model_commit) or not COMMIT.fullmatch(processor_commit):
        raise SnapshotManifestError("model and processor commits must be 40 lowercase hex characters")
    architectures, model_type = _architecture(root)
    if expected_architecture not in architectures:
        raise SnapshotManifestError(
            f"architecture mismatch: expected {expected_architecture}, found {architectures}"
        )
    files = {
        path.relative_to(root).as_posix(): {"sha256": _hash(path), "size": path.stat().st_size}
        for path in snapshot_files(root)
    }
    return _manifest_from_files(
        files,
        model_id=model_id,
        model_commit=model_commit,
        processor_commit=processor_commit,
        expected_architecture=expected_architecture,
        architectures=architectures,
        model_type=model_type,
        processor_id=processor_id,
    )


def create_manifest_from_records(
    files: Mapping[str, Mapping[str, Any]],
    *,
    config_payload: bytes,
    model_id: str,
    model_commit: str,
    processor_commit: str,
    expected_architecture: str,
    processor_id: str | None = None,
) -> dict[str, Any]:
    """Build a v2 snapshot manifest from already-hashed file records."""
    if not COMMIT.fullmatch(model_commit) or not COMMIT.fullmatch(processor_commit):
        raise SnapshotManifestError("model and processor commits must be 40 lowercase hex characters")
    try:
        config = json.loads(config_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SnapshotManifestError("snapshot config.json is invalid") from exc
    architectures = config.get("architectures", [])
    if not isinstance(architectures, list) or not architectures:
        raise SnapshotManifestError("config.json does not declare architectures")
    model_type = str(config.get("model_type", ""))
    if not model_type:
        raise SnapshotManifestError("config.json does not declare model_type")
    architectures = [str(value) for value in architectures]
    if expected_architecture not in architectures:
        raise SnapshotManifestError(
            f"architecture mismatch: expected {expected_architecture}, found {architectures}"
        )
    normalized = {
        name: {"sha256": str(record["sha256"]), "size": int(record["size"])}
        for name, record in sorted(files.items())
    }
    return _manifest_from_files(
        normalized,
        model_id=model_id,
        model_commit=model_commit,
        processor_commit=processor_commit,
        expected_architecture=expected_architecture,
        architectures=architectures,
        model_type=model_type,
        processor_id=processor_id,
    )


def _manifest_from_files(
    files: dict[str, dict[str, Any]],
    *,
    model_id: str,
    model_commit: str,
    processor_commit: str,
    expected_architecture: str,
    architectures: list[str],
    model_type: str,
    processor_id: str | None = None,
) -> dict[str, Any]:
    processor_files = sorted(path for path in files if Path(path).name in PROCESSOR_FILES)
    if not processor_files:
        raise SnapshotManifestError("snapshot has no tokenizer or processor contract files")
    weight_files = sorted(
        path for path in files
        if path.endswith((".safetensors", ".bin", ".pt", ".pth"))
    )
    if not weight_files:
        raise SnapshotManifestError("snapshot has no local model weights")
    return {
        "schema": "certvic.cvpr.model_snapshot_manifest.v2",
        "snapshot_contract": "UNIFIED_SNAPSHOT",
        "model_id": model_id,
        "processor_id": processor_id or model_id,
        "model_commit": model_commit,
        "processor_commit": processor_commit,
        "expected_architecture": expected_architecture,
        "architectures": architectures,
        "model_type": model_type,
        "offline_required": True,
        "processor_files": processor_files,
        "weight_files": weight_files,
        "files": files,
        "unified_snapshot_root_sha256": hashlib.sha256(
            (json.dumps(files, sort_keys=True, separators=(",", ":")) + "\n").encode()
        ).hexdigest(),
        "model_and_processor_share_verified_root": True,
        "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
    }


def write_manifest(snapshot: str | Path, manifest: dict[str, Any]) -> Path:
    path = Path(snapshot) / MANIFEST_NAME
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def verify_manifest(
    snapshot: str | Path,
    manifest: str | Path | dict[str, Any] | None = None,
    *,
    expected_model_id: str | None = None,
    expected_model_commit: str | None = None,
    expected_processor_commit: str | None = None,
    expected_architecture: str | None = None,
    reject_extra_files: bool = True,
) -> dict[str, Any]:
    root = Path(snapshot).resolve()
    if isinstance(manifest, dict):
        value = manifest
    else:
        path = Path(manifest) if manifest else root / MANIFEST_NAME
        if not path.is_file():
            return {"passed": False, "errors": ["snapshot manifest is missing"]}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"passed": False, "errors": ["snapshot manifest is invalid JSON"]}
    errors: list[str] = []
    expected = {
        "model_id": expected_model_id,
        "model_commit": expected_model_commit,
        "processor_commit": expected_processor_commit,
        "expected_architecture": expected_architecture,
    }
    for field, required in expected.items():
        if required is not None and value.get(field) != required:
            errors.append(f"{field} mismatch")
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        errors.append("manifest files mapping is missing")
        files = {}
    observed = {path.relative_to(root).as_posix(): path for path in snapshot_files(root)}
    missing = sorted(set(files) - set(observed))
    extra = sorted(set(observed) - set(files)) if reject_extra_files else []
    if missing:
        errors.append(f"missing snapshot files: {missing[:10]}")
    if extra:
        errors.append(f"unmanifested snapshot files: {extra[:10]}")
    for relative in sorted(set(files) & set(observed)):
        record = files[relative]
        if not isinstance(record, dict):
            errors.append(f"invalid manifest record: {relative}")
            continue
        if record.get("size") != observed[relative].stat().st_size:
            errors.append(f"size mismatch: {relative}")
        if record.get("sha256") != _hash(observed[relative]):
            errors.append(f"hash mismatch: {relative}")
    try:
        architectures, model_type = _architecture(root)
        if value.get("architectures") != architectures or value.get("model_type") != model_type:
            errors.append("live config architecture differs from manifest")
        declared = expected_architecture or value.get("expected_architecture")
        if declared not in architectures:
            errors.append("expected architecture is not declared by live config")
    except SnapshotManifestError as exc:
        errors.append(str(exc))
    processor_files = value.get("processor_files", [])
    if not processor_files or any(path not in observed for path in processor_files):
        errors.append("processor/tokenizer manifest is incomplete")
    if value.get("offline_required") is not True:
        errors.append("manifest must require offline execution")
    if value.get("snapshot_contract") != "UNIFIED_SNAPSHOT":
        errors.append("snapshot manifest must explicitly declare UNIFIED_SNAPSHOT")
    calculated_root_hash = hashlib.sha256(
        (json.dumps(files, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    if value.get("unified_snapshot_root_sha256") != calculated_root_hash:
        errors.append("unified snapshot root hash mismatch")
    if value.get("model_and_processor_share_verified_root") is not True:
        errors.append("unified snapshot must bind model and processor to the same verified root")
    return {
        "passed": not errors,
        "errors": errors,
        "files_verified": len(set(files) & set(observed)),
        "manifest_sha256": hashlib.sha256(
            (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        ).hexdigest(),
        "offline": True,
        "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED" if not errors
                           else "LOCAL_SNAPSHOT_VERIFICATION_FAILED",
    }


def classify_snapshot_provenance(
    *, local_bytes_verified: bool, remote_commit_authenticated: bool, commit_declared: bool,
) -> str:
    """Keep byte verification, authenticated commits, and declarations distinct."""
    if local_bytes_verified:
        return "LOCAL_SNAPSHOT_BYTES_VERIFIED"
    if remote_commit_authenticated:
        return "REMOTE_COMMIT_AUTHENTICATED"
    if commit_declared:
        return "REMOTE_COMMIT_DECLARED"
    return "SNAPSHOT_PROVENANCE_UNRESOLVED"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or verify an offline model snapshot manifest")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--snapshot", required=True)
    create.add_argument("--model-id", required=True)
    create.add_argument("--model-commit", required=True)
    create.add_argument("--processor-commit", required=True)
    create.add_argument("--architecture", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--snapshot", required=True)
    verify.add_argument("--manifest")
    verify.add_argument("--model-id")
    verify.add_argument("--model-commit")
    verify.add_argument("--processor-commit")
    verify.add_argument("--architecture")
    args = parser.parse_args(argv)
    if args.command == "create":
        value = create_manifest(
            args.snapshot,
            model_id=args.model_id,
            model_commit=args.model_commit,
            processor_commit=args.processor_commit,
            expected_architecture=args.architecture,
        )
        path = write_manifest(args.snapshot, value)
        result = {"status": "CREATED", "manifest": str(path), "files": len(value["files"])}
        code = 0
    else:
        result = verify_manifest(
            args.snapshot,
            args.manifest,
            expected_model_id=args.model_id,
            expected_model_commit=args.model_commit,
            expected_processor_commit=args.processor_commit,
            expected_architecture=args.architecture,
        )
        code = 0 if result["passed"] else 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
