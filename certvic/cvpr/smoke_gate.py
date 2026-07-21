"""Machine gate from pending real-model smoke to scientific-run permission."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from certvic.cvpr.contracts import canonical_json_bytes, load_yaml, sha256_bytes
from certvic.cvpr.schema_contract import OUTPUT_SCHEMA, validate_schema_matrix
from certvic.cvpr.smoke_artifacts import SmokeArtifactError, read_smoke_archive


NON_BLOCKING_WARNING_CODES = frozenset({"CUDA_CACHE_ALREADY_EMPTY", "OPTIONAL_TELEMETRY_UNAVAILABLE"})


def _diagnostics(provider: str, errors: list[str]) -> list[dict[str, Any]]:
    mappings = (
        ("snapshot", "SMOKE_SNAPSHOT_MISMATCH", "Re-run 00B and 00C2 from the same snapshot bytes."),
        ("run contract", "SMOKE_RUN_CONTRACT_MISMATCH", "Regenerate the frozen run contract and rerun 00C2."),
        ("run_contract", "SMOKE_RUN_CONTRACT_MISMATCH", "Regenerate the frozen run contract and rerun 00C2."),
        ("prompt", "SMOKE_PROMPT_MISMATCH", "Restore the authorized prompt template and reissue permission."),
        ("oom", "SMOKE_OOM_DETECTED", "Reduce memory pressure and rerun the real-model smoke."),
        ("warning", "SMOKE_WARNING_UNRESOLVED", "Resolve or explicitly classify the warning, then rerun."),
        ("cuda cleanup", "SMOKE_CLEANUP_FAILED", "Repair CUDA teardown and rerun 00C2."),
        ("model release", "SMOKE_CLEANUP_FAILED", "Repair model release and rerun 00C2."),
        ("cleanup", "SMOKE_CLEANUP_FAILED", "Repair teardown and rerun 00C2."),
        ("parent", "SMOKE_PARENT_AUTHORIZATION_MISMATCH", "Attach the matching parent matrix and child permission."),
    )
    diagnostics: list[dict[str, Any]] = []
    for error in errors:
        lowered = error.lower()
        code, remediation = "SMOKE_ARTIFACT_INVALID", "Regenerate 00C2 without editing returned files."
        for marker, candidate, action in mappings:
            if marker in lowered:
                code, remediation = candidate, action
                break
        diagnostics.append({
            "provider": provider,
            "file": "00C2 canonical package",
            "field": error.split(" ", 1)[0][:80],
            "expected_value": "trusted contract",
            "observed_value": "mismatch",
            "error_code": code,
            "remediation": remediation,
        })
    return diagnostics


def _safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        names = [member.filename for member in handle.infolist()]
        if len(names) != len(set(names)) or handle.testzip() is not None:
            raise ValueError("smoke ZIP has duplicate or corrupt members")
        if any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
               for name in names):
            raise ValueError("smoke ZIP has an unsafe member")
        handle.extractall(destination)


def _single(root: Path, name: str) -> Path:
    paths = list(root.rglob(name))
    if len(paths) != 1:
        raise ValueError(f"smoke ZIP must contain exactly one {name}")
    return paths[0]


def _hash(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _verify_member_hashes(root: Path) -> dict[str, str]:
    manifest_path = _single(root, "hash_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = manifest.get("files", manifest) if isinstance(manifest, dict) else None
    if not isinstance(declared, dict) or not declared:
        raise ValueError("hash_manifest.json must enumerate every ZIP member")
    observed = {
        path.relative_to(manifest_path.parent).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in manifest_path.parent.rglob("*") if path.is_file() and path != manifest_path
    }
    missing = sorted(set(declared) - set(observed))
    extras = sorted(set(observed) - set(declared))
    mismatches = sorted(name for name in set(declared) & set(observed)
                        if declared[name] != observed[name])
    if missing or extras or mismatches:
        raise ValueError(
            f"smoke ZIP member hash mismatch: missing={missing}, extras={extras}, "
            f"mismatches={mismatches}"
        )
    return observed


def _strict_checks(
    unpacked: Path,
    *,
    provider: str,
    rows: list[dict[str, Any]],
    runtime: dict[str, Any],
    validation: dict[str, Any],
    environment: dict[str, Any],
    snapshot: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    member_hashes = _verify_member_hashes(unpacked)
    required_members = {
        "merged_raw.jsonl", "runtime_manifest.json", "environment_manifest.json",
        "snapshot_manifest.json", "validation_report.json", "failure_report.json",
        "cleanup_report.json", "run_contract.json",
    }
    basenames = {Path(name).name for name in member_hashes}
    missing_members = sorted(required_members - basenames)
    if missing_members:
        errors.append(f"required importer-grade members missing: {missing_members}")
    expected_rows = contract.get("fixture_rows")
    if not isinstance(expected_rows, list) or len({
        str(row.get("item_id")) for row in expected_rows
    }) != 2:
        errors.append("trusted smoke contract must declare rows for exactly two fixture items")
        expected_rows = []
    observed_map = {
        (str(row.get("item_id")), str(row.get("variant", ""))): row for row in rows
    }
    expected_map = {
        (str(row.get("item_id")), str(row.get("variant", ""))): row for row in expected_rows
    }
    if len(observed_map) != len(rows) or set(observed_map) != set(expected_map):
        errors.append("smoke rows differ from the exact trusted two-item fixture universe")
    provider_contract = contract.get("providers", {}).get(provider)
    if not isinstance(provider_contract, dict):
        errors.append("trusted smoke provider contract is missing")
        provider_contract = {}
    global_expected = {
        "provider": provider,
        "model_id": provider_contract.get("model_id"),
        "model_commit": provider_contract.get("model_commit"),
        "processor_commit": provider_contract.get("processor_commit"),
        "model_snapshot_manifest_hash": provider_contract.get("snapshot_manifest_hash"),
        "environment_lock_hash": contract.get("environment_hash"),
        "code_bundle_hash": contract.get("code_hash"),
        "prompt_template_hash": contract.get("prompt_hash"),
        "parser_version": contract.get("parser_version"),
        "run_contract_hash": provider_contract.get("run_contract_hash"),
    }
    for field, expected in global_expected.items():
        runtime_field = {
            "model_snapshot_manifest_hash": "snapshot_manifest_hash",
            "environment_lock_hash": "environment_hash",
            "code_bundle_hash": "code_bundle_hash",
            "prompt_template_hash": "prompt_template_hash",
        }.get(field, field)
        observed = runtime.get(runtime_field, runtime.get(field))
        if expected is None or observed != expected:
            errors.append(f"runtime {field} differs from trusted contract")
    if environment.get("environment_hash", environment.get("environment_lock_hash")) != contract.get(
        "environment_hash"
    ):
        errors.append("returned environment manifest differs from trusted environment")
    try:
        returned_environment = json.loads(_single(
            unpacked, "environment_manifest.json"
        ).read_text(encoding="utf-8"))
        if returned_environment.get(
            "environment_hash", returned_environment.get("environment_lock_hash")
        ) != contract.get("environment_hash"):
            errors.append("packaged environment manifest differs from trusted environment")
    except (ValueError, json.JSONDecodeError):
        errors.append("packaged environment manifest is absent or invalid")
    snapshot_artifact_hash = hashlib.sha256(
        _single(unpacked, "snapshot_manifest.json").read_bytes()
    ).hexdigest() if "snapshot_manifest.json" in basenames else None
    if snapshot_artifact_hash != provider_contract.get("snapshot_manifest_hash"):
        errors.append("returned snapshot artifact differs from trusted snapshot")
    try:
        returned_snapshot = json.loads(_single(
            unpacked, "snapshot_manifest.json"
        ).read_text(encoding="utf-8"))
        if returned_snapshot.get("model_id") != provider_contract.get(
            "model_id"
        ) or returned_snapshot.get("model_commit") != provider_contract.get("model_commit"):
            errors.append("returned snapshot model identity/revision mismatch")
    except (ValueError, json.JSONDecodeError):
        errors.append("returned snapshot artifact is absent or invalid")
    try:
        returned_contract = json.loads(_single(
            unpacked, "run_contract.json"
        ).read_text(encoding="utf-8"))
        if returned_contract.get("run_contract_hash") != provider_contract.get("run_contract_hash"):
            errors.append("returned run contract differs from trusted contract")
    except (ValueError, json.JSONDecodeError):
        errors.append("returned run contract is absent or invalid")
    for key, expected_row in expected_map.items():
        row = observed_map.get(key, {})
        expected = {
            "task_hash": expected_row.get("task_hash"),
            "image_hash": expected_row.get("image_hash"),
            "prompt_hash": expected_row.get("prompt_hash", contract.get("prompt_hash")),
            "provider": provider,
            "model_id": provider_contract.get("model_id"),
            "model_commit": provider_contract.get("model_commit"),
            "processor_commit": provider_contract.get("processor_commit"),
            "parser_version": contract.get("parser_version"),
            "code_bundle_hash": contract.get("code_hash"),
            "model_snapshot_manifest_hash": provider_contract.get("snapshot_manifest_hash"),
            "run_contract_hash": provider_contract.get("run_contract_hash"),
            "parse_status": "PARSE_OK",
        }
        for field, value in expected.items():
            if value is None or row.get(field) != value:
                errors.append(f"{key}: row {field} differs from trusted contract")
    if validation.get("passed") is not True or validation.get(
        "validation_source"
    ) != "RECOMPUTED_FROM_RETURNED_BYTES":
        errors.append("validation report is not recomputed from returned bytes")
    try:
        failures = json.loads(_single(unpacked, "failure_report.json").read_text(encoding="utf-8"))
        if failures.get("failures") not in (None, []) or failures.get("count", 0) != 0:
            errors.append("failure report is nonempty")
    except (ValueError, json.JSONDecodeError):
        errors.append("failure report is absent or invalid")
    try:
        cleanup = json.loads(_single(unpacked, "cleanup_report.json").read_text(encoding="utf-8"))
        if cleanup.get("status") != "PASS" or cleanup.get("model_released") is not True:
            errors.append("cleanup report did not prove model release")
    except (ValueError, json.JSONDecodeError):
        errors.append("cleanup report is absent or invalid")
    if runtime.get("raw_prediction_sha256") != hashlib.sha256(
        _single(unpacked, "merged_raw.jsonl").read_bytes()
    ).hexdigest():
        errors.append("raw prediction file hash differs from runtime manifest")
    return errors


def _validate_provider(
    root: Path, provider: str, *, contract: dict[str, Any] | None = None
) -> dict[str, Any]:
    environment_path = root / "00A_environment.json"
    snapshot_path = root / f"00B_{provider}_snapshot.json"
    archive = root / f"00C2_{provider}_real_model_smoke.zip"
    missing = [path.name for path in (environment_path, snapshot_path, archive) if not path.is_file()]
    if missing:
        return {"model": provider, "status": "PENDING", "reason": "missing:" + "|".join(missing)}
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    if environment.get("status") not in {
        "EXACT_PREINSTALLED_ENVIRONMENT_ACCEPTED", "OFFLINE_WHEELHOUSE_INSTALLED_AND_VERIFIED",
    } or environment.get("passed") is not True:
        return {"model": provider, "status": "FAIL", "reason": "00A environment invalid"}
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("status") == "BLOCKED_HARDWARE":
        return {"model": provider, "status": "BLOCKED_HARDWARE", "reason": "00B hardware block"}
    if snapshot.get("passed") is not True or snapshot.get("snapshot_contract") != "UNIFIED_SNAPSHOT":
        return {"model": provider, "status": "FAIL", "reason": "00B snapshot invalid"}
    try:
        canonical = read_smoke_archive(archive)
    except SmokeArtifactError as exc:
        try:
            with zipfile.ZipFile(archive) as handle:
                is_canonical = "predictions.jsonl" in handle.namelist()
        except zipfile.BadZipFile:
            is_canonical = False
        if is_canonical:
            errors = [str(exc)]
            return {
                "model": provider, "provider": provider, "status": "FAIL",
                "reason": str(exc), "diagnostics": _diagnostics(provider, errors),
                "strict_contract_verified": False,
            }
        canonical = None
    if canonical is not None:
        errors: list[str] = []
        runtime = canonical["runtime"]
        validation = canonical["validation"]
        rows = canonical["rows"]
        proof = canonical["authorization_proof"]
        task_bundle = canonical["task_bundle"]
        runtime_class = proof.get("runtime_class")
        synthetic = proof.get("synthetic_fixture") is True
        expected_class = (
            "SYNTHETIC_SMOKE"
            if contract and contract.get("synthetic_fixture") is True
            else "REAL_MODEL_SMOKE"
        )
        if runtime_class != expected_class or synthetic != (expected_class == "SYNTHETIC_SMOKE"):
            errors.append("canonical smoke runtime class/synthetic marker mismatch")
        if proof.get("provider") != provider or runtime.get("provider") != provider:
            errors.append("provider mismatch")
        if validation.get("passed") is not True or validation.get(
            "validation_source"
        ) != "RECOMPUTED_FROM_RETURNED_BYTES":
            errors.append("validation report is not recomputed from returned bytes")
        if runtime.get("expected_shards") != runtime.get("produced_shards"):
            errors.append("runtime expected/produced shard counts differ")
        if runtime.get("expected_shards") != 1:
            errors.append("canonical two-item smoke requires one intentional logical shard")
        if runtime.get("task_bundle_hash") != task_bundle.get("bundle_hash") or proof.get(
            "task_bundle_hash"
        ) != task_bundle.get("bundle_hash"):
            errors.append("preflight/worker/package task bundle hashes differ")
        expected_rows = contract.get("fixture_rows", []) if contract else []
        if contract is not None:
            expected_map = {
                (str(row.get("item_id")), str(row.get("variant", ""))): row
                for row in expected_rows
            }
            observed_map = {
                (str(row.get("item_id")), str(row.get("variant", ""))): row for row in rows
            }
            if len(expected_map) != 4 or set(observed_map) != set(expected_map):
                errors.append("smoke rows differ from the exact trusted two-item fixture universe")
            for key, expected in expected_map.items():
                observed = observed_map.get(key, {})
                for field in ("task_hash", "image_hash", "prompt_hash"):
                    if expected.get(field) is None or observed.get(field) != expected.get(field):
                        errors.append(f"{key}: {field} differs from trusted fixture")
            provider_contract = contract.get("providers", {}).get(provider, {})
            semantic_equalities = {
                "model_id": provider_contract.get("model_id"),
                "model_revision": provider_contract.get(
                    "model_revision", provider_contract.get("model_commit")
                ),
                "snapshot_manifest_hash": provider_contract.get(
                    "snapshot_manifest_hash", provider_contract.get("snapshot_hash")
                ),
                "snapshot_root_hash": provider_contract.get("snapshot_root_hash"),
                "environment_manifest_hash": contract.get(
                    "environment_manifest_hash", contract.get("environment_hash")
                ),
                "code_hash": contract.get("code_hash"),
                "parser_version": contract.get("parser_version"),
                "prompt_hash": contract.get("prompt_hash"),
                "prompt_template_hash": contract.get("prompt_template_hash", contract.get("prompt_hash")),
                "task_bundle_hash": contract.get(
                    "task_bundle_hash", task_bundle.get("bundle_hash")
                ),
                "smoke_fixture_hash": contract.get(
                    "smoke_fixture_hash", runtime.get("task_manifest_sha256")
                ),
                "run_contract_hash": provider_contract.get("run_contract_hash"),
            }
            for field, expected in semantic_equalities.items():
                if expected is not None and proof.get(field) != expected:
                    errors.append(f"canonical smoke {field} differs from trusted contract")
        if len(rows) != 4 or len({str(row.get("item_id")) for row in rows}) != 2:
            errors.append("canonical smoke must contain two items and four variant rows")
        if any(row.get("parse_status") != "PARSE_OK" for row in rows):
            errors.append("one or more canonical smoke predictions did not parse")
        schema = validate_schema_matrix(rows)
        if not schema["passed"]:
            errors.extend(schema["errors"])
        environment_hash = proof.get("environment_manifest_hash")
        snapshot_hash = proof.get("snapshot_manifest_hash")
        if environment.get("environment_hash", environment.get("environment_lock_hash")) != environment_hash:
            errors.append("00A and canonical smoke environment identities differ")
        if snapshot.get("manifest_sha256", snapshot.get("snapshot_manifest_hash")) != snapshot_hash:
            errors.append("00B and canonical smoke snapshot identities differ")
        peak_vram = runtime.get("peak_vram_gib")
        if runtime.get("cleanup_status") != "PASS" or runtime.get(
            "teardown_complete"
        ) is not True:
            errors.append("cleanup status or teardown completion failed")
        if runtime.get("model_release_status") != "PASS":
            errors.append("model release status failed")
        if runtime.get("cuda_cleanup_status") not in {"PASS", "NOT_APPLICABLE"}:
            errors.append("CUDA cleanup status failed")
        if runtime.get("oom_events") != 0:
            errors.append("OOM event count is nonzero")
        if runtime.get("unresolved_warnings") != []:
            errors.append("warning list contains unresolved entries")
        warnings = runtime.get("warnings", [])
        if not isinstance(warnings, list) or any(
            not isinstance(row, dict) or row.get("code") not in NON_BLOCKING_WARNING_CODES
            for row in warnings
        ):
            errors.append("warning allowlist contains an unknown entry")
        if expected_class == "REAL_MODEL_SMOKE" and (
            not isinstance(peak_vram, (int, float)) or peak_vram <= 0
        ):
            errors.append("real-model smoke peak VRAM is absent")
        return {
            "model": provider,
            "provider": provider,
            "status": "PASS" if not errors else "FAIL",
            "reason": "validated canonical 00A+00B+00C2" if not errors else "|".join(errors),
            "diagnostics": _diagnostics(provider, errors),
            "runtime_class": runtime_class,
            "synthetic_fixture": synthetic,
            "model_id": proof.get("model_id"),
            "model_revision": proof.get("model_revision"),
            "snapshot_hash": snapshot_hash,
            "snapshot_manifest_hash": snapshot_hash,
            "snapshot_root_hash": proof.get("snapshot_root_hash"),
            "environment_hash": environment_hash,
            "environment_manifest_hash": environment_hash,
            "code_hash": proof.get("code_hash"),
            "processor_model_contract": proof.get("processor_model_contract"),
            "parser_version": proof.get("parser_version"),
            "prompt_hash": proof.get("prompt_hash"),
            "task_bundle_hash": proof.get("task_bundle_hash"),
            "smoke_fixture_hash": proof.get("smoke_fixture_hash"),
            "peak_vram_gib": peak_vram,
            "run_contract_hash": runtime.get("run_contract_hash"),
            "smoke_zip_sha256": canonical["archive_sha256"],
            "strict_contract_verified": contract is not None and not errors,
            "artifact_schema": "certvic.cvpr.smoke_artifact.v1",
        }
    try:
        with tempfile.TemporaryDirectory(prefix="certvic_smoke_gate_") as temporary:
            unpacked = Path(temporary)
            _safe_extract(archive, unpacked)
            runtime = json.loads(_single(unpacked, "runtime_manifest.json").read_text(encoding="utf-8"))
            validation = json.loads(_single(unpacked, "validation_report.json").read_text(encoding="utf-8"))
            rows = [json.loads(line) for line in _single(unpacked, "merged_raw.jsonl").read_text(
                encoding="utf-8"
            ).splitlines() if line]
            if runtime.get("status") == "BLOCKED_HARDWARE":
                return {"model": provider, "status": "BLOCKED_HARDWARE",
                        "reason": "00C2 reported hardware block"}
            errors: list[str] = []
            expected_runtime_class = (
                "SYNTHETIC_END_TO_END_FIXTURE" if contract and contract.get(
                    "synthetic_fixture"
                ) is True else "NON_EVIDENCE_REAL_MODEL_SMOKE"
            )
            if runtime.get("runtime_class") != expected_runtime_class:
                errors.append(f"runtime class is not {expected_runtime_class}")
            if runtime.get("provider") != provider:
                errors.append("provider mismatch")
            expected_row_count = len(contract.get("fixture_rows", [])) if contract else 2
            if len(rows) != expected_row_count or len({str(row.get("item_id")) for row in rows}) != 2:
                errors.append(
                    "00C2 must contain the exact trusted rows for two distinct fixture items"
                )
            if any(row.get("parse_status") != "PARSE_OK" for row in rows):
                errors.append("one or more smoke predictions did not parse")
            schema = validate_schema_matrix(rows)
            if not schema["passed"]:
                errors.extend(schema["errors"])
            if validation.get("passed") is not True:
                errors.append("validation report failed")
            if runtime.get("oom_events", 0) or runtime.get("unresolved_warnings"):
                errors.append("OOM or unresolved warning recorded")
            peak_vram = runtime.get("peak_vram_gib")
            synthetic = expected_runtime_class == "SYNTHETIC_END_TO_END_FIXTURE"
            if synthetic:
                if peak_vram != 0 or runtime.get("peak_vram_status") != "SYNTHETIC_NOT_MEASURED":
                    errors.append("synthetic smoke must label zero VRAM as not measured")
            elif not isinstance(peak_vram, (int, float)) or peak_vram <= 0:
                errors.append("peak VRAM is absent")
            for field in ("environment_hash", "snapshot_manifest_hash", "run_contract_hash"):
                if not _hash(str(runtime.get(field, ""))):
                    errors.append(f"invalid {field}")
            if runtime.get("environment_hash") != environment.get("environment_hash"):
                errors.append("00C2 environment hash differs from 00A")
            if runtime.get("snapshot_manifest_hash") != snapshot.get("manifest_sha256"):
                errors.append("00C2 snapshot hash differs from 00B")
            if contract is not None:
                errors.extend(_strict_checks(
                    unpacked, provider=provider, rows=rows, runtime=runtime,
                    validation=validation, environment=environment, snapshot=snapshot,
                    contract=contract,
                ))
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        errors = [str(exc)]
        return {"model": provider, "status": "FAIL", "reason": str(exc),
                "diagnostics": _diagnostics(provider, errors)}
    return {
        "model": provider, "status": "PASS" if not errors else "FAIL",
        "reason": "validated 00A+00B+00C2" if not errors else "|".join(errors),
        "diagnostics": _diagnostics(provider, errors),
        "peak_vram_gib": peak_vram,
        "environment_hash": runtime.get("environment_hash"),
        "snapshot_hash": runtime.get("snapshot_manifest_hash"),
        "run_contract_hash": runtime.get("run_contract_hash"),
        "smoke_zip_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "strict_contract_verified": contract is not None and not errors,
        "runtime_class": (
            "SYNTHETIC_SMOKE"
            if expected_runtime_class == "SYNTHETIC_END_TO_END_FIXTURE"
            else "REAL_MODEL_SMOKE"
        ),
        "synthetic_fixture": expected_runtime_class == "SYNTHETIC_END_TO_END_FIXTURE",
    }


def evaluate(
    smoke_root: str | Path, providers: list[str], *, contract: dict[str, Any] | None = None
) -> dict[str, Any]:
    rows = [_validate_provider(Path(smoke_root), provider, contract=contract) for provider in providers]
    statuses = {row["status"] for row in rows}
    if statuses == {"PASS"}:
        status = ("SYNTHETIC_SMOKE_PASSED" if contract and contract.get(
            "synthetic_fixture"
        ) is True else "REAL_MODEL_SMOKE_PASSED")
    elif "FAIL" in statuses:
        status = "REAL_MODEL_SMOKE_FAILED"
    else:
        status = "REAL_MODEL_SMOKE_PENDING"
    return {
        "schema": "certvic.cvpr.real_model_smoke_gate.v1",
        "status": status,
        "scientific_run_allowed": status == "REAL_MODEL_SMOKE_PASSED",
        "required_output_schema": OUTPUT_SCHEMA,
        "models": rows,
        "strict_contract_verified": contract is not None and statuses == {"PASS"}
        and all(row.get("strict_contract_verified") for row in rows),
        "trusted_contract_sha256": sha256_bytes(canonical_json_bytes(contract))
        if contract is not None else None,
        "paper_evidence": False,
    }


def write_gate(result: dict[str, Any], out: str | Path) -> None:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["model", "status", "reason", "peak_vram_gib", "environment_hash",
              "snapshot_hash", "run_contract_hash", "smoke_zip_sha256"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["models"])
    path.with_suffix(".json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                         encoding="utf-8")


def require_scientific_run_gate(path: str | Path, providers: list[str]) -> None:
    gate_path = Path(path)
    json_path = gate_path if gate_path.suffix.lower() == ".json" else gate_path.with_suffix(".json")
    csv_path = gate_path.with_suffix(".csv") if gate_path.suffix.lower() == ".json" else gate_path
    if not json_path.is_file():
        raise ValueError("scientific execution requires the signed strict smoke-gate JSON")
    gate = json.loads(json_path.read_text(encoding="utf-8"))
    if gate.get("strict_contract_verified") is not True:
        raise ValueError("scientific execution requires importer-grade strict smoke validation")
    if gate.get("status") != "REAL_MODEL_SMOKE_PASSED" or gate.get(
        "scientific_run_allowed"
    ) is not True:
        raise ValueError("synthetic smoke cannot authorize a scientific run")
    if any(
        row.get("runtime_class") != "REAL_MODEL_SMOKE"
        or row.get("synthetic_fixture") is not False
        for row in gate.get("models", [])
    ):
        raise ValueError("scientific execution requires explicit real, non-synthetic smoke identities")
    if not csv_path.is_file():
        raise ValueError("scientific execution requires the strict smoke-gate CSV beside its JSON")
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    status = {row.get("model"): row.get("status") for row in rows}
    if set(status) != set(providers) or any(status[provider] != "PASS" for provider in providers):
        raise ValueError("scientific execution blocked until every required real-model smoke is PASS")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate real-model Kaggle smoke promotion")
    parser.add_argument("--smoke-root", required=True)
    parser.add_argument("--model-registry", default="configs/models/certvic_cvpr_model_registry.yaml")
    parser.add_argument("--smoke-contract", required=True)
    parser.add_argument("--out", default="reports/cvpr_final_integration/REAL_MODEL_SMOKE_GATE.csv")
    args = parser.parse_args(argv)
    registry = load_yaml(args.model_registry)
    contract = json.loads(Path(args.smoke_contract).read_text(encoding="utf-8"))
    result = evaluate(args.smoke_root, list(registry["primary_models"]), contract=contract)
    write_gate(result, args.out)
    print(json.dumps({"status": result["status"], "out": args.out}, sort_keys=True))
    return 0 if result["status"] == "REAL_MODEL_SMOKE_PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
