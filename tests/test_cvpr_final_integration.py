from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from certvic.cvpr.agreement import agreement_report
from certvic.cvpr.candidate_selection import balanced_select
from certvic.cvpr.confirmatory_qa import enrich
from certvic.cvpr.environment_lock import offline_environment_flags, verify_wheelhouse
from certvic.cvpr.main_task_builder import build_tasks
from certvic.cvpr.model_snapshot_manifest import create_manifest, verify_manifest, write_manifest
from certvic.cvpr.package_generation import GenerationPackageError, package_generation
from certvic.cvpr.review import (
    finalize_review_state,
    score_qualification,
    validate_adjudication,
    validate_completed_sheet,
)
from certvic.cvpr.review_packets import build_visual_packet
from certvic.cvpr.schema_contract import OUTPUT_SCHEMA, validate_schema_matrix
from certvic.cvpr.semantic_edits import prospective_engine_selection
from certvic.cvpr.smoke_gate import evaluate, require_scientific_run_gate, write_gate
from certvic.cvpr.adjudication import extract_disagreements
from certvic.cvpr.human_review import judgment_fields
from certvic.cvpr.task_schema import convert_legacy_task


ROOT = Path(__file__).resolve().parents[1]


def _json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _image(path: Path, color: tuple[int, int, int] = (0, 0, 0), size: int = 64) -> None:
    Image.new("RGB", (size, size), color).save(path)


def test_output_schema_v2_is_the_only_accepted_matrix_version() -> None:
    assert validate_schema_matrix([{"output_schema": OUTPUT_SCHEMA}])["passed"] is True
    mixed = validate_schema_matrix([
        {"output_schema": OUTPUT_SCHEMA}, {"output_schema": "certvic.cvpr.output.v1"}
    ])
    assert mixed["passed"] is False and "observed" in mixed["errors"][0]


def test_exact_solver_finds_solution_that_seeded_greedy_order_can_miss() -> None:
    config = {"design": {"category_targets": {"person": {
        "primary": 2, "reserve": 0,
        "expected_answer_polarities": {"yes": 1, "no": 1},
        "size_strata": {"small": 1, "large": 1},
        "position_strata": {"left": 1, "right": 1},
    }}}}
    # a+d is invalid on position; b+c is the unique joint solution.
    rows = [
        {"item_id": "a", "source_id": "a", "category": "person", "expected_answer": "yes",
         "target_size_stratum": "small", "target_position_stratum": "left"},
        {"item_id": "b", "source_id": "b", "category": "person", "expected_answer": "yes",
         "target_size_stratum": "large", "target_position_stratum": "left"},
        {"item_id": "c", "source_id": "c", "category": "person", "expected_answer": "no",
         "target_size_stratum": "small", "target_position_stratum": "right"},
        {"item_id": "d", "source_id": "d", "category": "person", "expected_answer": "no",
         "target_size_stratum": "large", "target_position_stratum": "left"},
    ]
    for row in rows:
        row["placement_proposals"] = {"control": [1, 1, 2, 2]}
    result = balanced_select(rows, config, seed=4)
    assert result["feasibility_status"] == "FEASIBLE_SELECTION_FOUND"
    assert {row["item_id"] for row in result["primary"]} == {"b", "c"}
    assert result["solution_report"]["categories"][0]["solver_version"].endswith("v2")


def test_confirmatory_qa_is_deterministic_and_manual_pass_rows_are_rejected(tmp_path: Path) -> None:
    source, output = tmp_path / "source.png", tmp_path / "generated.png"
    _image(source)
    image = Image.open(source).copy()
    for x in range(48, 56):
        for y in range(48, 56):
            image.putpixel((x, y), (255, 255, 255))
    image.save(output)
    candidate = {
        "item_id": "i1", "source_id": "s1", "source_image_path": str(source),
        "target_bbox": [0, 0, 8, 8], "category": "person", "expected_answer": "yes",
        "target_size_stratum": "small", "target_position_stratum": "top_left",
        "license_eligible": True, "placement_proposals": {"control": [48, 48, 56, 56]},
    }
    record = {
        "item_id": "i1", "output_path": str(output), "output_sha256": hashlib.sha256(
            output.read_bytes()
        ).hexdigest(), "engine_family": "structured_texture_patch", "engine_version": "v1",
        "engine_parameters": {"seed": 1}, "placement_box": [48, 48, 56, 56],
    }
    (tmp_path / "generation_records.jsonl").write_text(json.dumps(record) + "\n")
    config = {"design": {
        "perturbation_area_fraction": {"minimum": 0.0025, "maximum": 0.02},
        "minimum_distance_from_target_px": 10,
        "salience_score_range": {"minimum": 0.015, "maximum": 0.12},
    }}
    first = enrich([candidate], tmp_path, config)
    second = enrich([candidate], tmp_path, config)
    assert first["qa_enriched_manifest_sha256"] == second["qa_enriched_manifest_sha256"]
    row = first["rows"][0]
    assert row["generation_qa_status"] == "PASS"
    selection_config = {"selection_requirements": {
        "require_qa_enriched_manifest": True, "require_license_eligible": True,
        "require_generation_qa": True, "require_salience_review": True,
        "require_detectability_review": True,
    }, "design": {"category_targets": {"person": {
        "primary": 1, "reserve": 0, "expected_answer_polarities": {"yes": 1},
        "size_strata": {"small": 1}, "position_strata": {"top_left": 1},
    }}}}
    assert balanced_select([row], selection_config, seed=1)["feasibility_status"] == \
        "FEASIBLE_SELECTION_FOUND"
    manual = {**candidate, "generation_qa_status": "PASS", "salience_review_status": "PASS",
              "detectability_review_status": "PASS"}
    assert balanced_select([manual], selection_config, seed=1)["feasibility_status"] == \
        "NO_FEASIBLE_SELECTION_EXISTS"


def _generation_root(tmp_path: Path) -> tuple[list[dict], Path]:
    root = tmp_path / "generation"
    for name in ("images", "qa", "engine_records", "shard_0"):
        (root / name).mkdir(parents=True, exist_ok=True)
    output = root / "images/i1.png"
    _image(output)
    qa = root / "qa/i1.json"
    engine = root / "engine_records/i1.json"
    _json(qa, {"status": "PASS"})
    _json(engine, {"engine": "fixture_engine", "version": "v1"})
    run_hash = "a" * 64
    source = root / "source.png"
    _image(source)
    task = convert_legacy_task({
        "item_id": "i1", "source_image_path": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_dataset": "SYNTHETIC_FIXTURE", "split": "synthetic",
        "license_status": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
        "question": "Is there an object?", "expected_answer": "yes",
        "required_change": False, "control_edit_family": "fixture_engine",
        "target_bbox": [1, 1, 8, 8], "selected_engine": "fixture_engine",
        "seed": 1,
    }, study="synthetic_confirmatory")
    record = {
        "item_id": "i1", "variant": "edited", "shard": 0,
        "task_sha256": task["task_hash"],
        "run_contract_hash": run_hash, "engine": "fixture_engine",
        "output_path": "images/i1.png", "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "qa_record_path": "qa/i1.json", "qa_record_sha256": hashlib.sha256(qa.read_bytes()).hexdigest(),
        "engine_record_path": "engine_records/i1.json",
        "engine_record_sha256": hashlib.sha256(engine.read_bytes()).hexdigest(),
    }
    (root / "generation_records.jsonl").write_text(json.dumps(record) + "\n")
    _json(root / "shard_0/shard_manifest.json", {
        "status": "SHARD_COMPLETE", "shard": 0, "members": [{"item_id": "i1", "variant": "edited"}]
    })
    _json(root / "run_contract.json", {"run_contract_hash": run_hash})
    _json(root / "environment_manifest.json", {"offline": True})
    _json(root / "runtime_manifest.json", {"status": "COMPLETE"})
    return [task], root


def test_generation_package_recomputes_global_checks_and_is_byte_deterministic(tmp_path: Path) -> None:
    tasks, root = _generation_root(tmp_path)
    first = package_generation(tasks, root, tmp_path / "a.zip", strict=True)
    package_generation(tasks, root, tmp_path / "b.zip", strict=True)
    assert first["validation"]["validation_source"] == "RECOMPUTED_GLOBAL_CHECKS"
    assert (tmp_path / "a.zip").read_bytes() == (tmp_path / "b.zip").read_bytes()
    record = json.loads((root / "generation_records.jsonl").read_text())
    record["task_sha256"] = "0" * 64
    (root / "generation_records.jsonl").write_text(json.dumps(record) + "\n")
    with pytest.raises(GenerationPackageError):
        package_generation(tasks, root, tmp_path / "bad.zip", strict=True)


def test_rich_wheelhouse_metadata_and_offline_flags(tmp_path: Path) -> None:
    wheel = tmp_path / "fixture-1.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    manifest = tmp_path / "manifest.json"
    _json(manifest, {"files": {wheel.name: {
        "filename": wheel.name, "package": "fixture", "version": "1.0",
        "python_tag": "py3", "platform_tag": "any", "size": wheel.stat().st_size,
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "dependency_role": "LOCKED_RUNTIME_DEPENDENCY",
    }}})
    assert verify_wheelhouse(tmp_path, manifest)["passed"] is True
    flags = offline_environment_flags()
    assert flags["PIP_NO_INDEX"] == flags["HF_HUB_OFFLINE"] == "1"


def test_unified_snapshot_contract_binds_model_and_processor_bytes(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text(json.dumps({
        "architectures": ["Fixture"], "model_type": "fixture",
    }))
    (tmp_path / "tokenizer_config.json").write_text("{}")
    (tmp_path / "model.safetensors").write_bytes(b"weights")
    manifest = create_manifest(tmp_path, model_id="fixture/model", model_commit="a" * 40,
                               processor_commit="b" * 40, expected_architecture="Fixture")
    path = write_manifest(tmp_path, manifest)
    verified = verify_manifest(tmp_path, path)
    assert verified["passed"] is True
    assert manifest["snapshot_contract"] == "UNIFIED_SNAPSHOT"
    assert manifest["model_and_processor_share_verified_root"] is True


def test_main_task_builder_is_annotation_and_license_bound(tmp_path: Path) -> None:
    source, mask = tmp_path / "source.png", tmp_path / "mask.png"
    _image(source)
    mask_image = Image.new("L", (64, 64), 0)
    for x in range(10, 30):
        for y in range(10, 30):
            mask_image.putpixel((x, y), 255)
    mask_image.save(mask)
    sources = [{
        "schema": "fixture.source.v1", "source_image_id": "s1", "source_image_path": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "split": "validation",
        "license_eligible": True, "license_status": "VERIFIED_ELIGIBLE",
        "annotations": [{"annotation_id": 1, "category": "chair", "bbox": [10, 10, 30, 30],
                         "mask_path": str(mask), "mask_sha256": hashlib.sha256(mask.read_bytes()).hexdigest()}],
    }]
    config = {"seed": 1, "semantic_interventions": {"allowed_families": ["object_removal"]},
              "task_builder": {"supported_categories": ["chair"],
                               "family_candidate_targets": {"object_removal": 1}}}
    result = build_tasks(tmp_path, sources, config)
    assert result["status"] == "MAIN_CANDIDATE_TASKS_BUILT"
    task = result["tasks"][0]
    assert task["mask_sha256"] and task["source_sha256"]
    assert task["original_expected_answer"] == "yes"
    assert task["edited_expected_answer"] == "no"
    assert prospective_engine_selection({"semantic_edit_family": "object_removal"})[
        "engine"
    ] == "manifest_verified_offline_inpainting_v1"


def _completed_sheet(template: Path, out: Path, *, confidence: str) -> None:
    with template.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    fields = ["blind_pair_id", *judgment_fields("specificity_confirmatory_cvpr")]
    for row in rows:
        for field in fields[1:]:
            row[field] = "high" if field == "confidence" else ("OK" if field == "reason_code" else "yes")
        row["confidence"] = confidence
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _strict_review_fixture(tmp_path: Path) -> dict[str, Path]:
    original, edited = tmp_path / "original.png", tmp_path / "edited.png"
    _image(original, (10, 20, 30))
    _image(edited, (30, 20, 10))
    packet = tmp_path / "packet"
    build_visual_packet([{"item_id": "i1", "original_image_path": str(original),
                          "edited_image_path": str(edited), "question": "Is it present?",
                          "expected_answer": "yes", "required_change": False}],
                        "specificity_confirmatory_cvpr", packet, seed=1)
    response = tmp_path / "response.csv"
    with (packet / "coordinator_qualification_answer_key.csv").open(newline="") as handle:
        answers = list(csv.DictReader(handle))
    with response.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question_id", "decision"])
        writer.writeheader()
        writer.writerows({"question_id": row["question_id"], "decision": row["answer"]}
                         for row in answers)
    q1 = score_qualification(response, packet / "coordinator_qualification_answer_key.csv",
                             reviewer_id="R1")
    q2 = score_qualification(response, packet / "coordinator_qualification_answer_key.csv",
                             reviewer_id="R2")
    q1_path, q2_path = tmp_path / "q1.json", tmp_path / "q2.json"
    _json(q1_path, q1)
    _json(q2_path, q2)
    r1, r2 = tmp_path / "r1.csv", tmp_path / "r2.csv"
    _completed_sheet(packet / "rater_1.csv", r1, confidence="high")
    _completed_sheet(packet / "rater_2.csv", r2, confidence="medium")
    v1 = validate_completed_sheet(r1, track="specificity_confirmatory_cvpr", qualification=q1,
                                  packet_manifest_path=packet / "packet_hash_manifest.json")
    v2 = validate_completed_sheet(r2, track="specificity_confirmatory_cvpr", qualification=q2,
                                  packet_manifest_path=packet / "packet_hash_manifest.json")
    v1_path, v2_path = tmp_path / "v1.json", tmp_path / "v2.json"
    _json(v1_path, v1)
    _json(v2_path, v2)
    agreement = agreement_report(r1, r2, rater_1_id="R1", rater_2_id="R2", bootstrap_draws=20)
    agreement_path = tmp_path / "agreement.json"
    _json(agreement_path, agreement)
    disagreement = tmp_path / "disagreement.csv"
    extract_disagreements(r1, r2, disagreement,
                          fields=judgment_fields("specificity_confirmatory_cvpr"))
    adjudication = tmp_path / "adjudication.csv"
    with disagreement.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    for row in rows:
        for field in judgment_fields("specificity_confirmatory_cvpr"):
            row[field] = "high" if field == "confidence" else ("OK" if field == "reason_code" else "yes")
    with adjudication.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    role = tmp_path / "role.json"
    _json(role, {"role": "ADJUDICATOR", "authorized": True,
                 "adjudicator_identity_sha256": "f" * 64})
    adjudication_value = validate_adjudication(
        adjudication, disagreement, agreement_path, role,
        fields=judgment_fields("specificity_confirmatory_cvpr"),
    )
    adjudication_path = tmp_path / "adjudication_validation.json"
    _json(adjudication_path, adjudication_value)
    return {"packet": packet, "r1": r1, "r2": r2, "q1": q1_path, "q2": q2_path,
            "v1": v1_path, "v2": v2_path, "agreement": agreement_path,
            "adjudication": adjudication_path}


def _finalize(paths: dict[str, Path], **overrides: Path) -> dict:
    values = {**paths, **overrides}
    return finalize_review_state(
        rater_1=values["r1"], rater_2=values["r2"],
        rater_1_validation=values["v1"], rater_2_validation=values["v2"],
        rater_1_qualification=values["q1"], rater_2_qualification=values["q2"],
        agreement_artifact=values["agreement"], adjudication_artifact=values["adjudication"],
        coordinator_key=values["packet"] / "coordinator_key.csv",
        packet_manifest=values["packet"] / "packet_hash_manifest.json",
        packet_root=values["packet"], fields=judgment_fields("specificity_confirmatory_cvpr"),
    )


def test_review_finalization_binds_independence_qualification_and_adjudication(tmp_path: Path) -> None:
    paths = _strict_review_fixture(tmp_path)
    final = _finalize(paths)
    assert final["status"] == "FINAL_INCLUSION_VALIDATED"
    assert len(final["ledger"]) == 1 and final["ledger"][0]["final_inclusion"] is True
    assert len(final["final_artifact_sha256"]) == 64
    with pytest.raises(ValueError, match="raw rater sheets must differ"):
        _finalize(paths, r2=paths["r1"])
    duplicate_qualification = tmp_path / "duplicate_q.json"
    duplicate_qualification.write_bytes(paths["q1"].read_bytes())
    with pytest.raises(ValueError, match="identities must be distinct|identities differ"):
        _finalize(paths, q2=duplicate_qualification)


def test_review_finalization_rejects_failed_qualification_stale_agreement_and_incomplete_adjudication(
    tmp_path: Path,
) -> None:
    paths = _strict_review_fixture(tmp_path)
    failed = json.loads(paths["q2"].read_text())
    failed["qualified"] = False
    failed_path = tmp_path / "failed_q.json"
    _json(failed_path, failed)
    with pytest.raises(ValueError, match="did not pass qualification"):
        _finalize(paths, q2=failed_path)
    stale = json.loads(paths["agreement"].read_text())
    stale["input_sheet_sha256"]["rater_2"] = "0" * 64
    stale_path = tmp_path / "stale_agreement.json"
    _json(stale_path, stale)
    with pytest.raises(ValueError, match="agreement was not computed"):
        _finalize(paths, agreement=stale_path)
    incomplete = json.loads(paths["adjudication"].read_text())
    incomplete["passed"] = False
    incomplete_path = tmp_path / "incomplete_adjudication.json"
    _json(incomplete_path, incomplete)
    with pytest.raises(ValueError, match="adjudication is incomplete"):
        _finalize(paths, adjudication=incomplete_path)


def _smoke_zip(path: Path, provider: str, env_hash: str, snapshot_hash: str) -> None:
    work = path.parent / provider
    work.mkdir()
    rows = [{"item_id": identity, "parse_status": "PARSE_OK", "output_schema": OUTPUT_SCHEMA}
            for identity in ("smoke-1", "smoke-2")]
    (work / "merged_raw.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    _json(work / "runtime_manifest.json", {
        "status": "COMPLETE", "runtime_class": "NON_EVIDENCE_REAL_MODEL_SMOKE",
        "provider": provider, "peak_vram_gib": 10.0, "oom_events": 0,
        "unresolved_warnings": [], "environment_hash": env_hash,
        "snapshot_manifest_hash": snapshot_hash, "run_contract_hash": "c" * 64,
    })
    _json(work / "validation_report.json", {"passed": True})
    with zipfile.ZipFile(path, "w") as archive:
        for file in work.iterdir():
            archive.write(file, file.name)


def test_smoke_gate_promotes_only_complete_validated_three_model_matrix(tmp_path: Path) -> None:
    providers = ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]
    env_hash = "a" * 64
    _json(tmp_path / "00A_environment.json", {
        "status": "EXACT_PREINSTALLED_ENVIRONMENT_ACCEPTED", "passed": True,
        "environment_hash": env_hash,
    })
    for index, provider in enumerate(providers):
        snapshot_hash = str(index + 1) * 64
        _json(tmp_path / f"00B_{provider}_snapshot.json", {
            "passed": True, "snapshot_contract": "UNIFIED_SNAPSHOT",
            "manifest_sha256": snapshot_hash,
        })
        _smoke_zip(tmp_path / f"00C2_{provider}_real_model_smoke.zip", provider,
                   env_hash, snapshot_hash)
    result = evaluate(tmp_path, providers)
    assert result["status"] == "REAL_MODEL_SMOKE_PASSED"
    gate = tmp_path / "gate.csv"
    write_gate(result, gate)
    with pytest.raises(ValueError, match="importer-grade strict smoke"):
        require_scientific_run_gate(gate, providers)
    (tmp_path / f"00C2_{providers[0]}_real_model_smoke.zip").unlink()
    assert evaluate(tmp_path, providers)["status"] == "REAL_MODEL_SMOKE_PENDING"


def test_final_notebooks_and_configs_contain_the_integrated_contracts() -> None:
    text = (ROOT / "certvic/cvpr/notebook_builder.py").read_text()
    for marker in ("WHEELHOUSE_PATH", "OFFLINE_WHEELHOUSE_INSTALLED_AND_VERIFIED",
                   "UNIFIED_SNAPSHOT", "REAL_MODEL_SMOKE_GATE", OUTPUT_SCHEMA):
        assert marker in text
    confirmatory = (ROOT / "configs/studies/specificity_confirmatory_cvpr.yaml").read_text()
    assert "absent_category_protected_scene_v1" in confirmatory
    assert "require_qa_enriched_manifest: true" in confirmatory
    coco = (ROOT / "configs/studies/second_domain_cvpr.yaml").read_text()
    assert "not_broad_cross_domain_generalization" in coco
