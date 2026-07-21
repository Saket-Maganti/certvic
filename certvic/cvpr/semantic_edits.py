"""Answer-changing semantic intervention construction for Main and COCO lanes."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.inpainting import OfflineInpaintingAdapter, validate_mask_contract
from certvic.cvpr.task_schema import require_task
from certvic.cvpr.transactional import read_jsonl


class SemanticEditError(RuntimeError):
    pass


SEMANTIC_FAMILIES = {"object_removal", "object_insertion", "attribute_modification"}
ATTRIBUTE_TRANSFORMS = {
    "red_to_blue", "blue_to_red", "saturated_to_desaturated",
    "desaturated_to_saturated",
}


@dataclass(frozen=True)
class SemanticEditSettings:
    seed: int
    max_target_fraction: float = 0.65
    max_non_target_change_fraction: float = 0.01


def validate_semantic_task(task: dict[str, Any]) -> None:
    require_task(task, verify_files=True)
    required = {
        "item_id", "source_image_path", "question", "original_expected_answer",
        "edited_expected_answer", "semantic_edit_family",
    }
    missing = sorted(required - set(task))
    if missing:
        raise SemanticEditError(f"missing semantic task fields: {missing}")
    if task["semantic_edit_family"] not in SEMANTIC_FAMILIES:
        raise SemanticEditError(f"unsupported semantic edit family: {task['semantic_edit_family']}")
    if str(task["original_expected_answer"]).strip().lower() == str(
        task["edited_expected_answer"]
    ).strip().lower():
        raise SemanticEditError("semantic interventions require an answer-changing target")
    if task.get("required_change") is not True:
        raise SemanticEditError("required_change=true is mandatory for a semantic intervention")


def _mask(task: dict[str, Any], size: tuple[int, int]) -> Image.Image:
    mask_path = task.get("target_mask_path")
    if mask_path:
        path = Path(str(mask_path))
        if not path.is_file():
            raise SemanticEditError(f"missing target mask: {path}")
        with Image.open(path) as opened:
            mask = opened.convert("L")
    else:
        bbox = task.get("target_bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise SemanticEditError("target_mask_path or target_bbox is required")
        mask = Image.new("L", size, 0)
        pixels = mask.load()
        x0, y0, x1, y1 = [int(value) for value in bbox]
        if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
            raise SemanticEditError("target_bbox is outside source dimensions")
        for y in range(y0, y1):
            for x in range(x0, x1):
                pixels[x, y] = 255
    validate_mask_contract(Image.new("RGB", size), mask)
    return mask


def _context_fill(image: Image.Image, mask: Image.Image) -> Image.Image:
    """Deterministic preliminary removal; human validity remains mandatory."""
    array = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    selected = np.asarray(mask) == 255
    dilated = np.asarray(mask.filter(ImageFilter.MaxFilter(11))) == 255
    boundary = dilated & ~selected
    if not boundary.any():
        raise SemanticEditError("object-removal mask has no surrounding context")
    fill = np.median(array[boundary], axis=0).astype(np.uint8)
    array[selected] = fill
    provisional = Image.fromarray(array, "RGB")
    blurred = provisional.filter(ImageFilter.GaussianBlur(radius=3.0))
    provisional.paste(blurred, mask=mask)
    return provisional


def _insert(image: Image.Image, mask: Image.Image, asset_path: str | Path) -> Image.Image:
    path = Path(asset_path)
    if not path.is_file():
        raise SemanticEditError(f"missing insertion asset: {path}")
    with Image.open(path) as opened:
        asset = opened.convert("RGBA")
    bbox = mask.getbbox()
    if bbox is None:
        raise SemanticEditError("insertion mask is empty")
    asset = asset.resize((bbox[2] - bbox[0], bbox[3] - bbox[1]), Image.Resampling.LANCZOS)
    canvas = image.convert("RGBA")
    alpha = np.minimum(np.asarray(asset.getchannel("A")),
                       np.asarray(mask.crop(bbox))).astype(np.uint8)
    asset.putalpha(Image.fromarray(alpha, "L"))
    canvas.alpha_composite(asset, dest=(bbox[0], bbox[1]))
    return canvas.convert("RGB")


def _attribute(image: Image.Image, mask: Image.Image, transform: str) -> Image.Image:
    source = np.asarray(image.convert("RGB"), dtype=np.uint8)
    changed = source.copy()
    selected = np.asarray(mask) == 255
    if transform == "red_to_blue":
        values = source[selected].copy()
        values[:, [0, 2]] = values[:, [2, 0]]
        changed[selected] = values
    elif transform == "blue_to_red":
        values = source[selected].copy()
        values[:, [0, 2]] = values[:, [2, 0]]
        changed[selected] = values
    elif transform == "saturated_to_desaturated":
        luminance = np.mean(source[selected], axis=1, keepdims=True).astype(np.uint8)
        changed[selected] = np.repeat(luminance, 3, axis=1)
    elif transform == "desaturated_to_saturated":
        values = source[selected].astype(np.float64)
        mean = values.mean(axis=1, keepdims=True)
        changed[selected] = np.clip(mean + 1.8 * (values - mean), 0, 255).astype(np.uint8)
    else:
        raise SemanticEditError(f"unsupported attribute transform: {transform}")
    return Image.fromarray(changed, "RGB")


def semantic_quality_metrics(source: Image.Image, edited: Image.Image, mask: Image.Image) -> dict[str, Any]:
    left = np.asarray(source.convert("RGB"), dtype=np.int16)
    right = np.asarray(edited.convert("RGB"), dtype=np.int16)
    selected = np.asarray(mask) == 255
    changed = np.any(left != right, axis=2)
    target_fraction = float(changed[selected].mean()) if selected.any() else 0.0
    non_target = ~selected
    non_target_fraction = float(changed[non_target].mean()) if non_target.any() else 0.0
    return {
        "target_change_fraction": target_fraction,
        "non_target_change_fraction": non_target_fraction,
        "mean_absolute_pixel_delta": float(np.abs(left - right).mean() / 255.0),
        "dimensions_preserved": source.size == edited.size,
        "mode_preserved": edited.mode == "RGB",
    }


def prospective_engine_selection(task: dict[str, Any]) -> dict[str, Any]:
    """Apply the frozen candidate-specific engine hierarchy without observing model outcomes."""
    family = str(task.get("semantic_edit_family", task.get("edit_family", "")))
    if family == "object_removal":
        if task.get("deterministic_simple_case_verified") is True:
            engine = "deterministic_context_fill_preliminary_v1"
            reason = "preverified_simple_background_and_small_mask"
            fallbacks = ["manifest_verified_offline_inpainting_v1", "REJECT"]
        else:
            engine = "manifest_verified_offline_inpainting_v1"
            reason = "complex_removal_requires_context_aware_inpainting"
            fallbacks = ["REJECT"]
    elif family == "object_insertion":
        if task.get("insertion_asset_sha256") and task.get("insertion_asset_license") not in {
            None, "", "UNVERIFIED",
        }:
            engine = "hash_locked_asset_composite_v1"
            reason = "hash_and_license_verified_asset_composite"
            fallbacks = ["manifest_verified_offline_inpainting_v1", "REJECT"]
        else:
            engine = "manifest_verified_offline_inpainting_v1"
            reason = "insertion_requires_scale_placement_occlusion_validation"
            fallbacks = ["REJECT"]
    elif family == "attribute_modification":
        if task.get("original_attribute_verified") is not True:
            return {"status": "REJECT", "engine": None,
                    "reason": "original_attribute_not_verified"}
        transform = str(task.get("attribute_transform", ""))
        expected = f"{task.get('original_attribute')}_to_{task.get('edited_attribute')}"
        if transform != expected or transform not in ATTRIBUTE_TRANSFORMS:
            return {"status": "REJECT", "engine": None,
                    "reason": "attribute_transform_not_registered_or_transition_mismatch"}
        engine = "verified_attribute_transform_v1"
        reason = "verified_attribute_transition"
        fallbacks = ["REJECT"]
    else:
        return {"status": "REJECT", "engine": None, "reason": "unsupported_edit_family"}
    return {"status": "ENGINE_SELECTED", "engine": engine, "reason": reason,
            "fallbacks": fallbacks,
            "policy_version": "certvic.semantic_engine_policy.v1"}


def semantic_verification(
    task: dict[str, Any], metrics: dict[str, Any], *, engine: str
) -> dict[str, Any]:
    """Produce explicit prospective QA/failure states before human review."""
    family = str(task.get("semantic_edit_family", task.get("edit_family", "")))
    semantic_success = metrics.get("target_change_fraction", 0.0) >= 0.25
    non_target_preserved = metrics.get("non_target_change_fraction", 1.0) <= 0.01
    artifact_pass = metrics.get("dimensions_preserved") is True and metrics.get("mode_preserved") is True
    failures: list[str] = []
    if not semantic_success:
        failures.append("semantic_target_change_too_weak")
    if not non_target_preserved:
        failures.append("non_target_preservation_failed")
    if not artifact_pass:
        failures.append("image_contract_or_artifact_check_failed")
    if family == "object_removal" and engine.startswith("deterministic_") and task.get(
        "deterministic_simple_case_verified"
    ) is not True:
        failures.append("deterministic_removal_not_candidate_verified")
    if family == "object_insertion":
        if task.get("insertion_asset_license") in {None, "", "UNVERIFIED"}:
            failures.append("insertion_asset_license_unverified")
        if not task.get("insertion_asset_sha256"):
            failures.append("insertion_asset_hash_missing")
    if family == "attribute_modification" and task.get("original_attribute_verified") is not True:
        failures.append("original_attribute_not_verified")
    return {
        "schema": "certvic.cvpr.semantic_quality.v1",
        "semantic_success_status": "PASS" if semantic_success else "FAIL",
        "artifact_status": "PASS" if artifact_pass else "FAIL",
        "non_target_preservation_status": "PASS" if non_target_preserved else "FAIL",
        "answerability_status": "HUMAN_REVIEW_PENDING" if not failures else "BLOCKED_AUTOMATED_QA",
        "automated_qa_status": "PASS" if not failures else "FAIL",
        "failure_modes": failures,
        "engine_fallback_history": task.get("engine_fallback_history", []),
        "paper_evidence": False,
    }


def _validated_existing(
    destination: Path, task: dict[str, Any], *, engine: str,
) -> dict[str, Any] | None:
    record_path = destination.with_suffix(".semantic_record.json")
    if not destination.exists() and not record_path.exists():
        return None
    if not destination.is_file() or not record_path.is_file():
        raise SemanticEditError("partial existing semantic output cannot be resumed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    expected = {
        "item_id": task["item_id"], "engine": engine,
        "task_sha256": str(task.get("task_hash") or sha256_bytes(canonical_json_bytes(task))),
        "edited_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
    }
    mismatches = [field for field, value in expected.items() if record.get(field) != value]
    if mismatches:
        raise SemanticEditError(f"existing semantic output conflicts with task contract: {mismatches}")
    return {**record, "status": "EXISTING_VALID_OUTPUT"}


def generate_semantic_edit(
    task: dict[str, Any],
    output_path: str | Path,
    settings: SemanticEditSettings,
) -> dict[str, Any]:
    validate_semantic_task(task)
    decision = prospective_engine_selection(task)
    if decision["status"] != "ENGINE_SELECTED":
        raise SemanticEditError(f"engine selection rejected task: {decision['reason']}")
    if task.get("selected_engine") != decision["engine"]:
        raise SemanticEditError("task selected_engine differs from prospective engine policy")
    source_path = Path(str(task["source_image_path"]))
    if not source_path.is_file():
        raise SemanticEditError(f"missing source image: {source_path}")
    with Image.open(source_path) as opened:
        source = opened.convert("RGB")
    mask = _mask(task, source.size)
    family = str(task["semantic_edit_family"])
    if family == "object_removal":
        if decision["engine"] != "deterministic_context_fill_preliminary_v1":
            raise SemanticEditError("complex removal requires the offline inpainting execution path")
        edited = _context_fill(source, mask)
        engine = "deterministic_context_fill_preliminary_v1"
    elif family == "object_insertion":
        if decision["engine"] != "hash_locked_asset_composite_v1":
            raise SemanticEditError("insertion requires offline inpainting or a verified asset composite")
        edited = _insert(source, mask, str(task.get("insertion_asset_path", "")))
        engine = "hash_locked_asset_composite_v1"
    else:
        transform = str(task.get("attribute_transform", ""))
        if transform not in ATTRIBUTE_TRANSFORMS:
            raise SemanticEditError("attribute task has no registered explicit transform")
        edited = _attribute(source, mask, transform)
        engine = "verified_attribute_transform_v1"
    destination = Path(output_path)
    existing = _validated_existing(destination, task, engine=engine)
    if existing is not None:
        with Image.open(destination) as opened:
            observed = np.asarray(opened.convert("RGB"))
        if not np.array_equal(observed, np.asarray(edited.convert("RGB"))):
            raise SemanticEditError("existing semantic output is not byte-contract equivalent")
        return existing
    metrics = semantic_quality_metrics(source, edited, mask)
    quality = semantic_verification(task, metrics, engine=engine)
    mask_fraction = mask.histogram()[255] / (source.width * source.height)
    if mask_fraction > settings.max_target_fraction:
        raise SemanticEditError("semantic mask exceeds the frozen target-area bound")
    if metrics["target_change_fraction"] == 0:
        raise SemanticEditError("semantic edit did not change any target pixel")
    if metrics["non_target_change_fraction"] > settings.max_non_target_change_fraction:
        raise SemanticEditError("semantic edit changed too many non-target pixels")
    destination.parent.mkdir(parents=True, exist_ok=True)
    edited.save(destination, format="PNG", compress_level=9)
    record = {
        "schema": "certvic.cvpr.semantic_edit_record.v1",
        "item_id": task["item_id"],
        "semantic_edit_family": family,
        "question": task["question"],
        "original_expected_answer": task["original_expected_answer"],
        "edited_expected_answer": task["edited_expected_answer"],
        "required_change": True,
        "source_image_path": str(source_path),
        "edited_image_path": str(destination),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "edited_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "mask_sha256": sha256_bytes(mask.tobytes()),
        "task_sha256": str(task.get("task_hash") or sha256_bytes(canonical_json_bytes(task))),
        "engine": engine,
        "engine_policy": decision["policy_version"],
        "engine_selection_reason": decision["reason"],
        "engine_fallback_sequence": decision["fallbacks"],
        "final_engine_used": engine,
        "seed": settings.seed,
        "status": "GENERATED",
        "metrics": metrics,
        "quality": quality,
        "automated_semantic_status": (
            "AUTOMATED_QA_PASS_HUMAN_REVIEW_PENDING"
            if quality["automated_qa_status"] == "PASS"
            else "MACHINE_ASSISTED_PRELIMINARY_BLOCKED_AUTOMATED_QA"
        ),
        "human_validity_status": "HUMAN_REVIEW_PENDING",
        "review_eligibility_status": (
            "ELIGIBLE_FOR_HUMAN_REVIEW" if quality["automated_qa_status"] == "PASS"
            else "BLOCKED_AUTOMATED_QA_FAILED"
        ),
        "paper_evidence": False,
    }
    destination.with_suffix(".semantic_record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return record


def run_semantic_generation(
    tasks: list[dict[str, Any]], out_dir: str | Path, *, seed: int,
    max_items: int | None, allow_full_run: bool,
) -> dict[str, Any]:
    if max_items is None and not allow_full_run:
        raise SemanticEditError("unbounded generation requires allow_full_run=true")
    selected = tasks if max_items is None else tasks[:max_items]
    out = Path(out_dir)
    records = [generate_semantic_edit(
        task, out / "images" / f"{task['item_id']}.png", SemanticEditSettings(seed + index)
    ) for index, task in enumerate(selected)]
    manifest = {
        "schema": "certvic.cvpr.semantic_generation_manifest.v1",
        "runtime_class": "PLANNED_SCIENTIFIC_GENERATION",
        "requested_total": len(tasks), "processed": len(records),
        "bounded": max_items is not None, "records": records,
        "human_validity_status": "HUMAN_REVIEW_PENDING", "paper_evidence": False,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "semantic_generation_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def run_inpainting_generation(
    tasks: list[dict[str, Any]], out_dir: str | Path, *, seed: int,
    max_items: int | None, allow_full_run: bool, adapter: OfflineInpaintingAdapter,
    batch_size: int = 1,
) -> dict[str, Any]:
    if max_items is None and not allow_full_run:
        raise SemanticEditError("unbounded generation requires allow_full_run=true")
    selected = tasks if max_items is None else tasks[:max_items]
    requests: list[dict[str, Any]] = []
    sources: list[tuple[dict[str, Any], Image.Image, Image.Image, dict[str, Any]]] = []
    record_by_id: dict[str, dict[str, Any]] = {}
    out = Path(out_dir)
    for task in selected:
        validate_semantic_task(task)
        decision = prospective_engine_selection(task)
        if decision.get("engine") != "manifest_verified_offline_inpainting_v1" or task.get(
            "selected_engine"
        ) != decision.get("engine"):
            raise SemanticEditError(
                f"{task['item_id']}: offline inpainting is not the prospective selected engine"
            )
        source_path = Path(str(task["source_image_path"]))
        with Image.open(source_path) as opened:
            source = opened.convert("RGB")
        mask = _mask(task, source.size)
        destination = out / "images" / f"{task['item_id']}.png"
        existing = _validated_existing(
            destination, task, engine="manifest_verified_offline_inpainting_v1"
        )
        if existing is not None:
            record_by_id[str(task["item_id"])] = existing
            continue
        prompt = str(task.get("inpainting_prompt", "")).strip()
        if not prompt:
            raise SemanticEditError(f"{task['item_id']}: inpainting_prompt must be frozen")
        requests.append({"image": source, "mask": mask, "prompt": prompt,
                         "num_inference_steps": int(task.get("num_inference_steps", 30)),
                         "guidance_scale": float(task.get("guidance_scale", 7.5))})
        sources.append((task, source, mask, decision))
    events: list[dict[str, Any]] = []
    generated: list[Image.Image] = []
    if requests:
        adapter.prepare()
        try:
            generated, events = adapter.generate_batch(requests, batch_size=batch_size, seed=seed)
        finally:
            adapter.release()
    for (task, source, mask, decision), edited in zip(sources, generated, strict=True):
        if edited.size != source.size:
            raise SemanticEditError("inpainting changed source dimensions")
        destination = out / "images" / f"{task['item_id']}.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        edited.convert("RGB").save(destination, format="PNG", compress_level=9)
        metrics = semantic_quality_metrics(source, edited, mask)
        quality = semantic_verification(
            task, metrics, engine="manifest_verified_offline_inpainting_v1"
        )
        record = {
            "schema": "certvic.cvpr.semantic_edit_record.v1", "item_id": task["item_id"],
            "semantic_edit_family": task["semantic_edit_family"], "question": task["question"],
            "original_expected_answer": task["original_expected_answer"],
            "edited_expected_answer": task["edited_expected_answer"], "required_change": True,
            "source_sha256": hashlib.sha256(Path(task["source_image_path"]).read_bytes()).hexdigest(),
            "edited_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "mask_sha256": sha256_bytes(mask.tobytes()),
            "task_sha256": str(task.get("task_hash") or sha256_bytes(canonical_json_bytes(task))),
            "engine": "manifest_verified_offline_inpainting_v1", "seed": seed,
            "engine_policy": decision["policy_version"],
            "engine_selection_reason": decision["reason"],
            "engine_fallback_sequence": decision["fallbacks"],
            "final_engine_used": "manifest_verified_offline_inpainting_v1",
            "status": "GENERATED",
            "metrics": metrics, "quality": quality,
            "automated_semantic_status": (
                "AUTOMATED_QA_PASS_HUMAN_REVIEW_PENDING"
                if quality["automated_qa_status"] == "PASS"
                else "MACHINE_ASSISTED_PRELIMINARY_BLOCKED_AUTOMATED_QA"
            ),
            "human_validity_status": "HUMAN_REVIEW_PENDING", "paper_evidence": False,
        }
        destination.with_suffix(".semantic_record.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        record_by_id[str(task["item_id"])] = record
    records = [record_by_id[str(task["item_id"])] for task in selected]
    manifest = {
        "schema": "certvic.cvpr.semantic_generation_manifest.v1",
        "runtime_class": "PLANNED_SCIENTIFIC_GENERATION",
        "engine": "manifest_verified_offline_inpainting_v1",
        "requested_total": len(tasks), "processed": len(records),
        "bounded": max_items is not None, "records": records, "runtime_events": events,
        "adapter_prepare_calls": adapter.prepare_calls,
        "human_validity_status": "HUMAN_REVIEW_PENDING", "paper_evidence": False,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "semantic_generation_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate answer-changing CertVIC semantic edits")
    parser.add_argument("--task-manifest", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--seed", type=int, default=15001)
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--allow-full-run", action="store_true")
    parser.add_argument("--resume", action="store_true",
                        help="reuse only existing outputs whose records and bytes revalidate")
    parser.add_argument("--inpainting-snapshot")
    parser.add_argument("--inpainting-manifest")
    parser.add_argument("--inpainting-model-id")
    parser.add_argument("--inpainting-model-commit")
    parser.add_argument("--inpainting-architecture")
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args(argv)
    tasks = read_jsonl(args.task_manifest)
    if args.inpainting_snapshot or args.inpainting_manifest:
        required = [args.inpainting_snapshot, args.inpainting_manifest, args.inpainting_model_id,
                    args.inpainting_model_commit, args.inpainting_architecture]
        if any(not value for value in required):
            parser.error("all inpainting snapshot/model fields are required together")
        adapter = OfflineInpaintingAdapter(
            snapshot_dir=args.inpainting_snapshot, snapshot_manifest=args.inpainting_manifest,
            expected_model_id=args.inpainting_model_id,
            expected_model_commit=args.inpainting_model_commit,
            expected_architecture=args.inpainting_architecture,
        )
        result = run_inpainting_generation(
            tasks, args.out_dir, seed=args.seed, max_items=args.max_items,
            allow_full_run=args.allow_full_run, adapter=adapter, batch_size=args.batch_size,
        )
    else:
        result = run_semantic_generation(
            tasks, args.out_dir, seed=args.seed,
            max_items=args.max_items, allow_full_run=args.allow_full_run,
        )
    print(json.dumps({"status": "SEMANTIC_GENERATION_COMPLETE", "processed": result["processed"],
                      "paper_evidence": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
