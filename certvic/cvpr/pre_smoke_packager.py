"""Bind 00A, three 00B returns, code, and smoke bytes into pre-smoke permissions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from certvic.cvpr.kaggle_bundle import build_bundle, verify_bundle
from certvic.cvpr.reconcile_provider_permissions import (
    verify_matrix_authorization,
    verify_provider_permission,
)


PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")
REQUIRED_ROLES = (
    "environment_identity", "code_bundle", "smoke_bundle",
    "snapshot_qwen2_5_vl_7b", "snapshot_internvl_8b", "snapshot_llava_onevision_7b",
)


class PreSmokePackagerError(ValueError):
    """The pre-smoke authorization dependency matrix is incomplete or inconsistent."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_pre_smoke_permissions(
    inputs: Mapping[str, str | Path],
    *,
    prompt_hash: str,
    parser_version: str,
    run_contract_hashes: Mapping[str, str],
    output: str | Path = "kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip",
) -> dict[str, Any]:
    missing_roles = sorted(set(REQUIRED_ROLES) - set(inputs))
    if missing_roles:
        raise PreSmokePackagerError(f"missing pre-smoke roles: {missing_roles}")
    if set(run_contract_hashes) != set(PROVIDERS):
        raise PreSmokePackagerError("run-contract hashes must cover exactly three providers")
    paths = {role: Path(value).resolve() for role, value in inputs.items()}
    absent = sorted(role for role, path in paths.items() if not path.is_file() or path.is_symlink())
    if absent:
        raise PreSmokePackagerError(f"pre-smoke artifacts absent: {absent}")
    for role in ("code_bundle", "smoke_bundle"):
        verification = verify_bundle(paths[role])
        if not verification["passed"]:
            raise PreSmokePackagerError(f"{role} is not a valid canonical bundle: {verification['errors']}")
    hashes = {role: _sha(path) for role, path in sorted(paths.items())}
    matrix = {
        "schema": "certvic.kaggle.pre_smoke_matrix_authorization.v1",
        "authorization_class": "REAL_MODEL_SMOKE_ONLY",
        "environment_identity_sha256": hashes["environment_identity"],
        "code_bundle_sha256": hashes["code_bundle"],
        "smoke_task_bundle_sha256": hashes["smoke_bundle"],
        "snapshot_sha256": {
            provider: hashes[f"snapshot_{provider}"] for provider in PROVIDERS
        },
        "prompt_template_sha256": prompt_hash,
        "parser_version": parser_version,
        "run_contract_sha256": dict(run_contract_hashes),
        "providers": list(PROVIDERS),
        "execution_allowed": True,
        "scientific_execution_allowed": False,
        "paper_evidence": False,
    }
    matrix_bytes = (json.dumps(matrix, indent=2, sort_keys=True) + "\n").encode()
    matrix["authorization_sha256"] = hashlib.sha256(matrix_bytes).hexdigest()
    files: dict[str, Path | bytes] = {
        "authorization/pre_smoke_matrix_authorization.json": (
            json.dumps(matrix, indent=2, sort_keys=True) + "\n"
        ).encode()
    }
    for provider in PROVIDERS:
        child = {
            "schema": "certvic.kaggle.pre_smoke_child_permission.v1",
            "parent_authorization_sha256": matrix["authorization_sha256"],
            "provider": provider,
            "snapshot_sha256": matrix["snapshot_sha256"][provider],
            "run_contract_sha256": run_contract_hashes[provider],
            "prompt_template_sha256": prompt_hash,
            "parser_version": parser_version,
            "execution_class": "REAL_MODEL_SMOKE_ONLY",
            "paper_evidence": False,
        }
        files[f"authorization/{provider}_permission.json"] = (
            json.dumps(child, indent=2, sort_keys=True) + "\n"
        ).encode()
    files["authorization/input_hashes.json"] = (
        json.dumps(hashes, indent=2, sort_keys=True) + "\n"
    ).encode()
    return build_bundle(
        output,
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
        builder_command="python3 -m certvic.cvpr.pre_smoke_packager --config <INPUTS_JSON>",
        readme=(
            "# CertVIC pre-smoke permissions\n\nThese permissions authorize only the two-item real-model "
            "smoke. They never authorize confirmatory, Main, COCO, or paper evidence execution."
        ),
    )


def package_verified_permissions(
    *,
    matrix_authorization: str | Path,
    provider_permissions: Mapping[str, str | Path],
    active_inputs: Mapping[str, str | Path],
    provider_active_inputs: Mapping[str, Mapping[str, str | Path]],
    output: str | Path = "kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip",
) -> dict[str, Any]:
    """Package current signed permissions and their otherwise-unattached input artifacts."""
    matrix_path = Path(matrix_authorization).resolve()
    matrix = verify_matrix_authorization(matrix_path)
    if set(provider_permissions) != set(PROVIDERS):
        raise PreSmokePackagerError("verified permission package must cover exactly three providers")
    files: dict[str, Path] = {"authorization/matrix_authorization.json": matrix_path}
    unique_inputs: dict[str, Path] = {}
    for provider in PROVIDERS:
        permission_path = Path(provider_permissions[provider]).resolve()
        permission = verify_provider_permission(
            permission_path, matrix=matrix, expected_provider=provider
        )
        if permission.get("runtime_class") != "REAL_MODEL_SMOKE":
            raise PreSmokePackagerError(f"{provider}: permission is not REAL_MODEL_SMOKE")
        files[f"authorization/{provider}_permission.json"] = permission_path
        supplied = {
            **{role: Path(path).resolve() for role, path in active_inputs.items()},
            **{
                role: Path(path).resolve()
                for role, path in provider_active_inputs.get(provider, {}).items()
            },
        }
        if set(supplied) != set(permission["active_input_hashes"]):
            raise PreSmokePackagerError(f"{provider}: active input role matrix is incomplete")
        for role, expected_hash in permission["active_input_hashes"].items():
            path = supplied[role]
            if not path.is_file() or path.is_symlink() or _sha(path) != expected_hash:
                raise PreSmokePackagerError(f"{provider}: active input hash mismatch for {role}")
            unique_inputs.setdefault(expected_hash, path)
    for digest, path in sorted(unique_inputs.items()):
        files[f"active_inputs/{digest}/{path.name}"] = path
    return build_bundle(
        output,
        files,
        bundle_type="PRE_SMOKE_PERMISSIONS",
        study=str(matrix["study"]),
        stage="authorization",
        provider=None,
        required_notebook="ALL_3_PROVIDER_SPECIFIC_00C2_NOTEBOOKS",
        dataset_slug="certvic/certvic-pre-smoke-permissions",
        mount_path="/kaggle/input/certvic-pre-smoke-permissions",
        external_dependency_status="UPSTREAM_NON_EVIDENCE_ARTIFACTS_VERIFIED",
        evidence_class="REAL_MODEL_SMOKE_AUTHORIZATION_ONLY",
        builder_command="python3 -m certvic.cvpr.pre_smoke_packager --config <INPUTS_JSON>",
        readme=(
            "# CertVIC pre-smoke permissions\n\nCurrent signed REAL_MODEL_SMOKE parent and "
            "provider permissions plus deduplicated byte-bound input artifacts."
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--output", default="kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    if args.status or not args.config:
        result = {
            "status": "BLOCKED_BY_UPSTREAM_GATE",
            "required_roles": list(REQUIRED_ROLES),
            "builder_command": "python3 -m certvic.cvpr.pre_smoke_packager --config <INPUTS_JSON>",
            "output": args.output,
            "expected_size": "under 1 MB",
            "paper_evidence": False,
        }
    else:
        config = json.loads(Path(args.config).read_text())
        if "matrix_authorization" in config:
            result = package_verified_permissions(
                matrix_authorization=config["matrix_authorization"],
                provider_permissions=config["provider_permissions"],
                active_inputs=config.get("active_inputs", {}),
                provider_active_inputs=config.get("provider_active_inputs", {}),
                output=args.output,
            )
        else:
            result = build_pre_smoke_permissions(
                config["inputs"],
                prompt_hash=config["prompt_hash"],
                parser_version=config["parser_version"],
                run_contract_hashes=config["run_contract_hashes"],
                output=args.output,
            )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
