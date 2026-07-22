"""Hash-bound verification of the entire scientific execution lineage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from certvic.cvpr.artifact_registry import load_registry, verify_registry
from certvic.cvpr.ceiling_common import atomic_json, canonical_json_bytes, repository_root, utc_now
from certvic.cvpr.contracts import sha256_bytes


CAPSULE_SCHEMA = "certvic.cvpr.reproducibility_capsule.v1"
REQUIRED_ROLES = (
    "code",
    "task_bundle",
    "task_freeze",
    "human_review",
    "detectability",
    "environment",
    "runtime_profile",
    "model_snapshots",
    "model_registry",
    "prompt",
    "parser",
    "run_contract",
    "execution_permission",
    "provider_nonce",
    "provider_return",
    "import_transaction",
    "analysis_plan",
)


class CapsuleError(ValueError):
    """The capsule cannot be built or verified without exact lineage."""


def create_capsule(
    registry_path: str | Path,
    out: str | Path,
    *,
    study: str,
    bindings: dict[str, str] | None = None,
) -> dict[str, Any]:
    registry = load_registry(registry_path)
    by_id = {str(row["artifact_id"]): row for row in registry["artifacts"]}
    selected = dict(bindings or {})
    for role in REQUIRED_ROLES:
        if role not in selected:
            candidates = [row for row in registry["artifacts"] if row.get("role") == role]
            if candidates:
                latest = max(candidates, key=lambda row: str(row.get("created_at_utc", "")))
                selected[role] = str(latest["artifact_id"])
    unknown = sorted(set(selected.values()) - set(by_id))
    if unknown:
        raise CapsuleError(f"capsule bindings reference unknown artifacts: {unknown}")
    missing = sorted(set(REQUIRED_ROLES) - set(selected))
    artifact_bindings = {
        role: {
            "artifact_id": artifact_id,
            "sha256": by_id[artifact_id]["sha256"],
            "location": by_id[artifact_id]["immutable_location"],
        }
        for role, artifact_id in sorted(selected.items())
    }
    payload: dict[str, Any] = {
        "schema": CAPSULE_SCHEMA,
        "study": study,
        "status": "COMPLETE" if not missing else "INCOMPLETE_EXTERNAL_BINDINGS",
        "created_at_utc": utc_now(),
        "required_roles": list(REQUIRED_ROLES),
        "missing_roles": missing,
        "artifact_bindings": artifact_bindings,
        "paper_evidence": False,
    }
    payload["capsule_hash"] = sha256_bytes(canonical_json_bytes(payload))
    atomic_json(out, payload)
    return payload


def verify_capsule(
    capsule_path: str | Path,
    registry_path: str | Path,
    *,
    root: str | Path,
) -> dict[str, Any]:
    capsule = json.loads(Path(capsule_path).read_text(encoding="utf-8"))
    errors: list[str] = []
    if capsule.get("schema") != CAPSULE_SCHEMA:
        errors.append("capsule schema mismatch")
    supplied_hash = capsule.get("capsule_hash")
    expected_hash = sha256_bytes(canonical_json_bytes({
        key: value for key, value in capsule.items() if key != "capsule_hash"
    }))
    if supplied_hash != expected_hash:
        errors.append("capsule hash mismatch")
    registry_verification = verify_registry(registry_path, root=root)
    if not registry_verification["passed"]:
        errors.append("artifact registry verification failed")
    registry = load_registry(registry_path)
    by_id = {str(row["artifact_id"]): row for row in registry["artifacts"]}
    for role, binding in capsule.get("artifact_bindings", {}).items():
        row = by_id.get(str(binding.get("artifact_id")))
        if row is None:
            errors.append(f"{role}: bound artifact is absent from registry")
        elif row.get("sha256") != binding.get("sha256") or row.get(
            "immutable_location"
        ) != binding.get("location"):
            errors.append(f"{role}: binding differs from registry")
    missing = sorted(set(REQUIRED_ROLES) - set(capsule.get("artifact_bindings", {})))
    if missing:
        errors.append(f"missing required roles: {missing}")
    return {
        "schema": "certvic.cvpr.reproducibility_capsule_verification.v1",
        "passed": not errors,
        "errors": errors,
        "missing_roles": missing,
        "registry": registry_verification,
        "paper_evidence": False,
    }


def _bindings(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise CapsuleError("--bind values must use role=artifact_id")
        role, artifact_id = value.split("=", 1)
        if not role or not artifact_id or role in result:
            raise CapsuleError(f"invalid or duplicate capsule binding: {value}")
        result[role] = artifact_id
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or verify a CertVIC lineage capsule")
    parser.add_argument("--root")
    parser.add_argument(
        "--registry", default="reports/max_ceiling_upgrade/artifact_registry.json"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--study", required=True)
    create.add_argument("--out", required=True)
    create.add_argument("--bind", action="append", default=[])
    verify = subparsers.add_parser("verify")
    verify.add_argument("capsule")
    args = parser.parse_args(argv)
    base = repository_root(args.root)
    registry = Path(args.registry)
    if not registry.is_absolute():
        registry = base / registry
    if args.action == "create":
        destination = Path(args.out)
        if not destination.is_absolute():
            destination = base / destination
        result = create_capsule(
            registry, destination, study=args.study, bindings=_bindings(args.bind)
        )
        passed = result["status"] == "COMPLETE"
    else:
        capsule = Path(args.capsule)
        if not capsule.is_absolute():
            capsule = base / capsule
        result = verify_capsule(capsule, registry, root=base)
        passed = result["passed"]
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
