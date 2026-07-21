from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image

from certvic.cvpr.candidate_selection import SolverLimits, balanced_select
from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.execution_gate import ExecutionAuthorizationError, authorize, verify_permission
from certvic.cvpr.generation import GenerationSettings, run_generation
from certvic.cvpr.main_task_builder import build_tasks
from certvic.cvpr.negative_item_builder import NegativeItemError, build_negative_item
from certvic.cvpr.notebook_builder import NOTEBOOKS, build_suite
from certvic.cvpr.package_generation import assemble_generation_shards, package_generation
from certvic.cvpr.semantic_edits import SemanticEditSettings, generate_semantic_edit
from certvic.cvpr.smoke_gate import evaluate
from certvic.cvpr.synthetic_closure import run as run_synthetic_closure
from certvic.cvpr.task_schema import TaskSchemaError, require_task, with_task_hash


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pattern(path: Path, size: int = 256) -> None:
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    for y in range(size):
        for x in range(size):
            pixels[x, y] = ((x + 3 * y) % 180, (2 * x + y) % 160, (x + y) % 140)
    image.save(path)


def _negative_fixture(tmp_path: Path) -> tuple[dict, dict]:
    source = tmp_path / "negative_source.png"
    _pattern(source)
    row = {
        "source_image_id": "negative-source", "source_image_path": str(source),
        "source_dataset": "SYNTHETIC_FIXTURE", "split": "synthetic",
        "license_eligible": True,
        "license_status": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
        "text_protection_status": "OCR_VERIFIED_NO_TEXT",
        "annotations": [{"annotation_id": "chair-1", "category": "chair",
                         "bbox": [96, 96, 160, 160]}],
    }
    config = {"negative_item_policy": {
        "policy_id": "absent_category_protected_scene_v1",
        "control_edit_family": "structured_texture_patch",
        "minimum_distance_from_any_protected_region_px": 10,
        "perturbation_area_fraction": 0.01, "image_boundary_margin_px": 4,
        "minimum_background_stddev": 1.0,
    }}
    return row, config


def test_canonical_schema_tampering_and_mixed_rows_fail_closed(tmp_path: Path) -> None:
    row, config = _negative_fixture(tmp_path)
    task = build_negative_item(tmp_path, row, "dog", tmp_path / "masks", config=config, seed=11)
    assert require_task(task, verify_files=True)["task_schema_version"] == "certvic.cvpr.task.v1"
    with pytest.raises(TaskSchemaError, match="task_hash"):
        require_task({**task, "question": "tampered"})
    with pytest.raises(TaskSchemaError, match="missing canonical fields"):
        require_task({"item_id": "legacy"})


def test_main_builder_all_families_run_directly_through_generator(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _pattern(source, 64)
    image = Image.open(source).convert("RGB")
    for y in range(16, 48):
        for x in range(16, 48):
            image.putpixel((x, y), (230, 10, 20))
    image.save(source)
    mask = Image.new("L", (64, 64), 0)
    for y in range(16, 48):
        for x in range(16, 48):
            mask.putpixel((x, y), 255)
    mask_path = tmp_path / "mask.png"
    mask.save(mask_path)
    asset = tmp_path / "dog.png"
    Image.new("RGBA", (16, 16), (30, 80, 220, 255)).save(asset)
    sources = [{
        "source_image_id": "source-1", "source_image_path": str(source),
        "source_sha256": _sha(source), "source_dataset": "SYNTHETIC_FIXTURE",
        "split": "synthetic", "license_eligible": True,
        "license_status": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
        "annotations": [{"annotation_id": "chair-1", "category": "chair",
                         "bbox": [16, 16, 48, 48], "mask_path": str(mask_path),
                         "mask_sha256": _sha(mask_path),
                         "deterministic_simple_case_verified": True,
                         "verified_attributes": {"color": {
                             "from": "red", "to": "blue", "verified": True,
                         }}}],
    }]
    config = {
        "seed": 19,
        "semantic_interventions": {"allowed_families": [
            "object_removal", "object_insertion", "attribute_modification"
        ]},
        "task_builder": {
            "supported_categories": ["chair", "dog"],
            "family_candidate_targets": {
                "object_removal": 1, "object_insertion": 1, "attribute_modification": 1,
            },
            "insertion_assets": {"dog": {
                "path": str(asset), "sha256": _sha(asset), "license_eligible": True,
                "license": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
            }},
        },
    }
    built = build_tasks(tmp_path, sources, config)
    assert built["status"] == "MAIN_CANDIDATE_TASKS_BUILT"
    assert {task["semantic_edit_family"] for task in built["tasks"]} == {
        "object_removal", "object_insertion", "attribute_modification"
    }
    for index, task in enumerate(built["tasks"]):
        record = generate_semantic_edit(
            task, tmp_path / "edits" / f"{task['task_id']}.png",
            SemanticEditSettings(20 + index),
        )
        assert record["quality"]["automated_qa_status"] == "PASS"
        assert record["final_engine_used"] == task["selected_engine"]


def test_negative_policy_protects_scene_and_rejects_present_or_unprotected_text(tmp_path: Path) -> None:
    row, config = _negative_fixture(tmp_path)
    task = build_negative_item(tmp_path, row, "dog", tmp_path / "masks", config=config, seed=23)
    assert task["queried_category_absent"] is True
    assert task["background_region_validation"]["status"] == "PASS"
    assert Path(task["protected_scene_mask_path"]).is_file()
    with pytest.raises(NegativeItemError, match="present"):
        build_negative_item(tmp_path, row, "chair", tmp_path / "present", config=config, seed=23)
    with pytest.raises(NegativeItemError, match="text"):
        build_negative_item(
            tmp_path, {**row, "text_protection_status": "UNKNOWN"}, "dog",
            tmp_path / "text", config=config, seed=23,
        )


def test_generation_shards_are_assembled_and_strictly_packaged(tmp_path: Path) -> None:
    row, config = _negative_fixture(tmp_path)
    task = build_negative_item(tmp_path, row, "dog", tmp_path / "masks", config=config, seed=29)
    root = tmp_path / "generation"
    run_generation(
        [task], root / "generation_shard_0",
        GenerationSettings("structured_texture_patch", 29, area_fraction=0.01,
                           minimum_distance_px=10, minimum_changed_fraction=0.001,
                           maximum_changed_fraction=0.05),
        max_items=1, allow_full_run=False, dry_run=False,
    )
    assembled = assemble_generation_shards(
        [task], root, run_contract={"run_contract_hash": "a" * 64},
        environment_manifest={"status": "SYNTHETIC_EXACT_ENVIRONMENT"},
        runtime_manifest={"schema": "certvic.cvpr.generation_runtime.v1"},
    )
    assert assembled["records"] == 1
    packaged = package_generation([task], root, tmp_path / "generation.zip", strict=True)
    assert packaged["status"] == "GENERATION_PACKAGE_VALIDATED_AND_WRITTEN"
    assert packaged["deterministic_rebuild"] is True


def _strict_smoke(tmp_path: Path) -> tuple[dict, str]:
    provider = "fixture_provider"
    environment_hash = "1" * 64
    code_hash = "2" * 64
    prompt_hash = "3" * 64
    run_hash = "4" * 64
    model_commit = "5" * 40
    processor_commit = "6" * 40
    model_id = "fixture/model"
    snapshot_payload = {"model_id": model_id, "model_commit": model_commit}
    snapshot_bytes = (json.dumps(snapshot_payload, indent=2, sort_keys=True) + "\n").encode()
    snapshot_hash = hashlib.sha256(snapshot_bytes).hexdigest()
    (tmp_path / "00A_environment.json").write_text(json.dumps({
        "status": "EXACT_PREINSTALLED_ENVIRONMENT_ACCEPTED", "passed": True,
        "environment_hash": environment_hash,
    }))
    (tmp_path / f"00B_{provider}_snapshot.json").write_text(json.dumps({
        "passed": True, "snapshot_contract": "UNIFIED_SNAPSHOT",
        "manifest_sha256": snapshot_hash,
    }))
    fixture_rows = []
    rows = []
    for item in ("smoke-1", "smoke-2"):
        for variant in ("original", "edited"):
            expected = {
                "item_id": item, "variant": variant,
                "task_hash": hashlib.sha256(f"task:{item}".encode()).hexdigest(),
                "image_hash": hashlib.sha256(f"image:{item}:{variant}".encode()).hexdigest(),
                "prompt_hash": prompt_hash,
            }
            fixture_rows.append(expected)
            rows.append({
                **expected, "provider": provider, "model_id": model_id,
                "model_commit": model_commit, "processor_commit": processor_commit,
                "parser_version": "certvic.parse.v2", "code_bundle_hash": code_hash,
                "model_snapshot_manifest_hash": snapshot_hash, "run_contract_hash": run_hash,
                "parse_status": "PARSE_OK", "output_schema": "certvic.cvpr.output.v2",
            })
    raw = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()
    members = {
        "merged_raw.jsonl": raw,
        "runtime_manifest.json": (json.dumps({
            "status": "COMPLETE", "runtime_class": "NON_EVIDENCE_REAL_MODEL_SMOKE",
            "provider": provider, "model_id": model_id, "model_commit": model_commit,
            "processor_commit": processor_commit, "peak_vram_gib": 7.5, "oom_events": 0,
            "unresolved_warnings": [], "environment_hash": environment_hash,
            "snapshot_manifest_hash": snapshot_hash, "code_bundle_hash": code_hash,
            "prompt_template_hash": prompt_hash, "parser_version": "certvic.parse.v2",
            "run_contract_hash": run_hash,
            "raw_prediction_sha256": hashlib.sha256(raw).hexdigest(),
        }, sort_keys=True) + "\n").encode(),
        "environment_manifest.json": (json.dumps({
            "environment_hash": environment_hash
        }, sort_keys=True) + "\n").encode(),
        "snapshot_manifest.json": snapshot_bytes,
        "validation_report.json": (json.dumps({
            "passed": True, "validation_source": "RECOMPUTED_FROM_RETURNED_BYTES"
        }, sort_keys=True) + "\n").encode(),
        "failure_report.json": b'{"count": 0, "failures": []}\n',
        "cleanup_report.json": b'{"model_released": true, "status": "PASS"}\n',
        "run_contract.json": (json.dumps({
            "run_contract_hash": run_hash
        }, sort_keys=True) + "\n").encode(),
    }
    members["hash_manifest.json"] = (json.dumps({
        name: hashlib.sha256(payload).hexdigest() for name, payload in members.items()
    }, indent=2, sort_keys=True) + "\n").encode()
    archive = tmp_path / f"00C2_{provider}_real_model_smoke.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        for name, payload in sorted(members.items()):
            handle.writestr(name, payload)
    contract = {
        "fixture_rows": fixture_rows, "environment_hash": environment_hash,
        "code_hash": code_hash, "prompt_hash": prompt_hash,
        "parser_version": "certvic.parse.v2",
        "providers": {provider: {
            "model_id": model_id, "model_commit": model_commit,
            "processor_commit": processor_commit, "snapshot_manifest_hash": snapshot_hash,
            "run_contract_hash": run_hash,
        }},
    }
    return contract, provider


def test_strict_smoke_gate_accepts_exact_package_and_rejects_tamper(tmp_path: Path) -> None:
    contract, provider = _strict_smoke(tmp_path)
    passed = evaluate(tmp_path, [provider], contract=contract)
    assert passed["status"] == "REAL_MODEL_SMOKE_PASSED"
    tampered = json.loads(json.dumps(contract))
    tampered["fixture_rows"][0]["task_hash"] = "f" * 64
    failed = evaluate(tmp_path, [provider], contract=tampered)
    assert failed["status"] == "REAL_MODEL_SMOKE_FAILED"


@pytest.mark.parametrize("pool_size", [100, 300, 600, 1000])
def test_exact_solver_scaling_is_bounded_and_deterministic(pool_size: int) -> None:
    rows = [{
        "source_id": f"source-{index}", "item_id": f"item-{index}", "category": "dog",
        "expected_answer": "yes" if index % 2 == 0 else "no",
        "target_size_stratum": "small", "target_position_stratum": "center",
        "placement_proposals": {"engine": [0, 0, 2, 2]},
    } for index in range(pool_size)]
    config = {"design": {"category_targets": {"dog": {
        "primary": 10, "reserve": 5, "max_per_source": 1,
        "expected_answer_polarities": {"yes": 5, "no": 5},
        "size_strata": {"small": 10}, "position_strata": {"center": 10},
    }}}}
    first = balanced_select(rows, config, seed=31, solver_limits=SolverLimits(
        max_states=20_000, timeout_seconds=5, progress_interval_states=1_000
    ))
    second = balanced_select(rows, config, seed=31, solver_limits=SolverLimits(
        max_states=20_000, timeout_seconds=5, progress_interval_states=1_000
    ))
    assert first["status"] == "BALANCED_SELECTION_COMPLETE"
    assert first["selection_sha256"] == second["selection_sha256"]
    assert first["solution_report"]["categories"][0]["resource_limited"] is False


def test_all_route_synthetic_proof_permission_and_notebooks(tmp_path: Path) -> None:
    closure = run_synthetic_closure(tmp_path / "closure")
    assert closure["status"] == "SYNTHETIC_ALL_STUDY_ROUTES_COMPLETE"
    assert closure["routes"]["coco"]["selected_items"] == 60
    assert closure["paper_evidence"] is False and closure["human_reviewed"] is False
    permission_path = tmp_path / "closure/confirmatory/execution_permission.json"
    verify_permission(permission_path, study="synthetic_confirmatory", allow_synthetic=True)
    with pytest.raises(ExecutionAuthorizationError, match="expired"):
        verify_permission(
            permission_path, study="synthetic_confirmatory", allow_synthetic=True,
            now=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
    main_root = tmp_path / "closure/main"
    task = json.loads((main_root / "tasks.jsonl").read_text().strip())
    task = with_task_hash({**task, "study": "main_study_cvpr"})
    main_tasks = tmp_path / "main_tasks.jsonl"
    main_tasks.write_text(json.dumps(task, sort_keys=True) + "\n")
    freeze = {
        "schema": "certvic.cvpr.main_task_freeze.v1", "status": "MAIN_FINAL_TASKS_FROZEN",
        "study": "main_study_cvpr",
        "primary_tasks_sha256": sha256_bytes(canonical_json_bytes([task])),
        "paper_evidence": False,
    }
    freeze["freeze_hash"] = sha256_bytes(canonical_json_bytes(freeze))
    freeze_path = tmp_path / "main_freeze.json"
    freeze_path.write_text(json.dumps(freeze))
    main_config = tmp_path / "main_config.json"
    main_config.write_text(json.dumps({
        "study_id": "main_study_cvpr", "execution_allowed": False, "paper_evidence": False,
    }))
    outcome = {
        "schema": "certvic.cvpr.confirmatory_outcome.v1",
        "status": "CONFIRMATORY_OUTCOME_VALIDATED",
        "study": "specificity_confirmatory_cvpr", "main_go_no_go": "GO",
        "paper_evidence": False,
    }
    outcome["content_signature_sha256"] = sha256_bytes(canonical_json_bytes(outcome))
    outcome_path = tmp_path / "confirmatory_outcome.json"
    outcome_path.write_text(json.dumps(outcome))
    main_permission = tmp_path / "main_permission.json"
    authorize(
        study="main_study_cvpr", smoke_gate_path=main_root / "synthetic_smoke_gate.json",
        final_task_manifest=main_tasks, final_review_ledger=main_root / "final_inclusion.json",
        freeze_manifest=freeze_path, code_hash=hashlib.sha256(b"main-code").hexdigest(),
        environment_lock=main_root / "environment_lock.json",
        model_registry=main_root / "model_registry.yaml", study_config=main_config,
        prerequisite_artifact=outcome_path, out=main_permission, synthetic_fixture=True,
    )
    verify_permission(main_permission, study="main_study_cvpr", allow_synthetic=True)
    notebook_root = tmp_path / "notebooks"
    build_suite(notebook_root)
    assert len(NOTEBOOKS) == 16
    for name in NOTEBOOKS:
        notebook = json.loads((notebook_root / name).read_text())
        assert all(cell.get("outputs", []) == [] for cell in notebook["cells"])
        text = "".join("".join(cell["source"]) for cell in notebook["cells"])
        assert "EXECUTION_PERMISSION" in text
        if "generation" in name:
            assert "--assemble-shards" in text and "certvic.cvpr.package_generation" in text
