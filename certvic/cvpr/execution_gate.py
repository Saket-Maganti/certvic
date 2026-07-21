"""Hash-bound authorization gate for frozen scientific execution.

The study YAML deliberately remains ``execution_allowed: false``.  Execution
authority is conferred only by a verified, expiring permission artifact whose
signature binds every prerequisite byte sequence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from certvic.cvpr.contracts import canonical_json_bytes, load_yaml, sha256_bytes, validate_model_registry
from certvic.cvpr.task_schema import require_task_matrix, resolve_task_path
from certvic.cvpr.transactional import read_jsonl


PERMISSION_SCHEMA = "certvic.cvpr.execution_permission.v1"
SHA256_LENGTH = 64


class ExecutionAuthorizationError(ValueError):
    pass


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _permission_signature(payload: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(
        {key: value for key, value in payload.items() if key != "content_signature_sha256"}
    ))


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == SHA256_LENGTH and all(
        character in "0123456789abcdef" for character in value
    )


def _validate_review(review: dict[str, Any], task_ids: set[str]) -> None:
    if review.get("schema") != "certvic.cvpr.final_review_state.v2" or review.get(
        "status"
    ) != "FINAL_INCLUSION_VALIDATED":
        raise ExecutionAuthorizationError("final review is not validated schema v2")
    ledger = review.get("ledger")
    if not isinstance(ledger, list) or review.get("final_ledger_sha256") != sha256_bytes(
        canonical_json_bytes(ledger)
    ):
        raise ExecutionAuthorizationError("final review ledger is absent or hash-mismatched")
    payload = {key: value for key, value in review.items() if key != "final_artifact_sha256"}
    if review.get("final_artifact_sha256") != sha256_bytes(canonical_json_bytes(payload)):
        raise ExecutionAuthorizationError("final review artifact signature mismatch")
    included = {str(row.get("item_id")) for row in ledger if row.get("final_inclusion") is True
                and row.get("review_status") == "VALID_ADJUDICATED"}
    if not task_ids or not task_ids <= included:
        raise ExecutionAuthorizationError("one or more frozen tasks are not retained by final review")
    provenance = review.get("provenance", {})
    for field in (
        "packet_hash", "agreement_artifact_hash", "adjudication_artifact_hash",
        "adjudicator_identity_sha256",
    ):
        if not _valid_hash(provenance.get(field)):
            raise ExecutionAuthorizationError(f"review provenance has invalid {field}")
    for field in (
        "qualification_artifact_hashes", "validation_artifact_hashes", "rater_sheet_hashes",
    ):
        values = provenance.get(field)
        if not isinstance(values, dict) or not values or any(not _valid_hash(value)
                                                             for value in values.values()):
            raise ExecutionAuthorizationError(f"review provenance has invalid {field}")


def _validate_smoke(
    smoke: dict[str, Any], required_providers: set[str], *, synthetic_fixture: bool
) -> None:
    expected_status = "SYNTHETIC_SMOKE_PASSED" if synthetic_fixture else "REAL_MODEL_SMOKE_PASSED"
    if smoke.get("status") != expected_status:
        raise ExecutionAuthorizationError(
            f"execution requires {expected_status}; synthetic and real smoke are not interchangeable"
        )
    if smoke.get("strict_contract_verified") is not True:
        raise ExecutionAuthorizationError("smoke gate was not importer-grade strict validation")
    models = smoke.get("models")
    if not isinstance(models, list):
        raise ExecutionAuthorizationError("smoke gate model matrix is missing")
    statuses = {str(row.get("model")): row.get("status") for row in models}
    if set(statuses) != required_providers or any(value != "PASS" for value in statuses.values()):
        raise ExecutionAuthorizationError("not every required provider has an exact PASS smoke row")
    if not synthetic_fixture:
        for row in models:
            if row.get("runtime_class") != "REAL_MODEL_SMOKE" or row.get(
                "synthetic_fixture"
            ) is not False:
                raise ExecutionAuthorizationError(
                    "scientific execution requires explicit non-synthetic REAL_MODEL_SMOKE rows"
                )


def _validate_freeze(freeze: dict[str, Any], tasks: list[dict[str, Any]], study: str) -> None:
    if freeze.get("status") not in {"FINAL_TASKS_FROZEN", "MAIN_FINAL_TASKS_FROZEN"}:
        raise ExecutionAuthorizationError("final tasks are not frozen")
    if freeze.get("study") != study:
        raise ExecutionAuthorizationError("task freeze study mismatch")
    observed = freeze.get("freeze_hash")
    expected = sha256_bytes(canonical_json_bytes(
        {key: value for key, value in freeze.items() if key != "freeze_hash"}
    ))
    if observed != expected:
        raise ExecutionAuthorizationError("freeze manifest hash mismatch")
    task_hash = sha256_bytes(canonical_json_bytes(tasks))
    declared = freeze.get("primary_tasks_sha256", freeze.get("final_tasks_sha256"))
    if declared != task_hash:
        raise ExecutionAuthorizationError("freeze manifest does not bind the supplied final tasks")


def authorize(
    *,
    study: str,
    smoke_gate_path: str | Path,
    final_task_manifest: str | Path,
    final_review_ledger: str | Path,
    freeze_manifest: str | Path,
    code_hash: str,
    environment_lock: str | Path,
    model_registry: str | Path,
    study_config: str | Path,
    out: str | Path,
    issued_at: datetime | None = None,
    validity_hours: int = 168,
    synthetic_fixture: bool = False,
    prerequisite_artifact: str | Path | None = None,
    task_bundle_manifest: str | Path | None = None,
    bundle_root: str | Path | None = None,
    detectability_gate: str | Path | None = None,
    permission_ledger: str | Path | None = None,
    model_snapshot_manifests: dict[str, str | Path] | None = None,
    run_tags: dict[str, str] | str | None = None,
    output_schema: str = "certvic.cvpr.output.v2",
) -> dict[str, Any]:
    if not _valid_hash(code_hash):
        raise ExecutionAuthorizationError("code hash must be a verified SHA-256")
    paths = {
        "smoke_gate": Path(smoke_gate_path), "final_tasks": Path(final_task_manifest),
        "final_review": Path(final_review_ledger), "freeze_manifest": Path(freeze_manifest),
        "environment_lock": Path(environment_lock), "model_registry": Path(model_registry),
        "study_config": Path(study_config),
    }
    optional_paths = {
        "task_bundle_manifest": task_bundle_manifest,
        "detectability_gate": detectability_gate,
        "permission_ledger": permission_ledger,
    }
    for role, value in optional_paths.items():
        if value is not None:
            paths[role] = Path(value)
    for provider, value in sorted((model_snapshot_manifests or {}).items()):
        paths[f"model_snapshot_manifest:{provider}"] = Path(value)
    missing = [role for role, path in paths.items() if not path.is_file()]
    if missing:
        raise ExecutionAuthorizationError(f"authorization inputs are missing: {missing}")
    config = load_yaml(paths["study_config"])
    if config.get("study_id") != study:
        raise ExecutionAuthorizationError("study config identity mismatch")
    if config.get("paper_evidence") is not False:
        raise ExecutionAuthorizationError("pre-execution study config must keep paper_evidence=false")
    resolved_bundle_root = Path(bundle_root) if bundle_root is not None else None
    bundle: dict[str, Any] | None = None
    if task_bundle_manifest is not None:
        from certvic.cvpr.task_bundle import verify_bundle
        manifest_path = Path(task_bundle_manifest)
        resolved_bundle_root = resolved_bundle_root or manifest_path.parent
        bundle = verify_bundle(resolved_bundle_root, manifest_path)
        if Path(bundle["tasks_path"]).resolve() != paths["final_tasks"].resolve():
            raise ExecutionAuthorizationError(
                "final task manifest is not the verified task bundle task matrix"
            )
    tasks = require_task_matrix(
        read_jsonl(paths["final_tasks"]), verify_files=True, bundle_root=resolved_bundle_root,
    )
    if {str(task["study"]) for task in tasks} != {study}:
        raise ExecutionAuthorizationError("canonical task study identity mismatch")
    if any(task.get("qa_status") != "PASS" or task.get("review_status") != "VALID_ADJUDICATED"
           for task in tasks):
        raise ExecutionAuthorizationError("every final task must have PASS QA and validated review")
    task_ids = {str(task["task_id"]) for task in tasks}
    review = json.loads(paths["final_review"].read_text(encoding="utf-8"))
    _validate_review(review, task_ids)
    freeze = json.loads(paths["freeze_manifest"].read_text(encoding="utf-8"))
    _validate_freeze(freeze, tasks, study)
    registry = load_yaml(paths["model_registry"])
    providers = set(map(str, registry.get("primary_models", [])))
    if not synthetic_fixture:
        model_validation = validate_model_registry(registry, for_execution=True)
        if not model_validation["passed"]:
            raise ExecutionAuthorizationError("model registry is not execution-locked: " + "; ".join(
                model_validation["errors"]
            ))
    elif not providers:
        raise ExecutionAuthorizationError("synthetic model registry has no provider matrix")
    smoke = json.loads(paths["smoke_gate"].read_text(encoding="utf-8"))
    _validate_smoke(smoke, providers, synthetic_fixture=synthetic_fixture)
    task_universe_hash = sha256_bytes(canonical_json_bytes(sorted(task_ids)))
    if detectability_gate is not None:
        detectability = json.loads(Path(detectability_gate).read_text(encoding="utf-8"))
        if detectability.get("status") != "DETECTABILITY_GATE_PASS" or detectability.get(
            "execution_allowed"
        ) is not True:
            raise ExecutionAuthorizationError("set-level detectability gate has not passed")
        if detectability.get("task_universe_sha256") != task_universe_hash:
            raise ExecutionAuthorizationError("detectability gate task universe mismatch")
        observed_gate_hash = detectability.get("gate_hash")
        expected_gate_hash = sha256_bytes(canonical_json_bytes({
            key: value for key, value in detectability.items() if key != "gate_hash"
        }))
        if observed_gate_hash != expected_gate_hash:
            raise ExecutionAuthorizationError("detectability gate hash mismatch")
        if not synthetic_fixture:
            exact = detectability.get("exact_byte_binding")
            if detectability.get("exact_byte_binding_verified") is not True or not isinstance(
                exact, dict
            ):
                raise ExecutionAuthorizationError(
                    "real execution requires detectability bound to exact frozen task bytes"
                )
            if bundle is None or task_bundle_manifest is None:
                raise ExecutionAuthorizationError(
                    "detectability exact-byte verification requires the current task bundle"
                )
            exact_hash = exact.get("binding_hash")
            if exact_hash != sha256_bytes(canonical_json_bytes({
                key: value for key, value in exact.items() if key != "binding_hash"
            })):
                raise ExecutionAuthorizationError("detectability exact-byte binding hash mismatch")
            expected_exact = {
                "final_task_manifest_sha256": _sha(paths["final_tasks"]),
                "task_bundle_manifest_sha256": _sha(task_bundle_manifest),
                "task_bundle_hash": bundle["bundle_hash"],
            }
            for field, expected in expected_exact.items():
                if exact.get(field) != expected:
                    raise ExecutionAuthorizationError(
                        f"detectability exact-byte binding mismatch: {field}"
                    )
            byte_rows = exact.get("task_byte_bindings")
            if not isinstance(byte_rows, list) or len(byte_rows) != len(tasks):
                raise ExecutionAuthorizationError("detectability task-byte universe is incomplete")
            bound = {str(row.get("task_id")): row for row in byte_rows}
            if set(bound) != task_ids:
                raise ExecutionAuthorizationError("detectability task-byte IDs differ from final tasks")
            for task in tasks:
                task_id = str(task["task_id"])
                edited = resolve_task_path(task, "edited_image_path", bundle_root=resolved_bundle_root)
                if edited is None or not edited.is_file():
                    raise ExecutionAuthorizationError(f"detectability edited image is missing: {task_id}")
                if (
                    bound[task_id].get("task_hash") != task.get("task_hash")
                    or bound[task_id].get("edited_image_sha256") != _sha(edited)
                ):
                    raise ExecutionAuthorizationError(
                        f"detectability task or edited-image bytes differ: {task_id}"
                    )
    provider_run_tags = (
        {provider: str(run_tags) for provider in providers}
        if isinstance(run_tags, str) else
        ({str(key): str(value) for key, value in run_tags.items()} if run_tags is not None else {})
    )
    if provider_run_tags and set(provider_run_tags) != providers:
        raise ExecutionAuthorizationError("provider run-tag matrix mismatch")
    if permission_ledger is not None:
        from certvic.cvpr.permission_ledger import load_ledger
        ledger = load_ledger(permission_ledger)
        if (ledger.get("study") != study or set(ledger.get("providers", [])) != providers
                or ledger.get("task_universe_sha256") != task_universe_hash
                or ledger.get("output_schema") != output_schema):
            raise ExecutionAuthorizationError("permission ledger authorization matrix mismatch")
        if provider_run_tags and ledger.get("run_tags") != provider_run_tags:
            raise ExecutionAuthorizationError("permission ledger run tags mismatch")
        provider_run_tags = dict(ledger["run_tags"])
    prerequisite_hash = None
    if study == "main_study_cvpr":
        if prerequisite_artifact is None or not Path(prerequisite_artifact).is_file():
            raise ExecutionAuthorizationError("Main authorization requires the signed confirmatory outcome")
        prerequisite = json.loads(Path(prerequisite_artifact).read_text(encoding="utf-8"))
        signature = prerequisite.get("content_signature_sha256")
        expected_signature = sha256_bytes(canonical_json_bytes({
            key: value for key, value in prerequisite.items()
            if key != "content_signature_sha256"
        }))
        if (
            prerequisite.get("schema") != "certvic.cvpr.confirmatory_outcome.v1"
            or prerequisite.get("status") != "CONFIRMATORY_OUTCOME_VALIDATED"
            or prerequisite.get("study") != "specificity_confirmatory_cvpr"
            or prerequisite.get("main_go_no_go") != "GO"
            or signature != expected_signature
        ):
            raise ExecutionAuthorizationError(
                "confirmatory outcome is not a valid signed Main GO decision"
            )
        prerequisite_hash = _sha(prerequisite_artifact)
    now = issued_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    input_hashes = {role: _sha(path) for role, path in paths.items()}
    permission_id = sha256_bytes(canonical_json_bytes({
        "study": study, "code_hash": code_hash, "input_hashes": input_hashes,
        "prerequisite_hash": prerequisite_hash, "provider_run_tags": provider_run_tags,
        "output_schema": output_schema,
    }))
    permission = {
        "schema": PERMISSION_SCHEMA, "study": study, "permission_id": permission_id,
        "authorization_status": "AUTHORIZED", "authorization_mode": "HASH_BOUND_ONE_RUN",
        "issued_at_utc": now.astimezone(timezone.utc).isoformat(),
        "expires_at_utc": (now + timedelta(hours=validity_hours)).astimezone(timezone.utc).isoformat(),
        "one_run_policy": True, "input_hashes": input_hashes, "code_hash": code_hash,
        "task_universe_sha256": task_universe_hash,
        "freeze_hash": freeze["freeze_hash"],
        "review_artifact_sha256": review["final_artifact_sha256"],
        "required_providers": sorted(providers), "prerequisite_hash": prerequisite_hash,
        "provider_run_tags": provider_run_tags, "output_schema": output_schema,
        "provider_slots": {provider: "ISSUED" for provider in sorted(providers)},
        "binding_level": ("FULL_CURRENT_INPUT_MATRIX" if task_bundle_manifest is not None
                          and detectability_gate is not None and permission_ledger is not None
                          and set(model_snapshot_manifests or {}) == providers else
                          "LEGACY_PREREQUISITE_MATRIX"),
        "synthetic_fixture": synthetic_fixture,
        "runtime_class": "SYNTHETIC_END_TO_END_FIXTURE" if synthetic_fixture else
        "SCIENTIFIC_EXECUTION_AUTHORIZATION",
        "paper_evidence": False,
    }
    permission["content_signature_sha256"] = _permission_signature(permission)
    destination = Path(out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(permission, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return permission


def verify_permission(
    permission_path: str | Path,
    *,
    study: str,
    now: datetime | None = None,
    allow_synthetic: bool = False,
    input_paths: dict[str, str | Path] | None = None,
    expected_code_hash: str | None = None,
    expected_provider: str | None = None,
    expected_run_tag: str | None = None,
    expected_output_schema: str | None = None,
) -> dict[str, Any]:
    path = Path(permission_path)
    if not path.is_file():
        raise ExecutionAuthorizationError("signed execution permission is missing")
    permission = json.loads(path.read_text(encoding="utf-8"))
    if permission.get("schema") != PERMISSION_SCHEMA or permission.get(
        "authorization_status"
    ) != "AUTHORIZED" or permission.get("study") != study:
        raise ExecutionAuthorizationError("execution permission identity/status mismatch")
    if permission.get("synthetic_fixture") is True and not allow_synthetic:
        raise ExecutionAuthorizationError("synthetic permission cannot authorize scientific execution")
    if permission.get("content_signature_sha256") != _permission_signature(permission):
        raise ExecutionAuthorizationError("execution permission signature mismatch")
    current = now or datetime.now(timezone.utc)
    expiry = datetime.fromisoformat(str(permission["expires_at_utc"]))
    if current.astimezone(timezone.utc) > expiry.astimezone(timezone.utc):
        raise ExecutionAuthorizationError("execution permission has expired")
    if permission.get("one_run_policy") is not True:
        raise ExecutionAuthorizationError("execution permission must use the frozen one-run policy")
    if expected_code_hash is not None and permission.get("code_hash") != expected_code_hash:
        raise ExecutionAuthorizationError("execution permission code hash mismatch")
    if expected_provider is not None:
        if expected_provider not in permission.get("required_providers", []):
            raise ExecutionAuthorizationError("execution permission provider mismatch")
        if permission.get("provider_slots", {}).get(expected_provider) != "ISSUED":
            raise ExecutionAuthorizationError("execution permission provider slot is invalid")
    if expected_run_tag is not None:
        if expected_provider is None:
            raise ExecutionAuthorizationError("run-tag verification requires expected_provider")
        if permission.get("provider_run_tags", {}).get(expected_provider) != expected_run_tag:
            raise ExecutionAuthorizationError("execution permission run tag mismatch")
    if expected_output_schema is not None and permission.get("output_schema") != expected_output_schema:
        raise ExecutionAuthorizationError("execution permission output schema mismatch")
    if input_paths is not None:
        declared = permission.get("input_hashes")
        if not isinstance(declared, dict) or set(declared) != set(input_paths):
            raise ExecutionAuthorizationError("execution permission input role matrix mismatch")
        for role, source in input_paths.items():
            source_path = Path(source)
            if not source_path.is_file() or _sha(source_path) != declared[role]:
                raise ExecutionAuthorizationError(f"execution permission input drift: {role}")
    return {"status": "EXECUTION_PERMISSION_VALID", "study": study,
            "permission_id": permission["permission_id"],
            "content_signature_sha256": permission["content_signature_sha256"],
            "task_universe_sha256": permission["task_universe_sha256"],
            "binding_level": permission.get("binding_level"),
            "paper_evidence": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Authorize or verify frozen CertVIC execution")
    sub = parser.add_subparsers(dest="command", required=True)
    authorize_parser = sub.add_parser("authorize")
    authorize_parser.add_argument("--study", required=True)
    authorize_parser.add_argument("--smoke-gate", required=True)
    authorize_parser.add_argument("--final-task-manifest", required=True)
    authorize_parser.add_argument("--final-review-ledger", required=True)
    authorize_parser.add_argument("--freeze-manifest", required=True)
    authorize_parser.add_argument("--code-hash", required=True)
    authorize_parser.add_argument("--environment-lock", required=True)
    authorize_parser.add_argument("--model-registry", required=True)
    authorize_parser.add_argument("--study-config", required=True)
    authorize_parser.add_argument("--prerequisite-artifact")
    authorize_parser.add_argument("--task-bundle-manifest")
    authorize_parser.add_argument("--bundle-root")
    authorize_parser.add_argument("--detectability-gate")
    authorize_parser.add_argument("--permission-ledger")
    authorize_parser.add_argument("--model-snapshot-manifest", action="append", default=[])
    authorize_parser.add_argument("--run-tag")
    authorize_parser.add_argument("--output-schema", default="certvic.cvpr.output.v2")
    authorize_parser.add_argument("--out", required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--permission", required=True)
    verify_parser.add_argument("--study", required=True)
    verify_parser.add_argument("--input", action="append", default=[])
    verify_parser.add_argument("--expected-code-hash")
    verify_parser.add_argument("--expected-provider")
    verify_parser.add_argument("--expected-run-tag")
    verify_parser.add_argument("--expected-output-schema")
    args = parser.parse_args(argv)
    try:
        if args.command == "authorize":
            snapshots = dict(value.split("=", 1) for value in args.model_snapshot_manifest)
            result = authorize(
                study=args.study, smoke_gate_path=args.smoke_gate,
                final_task_manifest=args.final_task_manifest,
                final_review_ledger=args.final_review_ledger, freeze_manifest=args.freeze_manifest,
                code_hash=args.code_hash, environment_lock=args.environment_lock,
                model_registry=args.model_registry, study_config=args.study_config,
                prerequisite_artifact=args.prerequisite_artifact, out=args.out,
                task_bundle_manifest=args.task_bundle_manifest, bundle_root=args.bundle_root,
                detectability_gate=args.detectability_gate,
                permission_ledger=args.permission_ledger,
                model_snapshot_manifests=snapshots or None, run_tags=args.run_tag,
                output_schema=args.output_schema,
            )
        else:
            inputs = dict(value.split("=", 1) for value in args.input)
            result = verify_permission(
                args.permission, study=args.study, input_paths=inputs or None,
                expected_code_hash=args.expected_code_hash,
                expected_provider=args.expected_provider, expected_run_tag=args.expected_run_tag,
                expected_output_schema=args.expected_output_schema,
            )
    except (ExecutionAuthorizationError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "EXECUTION_AUTHORIZATION_BLOCKED", "reason": str(exc),
                          "paper_evidence": False}, sort_keys=True))
        return 2
    print(json.dumps({"status": result.get("authorization_status", result.get("status")),
                      "study": args.study, "paper_evidence": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
