"""Canonical run-provenance contracts for CVPR execution and resume checks.

The hash intentionally covers every input that can change model outputs.  A legacy
compatibility mode exists only so historical synthetic tests can still be inspected;
scientific execution must use ``strict=True`` and cannot contain legacy sentinels.
"""

from __future__ import annotations

import re
from typing import Any

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.schema_contract import OUTPUT_SCHEMA


RUN_CONTRACT_SCHEMA = "certvic.cvpr.run_contract.v1"
SNAPSHOT_STATUS_CLASSES = {
    "LOCAL_SNAPSHOT_BYTES_VERIFIED",
    "REMOTE_COMMIT_AUTHENTICATED",
    "REMOTE_COMMIT_DECLARED",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
LEGACY_SENTINEL = "LEGACY_TEST_UNSPECIFIED"


def _hash(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def build_run_contract(
    config: dict[str, Any],
    *,
    task_manifest_sha256: str,
    strict: bool = True,
) -> dict[str, Any]:
    """Return a canonical run contract and its SHA-256.

    ``REMOTE_COMMIT_DECLARED`` is recorded truthfully but is never sufficient for a
    strict offline scientific run.  Only verified local bytes or an authenticated
    remote commit may enter strict execution.
    """

    snapshot_status = str(config.get("snapshot_status", LEGACY_SENTINEL))
    model_snapshot_hash = config.get("model_snapshot_manifest_hash", LEGACY_SENTINEL)
    processor_snapshot_hash = config.get("processor_snapshot_manifest_hash", LEGACY_SENTINEL)
    snapshot_contract = config.get("snapshot_contract")
    if snapshot_contract is None:
        snapshot_contract = (
            "UNIFIED_SNAPSHOT" if model_snapshot_hash == processor_snapshot_hash
            and model_snapshot_hash != LEGACY_SENTINEL else "SEPARATE_SNAPSHOTS"
        )
    fields: dict[str, Any] = {
        "schema": RUN_CONTRACT_SCHEMA,
        "study": config.get("study", LEGACY_SENTINEL),
        "run_tag": config.get("run_tag", LEGACY_SENTINEL),
        "runtime_class": config.get("runtime_class", LEGACY_SENTINEL),
        "provider": config.get("provider", LEGACY_SENTINEL),
        "model_id": config.get("model_id", LEGACY_SENTINEL),
        "model_commit": config.get("model_commit", LEGACY_SENTINEL),
        "processor_id": config.get("processor_id", config.get("model_id", LEGACY_SENTINEL)),
        "processor_commit": config.get("processor_commit", LEGACY_SENTINEL),
        "snapshot_status": snapshot_status,
        "snapshot_contract": snapshot_contract,
        "model_snapshot_manifest_hash": model_snapshot_hash,
        "processor_snapshot_manifest_hash": processor_snapshot_hash,
        "task_manifest_sha256": task_manifest_sha256,
        "code_bundle_hash": config.get("code_bundle_hash", LEGACY_SENTINEL),
        "environment_lock_hash": config.get("environment_lock_hash", LEGACY_SENTINEL),
        "prompt_template_id": config.get("prompt_template_id", LEGACY_SENTINEL),
        "prompt_template_hash": config.get("prompt_template_hash", LEGACY_SENTINEL),
        "parser_version": config.get("parser_version", "certvic.parse.v2"),
        "output_schema": config.get("output_schema", OUTPUT_SCHEMA),
        "generation_parameters": config.get("generation_parameters", {}),
        "seed": config.get("seed", LEGACY_SENTINEL),
        "sharding": config.get("sharding", {"algorithm": "balanced_cost_v1"}),
    }
    # Provider-local permissions bind this run_contract_hash. Including their own
    # permission ID here would create a cryptographic cycle. Historical shared-ledger
    # SCIENTIFIC_EXECUTION contracts retain their explicit permission identity.
    if fields["runtime_class"] == "SCIENTIFIC_EXECUTION" or (
        config.get("execution_permission_id") is not None
        and config.get("provider_permission_path") is None
    ):
        fields["execution_permission_id"] = config.get(
            "execution_permission_id", LEGACY_SENTINEL
        )
        fields["execution_permission_signature"] = config.get(
            "execution_permission_signature", LEGACY_SENTINEL
        )
    errors: list[str] = []
    if snapshot_status not in SNAPSHOT_STATUS_CLASSES and strict:
        errors.append(f"invalid snapshot_status: {snapshot_status}")
    if strict and snapshot_status not in {
        "LOCAL_SNAPSHOT_BYTES_VERIFIED",
        "REMOTE_COMMIT_AUTHENTICATED",
    }:
        errors.append("strict execution requires verified bytes or an authenticated commit")
    if snapshot_contract not in {"UNIFIED_SNAPSHOT", "SEPARATE_SNAPSHOTS"}:
        errors.append("snapshot_contract must be UNIFIED_SNAPSHOT or SEPARATE_SNAPSHOTS")
    if snapshot_contract == "UNIFIED_SNAPSHOT" and model_snapshot_hash != processor_snapshot_hash:
        errors.append("unified snapshot contract requires one shared manifest hash")
    if fields["output_schema"] != OUTPUT_SCHEMA:
        errors.append(f"output_schema must be exactly {OUTPUT_SCHEMA}")
    hash_fields = (
        "model_snapshot_manifest_hash",
        "processor_snapshot_manifest_hash",
        "task_manifest_sha256",
        "code_bundle_hash",
        "environment_lock_hash",
        "prompt_template_hash",
    )
    if "execution_permission_id" in fields:
        hash_fields += ("execution_permission_id", "execution_permission_signature")
    for name in hash_fields:
        if (strict or fields[name] != LEGACY_SENTINEL) and not HEX64.fullmatch(str(fields[name])):
            errors.append(f"{name} must be a SHA-256")
    for name, value in fields.items():
        if strict and value == LEGACY_SENTINEL:
            errors.append(f"{name} is unresolved")
    if errors:
        raise ValueError("invalid run contract: " + "; ".join(errors))
    contract_hash = _hash(fields)
    return {
        **fields,
        "contract_complete": not any(value == LEGACY_SENTINEL for value in fields.values()),
        "run_contract_hash": contract_hash,
    }


def validate_run_contract(contract: dict[str, Any], expected_hash: str | None = None) -> list[str]:
    errors: list[str] = []
    observed_hash = str(contract.get("run_contract_hash", ""))
    payload = {key: value for key, value in contract.items() if key not in {
        "run_contract_hash", "contract_complete"
    }}
    calculated = _hash(payload)
    if observed_hash != calculated:
        errors.append("run_contract_hash does not match canonical contract bytes")
    if expected_hash is not None and observed_hash != expected_hash:
        errors.append("run_contract_hash does not match expected execution contract")
    if contract.get("contract_complete") is not True:
        errors.append("run contract is not complete")
    return errors
