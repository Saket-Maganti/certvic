"""One-command, fail-closed confirmatory continuation after genuine human review."""

from __future__ import annotations

import csv
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from certvic.cvpr.candidate_selection import main as select_main
from certvic.cvpr.contracts import (
    canonical_json_bytes,
    load_yaml,
    sha256_bytes,
    validate_model_registry,
)
from certvic.cvpr.detectability_gate import evaluate as evaluate_detectability
from certvic.cvpr.kaggle_bundle import verify_bundle as verify_kaggle_bundle
from certvic.cvpr.reconcile_provider_permissions import (
    ProviderPermissionError,
    create_matrix_authorization_from_paths,
    derive_provider_permission,
    verify_matrix_authorization,
    verify_provider_permission,
)
from certvic.cvpr.run_contract import build_run_contract
from certvic.cvpr.scientific_input_builder import build_scientific_input
from certvic.cvpr.task_bundle import create_bundle
from certvic.cvpr.transactional import read_jsonl


PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")
ALIASES = {
    "qwen2_5_vl_7b": "qwen",
    "internvl_8b": "internvl",
    "llava_onevision_7b": "llava",
}
GLOBAL_PATH_ROLES = (
    "qa_enriched_manifest",
    "final_inclusion",
    "agreement",
    "rater_1_qualification",
    "rater_2_qualification",
    "rater_1_validation",
    "rater_2_validation",
    "adjudication",
    "study_config",
    "smoke_gate",
    "environment_lock",
    "model_registry",
    "code_bundle",
    "prompt_template",
    "output_schema",
)
PROVIDER_PATH_ROLES = ("smoke_return_zip",)


class PostReviewPipelineError(ValueError):
    """The genuine post-review continuation cannot pass its frozen gates."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _extract_unique_member(archive_path: Path, member_name: str, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise PostReviewPipelineError(f"unsafe or corrupt smoke return: {archive_path}")
        matches = [info for info in infos if Path(info.filename).name == member_name]
        if len(matches) != 1:
            raise PostReviewPipelineError(
                f"{archive_path.name}: expected one {member_name}, found {len(matches)}"
            )
        pure = PurePosixPath(matches[0].filename)
        mode = (matches[0].external_attr >> 16) & 0xFFFF
        if matches[0].is_dir() or pure.is_absolute() or ".." in pure.parts or stat.S_ISLNK(mode):
            raise PostReviewPipelineError(f"unsafe smoke member: {matches[0].filename}")
        payload = archive.read(matches[0])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _load_config(root: Path, config_path: str | Path) -> tuple[dict[str, Any], Path]:
    path = _resolve(root, config_path)
    if not path.is_file():
        raise PostReviewPipelineError(f"post-review pipeline config is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "certvic.phase_c.post_review_pipeline.v1":
        raise PostReviewPipelineError("post-review pipeline config schema mismatch")
    return value, path


def preflight(root: str | Path, config_path: str | Path) -> dict[str, Any]:
    base = Path(root).resolve()
    config, source = _load_config(base, config_path)
    paths = config.get("paths", {})
    missing: list[str] = []
    for role in GLOBAL_PATH_ROLES:
        value = paths.get(role)
        if not value or not _resolve(base, value).is_file():
            missing.append(role)
    provider_configs = config.get("providers", {})
    if set(provider_configs) != set(PROVIDERS):
        missing.append("providers:exact_three_provider_matrix")
    for provider in PROVIDERS:
        provider_config = provider_configs.get(provider, {})
        for role in PROVIDER_PATH_ROLES:
            value = provider_config.get(role)
            if not value or not _resolve(base, value).is_file():
                missing.append(f"providers.{provider}.{role}")
        if not provider_config.get("run_tag"):
            missing.append(f"providers.{provider}.run_tag")
    return {
        "schema": "certvic.phase_c.post_review_preflight.v1",
        "status": "READY" if not missing else "BLOCKED_MISSING_EXTERNAL_OR_REVIEW_INPUTS",
        "config": str(source),
        "missing_roles": sorted(missing),
        "paper_evidence": False,
    }


def _validate_genuine_review(paths: Mapping[str, Path]) -> tuple[dict[str, Any], dict[str, Any]]:
    values = {
        role: json.loads(paths[role].read_text(encoding="utf-8"))
        for role in (
            "final_inclusion",
            "agreement",
            "rater_1_qualification",
            "rater_2_qualification",
            "rater_1_validation",
            "rater_2_validation",
            "adjudication",
        )
    }
    final, agreement = values["final_inclusion"], values["agreement"]
    if final.get("status") != "FINAL_INCLUSION_VALIDATED":
        raise PostReviewPipelineError("final human-review state is not validated")
    if final.get("schema") != "certvic.cvpr.final_review_state.v2":
        raise PostReviewPipelineError("final human-review state lacks full v2 provenance")
    if agreement.get("rater_identities_distinct") is not True:
        raise PostReviewPipelineError("two independent reviewer identities were not proven")
    identities = set(agreement.get("rater_identity_hashes", {}).values())
    qualifications = [values["rater_1_qualification"], values["rater_2_qualification"]]
    if len(identities) != 2 or any(value.get("qualified") is not True for value in qualifications):
        raise PostReviewPipelineError("reviewer qualification or independence gate failed")
    if identities != {value.get("reviewer_identity_sha256") for value in qualifications}:
        raise PostReviewPipelineError("agreement identities differ from qualification identities")
    for role in ("rater_1_validation", "rater_2_validation"):
        if values[role].get("passed") is not True:
            raise PostReviewPipelineError(f"{role} did not pass")
    if values["adjudication"].get("passed") is not True or values["adjudication"].get(
        "all_disagreements_resolved"
    ) is not True:
        raise PostReviewPipelineError("adjudication is incomplete")
    ledger = final.get("ledger")
    if not isinstance(ledger, list) or final.get("final_ledger_sha256") != sha256_bytes(
        canonical_json_bytes(ledger)
    ):
        raise PostReviewPipelineError("final review ledger hash mismatch")
    return final, agreement


def _matrix(
    *,
    destination: Path,
    study: str,
    task_bundle_manifest: Path,
    bundle_root: Path,
    final_task_manifest: Path,
    final_review: Path,
    detectability_gate: Path,
    environment_lock: Path,
    model_registry: Path,
    code_bundle: Path,
    prompt_template: Path,
) -> dict[str, Any]:
    arguments = {
        "study": study,
        "task_bundle_manifest": task_bundle_manifest,
        "bundle_root": bundle_root,
        "final_task_manifest": final_task_manifest,
        "final_review": final_review,
        "detectability_gate": detectability_gate,
        "environment_lock": environment_lock,
        "model_registry": model_registry,
        "providers": list(PROVIDERS),
        "code_bundle": code_bundle,
        "prompt_template": prompt_template,
        "output_schema": "certvic.cvpr.output.v2",
    }
    if destination.is_file():
        try:
            existing = verify_matrix_authorization(destination)
            expected = create_matrix_authorization_from_paths(**arguments)
            binding_fields = (
                "study",
                "task_bundle_hash",
                "final_task_manifest_hash",
                "task_universe_sha256",
                "edited_image_hashes_hash",
                "review_hash",
                "detectability_hash",
                "environment_hash",
                "model_registry_hash",
                "providers",
                "code_hash",
                "prompt_template_hash",
                "output_schema",
            )
            if all(existing.get(field) == expected.get(field) for field in binding_fields):
                return existing
        except (ProviderPermissionError, OSError, ValueError, json.JSONDecodeError):
            pass
    return create_matrix_authorization_from_paths(**arguments, out=destination)


def _provider_permission(
    *,
    destination: Path,
    matrix_path: Path,
    matrix: Mapping[str, Any],
    provider: str,
    provider_config: Mapping[str, Any],
    smoke_row: Mapping[str, Any],
    active_paths: Mapping[str, Path],
    task_bundle_hash: str,
    run_contract_hash: str,
) -> dict[str, Any]:
    run_tag = str(provider_config["run_tag"])
    active_hashes = {role: _sha(path) for role, path in active_paths.items()}
    if destination.is_file():
        try:
            existing = verify_provider_permission(
                destination,
                matrix=matrix_path,
                expected_provider=provider,
                expected_run_tag=run_tag,
            )
            if existing.get("active_input_hashes") == active_hashes:
                return existing
        except (ProviderPermissionError, OSError, ValueError, json.JSONDecodeError):
            pass
    return derive_provider_permission(
        matrix,
        provider=provider,
        model_id=str(smoke_row["model_id"]),
        model_revision=str(smoke_row["model_revision"]),
        snapshot_hash=str(smoke_row["snapshot_manifest_hash"]),
        snapshot_root_hash=str(smoke_row["snapshot_root_hash"]),
        environment_hash=str(matrix["environment_hash"]),
        task_bundle_hash=task_bundle_hash,
        run_tag=run_tag,
        code_hash=str(matrix["code_hash"]),
        parser_version=str(smoke_row["parser_version"]),
        processor_model_contract=str(smoke_row["processor_model_contract"]),
        active_input_hashes=active_hashes,
        active_scalars={
            "schema_version": "certvic.cvpr.output.v2",
            "provider": provider,
            "run_tag": run_tag,
        },
        smoke_identity=smoke_row,
        run_contract_hash=run_contract_hash,
        prompt_template_hash=str(matrix["prompt_template_hash"]),
        out=destination,
    )


def run(root: str | Path, config_path: str | Path) -> dict[str, Any]:
    base = Path(root).resolve()
    config, config_source = _load_config(base, config_path)
    readiness = preflight(base, config_source)
    if readiness["status"] != "READY":
        return readiness
    paths = {role: _resolve(base, value) for role, value in config["paths"].items()}
    final_review, agreement = _validate_genuine_review(paths)
    output_root = _resolve(base, config.get(
        "output_root", "data/studies/specificity_confirmatory_cvpr"
    ))
    selection_root = output_root / "selection"
    selection_root.mkdir(parents=True, exist_ok=True)
    exit_code = select_main([
        "--qa-enriched-manifest", str(paths["qa_enriched_manifest"]),
        "--final-inclusion-ledger", str(paths["final_inclusion"]),
        "--config", str(paths["study_config"]),
        "--out-dir", str(selection_root),
        "--seed", str(config.get("selection_seed", 12013)),
    ])
    if exit_code:
        raise PostReviewPipelineError("exact deterministic candidate selection failed")
    selected = read_jsonl(selection_root / "selected_primary.jsonl")
    bundle_root = output_root / "task_bundle"
    bundle = create_bundle(selected, bundle_root, replace=True)
    final_tasks_path = bundle_root / "tasks.jsonl"
    bundle_manifest_path = bundle_root / "task_bundle_manifest.json"
    final_tasks = read_jsonl(final_tasks_path)
    import yaml

    study_config = yaml.safe_load(paths["study_config"].read_text(encoding="utf-8"))
    model_validation = validate_model_registry(load_yaml(paths["model_registry"]), for_execution=True)
    if not model_validation["passed"]:
        raise PostReviewPipelineError(
            "model registry is not execution-locked: " + "; ".join(model_validation["errors"])
        )
    threshold = float(study_config["design"]["set_level_symmetric_detectability_auc_max"])
    detectability = evaluate_detectability(
        final_tasks,
        bundle_root=bundle_root,
        threshold=threshold,
        folds=int(config.get("detectability_folds", 5)),
        bootstrap_samples=int(config.get("detectability_bootstrap_samples", 1000)),
        seed=int(config.get("detectability_seed", 17031)),
        final_task_manifest=final_tasks_path,
        task_bundle_manifest=bundle_manifest_path,
        study_config=paths["study_config"],
        qa_manifest=paths["qa_enriched_manifest"],
    )
    detectability_path = output_root / "detectability_gate.json"
    _write_json(detectability_path, detectability)
    if detectability["status"] != "DETECTABILITY_GATE_PASS":
        return {
            "schema": "certvic.phase_c.post_review_pipeline_status.v1",
            "status": "BLOCKED_FINAL_SELECTED_SET_DETECTABILITY_GATE",
            "detectability_gate": str(detectability_path),
            "refused_execution": True,
            "paper_evidence": False,
        }
    selection_freeze = json.loads(
        (selection_root / "final_task_freeze.json").read_text(encoding="utf-8")
    )
    freeze = {
        "schema": "certvic.cvpr.final_task_freeze.v1",
        "status": "FINAL_TASKS_FROZEN",
        "study": str(study_config["study_id"]),
        "primary_tasks_sha256": sha256_bytes(canonical_json_bytes(final_tasks)),
        "selection_sha256": selection_freeze["selection_sha256"],
        "review_artifact_sha256": final_review["final_artifact_sha256"],
        "task_bundle_hash": bundle["bundle_hash"],
        "detectability_gate_hash": detectability["gate_hash"],
        "paper_evidence": False,
    }
    freeze["freeze_hash"] = sha256_bytes(canonical_json_bytes(freeze))
    freeze_path = output_root / "final_task_freeze.json"
    _write_json(freeze_path, freeze)
    matrix_path = output_root / "execution_permission.json"
    matrix = _matrix(
        destination=matrix_path,
        study=str(study_config["study_id"]),
        task_bundle_manifest=bundle_manifest_path,
        bundle_root=bundle_root,
        final_task_manifest=final_tasks_path,
        final_review=paths["final_inclusion"],
        detectability_gate=detectability_path,
        environment_lock=paths["environment_lock"],
        model_registry=paths["model_registry"],
        code_bundle=paths["code_bundle"],
        prompt_template=paths["prompt_template"],
    )
    smoke = json.loads(paths["smoke_gate"].read_text(encoding="utf-8"))
    if smoke.get("status") != "REAL_MODEL_SMOKE_PASSED":
        raise PostReviewPipelineError("real-model smoke gate is not PASS")
    smoke_rows = {str(row.get("model")): row for row in smoke.get("models", [])}
    if set(smoke_rows) != set(PROVIDERS):
        raise PostReviewPipelineError("real-model smoke gate provider matrix mismatch")
    provider_results: list[dict[str, Any]] = []
    for provider in PROVIDERS:
        provider_config = config["providers"][provider]
        smoke_return = _resolve(base, provider_config["smoke_return_zip"])
        if _sha(smoke_return) != smoke_rows[provider].get("smoke_zip_sha256"):
            raise PostReviewPipelineError(f"{provider}: smoke return differs from the validated gate")
        binding_root = output_root / "smoke_bindings" / provider
        snapshot_manifest = binding_root / "snapshot_manifest.json"
        _extract_unique_member(smoke_return, "snapshot_manifest.json", snapshot_manifest)
        if _sha(snapshot_manifest) != smoke_rows[provider].get("snapshot_manifest_hash"):
            raise PostReviewPipelineError(f"{provider}: snapshot manifest differs from real smoke")
        snapshot = json.loads(snapshot_manifest.read_text(encoding="utf-8"))
        run_contract_value = build_run_contract(
            {
                "study": study_config["study_id"],
                "runtime_class": "SCIENTIFIC_RUN",
                "provider": provider,
                "model_id": smoke_rows[provider]["model_id"],
                "processor_id": snapshot.get("processor_id", smoke_rows[provider]["model_id"]),
                "model_commit": smoke_rows[provider]["model_revision"],
                "processor_commit": snapshot["processor_commit"],
                "model_snapshot_manifest_hash": _sha(snapshot_manifest),
                "processor_snapshot_manifest_hash": _sha(snapshot_manifest),
                "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
                "snapshot_contract": smoke_rows[provider]["processor_model_contract"],
                "environment_lock_hash": matrix["environment_hash"],
                "prompt_template_id": "certification_yes_no_v1",
                "prompt_template_hash": matrix["prompt_template_hash"],
                "parser_version": smoke_rows[provider]["parser_version"],
                "output_schema": "certvic.cvpr.output.v2",
                "run_tag": provider_config["run_tag"],
                "code_bundle_hash": matrix["code_hash"],
                "seed": int(config.get("run_seed", 12013)),
                "generation_parameters": {
                    "do_sample": False,
                    "temperature": 0.0,
                    "max_new_tokens": 16,
                },
            },
            task_manifest_sha256=sha256_bytes(canonical_json_bytes(final_tasks)),
            strict=True,
        )
        run_contract = binding_root / "run_contract.json"
        _write_json(run_contract, run_contract_value)
        permission_path = output_root / "permissions" / f"{provider}.json"
        active_paths = {
            "task_bundle_manifest": bundle_manifest_path,
            "freeze_manifest": freeze_path,
            "final_review": paths["final_inclusion"],
            "smoke_gate": paths["smoke_gate"],
            "environment_lock": paths["environment_lock"],
            "model_registry": paths["model_registry"],
            "snapshot_manifest": snapshot_manifest,
            "code_bundle": paths["code_bundle"],
            "study_config": paths["study_config"],
            "matrix_authorization": matrix_path,
        }
        permission = _provider_permission(
            destination=permission_path,
            matrix_path=matrix_path,
            matrix=matrix,
            provider=provider,
            provider_config=provider_config,
            smoke_row=smoke_rows[provider],
            active_paths=active_paths,
            task_bundle_hash=bundle["bundle_hash"],
            run_contract_hash=run_contract_value["run_contract_hash"],
        )
        roles = {
            "task_bundle": bundle_manifest_path,
            "task_freeze": freeze_path,
            "review_ledger": paths["final_inclusion"],
            "detectability_gate": detectability_path,
            "environment_lock": paths["environment_lock"],
            "model_registry": paths["model_registry"],
            "snapshot_manifest": snapshot_manifest,
            "code_bundle": paths["code_bundle"],
            "prompt_contract": paths["prompt_template"],
            "run_contract": run_contract,
            "parent_authorization": matrix_path,
            "child_permission": permission_path,
            "output_schema": paths["output_schema"],
        }
        built = build_scientific_input(
            "confirmatory",
            ALIASES[provider],
            roles,
            run_tag=str(provider_config["run_tag"]),
        )
        verification = verify_kaggle_bundle(built["path"])
        if not verification["passed"]:
            raise PostReviewPipelineError(f"{provider}: scientific input ZIP failed validation")
        provider_results.append({
            "provider": provider,
            "run_tag": provider_config["run_tag"],
            "permission_id": permission["permission_id"],
            "input_zip": built["path"],
            "size": built["size"],
            "sha256": built["sha256"],
            "notebook": built["manifest"]["required_notebook"],
            "dataset_slug": built["manifest"]["expected_kaggle_dataset_slug"],
            "mount_path": built["manifest"]["mount_path"],
        })
    capsule = {
        "schema": "certvic.phase_c.post_review_reproducibility_capsule.v1",
        "status": "COMPLETE_PRE_RUN",
        "study": study_config["study_id"],
        "task_bundle_hash": bundle["bundle_hash"],
        "task_freeze_hash": freeze["freeze_hash"],
        "final_review_sha256": _sha(paths["final_inclusion"]),
        "agreement_sha256": _sha(paths["agreement"]),
        "detectability_gate_hash": detectability["gate_hash"],
        "matrix_authorization_id": matrix["matrix_authorization_id"],
        "provider_input_sha256": {
            row["provider"]: row["sha256"] for row in provider_results
        },
        "paper_evidence": False,
    }
    capsule["capsule_hash"] = sha256_bytes(canonical_json_bytes(capsule))
    capsule_path = output_root / "post_review_reproducibility_capsule.json"
    _write_json(capsule_path, capsule)
    manifest_path = output_root / "confirmatory_kaggle_upload_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(provider_results[0]))
        writer.writeheader()
        writer.writerows(provider_results)
    handoff_path = output_root / "CONFIRMATORY_PROVIDER_RUN_HANDOFF.md"
    table = "\n".join(
        f"| {row['provider']} | `{row['input_zip']}` | `{row['sha256']}` | "
        f"`{row['dataset_slug']}` | `{row['notebook']}` |"
        for row in provider_results
    )
    handoff_path.write_text(
        "# Confirmatory provider run handoff\n\n"
        "All inputs below are frozen, permission-bound, and non-evidence until returned outputs "
        "are validated and imported. Use T4 x2 with Internet off.\n\n"
        "| Provider | Input ZIP | SHA-256 | Private dataset | Notebook |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{table}\n\n"
        "After all three canonical return ZIPs are copied unchanged to "
        "`local_inputs/provider_returns/specificity_confirmatory_cvpr/`, run:\n\n"
        "```bash\npython3 scripts/run_all_cpu_workflows.py "
        "--resume-after-confirmatory-returns\n```\n",
        encoding="utf-8",
    )
    status = {
        "schema": "certvic.phase_c.post_review_pipeline_status.v1",
        "status": "POST_REVIEW_CONFIRMATORY_INPUTS_READY",
        "reviewer_identities_distinct": agreement["rater_identities_distinct"],
        "selected_primary_tasks": len(final_tasks),
        "task_bundle": str(bundle_manifest_path),
        "detectability_gate": str(detectability_path),
        "matrix_authorization": str(matrix_path),
        "provider_inputs": provider_results,
        "reproducibility_capsule": str(capsule_path),
        "upload_manifest": str(manifest_path),
        "handoff": str(handoff_path),
        "paper_evidence": False,
    }
    _write_json(output_root / "post_review_pipeline_status.json", status)
    return status
