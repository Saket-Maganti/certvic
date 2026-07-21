"""Machine-readable CVPR protocol, evidence, model, and output contracts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class EvidenceClass(str, Enum):
    REAL_OBSERVED_EVIDENCE = "REAL_OBSERVED_EVIDENCE"
    DERIVED_FROM_REAL_EVIDENCE = "DERIVED_FROM_REAL_EVIDENCE"
    DIAGNOSTIC_ONLY = "DIAGNOSTIC_ONLY"
    RETROSPECTIVE_SENSITIVITY_ONLY = "RETROSPECTIVE_SENSITIVITY_ONLY"
    MACHINE_ASSISTED_PRELIMINARY = "MACHINE_ASSISTED_PRELIMINARY"
    HUMAN_REVIEW_PENDING = "HUMAN_REVIEW_PENDING"
    PLANNED_NOT_EXECUTED = "PLANNED_NOT_EXECUTED"
    SYNTHETIC_TEST_FIXTURE = "SYNTHETIC_TEST_FIXTURE"
    DEPRECATED_OR_STALE = "DEPRECATED_OR_STALE"


FREEZE_MARKERS = {
    "REQUIRED_USER_FILL",
    "REQUIRED_USER_OR_RESEARCHER_FREEZE_BEFORE_BUILD",
}
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_yaml(path: str | Path) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return value


def unresolved_freeze_fields(value: Any, prefix: str = "") -> list[str]:
    unresolved: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            unresolved.extend(unresolved_freeze_fields(child, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            unresolved.extend(unresolved_freeze_fields(child, f"{prefix}[{index}]"))
    elif isinstance(value, str) and value in FREEZE_MARKERS:
        unresolved.append(prefix)
    return unresolved


def validate_study_config(config: dict[str, Any], *, require_frozen: bool) -> dict[str, Any]:
    errors: list[str] = []
    required = {"schema", "study_id", "status", "paper_evidence", "execution_allowed"}
    missing = sorted(required - set(config))
    if missing:
        errors.append(f"missing fields: {missing}")
    if config.get("paper_evidence") is not False:
        errors.append("paper_evidence must remain false before validated returned evidence")
    unresolved = unresolved_freeze_fields(config)
    if require_frozen and unresolved:
        errors.append(f"unresolved freeze fields: {unresolved}")
    if config.get("execution_allowed") is True and unresolved:
        errors.append("execution cannot be allowed while freeze fields remain unresolved")
    return {"passed": not errors, "errors": errors, "unresolved_fields": unresolved}


def validate_model_registry(registry: dict[str, Any], *, for_execution: bool) -> dict[str, Any]:
    errors: list[str] = []
    models = registry.get("models")
    if not isinstance(models, dict) or not models:
        return {"passed": False, "errors": ["models must be a non-empty mapping"]}
    for provider, model in sorted(models.items()):
        if not isinstance(model, dict):
            errors.append(f"{provider}: model contract must be a mapping")
            continue
        for key in (
            "model_id",
            "model_commit",
            "processor_id",
            "processor_commit",
            "expected_architecture",
            "snapshot_manifest_sha256",
            "snapshot_verification",
            "preprocessing",
            "prompt_template",
            "dtype",
            "quantization",
            "attention_implementation",
            "device_map",
            "batch_strategy",
            "generation_parameters",
            "tokenizer_settings",
            "parser_mode",
            "retry_policy",
        ):
            if key not in model:
                errors.append(f"{provider}: missing {key}")
        for key in ("model_commit", "processor_commit"):
            revision = model.get(key)
            if for_execution and not (isinstance(revision, str) and COMMIT_RE.fullmatch(revision)):
                errors.append(f"{provider}: {key} must be a 40-character immutable commit")
        snapshot_hash = model.get("snapshot_manifest_sha256")
        if for_execution and not (
            isinstance(snapshot_hash, str) and re.fullmatch(r"[0-9a-f]{64}", snapshot_hash)
        ):
            errors.append(f"{provider}: snapshot_manifest_sha256 must be a verified SHA-256")
    return {"passed": not errors, "errors": errors, "for_execution": for_execution}


def validate_evidence_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        evidence_class = EvidenceClass(row.get("evidence_class"))
    except ValueError:
        return [f"invalid evidence_class: {row.get('evidence_class')!r}"]
    if row.get("paper_evidence") is True and evidence_class not in {
        EvidenceClass.REAL_OBSERVED_EVIDENCE,
        EvidenceClass.DERIVED_FROM_REAL_EVIDENCE,
    }:
        errors.append("paper_evidence cannot be promoted from this evidence class")
    if row.get("human_reviewed") is True and not row.get("human_review_artifact_sha256"):
        errors.append("human_reviewed=true requires a human review artifact hash")
    if evidence_class is EvidenceClass.REAL_OBSERVED_EVIDENCE:
        if not row.get("sha256") or row.get("observed") is not True:
            errors.append("real observed evidence requires observed=true and sha256")
    if evidence_class is EvidenceClass.DERIVED_FROM_REAL_EVIDENCE:
        if not row.get("upstream_sha256") or row.get("validation_status") != "PASS":
            errors.append("derived evidence requires upstream_sha256 and PASS validation")
    return errors


@dataclass(frozen=True)
class OutputContract:
    provider: str
    run_tag: str
    model_commit: str
    processor_commit: str
    item_ids: tuple[str, ...]
    variants: tuple[str, ...] = ("original", "edited")
    bundle_sha256: str | None = None
    run_contract_hash: str | None = None
    prompt_template_hash: str | None = None
    strict_provenance: bool = False

    @property
    def expected_keys(self) -> set[tuple[str, str]]:
        return {(item_id, variant) for item_id in self.item_ids for variant in self.variants}


OUTPUT_FIELDS = {
    "item_id",
    "variant",
    "raw_response",
    "parsed_response",
    "parse_status",
    "provider",
    "model_id",
    "model_commit",
    "processor_commit",
    "prompt_hash",
    "image_hash",
    "task_hash",
    "code_bundle_hash",
    "seed",
    "generation_parameters",
    "shard",
    "timestamp",
    "run_tag",
    "parser_version",
}

RUN_CONTRACT_OUTPUT_FIELDS = {
    "processor_id",
    "snapshot_contract",
    "model_snapshot_manifest_hash",
    "processor_snapshot_manifest_hash",
    "snapshot_status",
    "environment_lock_hash",
    "output_schema",
    "run_contract_hash",
}


def validate_output_rows(rows: list[dict[str, Any]], contract: OutputContract) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows, start=1):
        required_fields = OUTPUT_FIELDS | ({"run_contract_hash"} if contract.run_contract_hash else set())
        if contract.strict_provenance:
            required_fields |= RUN_CONTRACT_OUTPUT_FIELDS
        missing = sorted(required_fields - set(row))
        if missing:
            errors.append(f"row {index}: missing fields {missing}")
            continue
        key = (str(row["item_id"]), str(row["variant"]))
        if key in seen:
            errors.append(f"row {index}: duplicate item/variant {key}")
        seen.add(key)
        if key not in contract.expected_keys:
            errors.append(f"row {index}: unexpected item/variant {key}")
        if row["provider"] != contract.provider or row["run_tag"] != contract.run_tag:
            errors.append(f"row {index}: wrong provider or run tag")
        if row["model_commit"] != contract.model_commit:
            errors.append(f"row {index}: wrong model revision")
        if row["processor_commit"] != contract.processor_commit:
            errors.append(f"row {index}: wrong processor revision")
        if contract.bundle_sha256 and row["code_bundle_hash"] != contract.bundle_sha256:
            errors.append(f"row {index}: wrong code bundle hash")
        if contract.run_contract_hash and row["run_contract_hash"] != contract.run_contract_hash:
            errors.append(f"row {index}: wrong run contract hash")
        if contract.prompt_template_hash:
            if row.get("prompt_template_hash") != contract.prompt_template_hash:
                errors.append(f"row {index}: wrong prompt template hash")
        hash_fields = ["prompt_hash", "image_hash", "task_hash", "code_bundle_hash"]
        if contract.strict_provenance:
            hash_fields.extend([
                "model_snapshot_manifest_hash", "processor_snapshot_manifest_hash",
                "environment_lock_hash", "run_contract_hash",
            ])
        if contract.prompt_template_hash:
            hash_fields.append("prompt_template_hash")
        for hash_field in hash_fields:
            if not re.fullmatch(r"[0-9a-f]{64}", str(row[hash_field])):
                errors.append(f"row {index}: invalid {hash_field}")
        if row["parse_status"] == "PARSE_OK" and row["parsed_response"] is None:
            errors.append(f"row {index}: PARSE_OK without parsed_response")
    missing_keys = sorted(contract.expected_keys - seen)
    if missing_keys:
        errors.append(f"missing item/variant keys: {missing_keys[:10]}")
    return errors
