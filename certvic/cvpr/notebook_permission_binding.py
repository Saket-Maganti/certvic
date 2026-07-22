"""Derive permission inputs from the variables a notebook will actually execute."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes


BINDING_SCHEMA = "certvic.cvpr.notebook_permission_binding.v1"
PATH_VARIABLES = {
    "TASK_BUNDLE_MANIFEST": "task_bundle_manifest",
    "FINAL_TASK_FREEZE": "freeze_manifest",
    "FINAL_REVIEW_LEDGER": "final_review",
    "SMOKE_GATE_JSON": "smoke_gate",
    "ENVIRONMENT_LOCK": "environment_lock",
    "MODEL_REGISTRY": "model_registry",
    "SNAPSHOT_MANIFEST": "snapshot_manifest",
    "CODE_BUNDLE": "code_bundle",
    "STUDY_CONFIG": "study_config",
    "MATRIX_AUTHORIZATION": "matrix_authorization",
}
SCALAR_VARIABLES = {
    "SCHEMA_VERSION": "schema_version",
    "PROVIDER": "provider",
    "RUN_TAG": "run_tag",
    "PROMPT_TEMPLATE_HASH": "prompt_template_hash",
    "RUNTIME_PROFILE_ID": "runtime_profile_id",
    "RUNTIME_PROFILE_HASH": "runtime_profile_hash",
    "WHEELHOUSE_CONTENT_IDENTITY_SHA256": "wheelhouse_content_identity_sha256",
}


class NotebookPermissionBindingError(ValueError):
    """Active notebook variables are incomplete or drifted after authorization."""


def _active_value(variables: Mapping[str, Any], name: str) -> Any:
    if name == "CODE_BUNDLE" and name not in variables:
        return variables.get("CODE_BUNDLE_PATH")
    if name == "SMOKE_GATE_JSON" and name not in variables:
        return variables.get("EXECUTION_SMOKE_GATE_JSON", variables.get("REAL_MODEL_SMOKE_GATE"))
    return variables.get(name)


def _placeholder(value: Any) -> bool:
    return value is None or not str(value).strip() or str(value).startswith("REQUIRED_USER_FILL")


def derive_permission_binding(
    variables: Mapping[str, Any], *, require_files: bool = True
) -> dict[str, Any]:
    """Construct the sole permission role matrix from the active notebook namespace."""
    enforce_final_binding = "MATRIX_AUTHORIZATION" in variables or "PROMPT_TEMPLATE" in variables
    if enforce_final_binding:
        prompt_template = variables.get("PROMPT_TEMPLATE")
        if _placeholder(prompt_template):
            raise NotebookPermissionBindingError("active notebook variable PROMPT_TEMPLATE is unset")
        derived_prompt_hash = hashlib.sha256(str(prompt_template).encode("utf-8")).hexdigest()
        supplied_prompt_hash = variables.get("PROMPT_TEMPLATE_HASH")
        if supplied_prompt_hash != derived_prompt_hash:
            raise NotebookPermissionBindingError(
                "PROMPT_TEMPLATE_HASH does not match the exact active prompt template"
            )
    paths: dict[str, str] = {}
    hashes: dict[str, str] = {}
    source_variables: dict[str, str] = {}
    authenticated_identities = variables.get("AUTHENTICATED_CONTENT_IDENTITIES", {})
    if not isinstance(authenticated_identities, Mapping):
        raise NotebookPermissionBindingError("authenticated content identities must be a mapping")
    for variable, role in PATH_VARIABLES.items():
        if variable == "MATRIX_AUTHORIZATION" and not enforce_final_binding:
            continue
        value = _active_value(variables, variable)
        if _placeholder(value):
            raise NotebookPermissionBindingError(f"active notebook variable {variable} is unset")
        path = Path(str(value))
        if require_files and not path.is_file():
            raise NotebookPermissionBindingError(f"active notebook file does not exist: {variable}")
        paths[role] = str(value)
        source_variables[role] = variable
        if path.is_file():
            override = authenticated_identities.get(role)
            if override is not None:
                value = str(override)
                if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                    raise NotebookPermissionBindingError(
                        f"authenticated content identity is invalid: {role}"
                    )
                hashes[role] = value
            else:
                hashes[role] = hashlib.sha256(path.read_bytes()).hexdigest()
    scalars: dict[str, str] = {}
    profile_binding_active = any(
        not _placeholder(variables.get(name))
        for name in ("RUNTIME_PROFILE_ID", "RUNTIME_PROFILE_HASH")
    )
    for variable, role in SCALAR_VARIABLES.items():
        if variable == "PROMPT_TEMPLATE_HASH" and not enforce_final_binding:
            continue
        if variable.startswith("RUNTIME_PROFILE_") and not profile_binding_active:
            continue
        if variable == "WHEELHOUSE_CONTENT_IDENTITY_SHA256" and not profile_binding_active:
            continue
        value = _active_value(variables, variable)
        if _placeholder(value):
            raise NotebookPermissionBindingError(f"active notebook variable {variable} is unset")
        scalars[role] = str(value)
        source_variables[role] = variable
    task_bundle_root = variables.get("TASK_BUNDLE_ROOT")
    if not _placeholder(task_bundle_root):
        scalars["task_bundle_root"] = str(task_bundle_root)
        source_variables["task_bundle_root"] = "TASK_BUNDLE_ROOT"
    payload = {
        "schema": BINDING_SCHEMA,
        "input_paths": dict(sorted(paths.items())),
        "input_hashes": dict(sorted(hashes.items())),
        "scalars": dict(sorted(scalars.items())),
        "source_variables": dict(sorted(source_variables.items())),
        "derived_from_active_variables": True,
        "paper_evidence": False,
    }
    payload["binding_hash"] = sha256_bytes(canonical_json_bytes(payload))
    return payload


def assert_runtime_binding(
    binding: Mapping[str, Any], runtime: Mapping[str, Any]
) -> dict[str, Any]:
    """Prove that worker values equal the variables verified before model loading."""
    if binding.get("schema") != BINDING_SCHEMA or binding.get(
        "derived_from_active_variables"
    ) is not True:
        raise NotebookPermissionBindingError("permission binding schema/provenance mismatch")
    observed_hash = binding.get("binding_hash")
    expected_hash = sha256_bytes(
        canonical_json_bytes({key: value for key, value in binding.items() if key != "binding_hash"})
    )
    if observed_hash != expected_hash:
        raise NotebookPermissionBindingError("permission binding hash mismatch")
    expected_runtime = {
        **dict(binding.get("input_paths", {})),
        **dict(binding.get("scalars", {})),
    }
    runtime_aliases = {
        "freeze_manifest": "final_task_freeze",
        "final_review": "final_review_ledger",
        "smoke_gate": "smoke_gate_json",
        "code_bundle": "code_bundle",
        "schema_version": "output_schema",
        "matrix_authorization": "matrix_authorization",
        "runtime_profile_id": "runtime_profile_id",
        "runtime_profile_hash": "runtime_profile_hash",
    }
    mismatches: dict[str, dict[str, Any]] = {}
    for role, expected in expected_runtime.items():
        runtime_field = runtime_aliases.get(role, role)
        observed = runtime.get(runtime_field)
        if observed != expected:
            mismatches[role] = {"expected": expected, "observed": observed}
    if mismatches:
        raise NotebookPermissionBindingError(
            f"worker runtime differs from active permission variables: {mismatches}"
        )
    return {
        "status": "ACTIVE_RUNTIME_BINDING_VERIFIED",
        "binding_hash": observed_hash,
        "roles": sorted(expected_runtime),
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive a notebook permission binding")
    parser.add_argument("--variables-json", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        variables = json.loads(Path(args.variables_json).read_text(encoding="utf-8"))
        result = derive_permission_binding(variables)
        destination = Path(args.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "NOTEBOOK_PERMISSION_BINDING_BLOCKED", "reason": str(exc)}))
        return 2
    print(json.dumps({"status": "ACTIVE_PERMISSION_BINDING_DERIVED", "out": args.out}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
