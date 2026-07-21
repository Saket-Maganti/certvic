"""Authoritative non-evidence proof for confirmatory, Main, and COCO joins."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from certvic.cvpr.analysis import human_aware_analysis, outcome_branch, write_human_aware_artifacts
from certvic.cvpr.candidate_selection import (
    SolverLimits,
    _exact_category_selection,
    balanced_select,
    bind_final_review,
)
from certvic.cvpr.confirmatory_qa import enrich
from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.execution_gate import authorize, verify_permission
from certvic.cvpr.generation import GenerationSettings, run_generation
from certvic.cvpr.negative_item_builder import build_negative_item
from certvic.cvpr.synthetic_study import _strict_synthetic_review, run as run_main_route
from certvic.cvpr.synthetic_smoke import PROVIDERS, run as run_strict_smoke
from certvic.cvpr.detectability_gate import evaluate as evaluate_detectability
from certvic.cvpr.model_snapshot_manifest import MANIFEST_NAME
from certvic.cvpr.package_run import package
from certvic.cvpr.permission_ledger import claim, initialize, status as permission_status
from certvic.cvpr.task_bundle import create_bundle
from certvic.cvpr.task_schema import require_task, with_task_hash
from certvic.cvpr.transactional import read_jsonl
from certvic.cvpr.whole_study_import import atomic_import_matrix
from certvic.cvpr.worker import run_shard
from certvic.cvpr.semantic_edits import SemanticEditSettings, generate_semantic_edit
from certvic.data.coco_adapter import build_feasibility_tasks


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _execute_synthetic_matrix(
    *,
    out: Path,
    study: str,
    run_tag: str,
    bundle_root: Path,
    review_path: Path,
    freeze_path: Path,
    smoke_result: dict[str, Any],
    detectability_path: Path | None,
) -> dict[str, Any]:
    providers = list(PROVIDERS)
    tasks_path = bundle_root / "tasks.jsonl"
    tasks = read_jsonl(tasks_path)
    registry = out / "model_registry.yaml"
    study_config = out / "study_config.yaml"
    _json(registry, {"primary_models": providers, "models": {name: {} for name in providers}})
    _json(
        study_config,
        {
            "schema": "certvic.cvpr.synthetic.v1",
            "study_id": study,
            "status": "SYNTHETIC_FIXTURE",
            "execution_allowed": False,
            "paper_evidence": False,
        },
    )
    smoke_root = Path(smoke_result["gate_json"]).parent
    environment = smoke_root / "00_environment_lock.json"
    smoke = Path(smoke_result["gate_json"])
    snapshots = {
        provider: smoke_root / "snapshots" / provider / MANIFEST_NAME for provider in providers
    }
    task_universe = sha256_bytes(
        canonical_json_bytes(sorted(str(task["task_id"]) for task in tasks))
    )
    ledger = out / "permission_ledger.json"
    initialize(
        ledger,
        study=study,
        providers=providers,
        run_tags=run_tag,
        task_universe_sha256=task_universe,
        output_schema="certvic.cvpr.output.v2",
        authorization_nonce=hashlib.sha256(f"{study}:synthetic-authorization".encode()).hexdigest(),
    )
    code_bundle = smoke_root / "synthetic_code_bundle.zip"
    code_hash = hashlib.sha256(code_bundle.read_bytes()).hexdigest()
    permission_path = out / "execution_permission.json"
    permission = authorize(
        study=study,
        smoke_gate_path=smoke,
        final_task_manifest=tasks_path,
        final_review_ledger=review_path,
        freeze_manifest=freeze_path,
        code_hash=code_hash,
        environment_lock=environment,
        model_registry=registry,
        study_config=study_config,
        out=permission_path,
        synthetic_fixture=True,
        task_bundle_manifest=bundle_root / "task_bundle_manifest.json",
        bundle_root=bundle_root,
        detectability_gate=detectability_path,
        permission_ledger=ledger,
        model_snapshot_manifests=snapshots,
        run_tags=run_tag,
    )
    input_paths: dict[str, Path] = {
        "smoke_gate": smoke,
        "final_tasks": tasks_path,
        "final_review": review_path,
        "freeze_manifest": freeze_path,
        "environment_lock": environment,
        "model_registry": registry,
        "study_config": study_config,
        "task_bundle_manifest": bundle_root / "task_bundle_manifest.json",
        "permission_ledger": ledger,
        **{f"model_snapshot_manifest:{provider}": path for provider, path in snapshots.items()},
    }
    if detectability_path is not None:
        input_paths["detectability_gate"] = detectability_path
    archives: dict[str, Path] = {}
    models: dict[str, dict[str, str]] = {}
    snapshot_hashes: dict[str, str] = {}
    for provider in providers:
        snapshot_path = snapshots[provider]
        snapshot = json.loads(snapshot_path.read_text())
        model = {
            key: str(snapshot[key]) for key in ("model_id", "model_commit", "processor_commit")
        }
        models[provider] = model
        snapshot_hashes[provider] = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        verify_permission(
            permission_path,
            study=study,
            allow_synthetic=True,
            input_paths=input_paths,
            expected_code_hash=code_hash,
            expected_provider=provider,
            expected_run_tag=run_tag,
            expected_output_schema="certvic.cvpr.output.v2",
        )
        claim(
            ledger,
            study=study,
            provider=provider,
            run_tag=run_tag,
            notebook=f"synthetic_{provider}_{study}.ipynb",
            task_universe_sha256=task_universe,
            permission_id=permission["permission_id"],
            permission_signature=permission["content_signature_sha256"],
        )
        runtime_path = out / "runtime" / f"{provider}.json"
        _json(
            runtime_path,
            {
                "study": study,
                "runtime_class": "SYNTHETIC_END_TO_END_FIXTURE",
                "provider": provider,
                "model_id": model["model_id"],
                "processor_id": model["model_id"],
                "model_commit": model["model_commit"],
                "processor_commit": model["processor_commit"],
                "model_path": str(snapshot_path.parent),
                "processor_path": str(snapshot_path.parent),
                "snapshot_manifest_path": str(snapshot_path),
                "expected_architecture": snapshot["expected_architecture"],
                "model_snapshot_manifest_hash": snapshot_hashes[provider],
                "processor_snapshot_manifest_hash": snapshot_hashes[provider],
                "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
                "snapshot_contract": "UNIFIED_SNAPSHOT",
                "environment_lock_path": str(environment),
                "environment_lock_hash": permission["input_hashes"]["environment_lock"],
                "prompt_template_id": f"{study}_yes_no_v1",
                "prompt_template": "{prompt}",
                "prompt_template_hash": hashlib.sha256(b"{prompt}").hexdigest(),
                "parser_version": "certvic.parse.v2",
                "output_schema": "certvic.cvpr.output.v2",
                "strict_run_contract": True,
                "strict_permission_binding": True,
                "run_tag": run_tag,
                "task_manifest": str(tasks_path),
                "task_bundle_root": str(bundle_root),
                "task_bundle_manifest": str(bundle_root / "task_bundle_manifest.json"),
                "output_dir": str(out / "runs" / provider),
                "code_bundle_hash": code_hash,
                "seed": 19101,
                "generation_parameters": {"do_sample": False, "max_new_tokens": 8},
                "execution_permission_path": str(permission_path),
                "execution_permission_id": permission["permission_id"],
                "execution_permission_signature": permission["content_signature_sha256"],
                "permission_input_paths": {key: str(value) for key, value in input_paths.items()},
                "permission_ledger_path": str(ledger),
                "notebook_name": f"synthetic_{provider}_{study}.ipynb",
            },
        )
        worker = run_shard(runtime_path, shard=0, num_shards=1, mock_runtime=True)
        if worker["status"] != "SHARD_COMPLETE":
            raise RuntimeError(f"synthetic matrix worker failed: {provider}: {worker}")
        packaged = package(runtime_path, expected_shards=1)
        archives[provider] = Path(str(packaged["zip"]))
    imported = out / "atomic_import"
    promotion = atomic_import_matrix(
        archives,
        study=study,
        run_tag=run_tag,
        model_contracts=models,
        tasks=tasks,
        expected_code_bundle_hash=code_hash,
        expected_snapshot_hashes=snapshot_hashes,
        expected_permission_id=permission["permission_id"],
        expected_permission_signature=permission["content_signature_sha256"],
        permission_ledger_path=ledger,
        bundle_root=bundle_root,
        destination_root=imported,
    )
    return {
        "tasks": tasks,
        "promotion": promotion,
        "permission": permission,
        "ledger": permission_status(ledger),
        "imported": imported,
        "provider_rows": {
            provider: read_jsonl(imported / "canonical" / f"{provider}.jsonl")
            for provider in providers
        },
    }


def _confirmatory_route(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    config = {
        "negative_item_policy": {
            "policy_id": "absent_category_protected_scene_v1",
            "control_edit_family": "structured_texture_patch",
            "minimum_distance_from_any_protected_region_px": 10,
            "perturbation_area_fraction": 0.00015,
            "image_boundary_margin_px": 4,
            "minimum_background_stddev": 1.0,
        }
    }
    candidate_tasks: list[dict[str, Any]] = []
    for index in range(12):
        source = out / "sources" / f"source_{index:02}.png"
        source.parent.mkdir(parents=True, exist_ok=True)
        rng = np.random.default_rng(19011 + index)
        image = Image.fromarray(
            rng.integers(0, 256, size=(256, 256, 3), dtype=np.uint8), mode="RGB"
        )
        image.save(source, format="PNG", compress_level=9)
        source_row = {
            "source_image_id": f"synthetic-confirmatory-source-{index:02}",
            "source_image_path": str(source),
            "source_dataset": "SYNTHETIC_FIXTURE",
            "split": "synthetic",
            "license_eligible": True,
            "license_status": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
            "text_protection_status": "OCR_VERIFIED_NO_TEXT",
            "annotations": [
                {
                    "annotation_id": f"protected-{index}",
                    "category": "chair",
                    "bbox": [96, 96, 160, 160],
                }
            ],
        }
        candidate_tasks.append(
            build_negative_item(
                out, source_row, "dog", out / "masks", config=config, seed=19011 + index
            )
        )
    generation_root = out / "generation"
    generated = run_generation(
        candidate_tasks,
        generation_root,
        GenerationSettings(
            engine="structured_texture_patch",
            seed=19011,
            area_fraction=0.00015,
            minimum_distance_px=10,
            minimum_changed_fraction=0.0001,
            maximum_changed_fraction=0.01,
        ),
        max_items=len(candidate_tasks),
        allow_full_run=False,
        dry_run=False,
    )
    qa_config = {
        "design": {
            "perturbation_area_fraction": {"minimum": 0.0001, "maximum": 0.01},
            "minimum_distance_from_target_px": 10,
            "salience_score_range": {"minimum": 0.0, "maximum": 1.0},
        }
    }
    qa = enrich(candidate_tasks, generation_root, qa_config)
    if qa["passed"] != len(candidate_tasks):
        raise RuntimeError("synthetic confirmatory QA did not pass the complete candidate set")
    generated_map = {str(row["item_id"]): row for row in generated["rows"]}
    review_tasks = [
        with_task_hash(
            {
                **task,
                "original_image_path": str(task["source_image_path"]),
                "edited_image_path": str(generated_map[str(task["item_id"])]["output_image_path"]),
            }
        )
        for task in candidate_tasks
    ]
    agreement, review = _strict_synthetic_review(
        review_tasks, out / "review", track="specificity_confirmatory_cvpr"
    )
    reviewed, review_exclusions, review_proof = bind_final_review(qa["rows"], review)
    selection_config = {
        "selection_requirements": {
            "require_qa_enriched_manifest": True,
            "require_license_eligible": False,
            "require_generation_qa": True,
            "require_salience_review": True,
            "require_detectability_review": True,
        },
        "design": {
            "category_targets": {
                "dog": {
                    "primary": 8,
                    "reserve": 4,
                    "expected_answer_polarities": {"primary": {"no": 8}, "reserve": {"no": 4}},
                    "size_strata": {
                        "primary": {"background_control": 8},
                        "reserve": {"background_control": 4},
                    },
                    "position_strata": {
                        "primary": {"protected_scene_safe": 8},
                        "reserve": {"protected_scene_safe": 4},
                    },
                }
            }
        },
    }
    selection = balanced_select(reviewed, selection_config, seed=19011)
    if selection["status"] != "BALANCED_SELECTION_COMPLETE" or review_exclusions:
        raise RuntimeError("synthetic confirmatory exact selection did not close")
    task_map = {str(row["task_id"]): row for row in review_tasks}
    final_absolute = [
        require_task(
            with_task_hash(
                {
                    **task_map[str(row["item_id"])],
                    "study": "synthetic_confirmatory",
                    "qa_status": "PASS",
                    "review_status": "VALID_ADJUDICATED",
                    "primary_or_reserve": row["selection_role"],
                    "review_provenance": review_proof,
                }
            ),
            verify_files=True,
        )
        for row in selection["primary"] + selection["reserve"]
    ]
    bundle_root = out / "task_bundle"
    create_bundle(final_absolute, bundle_root)
    final_tasks_path = bundle_root / "tasks.jsonl"
    final_tasks = read_jsonl(final_tasks_path)
    detectability = evaluate_detectability(
        final_tasks,
        bundle_root=bundle_root,
        threshold=0.80,
        folds=4,
        bootstrap_samples=200,
        seed=19031,
    )
    if detectability["status"] != "DETECTABILITY_GATE_PASS":
        raise RuntimeError(f"synthetic confirmatory detectability failed: {detectability}")
    detectability_path = out / "detectability_gate.json"
    _json(detectability_path, detectability)
    freeze = {
        "schema": "certvic.cvpr.final_task_freeze.v1",
        "status": "FINAL_TASKS_FROZEN",
        "study": "synthetic_confirmatory",
        "primary_tasks_sha256": sha256_bytes(canonical_json_bytes(final_tasks)),
        "selection_sha256": selection["selection_sha256"],
        "review_artifact_sha256": review["final_artifact_sha256"],
        "paper_evidence": False,
    }
    freeze["freeze_hash"] = sha256_bytes(canonical_json_bytes(freeze))
    freeze_path = out / "freeze_manifest.json"
    _json(freeze_path, freeze)
    smoke_result = run_strict_smoke(out / "strict_smoke")
    environment = out / "strict_smoke/00_environment_lock.json"
    registry = out / "model_registry.yaml"
    study_config = out / "study_config.yaml"
    smoke = Path(smoke_result["gate_json"])
    review_path = out / "review/final_inclusion.json"
    providers = list(PROVIDERS)
    _json(registry, {"primary_models": providers, "models": {name: {} for name in providers}})
    _json(
        study_config,
        {
            "schema": "certvic.cvpr.synthetic.v1",
            "study_id": "synthetic_confirmatory",
            "status": "SYNTHETIC_FIXTURE",
            "execution_allowed": False,
            "paper_evidence": False,
        },
    )
    run_tag = "synthetic_confirmatory_v1"
    task_universe_hash = sha256_bytes(
        canonical_json_bytes(sorted(str(task["task_id"]) for task in final_tasks))
    )
    ledger_path = out / "permission_ledger.json"
    initialize(
        ledger_path,
        study="synthetic_confirmatory",
        providers=providers,
        run_tags=run_tag,
        task_universe_sha256=task_universe_hash,
        output_schema="certvic.cvpr.output.v2",
        authorization_nonce=hashlib.sha256(b"SYNTHETIC_CONFIRMATORY_AUTHORIZATION").hexdigest(),
    )
    snapshot_manifests = {
        provider: out / "strict_smoke/snapshots" / provider / MANIFEST_NAME
        for provider in providers
    }
    code_bundle = out / "strict_smoke/synthetic_code_bundle.zip"
    code_hash = hashlib.sha256(code_bundle.read_bytes()).hexdigest()
    permission_path = out / "execution_permission.json"
    permission = authorize(
        study="synthetic_confirmatory",
        smoke_gate_path=smoke,
        final_task_manifest=final_tasks_path,
        final_review_ledger=review_path,
        freeze_manifest=freeze_path,
        code_hash=code_hash,
        environment_lock=environment,
        model_registry=registry,
        study_config=study_config,
        out=permission_path,
        synthetic_fixture=True,
        task_bundle_manifest=bundle_root / "task_bundle_manifest.json",
        bundle_root=bundle_root,
        detectability_gate=detectability_path,
        permission_ledger=ledger_path,
        model_snapshot_manifests=snapshot_manifests,
        run_tags=run_tag,
    )
    input_paths = {
        "smoke_gate": smoke,
        "final_tasks": final_tasks_path,
        "final_review": review_path,
        "freeze_manifest": freeze_path,
        "environment_lock": environment,
        "model_registry": registry,
        "study_config": study_config,
        "task_bundle_manifest": bundle_root / "task_bundle_manifest.json",
        "detectability_gate": detectability_path,
        "permission_ledger": ledger_path,
        **{
            f"model_snapshot_manifest:{provider}": path
            for provider, path in snapshot_manifests.items()
        },
    }
    verify_permission(
        permission_path,
        study="synthetic_confirmatory",
        allow_synthetic=True,
        input_paths=input_paths,
        expected_code_hash=code_hash,
        expected_provider=providers[0],
        expected_run_tag=run_tag,
        expected_output_schema="certvic.cvpr.output.v2",
    )
    archives: dict[str, Path] = {}
    models: dict[str, dict[str, str]] = {}
    snapshot_hashes: dict[str, str] = {}
    for provider in providers:
        snapshot_path = snapshot_manifests[provider]
        snapshot = json.loads(snapshot_path.read_text())
        model = {
            key: str(snapshot[key]) for key in ("model_id", "model_commit", "processor_commit")
        }
        models[provider] = model
        snapshot_hashes[provider] = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        claim(
            ledger_path,
            study="synthetic_confirmatory",
            provider=provider,
            run_tag=run_tag,
            notebook=f"synthetic_{provider}_confirmatory.ipynb",
            task_universe_sha256=task_universe_hash,
            permission_id=permission["permission_id"],
            permission_signature=permission["content_signature_sha256"],
        )
        runtime_path = out / "runtime" / f"{provider}.json"
        runtime = {
            "study": "synthetic_confirmatory",
            "runtime_class": "SYNTHETIC_END_TO_END_FIXTURE",
            "provider": provider,
            "model_id": model["model_id"],
            "processor_id": model["model_id"],
            "model_commit": model["model_commit"],
            "processor_commit": model["processor_commit"],
            "model_path": str(snapshot_path.parent),
            "processor_path": str(snapshot_path.parent),
            "snapshot_manifest_path": str(snapshot_path),
            "expected_architecture": snapshot["expected_architecture"],
            "model_snapshot_manifest_hash": snapshot_hashes[provider],
            "processor_snapshot_manifest_hash": snapshot_hashes[provider],
            "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
            "snapshot_contract": "UNIFIED_SNAPSHOT",
            "environment_lock_path": str(environment),
            "environment_lock_hash": permission["input_hashes"]["environment_lock"],
            "prompt_template_id": "synthetic_confirmatory_yes_no_v1",
            "prompt_template": "{prompt}",
            "prompt_template_hash": hashlib.sha256(b"{prompt}").hexdigest(),
            "parser_version": "certvic.parse.v2",
            "output_schema": "certvic.cvpr.output.v2",
            "strict_run_contract": True,
            "strict_permission_binding": True,
            "run_tag": run_tag,
            "task_manifest": str(final_tasks_path),
            "task_bundle_root": str(bundle_root),
            "task_bundle_manifest": str(bundle_root / "task_bundle_manifest.json"),
            "output_dir": str(out / "runs" / provider),
            "code_bundle_hash": code_hash,
            "seed": 19041,
            "generation_parameters": {"do_sample": False, "max_new_tokens": 8},
            "execution_permission_path": str(permission_path),
            "execution_permission_id": permission["permission_id"],
            "execution_permission_signature": permission["content_signature_sha256"],
            "permission_input_paths": {key: str(value) for key, value in input_paths.items()},
            "permission_ledger_path": str(ledger_path),
            "notebook_name": f"synthetic_{provider}_confirmatory.ipynb",
        }
        _json(runtime_path, runtime)
        worker = run_shard(runtime_path, shard=0, num_shards=1, mock_runtime=True)
        if worker["status"] != "SHARD_COMPLETE":
            raise RuntimeError(f"synthetic confirmatory worker failed: {provider}: {worker}")
        packaged = package(runtime_path, expected_shards=1)
        archives[provider] = Path(str(packaged["zip"]))
    imported = out / "atomic_import"
    promotion = atomic_import_matrix(
        archives,
        study="synthetic_confirmatory",
        run_tag=run_tag,
        model_contracts=models,
        tasks=final_tasks,
        expected_code_bundle_hash=code_hash,
        expected_snapshot_hashes=snapshot_hashes,
        destination_root=imported,
        expected_permission_id=permission["permission_id"],
        expected_permission_signature=permission["content_signature_sha256"],
        permission_ledger_path=ledger_path,
        bundle_root=bundle_root,
    )
    provider_rows = {
        provider: read_jsonl(imported / "canonical" / f"{provider}.jsonl") for provider in providers
    }
    analysis = human_aware_analysis(
        provider_rows,
        final_tasks,
        final_inclusion=review,
        agreement=agreement,
        study_kind="specificity_confirmatory_cvpr",
    )
    artifacts = write_human_aware_artifacts(out / "analysis", analysis)
    branch = outcome_branch(analysis["adjudicated_filtered_analysis"], human_invalidation_rate=0.0)
    outcome = {
        "schema": "certvic.cvpr.synthetic_confirmatory_outcome.v1",
        "status": "SYNTHETIC_CONFIRMATORY_OUTCOME_EVALUATED",
        "active_outcome_branch": branch["active_branch"],
        "main_go_no_go": (
            "GO_SYNTHETIC_ROUTE_ONLY"
            if branch["active_branch"] == "ALL_MODELS_PASS"
            else "NO_GO_SYNTHETIC_LOW_N_OR_FAILURE_BRANCH"
        ),
        "permission_ledger_states": {
            provider: slot["state"]
            for provider, slot in permission_status(ledger_path)["slots"].items()
        },
        "paper_evidence": False,
    }
    outcome["content_signature_sha256"] = sha256_bytes(canonical_json_bytes(outcome))
    _json(out / "confirmatory_outcome_and_main_go_no_go.json", outcome)
    return {
        "status": "SYNTHETIC_CONFIRMATORY_ROUTE_COMPLETE",
        "negative_items": len(final_tasks),
        "qa_passed": qa["passed"],
        "review_included": len(review["included"]),
        "selection_status": selection["status"],
        "permission_id": permission["permission_id"],
        "smoke_status": smoke_result["status"],
        "detectability_status": detectability["status"],
        "atomic_import_status": promotion["status"],
        "analysis_artifacts": artifacts,
        "main_go_no_go": outcome["main_go_no_go"],
        "agreement_schema": agreement["schema"],
        "paper_evidence": False,
        "human_reviewed": False,
    }


def _coco_route(out: Path) -> dict[str, Any]:
    root = out / "coco"
    (root / "annotations").mkdir(parents=True)
    (root / "val2017").mkdir()
    categories = [
        {"id": 1, "name": "chair"},
        {"id": 2, "name": "couch"},
        {"id": 3, "name": "car"},
        {"id": 4, "name": "dining table"},
    ]
    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    for image_id in range(1, 61):
        filename = f"{image_id:012}.jpg"
        rng = np.random.default_rng(20000 + image_id)
        array = rng.integers(0, 180, size=(384, 384, 3), dtype=np.uint8)
        if image_id <= 30:
            array[96:192, 96:192] = np.asarray([245, 225, 40], dtype=np.uint8)
        Image.fromarray(array, mode="RGB").save(root / "val2017" / filename, quality=95)
        images.append(
            {"id": image_id, "file_name": filename, "width": 384, "height": 384, "license": 1}
        )
        if image_id <= 30:
            category_id = (image_id - 1) % 4 + 1
            annotations.append(
                {
                    "id": image_id,
                    "image_id": image_id,
                    "category_id": category_id,
                    "iscrowd": 0,
                    "area": 9216,
                    "bbox": [96, 96, 96, 96],
                    "segmentation": [[96, 96, 192, 96, 192, 192, 96, 192]],
                }
            )
    _json(
        root / "annotations/instances_val2017.json",
        {
            "images": images,
            "annotations": annotations,
            "categories": categories,
            "licenses": [{"id": 1, "name": "synthetic", "url": "https://example.invalid"}],
        },
    )
    asset = out / "synthetic_insertion_asset.png"
    asset_image = Image.new("RGBA", (64, 64), (20, 210, 240, 255))
    asset_image.save(asset)
    asset_hash = hashlib.sha256(asset.read_bytes()).hexdigest()
    asset_manifest = out / "synthetic_asset_manifest.json"
    _json(
        asset_manifest,
        {
            "categories": {
                category: {
                    "path": str(asset),
                    "sha256": asset_hash,
                    "license_eligible": True,
                    "license": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
                }
                for category in ("chair", "sofa", "car", "table")
            }
        },
    )
    result = build_feasibility_tasks(
        root,
        out_dir=out / "built",
        items=60,
        seed=19021,
        insertion_asset_manifest=asset_manifest,
    )
    if result["selected_items"] != 60:
        raise RuntimeError(f"synthetic COCO-60 construction shortage: {result}")
    candidates = read_jsonl(out / "built/coco_feasibility_candidates.jsonl")
    generation_records: list[dict[str, Any]] = []
    review_tasks: list[dict[str, Any]] = []
    for index, task in enumerate(candidates):
        family = str(task["semantic_edit_family"])
        updated = with_task_hash(
            {
                **task,
                "study": "synthetic_coco",
                "license_status": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
                "license_eligible": True,
                "deterministic_simple_case_verified": family == "object_removal",
                "selected_engine": (
                    "deterministic_context_fill_preliminary_v1"
                    if family == "object_removal"
                    else "hash_locked_asset_composite_v1"
                ),
                "insertion_asset_path": str(asset) if family == "object_insertion" else None,
                "insertion_asset_sha256": asset_hash if family == "object_insertion" else None,
                "insertion_asset_license": (
                    "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE"
                    if family == "object_insertion"
                    else "NOT_APPLICABLE"
                ),
            }
        )
        edited = out / "generation/images" / f"{updated['task_id']}.png"
        record = generate_semantic_edit(updated, edited, SemanticEditSettings(19021 + index))
        if record["quality"]["automated_qa_status"] != "PASS":
            raise RuntimeError(f"synthetic COCO semantic QA failed: {updated['task_id']}")
        generation_records.append(record)
        review_tasks.append(
            with_task_hash(
                {
                    **updated,
                    "original_image_path": updated["source_image_path"],
                    "edited_image_path": str(edited),
                    "qa_status": "PASS",
                }
            )
        )
    _json(
        out / "generation/semantic_generation_manifest.json",
        {
            "schema": "certvic.cvpr.synthetic_coco_generation.v1",
            "status": "QA_PASS",
            "records": generation_records,
            "paper_evidence": False,
        },
    )
    agreement, review = _strict_synthetic_review(
        review_tasks, out / "review", track="second_domain_cvpr"
    )
    reviewed, exclusions, review_proof = bind_final_review(review_tasks, review)
    if exclusions:
        raise RuntimeError("synthetic COCO review unexpectedly excluded a task")
    for row in reviewed:
        row.update(
            {
                "selection_category": str(row.get("target_category", row.get("category"))),
                "answer_transition": f"{row['original_expected_answer']}_to_{row['edited_expected_answer']}",
            }
        )
    family_counts = dict(Counter(str(row["semantic_edit_family"]) for row in reviewed))
    category_counts = dict(Counter(str(row["selection_category"]) for row in reviewed))
    primary, reserve, solver = _exact_category_selection(
        reviewed,
        {
            "primary": 60,
            "reserve": 0,
            "max_per_source": 1,
            "edit_family_balance": {"primary": family_counts},
            "category_balance": {"primary": category_counts},
        },
        seed=19021,
        limits=SolverLimits(max_states=250_000, timeout_seconds=30),
    )
    if not solver.get("feasible") or reserve:
        raise RuntimeError(f"synthetic COCO exact selection failed: {solver}")
    task_map = {str(task["task_id"]): task for task in review_tasks}
    final_absolute = [
        require_task(
            with_task_hash(
                {
                    **task_map[str(row["task_id"])],
                    "primary_or_reserve": "primary",
                    "review_status": "VALID_ADJUDICATED",
                    "qa_status": "PASS",
                    "review_provenance": review_proof,
                }
            ),
            verify_files=True,
        )
        for row in primary
    ]
    bundle_root = out / "task_bundle"
    create_bundle(final_absolute, bundle_root)
    final_tasks = read_jsonl(bundle_root / "tasks.jsonl")
    freeze = {
        "schema": "certvic.cvpr.synthetic_coco_freeze.v1",
        "status": "FINAL_TASKS_FROZEN",
        "study": "synthetic_coco",
        "primary_tasks_sha256": sha256_bytes(canonical_json_bytes(final_tasks)),
        "review_artifact_sha256": review["final_artifact_sha256"],
        "solver_version": solver["solver_version"],
        "paper_evidence": False,
    }
    freeze["freeze_hash"] = sha256_bytes(canonical_json_bytes(freeze))
    freeze_path = out / "freeze_manifest.json"
    _json(freeze_path, freeze)
    # COCO edits intentionally change semantics; this diagnostic informs the
    # expansion decision but is not the irrelevant-edit authorization gate.
    detectability = evaluate_detectability(
        final_tasks,
        bundle_root=bundle_root,
        threshold=0.80,
        folds=5,
        bootstrap_samples=200,
        seed=19071,
    )
    _json(out / "feasibility_detectability.json", detectability)
    smoke_result = run_strict_smoke(out / "strict_smoke")
    matrix = _execute_synthetic_matrix(
        out=out,
        study="synthetic_coco",
        run_tag="synthetic_coco_v1",
        bundle_root=bundle_root,
        review_path=out / "review/final_inclusion.json",
        freeze_path=freeze_path,
        smoke_result=smoke_result,
        detectability_path=None,
    )
    analysis = human_aware_analysis(
        matrix["provider_rows"],
        matrix["tasks"],
        final_inclusion=review,
        agreement=agreement,
        study_kind="second_domain_cvpr",
    )
    artifacts = write_human_aware_artifacts(out / "analysis", analysis)
    from certvic.cvpr.analysis import second_domain_decision

    expansion = second_domain_decision(
        analysis["adjudicated_filtered_analysis"],
        edit_success=len(generation_records) / 60,
        human_valid=len(review["included"]) / 60,
        detectability_auc=float(detectability["symmetric_detectability_auc"]),
    )
    _json(out / "expansion_decision.json", expansion)
    return {
        **result,
        "status": "SYNTHETIC_COCO_FEASIBILITY_COMPLETE",
        "selected_items": len(final_tasks),
        "qa_passed": len(generation_records),
        "review_included": len(review["included"]),
        "exact_selection": solver["feasible"],
        "smoke_status": smoke_result["status"],
        "atomic_import_status": matrix["promotion"]["status"],
        "permission_states": {
            provider: slot["state"] for provider, slot in matrix["ledger"]["slots"].items()
        },
        "analysis_artifacts": artifacts,
        "expansion_decision": expansion["decision"],
        "runtime_class": "SYNTHETIC_END_TO_END_FIXTURE",
        "paper_evidence": False,
    }


def run(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    if out.exists() and any(out.iterdir()):
        raise ValueError("synthetic closure output directory must be new or empty")
    out.mkdir(parents=True, exist_ok=True)
    confirmatory = _confirmatory_route(out / "confirmatory")
    main = run_main_route(out / "main")
    coco = _coco_route(out / "coco_route")
    result = {
        "schema": "certvic.cvpr.absolute_final_synthetic_closure.v1",
        "status": "SYNTHETIC_ALL_STUDY_ROUTES_COMPLETE",
        "runtime_class": "SYNTHETIC_END_TO_END_FIXTURE",
        "routes": {"confirmatory": confirmatory, "main": main, "coco": coco},
        "paper_evidence": False,
        "human_reviewed": False,
    }
    _json(out / "synthetic_closure_status.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run all non-evidence CVPR synthetic routes")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    result = run(args.out_dir)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
