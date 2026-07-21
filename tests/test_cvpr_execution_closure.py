from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from certvic.cvpr.adapters import AdapterError, internvl_t4_strategy
from certvic.cvpr.candidate_selection import balanced_select
from certvic.cvpr.environment_lock import environment_lock_hash, load_environment_lock
from certvic.cvpr.freeze_manifest import build_freeze_manifest
from certvic.cvpr.human_review import SEMANTIC_JUDGMENT_FIELDS
from certvic.cvpr.inpainting import OfflineInpaintingAdapter
from certvic.cvpr.model_snapshot_manifest import create_manifest, write_manifest
from certvic.cvpr.notebook_builder import NOTEBOOKS, build_suite
from certvic.cvpr.review import score_qualification, validate_completed_sheet
from certvic.cvpr.review_packets import build_visual_packet
from certvic.cvpr.paper_branch import activate_paper_branch
from certvic.cvpr.run_contract import build_run_contract, validate_run_contract
from certvic.cvpr.runtime_calibration import calibrate
from certvic.cvpr.semantic_edits import SemanticEditSettings, generate_semantic_edit
from certvic.cvpr.synthetic_study import run as run_synthetic_study
from certvic.cvpr.task_schema import convert_legacy_task
from certvic.data.coco_adapter_stub import build_feasibility_tasks, load_coco_instances


ROOT = Path(__file__).resolve().parents[1]


def _image(path: Path, color: tuple[int, int, int] = (180, 20, 40)) -> None:
    Image.new("RGB", (64, 64), color).save(path)


def _strict_runtime() -> dict:
    return {
        "study": "fixture", "run_tag": "fixture_v1", "runtime_class": "SCIENTIFIC_EXECUTION",
        "provider": "qwen2_5_vl_7b", "model_id": "fixture/model",
        "model_commit": "a" * 40, "processor_id": "fixture/model",
        "processor_commit": "b" * 40, "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
        "model_snapshot_manifest_hash": "1" * 64,
        "processor_snapshot_manifest_hash": "2" * 64, "code_bundle_hash": "3" * 64,
        "environment_lock_hash": "4" * 64, "prompt_template_id": "yes_no_v1",
        "prompt_template_hash": "5" * 64, "parser_version": "certvic.parse.v2",
        "output_schema": "certvic.cvpr.output.v2", "generation_parameters": {"do_sample": False},
        "seed": 7, "sharding": {"algorithm": "balanced_cost_v1", "num_shards": 2},
        "execution_permission_id": "7" * 64,
        "execution_permission_signature": "8" * 64,
    }


def test_run_contract_is_complete_canonical_and_declared_only_is_rejected() -> None:
    config = _strict_runtime()
    contract = build_run_contract(config, task_manifest_sha256="6" * 64)
    assert contract["contract_complete"] is True
    assert validate_run_contract(contract) == []
    changed = {**config, "seed": 8}
    assert build_run_contract(changed, task_manifest_sha256="6" * 64)["run_contract_hash"] != contract[
        "run_contract_hash"
    ]
    with pytest.raises(ValueError, match="verified bytes or an authenticated commit"):
        build_run_contract({**config, "snapshot_status": "REMOTE_COMMIT_DECLARED"},
                           task_manifest_sha256="6" * 64)


def test_main_semantic_edit_is_answer_changing_mask_scoped_and_review_pending(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _image(source)
    mask = tmp_path / "mask.png"
    mask_image = Image.new("L", (64, 64), 0)
    for x in range(16, 48):
        for y in range(16, 48):
            mask_image.putpixel((x, y), 255)
    mask_image.save(mask)
    task = convert_legacy_task({
        "item_id": "main-1", "source_image_path": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_dataset": "SYNTHETIC_FIXTURE", "split": "synthetic",
        "license_status": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
        "question": "Is the object red?", "original_expected_answer": "yes",
        "edited_expected_answer": "no", "required_change": True,
        "target_category": "object", "queried_category": "object",
        "semantic_edit_family": "attribute_modification", "attribute_transform": "red_to_blue",
        "attribute_name": "color", "original_attribute": "red", "edited_attribute": "blue",
        "original_attribute_verified": True, "selected_engine": "verified_attribute_transform_v1",
        "target_bbox": [16, 16, 48, 48], "target_mask_path": str(mask),
        "target_mask_hash": hashlib.sha256(mask.read_bytes()).hexdigest(),
        "seed": 9,
    }, study="synthetic_main")
    record = generate_semantic_edit(task, tmp_path / "edited.png", SemanticEditSettings(9))
    assert record["metrics"]["target_change_fraction"] == 1.0
    assert record["metrics"]["non_target_change_fraction"] == 0.0
    assert record["original_expected_answer"] != record["edited_expected_answer"]
    assert record["human_validity_status"] == "HUMAN_REVIEW_PENDING"
    assert record["paper_evidence"] is False
    resumed = generate_semantic_edit(task, tmp_path / "edited.png", SemanticEditSettings(9))
    assert resumed["status"] == "EXISTING_VALID_OUTPUT"


class _OOMThenImages:
    def __init__(self) -> None:
        self.calls = 0
        self.to_calls: list[str] = []

    def enable_attention_slicing(self) -> None:
        pass

    def enable_vae_slicing(self) -> None:
        pass

    def to(self, device: str) -> "_OOMThenImages":
        self.to_calls.append(device)
        return self

    def __call__(self, *, image: list[Image.Image], **_kwargs: object) -> object:
        self.calls += 1
        if len(image) > 1:
            raise RuntimeError("CUDA out of memory synthetic fixture")
        return type("Result", (), {"images": image})()


def test_inpainting_snapshot_loads_once_and_halves_oom_batch(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "config.json").write_text(json.dumps({
        "architectures": ["FixtureInpaint"], "model_type": "fixture"
    }))
    (snapshot / "tokenizer_config.json").write_text("{}")
    (snapshot / "model.safetensors").write_bytes(b"weights")
    manifest = create_manifest(snapshot, model_id="fixture/inpaint", model_commit="a" * 40,
                               processor_commit="a" * 40,
                               expected_architecture="FixtureInpaint")
    manifest_path = write_manifest(snapshot, manifest)
    pipeline = _OOMThenImages()
    adapter = OfflineInpaintingAdapter(
        snapshot_dir=snapshot, snapshot_manifest=manifest_path,
        expected_model_id="fixture/inpaint", expected_model_commit="a" * 40,
        expected_architecture="FixtureInpaint", pipeline_factory=lambda _path: pipeline,
        device="cpu",
    )
    adapter.prepare()
    adapter.prepare()
    image = Image.new("RGB", (8, 8))
    mask = Image.new("L", (8, 8), 0)
    for y in range(2, 6):
        for x in range(2, 6):
            mask.putpixel((x, y), 255)
    outputs, events = adapter.generate_batch(
        [{"image": image, "mask": mask, "prompt": "fill"} for _ in range(2)],
        batch_size=2, seed=1,
    )
    assert len(outputs) == 2 and adapter.prepare_calls == 1
    assert any(event["event"] == "CUDA_OOM_BATCH_REDUCTION" for event in events)
    adapter.release()


def _coco_fixture(root: Path) -> None:
    (root / "annotations").mkdir(parents=True)
    (root / "val2017").mkdir()
    images = []
    annotations = []
    for image_id in (1, 2):
        filename = f"{image_id:012}.jpg"
        Image.new("RGB", (512, 512), (30 * image_id, 40, 50)).save(root / "val2017" / filename)
        images.append({"id": image_id, "file_name": filename, "width": 512, "height": 512,
                       "license": 1})
    annotations.append({"id": 10, "image_id": 1, "category_id": 1, "iscrowd": 0,
                        "area": 10000, "bbox": [50, 50, 100, 100],
                        "segmentation": [[50, 50, 150, 50, 150, 150, 50, 150]]})
    payload = {"images": images, "annotations": annotations,
               "categories": [{"id": 1, "name": "chair"}, {"id": 2, "name": "car"}],
               "licenses": [{"id": 1, "name": "fixture", "url": "https://example.invalid"}]}
    (root / "annotations/instances_val2017.json").write_text(json.dumps(payload))


def test_coco_adapter_builds_real_offline_removal_and_insertion_candidates(tmp_path: Path) -> None:
    root = tmp_path / "coco"
    _coco_fixture(root)
    assert len(load_coco_instances(root)["images"]) == 2
    manifest = build_feasibility_tasks(root, out_dir=tmp_path / "out", items=2)
    assert manifest["status"].startswith("FEASIBILITY_CANDIDATES_READY")
    assert manifest["family_counts"] == {"object_insertion": 1, "object_removal": 1}
    assert manifest["license_status"] == "REQUIRES_PER_IMAGE_VERIFICATION"


def test_selection_hash_covers_full_selected_content() -> None:
    config = {"design": {"category_targets": {"person": {
        "primary": 1, "reserve": 0, "expected_answer_polarities": {"yes": 1},
        "size_strata": {"small": 1}, "position_strata": {"center": 1},
    }}}}
    row = {"source_id": "s1", "item_id": "i1", "category": "person", "expected_answer": "yes",
           "target_size_stratum": "small", "target_position_stratum": "center",
           "placement_proposals": {"texture": [0, 0, 1, 1]}, "metadata": {"version": 1}}
    first = balanced_select([row], config, seed=1)
    second = balanced_select([{**row, "metadata": {"version": 2}}], config, seed=1)
    assert first["selection_sha256"] != second["selection_sha256"]
    assert first["selection_hash_scope"].startswith("canonical_full")
    strict = {**config, "selection_requirements": {
        "require_license_eligible": True, "require_generation_qa": True,
        "require_salience_review": True, "require_detectability_review": True,
    }}
    assert balanced_select([row], strict, seed=1)["status"] == "BLOCKED_SHORTAGE"
    eligible = {**row, "license_eligible": True, "generation_qa_status": "PASS",
                "salience_review_status": "PASS", "detectability_review_status": "PASS"}
    assert balanced_select([eligible], strict, seed=1)["status"] == "BALANCED_SELECTION_COMPLETE"


def test_semantic_review_qualification_and_sheet_schema(tmp_path: Path) -> None:
    original, edited = tmp_path / "o.png", tmp_path / "e.png"
    _image(original)
    _image(edited, (10, 30, 200))
    packet = tmp_path / "packet"
    build_visual_packet([{
        "item_id": "i1", "original_image_path": str(original), "edited_image_path": str(edited),
        "question": "Is the object red?", "required_change": True,
        "original_expected_answer": "yes", "edited_expected_answer": "no",
    }], "main_study_cvpr", packet, seed=1)
    manifest = json.loads((packet / "packet_hash_manifest.json").read_text())
    assert tuple(manifest["judgment_fields"]) == SEMANTIC_JUDGMENT_FIELDS
    response = tmp_path / "quiz.csv"
    with (packet / "coordinator_qualification_answer_key.csv").open(newline="") as handle:
        key_rows = list(csv.DictReader(handle))
    with response.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question_id", "decision"])
        writer.writeheader()
        writer.writerows(
            {"question_id": row["question_id"], "decision": row["answer"]} for row in key_rows
        )
    qualification = score_qualification(
        response, packet / "coordinator_qualification_answer_key.csv", reviewer_id="reviewer-A"
    )
    assert qualification["qualified"] is True
    sheet = tmp_path / "completed.csv"
    with (packet / "rater_1.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for field in SEMANTIC_JUDGMENT_FIELDS:
            row[field] = "high" if field == "confidence" else ("OK" if field == "reason_code" else "yes")
    with sheet.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["blind_pair_id", *SEMANTIC_JUDGMENT_FIELDS])
        writer.writeheader()
        writer.writerows(rows)
    assert validate_completed_sheet(
        sheet, track="main_study_cvpr", qualification=qualification,
        packet_manifest_path=packet / "packet_hash_manifest.json",
    )["passed"] is True


def test_notebook_suite_has_global_bound_concurrency_and_separate_smokes(tmp_path: Path) -> None:
    expected = {
        "00A_certvic_code_and_environment_smoke.ipynb",
        "00B_qwen2_5_vl_7b_snapshot_smoke.ipynb",
        "00B_internvl_8b_snapshot_smoke.ipynb",
        "00B_llava_onevision_7b_snapshot_smoke.ipynb",
        "00C1_certvic_mock_adapter_smoke.ipynb",
        "00C2_qwen2_5_vl_7b_real_model_two_item_smoke.ipynb",
        "00C2_internvl_8b_real_model_two_item_smoke.ipynb",
        "00C2_llava_onevision_7b_real_model_two_item_smoke.ipynb",
        "01_specificity_confirmatory_generation_T4x2.ipynb",
        "02_qwen_specificity_confirmatory_T4x2.ipynb", "03_internvl_specificity_confirmatory_T4x2.ipynb",
        "04_llava_specificity_confirmatory_T4x2.ipynb", "10_main_study_generation_T4x2.ipynb",
        "11_qwen_main_study_T4x2.ipynb", "12_internvl_main_study_T4x2.ipynb",
        "13_llava_main_study_T4x2.ipynb", "20_second_domain_generation_T4x2.ipynb",
        "21_second_domain_qwen_T4x2.ipynb", "22_second_domain_internvl_T4x2.ipynb",
        "23_second_domain_llava_T4x2.ipynb",
    }
    assert set(NOTEBOOKS) == expected
    build_suite(tmp_path)
    text = "\n".join(path.read_text() for path in tmp_path.glob("*.ipynb"))
    assert "bounded_rows = rows if MAX_ITEMS is None else rows[:MAX_ITEMS]" in text
    assert "subprocess.Popen(command" in text
    assert "CONTENT_AUTHENTICATED_ANY_LOCATION" in text
    assert "CERTVIC_DISCOVERY_02_AMBIGUOUS_DISTINCT_CONTENT" in text
    assert "USE_REAL_MODEL = True" in text
    for name in expected:
        assert "REQUIRED_USER_FILL" not in (tmp_path / name).read_text()


def test_environment_lock_and_internvl_t4_policy_are_explicit() -> None:
    lock_path = ROOT / "configs/runtime/kaggle_t4x2_environment.lock.json"
    lock = load_environment_lock(lock_path)
    assert len(environment_lock_hash(lock_path)) == 64
    assert lock["offline_install"]["allow_index"] is False
    strategy = internvl_t4_strategy({"quantization": "nf4_4bit", "max_patches": 6})
    assert strategy["max_patches"] == 6 and strategy["device_map"] == {"": 0}
    with pytest.raises(AdapterError):
        internvl_t4_strategy({"quantization": "none", "max_patches": 12})


def test_no_required_closure_path_contains_notimplemented() -> None:
    required = [
        ROOT / "certvic/cvpr/semantic_edits.py", ROOT / "certvic/cvpr/inpainting.py",
        ROOT / "certvic/data/coco_adapter_stub.py", ROOT / "certvic/cvpr/review.py",
        ROOT / "certvic/cvpr/run_contract.py", ROOT / "certvic/cvpr/environment_lock.py",
    ]
    assert not any("NotImplementedError" in path.read_text() for path in required)


def test_synthetic_end_to_end_fixture_and_paper_branch_gate(tmp_path: Path) -> None:
    result = run_synthetic_study(tmp_path / "synthetic")
    assert result["status"] == "SYNTHETIC_END_TO_END_FIXTURE_COMPLETE"
    assert result["paper_evidence"] is False and result["human_reviewed"] is False
    audit = json.loads(
        (tmp_path / "synthetic/atomic_import/study_import_audit.json").read_text()
    )
    assert all(
        {"archive_sha256", "merged_raw_sha256", "canonical_normalized_sha256"}
        <= set(provider)
        for provider in audit["providers"].values()
    )
    ledger = json.loads(
        (tmp_path / "synthetic/atomic_import/import_evidence_ledger.json").read_text()
    )
    assert {row["content_role"] for row in ledger if "content_role" in row} == {
        "IMMUTABLE_RETURNED_ARCHIVE"
    }
    blocked = activate_paper_branch(
        study_import={"status": "BLOCKED"}, final_inclusion={}, evidence_hashes_match=False,
        intervals={}, claim_guard={"passed": False}, requested_branch="ALL_MODELS_PASS",
    )
    assert blocked["status"] == "PAPER_BRANCH_BLOCKED"
    assert len(blocked["blockers"]) == 5 and blocked["active_branch"] is None


def test_runtime_calibration_rejects_mock_and_freeze_hashes_all_contracts() -> None:
    with pytest.raises(ValueError, match="refuses mock"):
        calibrate([{"runtime_class": "SYNTHETIC_MOCK_RUNTIME"}], [60])
    observed = calibrate([{
        "runtime_class": "NON_EVIDENCE_REAL_MODEL_SMOKE", "observed": True,
        "provider": "qwen2_5_vl_7b", "items": 2, "duration_seconds": 8,
        "peak_vram_gib": 11.5,
    }], [60])
    assert observed["estimates"][0]["estimated_seconds"] == 480
    freeze = build_freeze_manifest(ROOT)
    assert set(freeze["contracts"]) == {
        "confirmatory_study", "main_study", "coco_feasibility", "model_matrix",
        "environment", "analysis_plan", "human_review_rules",
        "protocol_authority", "primary_analysis",
    }
    assert all(len(record["sha256"]) == 64 for record in freeze["contracts"].values())


def test_sealed_release_dependency_and_clean_extraction_reports() -> None:
    dependency = json.loads(
        (ROOT / "release/cvpr_execution_closure/RELEASE_DEPENDENCY_AUDIT.json").read_text()
    )
    clean = json.loads(
        (ROOT / "release/cvpr_execution_closure/CLEAN_EXTRACTION_TEST.json").read_text()
    )
    assert dependency["passed"] is True and dependency["missing_local_modules"] == []
    assert clean["passed"] is True
    assert clean["synthetic_status"] == "SYNTHETIC_ALL_STUDY_ROUTES_COMPLETE"
    assert (ROOT / "release/certvic_cvpr_execution_closure.zip").is_file()
