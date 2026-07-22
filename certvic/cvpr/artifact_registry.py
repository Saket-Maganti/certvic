"""Content-addressed registry for canonical CertVIC execution artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from certvic.cvpr.ceiling_common import (
    atomic_json,
    canonical_json_bytes,
    relative_to_root,
    repository_root,
    sha256_file,
    utc_now,
)
from certvic.cvpr.contracts import EvidenceClass, sha256_bytes


REGISTRY_SCHEMA = "certvic.cvpr.artifact_registry.v1"
CODE_SNAPSHOT_ROOTS = (
    "certvic", "configs", "notebooks/kaggle/cvpr", "notebooks/kaggle/provisioning",
    "scripts", "tests",
)


class ArtifactRegistryError(ValueError):
    """A registry mutation or verification failed closed."""


def load_registry(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        return {"schema": REGISTRY_SCHEMA, "paper_evidence": False, "artifacts": []}
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != REGISTRY_SCHEMA or not isinstance(
        value.get("artifacts"), list
    ):
        raise ArtifactRegistryError("artifact registry schema mismatch")
    return value


def add_artifact(
    registry_path: str | Path,
    location: str | Path,
    *,
    root: str | Path,
    role: str,
    schema: str,
    study: str,
    evidence_class: str,
    parents: list[str] | None = None,
    aliases: list[str] | None = None,
) -> dict[str, Any]:
    base = Path(root).resolve()
    source = Path(location)
    if not source.is_absolute():
        source = base / source
    if not source.is_file():
        raise ArtifactRegistryError(f"artifact does not exist: {source}")
    try:
        EvidenceClass(evidence_class)
    except ValueError as error:
        raise ArtifactRegistryError(f"invalid evidence class: {evidence_class}") from error
    registry = load_registry(registry_path)
    parent_ids = sorted(set(parents or []))
    known = {str(row["artifact_id"]) for row in registry["artifacts"]}
    unknown = set(parent_ids) - known
    if unknown:
        raise ArtifactRegistryError(f"unknown parent artifact IDs: {sorted(unknown)}")
    relative = relative_to_root(source, base)
    digest = sha256_file(source)
    artifact_id = sha256_bytes(canonical_json_bytes({
        "role": role, "sha256": digest, "study": study, "schema": schema
    }))[:24]
    existing = next(
        (row for row in registry["artifacts"] if row["artifact_id"] == artifact_id), None
    )
    if existing:
        if existing["sha256"] != digest or existing["immutable_location"] != relative:
            raise ArtifactRegistryError("artifact ID collision or immutable-location conflict")
        return existing
    row = {
        "artifact_id": artifact_id,
        "role": role,
        "sha256": digest,
        "size": source.stat().st_size,
        "schema": schema,
        "study": study,
        "parent_artifacts": parent_ids,
        "evidence_class": evidence_class,
        "immutable_location": relative,
        "aliases": sorted(set(aliases or [])),
        "created_at_utc": utc_now(),
    }
    registry["artifacts"].append(row)
    registry["artifacts"].sort(key=lambda item: item["artifact_id"])
    registry["registry_hash"] = sha256_bytes(canonical_json_bytes(registry["artifacts"]))
    atomic_json(registry_path, registry)
    return row


def verify_registry(registry_path: str | Path, *, root: str | Path) -> dict[str, Any]:
    base = Path(root).resolve()
    registry = load_registry(registry_path)
    errors: list[dict[str, str]] = []
    known = {str(row.get("artifact_id")) for row in registry["artifacts"]}
    # Registry rows are append-only history, while a few repository paths are
    # deliberately refreshed in place.  Only the newest row for a location is
    # the active byte binding; older rows remain available for lineage.
    newest_by_location: dict[str, dict[str, Any]] = {}
    for row in registry["artifacts"]:
        location = str(row.get("immutable_location", ""))
        current = newest_by_location.get(location)
        if current is None or str(row.get("created_at_utc", "")) > str(
            current.get("created_at_utc", "")
        ):
            newest_by_location[location] = row
    for row in registry["artifacts"]:
        active = newest_by_location.get(str(row.get("immutable_location", ""))) is row
        source = (base / str(row.get("immutable_location", ""))).resolve()
        try:
            source.relative_to(base)
        except ValueError:
            errors.append({"artifact_id": row["artifact_id"], "error": "path escapes root"})
            continue
        if active and not source.is_file():
            errors.append({"artifact_id": row["artifact_id"], "error": "file missing"})
        elif active and (
            sha256_file(source) != row.get("sha256") or source.stat().st_size != row.get("size")
        ):
            errors.append({"artifact_id": row["artifact_id"], "error": "hash or size mismatch"})
        unknown = set(row.get("parent_artifacts", [])) - known
        if unknown:
            errors.append({
                "artifact_id": row["artifact_id"],
                "error": f"unknown parents: {sorted(unknown)}",
            })
    expected_hash = sha256_bytes(canonical_json_bytes(registry["artifacts"]))
    if registry["artifacts"] and registry.get("registry_hash") != expected_hash:
        errors.append({"artifact_id": "REGISTRY", "error": "registry hash mismatch"})
    return {
        "schema": "certvic.cvpr.artifact_registry_verification.v1",
        "passed": not errors,
        "artifact_count": len(registry["artifacts"]),
        "errors": errors,
        "paper_evidence": False,
    }


def lineage(registry_path: str | Path, artifact_id: str) -> dict[str, Any]:
    registry = load_registry(registry_path)
    by_id = {str(row["artifact_id"]): row for row in registry["artifacts"]}
    if artifact_id not in by_id:
        raise ArtifactRegistryError(f"unknown artifact ID: {artifact_id}")
    ordered: list[dict[str, Any]] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(current: str) -> None:
        if current in visiting:
            raise ArtifactRegistryError("artifact lineage contains a cycle")
        if current in visited:
            return
        visiting.add(current)
        for parent in by_id[current].get("parent_artifacts", []):
            if parent not in by_id:
                raise ArtifactRegistryError(f"lineage parent is missing: {parent}")
            visit(parent)
        visiting.remove(current)
        visited.add(current)
        ordered.append(by_id[current])

    visit(artifact_id)
    return {"artifact_id": artifact_id, "lineage": ordered}


def snapshot_code(root: str | Path, out: str | Path) -> dict[str, Any]:
    base = Path(root).resolve()
    files: list[Path] = [
        base / name for name in ("pyproject.toml", "README.md", "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md")
        if (base / name).is_file()
    ]
    for relative in CODE_SNAPSHOT_ROOTS:
        tree = base / relative
        if tree.is_dir():
            files.extend(
                path for path in tree.rglob("*")
                if path.is_file() and not path.is_symlink()
                and not {"__pycache__", ".pytest_cache", ".ruff_cache"} & set(path.parts)
                and path.suffix.lower() in {".py", ".json", ".yaml", ".yml", ".toml", ".ipynb", ".md", ".sh"}
            )
    inventory = {
        path.relative_to(base).as_posix(): {"size": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(set(files), key=lambda value: value.relative_to(base).as_posix())
    }
    value = {
        "schema": "certvic.cvpr.code_snapshot.v1",
        "files": inventory,
        "tree_hash": sha256_bytes(canonical_json_bytes(inventory)),
        "paper_evidence": False,
    }
    atomic_json(out, value)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage the CertVIC artifact registry")
    parser.add_argument("--root")
    parser.add_argument(
        "--registry", default="reports/max_ceiling_upgrade/artifact_registry.json"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    add = subparsers.add_parser("add")
    add.add_argument("--location", required=True)
    add.add_argument("--role", required=True)
    add.add_argument("--schema", required=True)
    add.add_argument("--study", required=True)
    add.add_argument("--evidence-class", required=True)
    add.add_argument("--parent", action="append", default=[])
    add.add_argument("--alias", action="append", default=[])
    subparsers.add_parser("verify")
    lineage_parser = subparsers.add_parser("lineage")
    lineage_parser.add_argument("artifact_id")
    snapshot = subparsers.add_parser("snapshot-code")
    snapshot.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    base = repository_root(args.root)
    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = base / registry_path
    if args.action == "add":
        result = add_artifact(
            registry_path,
            args.location,
            root=base,
            role=args.role,
            schema=args.schema,
            study=args.study,
            evidence_class=args.evidence_class,
            parents=args.parent,
            aliases=args.alias,
        )
    elif args.action == "verify":
        result = verify_registry(registry_path, root=base)
    elif args.action == "lineage":
        result = lineage(registry_path, args.artifact_id)
    else:
        destination = Path(args.out)
        if not destination.is_absolute():
            destination = base / destination
        result = snapshot_code(base, destination)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("passed", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
