"""Complete non-evidence closure exercise labeled SYNTHETIC_END_TO_END_FIXTURE."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from certvic.cvpr.adjudication import extract_disagreements
from certvic.cvpr.agreement import agreement_report
from certvic.cvpr.analysis import human_aware_analysis, write_human_aware_artifacts
from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.execution_gate import authorize, verify_permission
from certvic.cvpr.human_review import judgment_fields
from certvic.cvpr.package_run import package
from certvic.cvpr.permission_ledger import claim, initialize, status as permission_status
from certvic.cvpr.review import (
    finalize_review_state, score_qualification, validate_adjudication, validate_completed_sheet,
)
from certvic.cvpr.review_packets import build_visual_packet
from certvic.cvpr.semantic_edits import SemanticEditSettings, generate_semantic_edit
from certvic.cvpr.task_schema import TASK_SCHEMA, require_task, with_task_hash
from certvic.cvpr.task_bundle import create_bundle
from certvic.cvpr.synthetic_smoke import run as run_strict_smoke
from certvic.cvpr.model_snapshot_manifest import MANIFEST_NAME
from certvic.cvpr.transactional import read_jsonl
from certvic.cvpr.whole_study_import import atomic_import_matrix
from certvic.cvpr.worker import run_shard


PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _complete_sheet(
    source: Path, destination: Path, *, confidence: str, fields: tuple[str, ...]
) -> None:
    with source.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for field in fields:
            row[field] = confidence if field == "confidence" else (
                "SYNTHETIC_FIXTURE_ACCEPT" if field == "reason_code" else "yes"
            )
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["blind_pair_id", *fields])
        writer.writeheader()
        writer.writerows(rows)


def _strict_synthetic_review(
    task: dict[str, Any] | list[dict[str, Any]], out: Path, *, track: str = "main_study_cvpr"
) -> tuple[dict[str, Any], dict[str, Any]]:
    fields_contract = judgment_fields(track)
    packet = out / "review_packet"
    build_visual_packet(task if isinstance(task, list) else [task], track, packet, seed=19001)
    response = out / "qualification_response.csv"
    with (packet / "coordinator_qualification_answer_key.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        answers = list(csv.DictReader(handle))
    with response.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question_id", "decision"])
        writer.writeheader()
        writer.writerows({"question_id": row["question_id"], "decision": row["answer"]}
                         for row in answers)
    qualifications = {
        "rater_1": score_qualification(
            response, packet / "coordinator_qualification_answer_key.csv",
            reviewer_id="SYNTHETIC_RATER_A",
        ),
        "rater_2": score_qualification(
            response, packet / "coordinator_qualification_answer_key.csv",
            reviewer_id="SYNTHETIC_RATER_B",
        ),
    }
    qualification_paths = {role: out / f"{role}_qualification.json" for role in qualifications}
    for role, value in qualifications.items():
        _json(qualification_paths[role], value)
    rater_paths = {"rater_1": out / "rater_1_completed.csv",
                   "rater_2": out / "rater_2_completed.csv"}
    _complete_sheet(packet / "rater_1.csv", rater_paths["rater_1"], confidence="high",
                    fields=fields_contract)
    _complete_sheet(packet / "rater_2.csv", rater_paths["rater_2"], confidence="medium",
                    fields=fields_contract)
    validation_paths = {role: out / f"{role}_validation.json" for role in rater_paths}
    for role in rater_paths:
        _json(validation_paths[role], validate_completed_sheet(
            rater_paths[role], track=track, qualification=qualifications[role],
            packet_manifest_path=packet / "packet_hash_manifest.json",
        ))
    agreement = agreement_report(
        rater_paths["rater_1"], rater_paths["rater_2"],
        rater_1_id="SYNTHETIC_RATER_A", rater_2_id="SYNTHETIC_RATER_B",
        fields=fields_contract, bootstrap_draws=50,
    )
    agreement_path = out / "agreement.json"
    _json(agreement_path, agreement)
    disagreement = out / "adjudication_fixture.csv"
    extract_disagreements(
        rater_paths["rater_1"], rater_paths["rater_2"], disagreement,
        fields=fields_contract,
    )
    with disagreement.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0]) if rows else ["blind_pair_id", "disagreement_fields",
                                             *fields_contract]
    for row in rows:
        for field in fields_contract:
            if not row.get(field):
                row[field] = "high" if field == "confidence" else (
                    "SYNTHETIC_FIXTURE_ACCEPT" if field == "reason_code" else "yes"
                )
    with disagreement.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    role_path = out / "synthetic_adjudicator_role.json"
    _json(role_path, {"authorized": True,
                      "adjudicator_identity_sha256": hashlib.sha256(
                          b"SYNTHETIC_ADJUDICATOR"
                      ).hexdigest(), "paper_evidence": False})
    adjudication_validation_path = out / "adjudication_validation.json"
    _json(adjudication_validation_path, validate_adjudication(
        disagreement, disagreement, agreement_path, role_path,
        fields=fields_contract,
    ))
    final = finalize_review_state(
        rater_1=rater_paths["rater_1"], rater_2=rater_paths["rater_2"],
        rater_1_validation=validation_paths["rater_1"],
        rater_2_validation=validation_paths["rater_2"],
        rater_1_qualification=qualification_paths["rater_1"],
        rater_2_qualification=qualification_paths["rater_2"],
        agreement_artifact=agreement_path, adjudication_artifact=adjudication_validation_path,
        coordinator_key=packet / "coordinator_key.csv",
        packet_manifest=packet / "packet_hash_manifest.json", packet_root=packet,
        fields=fields_contract,
    )
    _json(out / "final_inclusion.json", final)
    return agreement, final


def run(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    if out.exists() and any(out.iterdir()):
        raise ValueError("synthetic study output directory must be new or empty")
    out.mkdir(parents=True, exist_ok=True)
    source = out / "source.png"
    Image.new("RGB", (64, 64), (220, 20, 30)).save(source)
    mask_path = out / "target_mask.png"
    mask = Image.new("L", (64, 64), 0)
    for y in range(8, 56):
        for x in range(8, 56):
            mask.putpixel((x, y), 255)
    mask.save(mask_path, format="PNG", compress_level=9)
    task = with_task_hash({
        "task_schema_version": TASK_SCHEMA, "study": "synthetic_main",
        "task_id": "synthetic-main-1", "item_id": "synthetic-main-1",
        "source_dataset": "SYNTHETIC_FIXTURE", "source_split": "synthetic",
        "source_image_id": "synthetic-source-1", "source_image_path": str(source),
        "source_image_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
        "license_status": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
        "original_image_path": str(source), "question": "Is the square red?",
        "original_expected_answer": "yes", "edited_expected_answer": "no",
        "required_change": True, "semantic_edit_family": "attribute_modification",
        "control_edit_family": None, "target_category": "square",
        "queried_category": "square", "queried_category_absent": False,
        "target_bbox": [8, 8, 56, 56], "target_mask_path": str(mask_path),
        "target_mask_hash": hashlib.sha256(mask_path.read_bytes()).hexdigest(),
        "protected_scene_mask_path": None, "protected_scene_mask_hash": None,
        "attribute_name": "color", "original_attribute": "red", "edited_attribute": "blue",
        "attribute_transform": "red_to_blue", "original_attribute_verified": True,
        "edit_engine_policy": "certvic.semantic_engine_policy.v1",
        "selected_engine": "verified_attribute_transform_v1", "engine_fallbacks": ["REJECT"],
        "engine_parameters": {}, "seed": 19001, "primary_or_reserve": None,
        "strata": {"difficulty": "synthetic"}, "review_status": "HUMAN_REVIEW_PENDING",
        "qa_status": "QA_PENDING", "answer_format": "yes_no", "mock_raw_response": "yes",
        "runtime_class": "SYNTHETIC_END_TO_END_FIXTURE", "paper_evidence": False,
    })
    require_task(task, verify_files=True)
    edit = generate_semantic_edit(task, out / "edited.png", SemanticEditSettings(19001))
    task = with_task_hash({**task, "edited_image_path": edit["edited_image_path"]})
    agreement, inclusion = _strict_synthetic_review(task, out)
    task = require_task(with_task_hash({
        **task, "qa_status": "PASS", "review_status": "VALID_ADJUDICATED",
        "primary_or_reserve": "primary",
        "review_provenance": {
            "final_review_artifact_sha256": inclusion["final_artifact_sha256"],
            "final_review_ledger_sha256": inclusion["final_ledger_sha256"],
        },
    }), verify_files=True)
    bundle_root = out / "task_bundle"
    create_bundle([task], bundle_root)
    tasks_path = bundle_root / "tasks.jsonl"
    task = read_jsonl(tasks_path)[0]

    freeze = {
        "schema": "certvic.cvpr.main_task_freeze.v1", "status": "MAIN_FINAL_TASKS_FROZEN",
        "study": "synthetic_main", "primary_tasks_sha256": sha256_bytes(
            canonical_json_bytes([task])
        ), "review_artifact_sha256": inclusion["final_artifact_sha256"],
        "solver_status": "PASS", "paper_evidence": False,
    }
    freeze["freeze_hash"] = sha256_bytes(canonical_json_bytes(freeze))
    freeze_path = out / "freeze_manifest.json"
    _json(freeze_path, freeze)

    strict_smoke = run_strict_smoke(out / "strict_smoke")
    environment_path = out / "strict_smoke/00_environment_lock.json"
    # Historical synthetic tests consume these explicit non-scientific aliases.
    # The authorization/runtime path above and below uses only the portable bundle.
    legacy_task = dict(task)
    for field in ("source_image_path", "original_image_path", "edited_image_path",
                  "target_mask_path", "protected_scene_mask_path"):
        if legacy_task.get(field):
            legacy_task[field] = str((bundle_root / str(legacy_task[field])).resolve())
    legacy_task["path_contract"] = "LEGACY_ABSOLUTE_SYNTHETIC_COMPATIBILITY"
    legacy_task = with_task_hash(legacy_task)
    (out / "tasks.jsonl").write_text(json.dumps(legacy_task, sort_keys=True) + "\n", encoding="utf-8")
    (out / "environment_lock.json").write_bytes(environment_path.read_bytes())
    (out / "synthetic_smoke_gate.json").write_bytes(Path(strict_smoke["gate_json"]).read_bytes())
    registry_path = out / "model_registry.yaml"
    _json(registry_path, {"primary_models": list(PROVIDERS),
                          "models": {provider: {} for provider in PROVIDERS}})
    config_path = out / "study_config.yaml"
    _json(config_path, {"schema": "certvic.cvpr.synthetic.v1", "study_id": "synthetic_main",
                        "status": "SYNTHETIC_FIXTURE", "paper_evidence": False,
                        "execution_allowed": False})
    smoke_path = Path(strict_smoke["gate_json"])
    code_bundle = out / "strict_smoke/synthetic_code_bundle.zip"
    code_hash = hashlib.sha256(code_bundle.read_bytes()).hexdigest()
    run_tag = "synthetic_main_v1"
    task_universe = sha256_bytes(canonical_json_bytes([str(task["task_id"])]))
    ledger_path = out / "permission_ledger.json"
    initialize(
        ledger_path, study="synthetic_main", providers=list(PROVIDERS), run_tags=run_tag,
        task_universe_sha256=task_universe, output_schema="certvic.cvpr.output.v2",
        authorization_nonce=hashlib.sha256(b"SYNTHETIC_MAIN_AUTHORIZATION").hexdigest(),
    )
    snapshot_manifests = {
        provider: out / "strict_smoke/snapshots" / provider / MANIFEST_NAME
        for provider in PROVIDERS
    }
    permission_path = out / "execution_permission.json"
    permission = authorize(
        study="synthetic_main", smoke_gate_path=smoke_path, final_task_manifest=tasks_path,
        final_review_ledger=out / "final_inclusion.json", freeze_manifest=freeze_path,
        code_hash=code_hash, environment_lock=environment_path, model_registry=registry_path,
        study_config=config_path, out=permission_path, synthetic_fixture=True,
        task_bundle_manifest=bundle_root / "task_bundle_manifest.json", bundle_root=bundle_root,
        permission_ledger=ledger_path, model_snapshot_manifests=snapshot_manifests,
        run_tags=run_tag,
    )
    input_paths = {
        "smoke_gate": smoke_path, "final_tasks": tasks_path,
        "final_review": out / "final_inclusion.json", "freeze_manifest": freeze_path,
        "environment_lock": environment_path, "model_registry": registry_path,
        "study_config": config_path,
        "task_bundle_manifest": bundle_root / "task_bundle_manifest.json",
        "permission_ledger": ledger_path,
        **{f"model_snapshot_manifest:{provider}": path
           for provider, path in snapshot_manifests.items()},
    }
    verify_permission(
        permission_path, study="synthetic_main", allow_synthetic=True,
        input_paths=input_paths, expected_code_hash=code_hash,
        expected_provider=PROVIDERS[0], expected_run_tag=run_tag,
        expected_output_schema="certvic.cvpr.output.v2",
    )

    archives: dict[str, Path] = {}
    models: dict[str, dict[str, str]] = {}
    snapshot_hashes: dict[str, str] = {}
    for index, provider in enumerate(PROVIDERS, start=1):
        snapshot_path = snapshot_manifests[provider]
        snapshot = json.loads(snapshot_path.read_text())
        model = {key: str(snapshot[key]) for key in ("model_id", "model_commit", "processor_commit")}
        models[provider] = model
        snapshot_hash = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        snapshot_hashes[provider] = snapshot_hash
        claim(
            ledger_path, study="synthetic_main", provider=provider, run_tag=run_tag,
            notebook=f"synthetic_{provider}_main.ipynb", task_universe_sha256=task_universe,
            permission_id=permission["permission_id"],
            permission_signature=permission["content_signature_sha256"],
        )
        provider_out = out / "runs" / provider
        config_path = out / f"runtime_{provider}.json"
        config = {
            "study": "synthetic_main", "runtime_class": "SYNTHETIC_END_TO_END_FIXTURE",
            "provider": provider, "model_id": model["model_id"],
            "model_commit": model["model_commit"], "processor_id": model["model_id"],
            "processor_commit": model["processor_commit"], "run_tag": run_tag,
            "task_manifest": str(tasks_path), "output_dir": str(provider_out),
            "code_bundle_hash": code_hash, "model_snapshot_manifest_hash": snapshot_hash,
            "processor_snapshot_manifest_hash": snapshot_hash,
            "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED", "snapshot_contract": "UNIFIED_SNAPSHOT",
            "snapshot_manifest_path": str(snapshot_path), "model_path": str(snapshot_path.parent),
            "processor_path": str(snapshot_path.parent),
            "expected_architecture": snapshot["expected_architecture"],
            "environment_lock_hash": permission["input_hashes"]["environment_lock"],
            "environment_lock_path": str(environment_path),
            "prompt_template_id": "synthetic_yes_no",
            "prompt_template": "{prompt}",
            "prompt_template_hash": hashlib.sha256(b"{prompt}").hexdigest(),
            "parser_version": "certvic.parse.v2", "output_schema": "certvic.cvpr.output.v2",
            "strict_run_contract": True, "strict_permission_binding": True,
            "task_bundle_root": str(bundle_root),
            "task_bundle_manifest": str(bundle_root / "task_bundle_manifest.json"),
            "seed": 19001, "generation_parameters": {"do_sample": False, "max_new_tokens": 8},
            "execution_permission_path": str(permission_path),
            "execution_permission_id": permission["permission_id"],
            "execution_permission_signature": permission["content_signature_sha256"],
            "permission_input_paths": {key: str(value) for key, value in input_paths.items()},
            "permission_ledger_path": str(ledger_path),
            "notebook_name": f"synthetic_{provider}_main.ipynb",
        }
        _json(config_path, config)
        result = run_shard(config_path, shard=0, num_shards=1, mock_runtime=True)
        if result["status"] != "SHARD_COMPLETE":
            raise RuntimeError(f"synthetic worker failed for {provider}: {result}")
        packaged = package(config_path, expected_shards=1)
        archives[provider] = Path(str(packaged["zip"]))
    imported = out / "atomic_import"
    promotion = atomic_import_matrix(
        archives, study="synthetic_main", run_tag=run_tag,
        model_contracts=models, tasks=[task], expected_code_bundle_hash=code_hash,
        expected_snapshot_hashes=snapshot_hashes, destination_root=imported,
        expected_permission_id=permission["permission_id"],
        expected_permission_signature=permission["content_signature_sha256"],
        permission_ledger_path=ledger_path, bundle_root=bundle_root,
    )
    provider_rows = {
        provider: [json.loads(line) for line in
                   (imported / "canonical" / f"{provider}.jsonl").read_text().splitlines() if line]
        for provider in PROVIDERS
    }
    analysis = human_aware_analysis(
        provider_rows, [task], final_inclusion=inclusion, agreement=agreement,
        study_kind="main_study_cvpr",
    )
    artifacts = write_human_aware_artifacts(out / "analysis", analysis)
    (out / "paper_injection_fixture.tex").write_text(
        "% SYNTHETIC_END_TO_END_FIXTURE -- NEVER PAPER EVIDENCE\n"
        "\\textbf{Synthetic closure fixture completed; no scientific result.}\n",
        encoding="utf-8",
    )
    synthetic_release = {
        "runtime_class": "SYNTHETIC_END_TO_END_FIXTURE",
        "artifacts": sorted(path.relative_to(out).as_posix() for path in out.rglob("*") if path.is_file()),
        "paper_evidence": False,
    }
    _json(out / "synthetic_release_update.json", synthetic_release)
    result = {
        "schema": "certvic.cvpr.synthetic_end_to_end.v1",
        "status": "SYNTHETIC_END_TO_END_FIXTURE_COMPLETE",
        "runtime_class": "SYNTHETIC_END_TO_END_FIXTURE",
        "stages": ["canonical_task_build", "semantic_generation", "review_packet",
                   "synthetic_qualification", "synthetic_independent_raters", "agreement",
                   "adjudication", "final_inclusion", "exact_single_item_selection",
                   "task_freeze", "strict_mock_smoke_gate", "signed_execution_permission",
                   "three_model_mock_outputs", "strict_package_validation", "atomic_import",
                   "human_aware_analysis", "table_generation", "paper_injection", "release_update"],
        "promotion": promotion, "analysis_artifacts": artifacts,
        "execution_permission_id": permission["permission_id"],
        "smoke_status": strict_smoke["status"],
        "permission_states": {provider: slot["state"] for provider, slot in
                              permission_status(ledger_path)["slots"].items()},
        "paper_evidence": False, "human_reviewed": False,
    }
    _json(out / "synthetic_study_status.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the non-evidence CVPR closure fixture")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    result = run(args.out_dir)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
