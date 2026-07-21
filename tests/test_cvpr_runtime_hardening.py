from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from certvic.cvpr.adapters import BaseAdapter, dynamic_preprocess
from certvic.cvpr.adjudication import extract_disagreements, finalize_inclusion
from certvic.cvpr.agreement import agreement_report
from certvic.cvpr.analysis import outcome_branch, specificity_analysis, write_analysis_artifacts
from certvic.cvpr.candidate_selection import balanced_select, hamming, overlap_certificate
from certvic.cvpr.contracts import canonical_json_bytes, load_yaml
from certvic.cvpr.generation import (
    GenerationError,
    GenerationSettings,
    generate_one,
    run_generation,
)
from certvic.cvpr.model_snapshot_manifest import (
    SnapshotManifestError,
    create_manifest,
    verify_manifest,
    write_manifest,
)
from certvic.cvpr.notebook_builder import NOTEBOOKS
from certvic.cvpr.review_packets import build_visual_packet
from certvic.cvpr.runtime_preflight import PreflightError, prepare_code_bundle
from certvic.cvpr.transactional import read_jsonl
from certvic.cvpr.task_schema import convert_legacy_task
from certvic.cvpr.whole_study_import import StudyImportError, atomic_import_matrix
from certvic.cvpr.worker import run_shard


ROOT = Path(__file__).resolve().parents[1]


def _image(path: Path, *, offset: int = 0) -> None:
    image = Image.new("RGB", (256, 256))
    pixels = image.load()
    for y in range(256):
        for x in range(256):
            pixels[x, y] = ((x + offset) % 256, (y + offset) % 256, (x + y + offset) % 256)
    image.save(path)


def _task(tmp_path: Path, identity: str = "i1") -> dict:
    source = tmp_path / f"{identity}.png"
    _image(source)
    return {
        "item_id": identity,
        "edit_id": identity,
        "source_id": identity,
        "source_image_id": identity,
        "image_path": str(source),
        "source_image_path": str(source),
        "original_image_path": str(source),
        "edited_image_path": str(source),
        "target_bbox": [100, 100, 150, 150],
        "category": "person",
        "question": "Is the person present?",
        "expected_answer": "yes",
        "mock_raw_response": "yes",
    }


def test_deterministic_generation_is_bounded_target_safe_and_resume_checked(tmp_path: Path) -> None:
    task = _task(tmp_path)
    settings = GenerationSettings(
        "structured_texture_patch", seed=12013, area_fraction=0.01, minimum_distance_px=20
    )
    first = generate_one(task, tmp_path / "a.png", settings)
    second = generate_one(task, tmp_path / "b.png", settings)
    assert first["output_sha256"] == second["output_sha256"]
    assert first["metrics"]["target_overlap_pixels"] == 0
    different = generate_one(
        task,
        tmp_path / "c.png",
        GenerationSettings("structured_texture_patch", seed=12014, area_fraction=0.01,
                           minimum_distance_px=20),
    )
    assert different["output_sha256"] != first["output_sha256"]
    assert generate_one(task, tmp_path / "a.png", settings)["status"] == "EXISTING_VALID_OUTPUT"
    _image(tmp_path / "a.png", offset=99)
    with pytest.raises(GenerationError, match="conflicting"):
        generate_one(task, tmp_path / "a.png", settings)
    with pytest.raises(GenerationError, match="allow-full-run"):
        run_generation([task], tmp_path / "run", settings, max_items=None,
                       allow_full_run=False, dry_run=False)
    result = run_generation([task], tmp_path / "smoke", settings, max_items=1,
                            allow_full_run=False, dry_run=False)
    assert result["mode"] == "BOUNDED_SMOKE"
    assert result["generated"] == 1


def test_generation_rejects_bad_source_mask_and_target_geometry(tmp_path: Path) -> None:
    task = _task(tmp_path)
    task["target_mask_path"] = str(tmp_path / "missing-mask.png")
    with pytest.raises(GenerationError, match="missing target mask"):
        generate_one(task, tmp_path / "out.png",
                     GenerationSettings("neutral_color_patch", 1, minimum_distance_px=5))
    task.pop("target_mask_path")
    task["target_bbox"] = [0, 0, 256, 256]
    with pytest.raises(GenerationError, match="no target-safe placement"):
        generate_one(task, tmp_path / "out.png",
                     GenerationSettings("neutral_color_patch", 1, minimum_distance_px=5))


def test_candidate_balance_and_overlap_contracts_fail_closed() -> None:
    config = {
        "design": {"category_targets": {
            "person": {"primary": 1, "reserve": 1, "source_availability": "CENSUS",
                       "expected_answer_polarities": {"yes": 1, "no": 0},
                       "size_strata": {"small": 1}, "position_strata": {"center": 1}}
        }}
    }
    rows = [{"source_id": f"s{i}", "item_id": f"i{i}", "source_image_id": f"s{i}",
             "image_sha256": str(i) * 64, "category": "person", "expected_answer": "yes",
             "target_size_stratum": "small", "target_position_stratum": "center",
             "placement_proposals": {"a": [0, 0, 2, 2]}} for i in range(2)]
    result = balanced_select(rows, config, seed=7)
    assert result["status"] == "BALANCED_SELECTION_COMPLETE"
    assert len(result["primary"]) == len(result["reserve"]) == 1
    certificate = overlap_certificate(result["primary"] + result["reserve"], {
        "item_ids": [], "source_ids": [], "source_image_ids": [], "original_image_sha256": []
    }, [])
    assert certificate["passed"] is True
    assert hamming("1010", "0011") == 2
    assert balanced_select(rows[:1], config, seed=7)["status"] == "BLOCKED_SHORTAGE"


def test_snapshot_manifest_detects_revision_architecture_hash_and_extra_file(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "config.json").write_text(json.dumps({
        "architectures": ["Qwen2_5_VLForConditionalGeneration"], "model_type": "qwen2_5_vl"
    }))
    (snapshot / "tokenizer_config.json").write_text("{}")
    (snapshot / "model.safetensors").write_bytes(b"fixture-weight")
    manifest = create_manifest(
        snapshot, model_id="fixture/qwen", model_commit="a" * 40,
        processor_commit="b" * 40, expected_architecture="Qwen2_5_VLForConditionalGeneration",
    )
    write_manifest(snapshot, manifest)
    assert verify_manifest(snapshot)["passed"] is True
    assert verify_manifest(snapshot, expected_model_commit="c" * 40)["passed"] is False
    (snapshot / "model.safetensors").write_bytes(b"mutated")
    assert any("mismatch" in error for error in verify_manifest(snapshot)["errors"])
    (snapshot / "extra.bin").write_bytes(b"extra")
    assert any("unmanifested" in error for error in verify_manifest(snapshot)["errors"])
    with pytest.raises(SnapshotManifestError, match="architecture mismatch"):
        create_manifest(snapshot, model_id="fixture", model_commit="a" * 40,
                        processor_commit="b" * 40, expected_architecture="WrongArchitecture")


def test_runtime_preflight_extracts_and_imports_hash_locked_bundle(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "certvic").mkdir(parents=True)
    (project / "pyproject.toml").write_text("[project]\nname='fixture'\nversion='0.0.0'\n")
    (project / "certvic/__init__.py").write_text("VALUE = 1\n")
    bundle = tmp_path / "bundle.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        for path in sorted(project.rglob("*")):
            if path.is_file():
                archive.write(path, Path("fixture") / path.relative_to(project))
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    result = prepare_code_bundle(bundle, tmp_path / "unpacked", digest)
    assert result["status"] == "CODE_BUNDLE_READY"
    with pytest.raises(PreflightError, match="hash mismatch"):
        prepare_code_bundle(bundle, tmp_path / "bad", "0" * 64)


class OOMOnceAdapter(BaseAdapter):
    provider = "qwen2_5_vl_7b"

    def prepare(self) -> dict:
        self._prepared = True
        return self.capability_report()

    def generate_one(self, image_path: str, prompt: str) -> str:
        return "yes"

    def generate_batch(self, requests: list[tuple[str, str]]) -> list[str]:
        if len(requests) > 2:
            raise RuntimeError("CUDA out of memory in synthetic adapter")
        return ["yes"] * len(requests)


def test_worker_exercises_batch_oom_resume_validation_and_quarantine(tmp_path: Path) -> None:
    tasks = [_task(tmp_path, "i1"), _task(tmp_path, "i2")]
    task_path = tmp_path / "tasks.jsonl"
    task_path.write_text("".join(json.dumps(task) + "\n" for task in tasks))
    output = tmp_path / "output"
    config = tmp_path / "runtime.json"
    config.write_text(json.dumps({
        "provider": "qwen2_5_vl_7b", "model_id": "fixture", "model_path": str(tmp_path),
        "model_commit": "a" * 40, "processor_commit": "b" * 40,
        "run_tag": "runtime_smoke", "task_manifest": str(task_path), "output_dir": str(output),
        "code_bundle_hash": "f" * 64, "model_snapshot_manifest_hash": "e" * 64,
        "seed": 12013, "generation_parameters": {"do_sample": False},
    }))
    result = run_shard(config, shard=0, num_shards=1, mock_runtime=False, batch_size=4,
                       adapter_factory=lambda _provider, cfg: OOMOnceAdapter(cfg))
    assert result["status"] == "SHARD_COMPLETE"
    assert result["effective_batch_size"] == 2
    assert result["oom_events"] == 1
    complete = output / "shard_0.complete.jsonl"
    rows = read_jsonl(complete)
    rows[0]["model_commit"] = "c" * 40
    complete.write_text("".join(json.dumps(row) + "\n" for row in rows))
    resumed = run_shard(config, shard=0, num_shards=1, mock_runtime=False, batch_size=2,
                        adapter_factory=lambda _provider, cfg: OOMOnceAdapter(cfg))
    assert resumed["status"] == "SHARD_COMPLETE"
    assert list(output.glob("shard_0.complete.jsonl.quarantine.*"))


def _fill_sheet(source: Path, destination: Path, *, disagree: bool = False) -> None:
    with source.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    fieldnames = ["blind_pair_id", "target_unaffected", "expected_answer_unchanged",
                  "perturbation_acceptable", "image_answerable", "prompt_unambiguous",
                  "retain", "confidence", "reason_code"]
    for index, row in enumerate(rows):
        for field in fieldnames[1:6]:
            row[field] = "yes"
        row["retain"] = "no" if disagree and index == 0 else "yes"
        row["confidence"] = "high"
        row["reason_code"] = "OK"
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def test_visual_review_agreement_and_adjudication_are_fail_closed(tmp_path: Path) -> None:
    task = _task(tmp_path)
    edited = tmp_path / "edited.png"
    _image(edited, offset=3)
    task["edited_image_path"] = str(edited)
    packet = tmp_path / "packet"
    result = build_visual_packet([task], "specificity_confirmatory_cvpr", packet, seed=12013)
    assert result["status"] == "HUMAN_REVIEW_PENDING"
    packet_html = (packet / "review_packet.html").read_text()
    assert task["original_image_path"] not in packet_html
    rater_1, rater_2 = tmp_path / "r1.csv", tmp_path / "r2.csv"
    _fill_sheet(packet / "rater_1.csv", rater_1)
    _fill_sheet(packet / "rater_2.csv", rater_2, disagree=True)
    agreement = agreement_report(rater_1, rater_2, rater_1_id="R1", rater_2_id="R2",
                                 bootstrap_draws=50)
    assert agreement["primary_statistic"] == "gwet_ac1_retain"
    adjudication = tmp_path / "adjudication.csv"
    assert extract_disagreements(rater_1, rater_2, adjudication)["disagreements"] == 1
    _fill_sheet(adjudication, tmp_path / "adjudication_complete.csv")
    final = finalize_inclusion(
        rater_1, rater_2, tmp_path / "adjudication_complete.csv", packet / "coordinator_key.csv",
        packet / "packet_hash_manifest.json", packet_root=packet,
    )
    assert final["status"] == "FINAL_INCLUSION_VALIDATED"
    assert len(final["included"]) == 1


def _prediction_row(task: dict, provider: str, model: dict, variant: str,
                    code_hash: str, snapshot_hash: str) -> dict:
    image = Path(task[f"{variant}_image_path"])
    return {
        "item_id": task["item_id"], "variant": variant, "raw_response": "yes",
        "parsed_response": "yes", "parse_status": "PARSE_OK", "provider": provider,
        "model_id": model["model_id"], "model_commit": model["model_commit"],
        "processor_commit": model["processor_commit"],
        "prompt_hash": hashlib.sha256(task["question"].encode()).hexdigest(),
        "image_hash": hashlib.sha256(image.read_bytes()).hexdigest(),
        "task_hash": task.get("task_hash", hashlib.sha256(canonical_json_bytes(task)).hexdigest()),
        "code_bundle_hash": code_hash, "model_snapshot_manifest_hash": snapshot_hash,
        "seed": 1, "generation_parameters": {"do_sample": False}, "shard": 0,
        "timestamp": "2026-07-14T00:00:00Z", "run_tag": "study_v1",
        "parser_version": "certvic.parse.v2",
    }


def _returned_zip(path: Path, task: dict, provider: str, model: dict,
                  code_hash: str, snapshot_hash: str) -> None:
    work = path.parent / f"work_{provider}"
    work.mkdir()
    rows = [_prediction_row(task, provider, model, variant, code_hash, snapshot_hash)
            for variant in ("original", "edited")]
    merged = work / "merged_raw.jsonl"
    merged.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    runtime = {"schema": "certvic.cvpr.runtime_manifest.v2", "study": "study",
               "run_tag": "study_v1", "provider": provider, "model_id": model["model_id"],
               "model_commit": model["model_commit"], "processor_commit": model["processor_commit"],
               "code_bundle_hash": code_hash, "model_snapshot_manifest_hash": snapshot_hash,
               "merged_raw_sha256": hashlib.sha256(merged.read_bytes()).hexdigest(), "rows": 2}
    (work / "runtime_manifest.json").write_text(json.dumps(runtime))
    (work / "environment_manifest.json").write_text(json.dumps({"offline": True}))
    (work / "validation_report.json").write_text(json.dumps({"passed": True}))
    (work / "failure_report.json").write_text(json.dumps({"failures": []}))
    files = sorted(work.glob("*.json*"))
    hashes = {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in files}
    (work / "hash_manifest.json").write_text(json.dumps(hashes))
    with zipfile.ZipFile(path, "w") as archive:
        for file in sorted(work.iterdir()):
            archive.write(file, file.name)


def test_whole_study_import_validates_all_before_atomic_promotion(tmp_path: Path) -> None:
    task = _task(tmp_path)
    task["edited_image_path"] = task["original_image_path"]
    task.update({
        "source_sha256": hashlib.sha256(Path(task["source_image_path"]).read_bytes()).hexdigest(),
        "source_dataset": "SYNTHETIC_FIXTURE", "split": "synthetic",
        "license_status": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
        "required_change": False, "control_edit_family": "structured_texture_patch",
        "selected_engine": "structured_texture_patch",
    })
    task = convert_legacy_task(task, study="synthetic_confirmatory")
    providers = ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]
    models = {provider: {"model_id": provider, "model_commit": character * 40,
                         "processor_commit": character.upper().lower() * 40}
              for provider, character in zip(providers, "abc", strict=True)}
    code_hash = "f" * 64
    snapshots = {provider: str(index) * 64 for index, provider in enumerate(providers, start=1)}
    archives = {}
    for provider in providers:
        archive = tmp_path / f"{provider}.zip"
        _returned_zip(archive, task, provider, models[provider], code_hash, snapshots[provider])
        archives[provider] = archive
    destination = tmp_path / "imported"
    result = atomic_import_matrix(
        archives, study="study", run_tag="study_v1", model_contracts=models, tasks=[task],
        expected_code_bundle_hash=code_hash, expected_snapshot_hashes=snapshots,
        destination_root=destination,
    )
    assert result["status"] == "ATOMIC_MATRIX_PROMOTED"
    assert len(list((destination / "canonical").glob("*.jsonl"))) == 3
    assert atomic_import_matrix(
        archives, study="study", run_tag="study_v1", model_contracts=models, tasks=[task],
        expected_code_bundle_hash=code_hash, expected_snapshot_hashes=snapshots,
        destination_root=destination,
    )["status"] == "IDEMPOTENT"
    bad_destination = tmp_path / "bad-import"
    snapshots[providers[0]] = "9" * 64
    with pytest.raises(StudyImportError):
        atomic_import_matrix(
            archives, study="study", run_tag="study_v1", model_contracts=models, tasks=[task],
            expected_code_bundle_hash=code_hash, expected_snapshot_hashes=snapshots,
            destination_root=bad_destination,
        )
    assert not bad_destination.exists()


def test_analysis_branches_and_artifacts_use_validated_pair_contract(tmp_path: Path) -> None:
    task = {"item_id": "i1", "perturbation_family": "texture", "category": "person"}
    rows = {}
    for provider, edited in (("qwen2_5_vl_7b", "no"), ("internvl_8b", "yes"),
                             ("llava_onevision_7b", "yes")):
        rows[provider] = [
            {"item_id": "i1", "variant": "original", "parse_status": "PARSE_OK",
             "parsed_response": "yes"},
            {"item_id": "i1", "variant": "edited", "parse_status": "PARSE_OK",
             "parsed_response": edited},
        ]
    result = specificity_analysis(rows, [task])
    result["providers"]["qwen2_5_vl_7b"]["primary_missing_as_failure"]["pass"] = False
    result["providers"]["internvl_8b"]["primary_missing_as_failure"]["pass"] = True
    result["providers"]["llava_onevision_7b"]["primary_missing_as_failure"]["pass"] = True
    branch = outcome_branch(result, human_invalidation_rate=0.0)
    assert branch["active_branch"] == "QWEN_FAILS_AGAIN"
    assert write_analysis_artifacts(tmp_path / "analysis", result)["files"] == 4


def test_notebooks_config_and_internvl_contract_are_runtime_hardened() -> None:
    assert len(NOTEBOOKS) == 20
    for smoke in ("00A_certvic_code_and_environment_smoke.ipynb",
                  "00B_qwen2_5_vl_7b_snapshot_smoke.ipynb",
                  "00B_internvl_8b_snapshot_smoke.ipynb",
                  "00B_llava_onevision_7b_snapshot_smoke.ipynb",
                  "00C1_certvic_mock_adapter_smoke.ipynb"):
        assert smoke in NOTEBOOKS
    text = "\n".join(path.read_text() for path in (ROOT / "notebooks/kaggle/cvpr").glob("*.ipynb"))
    assert "diffusers_inpaint_optional" not in text
    assert "--max-items" in text and "--allow-full-run" in text
    assert "NON_EVIDENCE_RUNTIME_SMOKE" in text
    registry = load_yaml(ROOT / "configs/studies/specificity_confirmatory_cvpr.yaml")
    assert len(registry["design"]["category_targets"]) == 12
    wide = Image.new("RGB", (1200, 400))
    tiles = dynamic_preprocess(wide, max_num=6)
    assert 2 <= len(tiles) <= 7
    assert all(tile.size == (448, 448) for tile in tiles)
