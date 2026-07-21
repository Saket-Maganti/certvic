"""Tiny local edit generation from planned edit manifests."""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from certvic.edit.inpaint import SimpleFillInpainter
from certvic.edit.quality_gates import DEFAULT_QUALITY_CONFIG, evaluate_edit_quality
from certvic.hashing import sha256_file
from certvic.io import read_jsonl, write_json, write_jsonl
from certvic.schema import EditType


class EditGenerationError(ValueError):
    """Raised when edit generation cannot proceed."""


def generate_edits(
    edit_plan_path: str,
    out_dir: str,
    out_manifest: str,
    rejected_out: str,
    summary_out: str,
    max_items: int = 20,
    mode: str = "simple",
    seed: int = 0,
    quality_config: dict | None = None,
    diffusers_model_id: str | None = None,
) -> dict:
    if max_items <= 0:
        raise EditGenerationError("max_items must be positive")
    if mode == "diffusers_inpaint":
        _assert_diffusers_mode_available(diffusers_model_id)
    if mode != "simple":
        raise EditGenerationError(f"Unsupported generator mode: {mode}")

    plans = read_jsonl(edit_plan_path)[:max_items]
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[dict] = []
    rejected: list[dict] = []
    cfg = {**DEFAULT_QUALITY_CONFIG, **(quality_config or {})}

    for index, plan in enumerate(plans):
        try:
            record = _generate_simple_edit(plan, output_dir, seed=seed, index=index, quality_config=cfg)
            generated.append(record)
        except Exception as exc:
            rejected.append(_rejected_record(plan, mode, seed, str(exc)))

    write_jsonl(out_manifest, generated)
    write_jsonl(rejected_out, rejected)
    summary = {
        "edit_plan_path": edit_plan_path,
        "out_dir": out_dir,
        "out_manifest": out_manifest,
        "rejected_out": rejected_out,
        "mode": mode,
        "seed": seed,
        "max_items": max_items,
        "input_plans": len(plans),
        "generated": len(generated),
        "rejected": len(rejected),
        "quality_passed": sum(1 for row in generated if row.get("quality_gate_status") == "pass"),
        "quality_failed": sum(1 for row in generated if row.get("quality_gate_status") != "pass"),
        "by_edit_type": dict(sorted(Counter(row["edit_type"] for row in generated).items())),
        "rejection_reasons": dict(sorted(Counter(row["rejection_reason"] for row in rejected).items())),
        "evidence_status": "GENERATED_EDIT_ONLY",
        "zero_cost": True,
        "vlm_inference_run": False,
        "paper_evidence": False,
    }
    write_json(summary_out, summary)
    return summary


def _generate_simple_edit(
    plan: dict,
    out_dir: Path,
    seed: int,
    index: int,
    quality_config: dict,
) -> dict:
    _validate_plan_for_generation(plan)
    image_path = Path(str(plan.get("image_path") or plan.get("original_image_path")))
    if not image_path.exists():
        raise EditGenerationError(f"original image path does not exist: {image_path}")
    image = Image.open(image_path).convert("RGB")
    mask, mask_source_info = _load_mask_for_plan(plan, image.size)
    edit_type = str(plan.get("edit_type"))
    edit_id = str(plan["edit_id"])
    out_path = out_dir / f"{edit_id}.png"
    rng = random.Random(f"{seed}|{index}|{edit_id}")

    if edit_type == EditType.REMOVE.value:
        edited, actual_params = _simple_remove(image, mask, plan, seed)
    elif edit_type == EditType.OCCLUDE.value:
        edited, actual_params = _simple_occlude(image, mask, plan, rng, seed)
    elif edit_type == EditType.DISPLACE.value:
        edited, actual_params = _simple_displace(image, mask, plan, seed)
    elif edit_type == EditType.CONTROL_IRRELEVANT.value:
        edited, actual_params = _simple_control(image, mask, plan, seed)
    else:
        raise EditGenerationError(f"unsupported edit type for simple generation: {edit_type}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    edited.save(out_path)
    edited_sha256 = sha256_file(out_path)
    quality = evaluate_edit_quality(
        str(image_path),
        str(out_path),
        mask,
        edit_type=edit_type,
        planned_params=plan.get("planned_params") or {},
        actual_params=actual_params,
        config=quality_config,
    )
    return {
        "edit_id": edit_id,
        "source_id": plan.get("source_id"),
        "mask_id": plan.get("mask_id"),
        "task_family": plan.get("task_family"),
        "domain": plan.get("domain"),
        "split": plan.get("split", "pilot"),
        "edit_type": edit_type,
        "required_change": plan.get("required_change"),
        "original_image_path": str(image_path),
        "edited_image_path": str(out_path),
        "mask_source_info": mask_source_info,
        "planned_params": plan.get("planned_params") or {},
        "actual_params": actual_params,
        "generation_status": "generated",
        "evidence_status": "GENERATED_EDIT_ONLY",
        "generator_mode": "simple",
        "seed": seed,
        "edited_sha256": edited_sha256,
        "quality_gate_status": quality["quality_gate_status"],
        "quality": quality,
        "rejection_reason": None,
        "zero_cost": True,
        "vlm_inference_run": False,
        "paper_evidence": False,
    }


def _validate_plan_for_generation(plan: dict) -> None:
    if plan.get("evidence_status") != "PLANNED_ONLY":
        raise EditGenerationError("edit plan evidence_status must be PLANNED_ONLY")
    if plan.get("generation_status") not in {None, "not_generated"}:
        raise EditGenerationError("edit plan was already marked generated")
    for key in ["edit_id", "source_id", "edit_type"]:
        if not plan.get(key):
            raise EditGenerationError(f"missing required plan field: {key}")


def _load_mask_for_plan(plan: dict, image_size: tuple[int, int]) -> tuple[np.ndarray, dict]:
    width, height = image_size
    mask_path = plan.get("mask_path")
    label_id = plan.get("label_id")
    if mask_path and Path(str(mask_path)).exists():
        arr = np.asarray(Image.open(str(mask_path)).convert("L"))
        if arr.shape != (height, width):
            raise EditGenerationError(
                f"mask dimensions {(arr.shape[1], arr.shape[0])} do not match image size {image_size}"
            )
        if label_id is not None and np.any(arr == int(label_id)):
            return arr == int(label_id), {
                "mask_path": str(mask_path),
                "mask_mode": "semantic_label_id",
                "label_id": int(label_id),
            }
        return arr > 127, {"mask_path": str(mask_path), "mask_mode": "binary_or_thresholded"}
    bbox = plan.get("bbox") or (plan.get("planned_params") or {}).get("bbox")
    if bbox:
        mask = _mask_from_bbox(bbox, image_size)
        return mask, {"mask_path": mask_path, "mask_mode": "bbox_fallback", "bbox": bbox}
    raise EditGenerationError("mask path missing/unavailable and bbox fallback missing")


def _simple_remove(image: Image.Image, mask: np.ndarray, plan: dict, seed: int) -> tuple[Image.Image, dict]:
    fill = _outside_mean_fill(image, mask)
    edited = SimpleFillInpainter().inpaint(image, mask, fill=fill)
    return edited, {
        "operation": "simple_fill_remove",
        "fill_rgb": list(fill),
        "bbox": plan.get("bbox") or (plan.get("planned_params") or {}).get("bbox"),
        "seed": seed,
    }


def _simple_occlude(
    image: Image.Image,
    mask: np.ndarray,
    plan: dict,
    rng: random.Random,
    seed: int,
) -> tuple[Image.Image, dict]:
    arr = np.asarray(image).copy()
    bbox = plan.get("bbox") or (plan.get("planned_params") or {}).get("bbox") or _bbox_from_mask(mask)
    if not _valid_bbox(bbox, image.size):
        raise EditGenerationError("invalid bbox for occlude edit")
    color = [70 + rng.randrange(40), 70 + rng.randrange(40), 70 + rng.randrange(40)]
    x1, y1, x2, y2 = [int(value) for value in bbox]
    arr[y1:y2, x1:x2] = np.asarray(color, dtype="uint8")
    return Image.fromarray(arr), {
        "operation": "simple_bbox_occluder",
        "occluder_bbox": [x1, y1, x2, y2],
        "occluder_rgb": color,
        "seed": seed,
    }


def _simple_displace(image: Image.Image, mask: np.ndarray, plan: dict, seed: int) -> tuple[Image.Image, dict]:
    offset = (plan.get("planned_params") or {}).get("offset_xy") or [16, 0]
    dx, dy = int(offset[0]), int(offset[1])
    arr = np.asarray(image).copy()
    object_pixels = arr.copy()
    edited = np.asarray(SimpleFillInpainter().inpaint(image, mask, fill=_outside_mean_fill(image, mask))).copy()
    ys, xs = np.where(mask)
    ny = ys + dy
    nx = xs + dx
    ok = (ny >= 0) & (ny < edited.shape[0]) & (nx >= 0) & (nx < edited.shape[1])
    edited[ny[ok], nx[ok]] = object_pixels[ys[ok], xs[ok]]
    destination_mask = np.zeros(mask.shape, dtype=bool)
    destination_mask[ny[ok], nx[ok]] = True
    return Image.fromarray(edited), {
        "operation": "simple_cut_paste_displace",
        "offset_xy": [dx, dy],
        "bbox": plan.get("bbox") or (plan.get("planned_params") or {}).get("bbox"),
        "destination_bbox": _bbox_from_mask(destination_mask),
        "seed": seed,
    }


def _simple_control(image: Image.Image, mask: np.ndarray, plan: dict, seed: int) -> tuple[Image.Image, dict]:
    arr = np.asarray(image).copy()
    bbox = _control_region_bbox(mask, image.size)
    x1, y1, x2, y2 = bbox
    patch = arr[y1:y2, x1:x2].astype(int)
    patch = np.clip(patch + np.asarray([8, 0, 8]), 0, 255)
    arr[y1:y2, x1:x2] = patch.astype("uint8")
    return Image.fromarray(arr), {
        "operation": "simple_irrelevant_corner_tint",
        "control_region_bbox": bbox,
        "bbox": plan.get("bbox") or (plan.get("planned_params") or {}).get("bbox"),
        "seed": seed,
    }


def _outside_mean_fill(image: Image.Image, mask: np.ndarray) -> tuple[int, int, int]:
    arr = np.asarray(image.convert("RGB"))
    outside = arr[~mask]
    if len(outside) == 0:
        return (238, 238, 232)
    fill = np.mean(outside, axis=0).round().astype(int)
    return tuple(int(value) for value in fill)


def _control_region_bbox(mask: np.ndarray, image_size: tuple[int, int]) -> list[int]:
    width, height = image_size
    size = max(2, min(width, height) // 4)
    candidates = [
        [0, 0, size, size],
        [width - size, 0, width, size],
        [0, height - size, size, height],
        [width - size, height - size, width, height],
    ]
    return min(candidates, key=lambda bbox: _mask_overlap(mask, bbox))


def _mask_overlap(mask: np.ndarray, bbox: list[int]) -> int:
    x1, y1, x2, y2 = bbox
    return int(mask[y1:y2, x1:x2].sum())


def _mask_from_bbox(bbox: list[int], image_size: tuple[int, int]) -> np.ndarray:
    if not _valid_bbox(bbox, image_size):
        raise EditGenerationError("invalid bbox fallback for mask")
    width, height = image_size
    mask = np.zeros((height, width), dtype=bool)
    x1, y1, x2, y2 = [int(value) for value in bbox]
    mask[y1:y2, x1:x2] = True
    return mask


def _bbox_from_mask(mask: np.ndarray) -> list[int]:
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return [0, 0, 0, 0]
    return [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]


def _valid_bbox(bbox: Any, image_size: tuple[int, int]) -> bool:
    if not isinstance(bbox, list) or len(bbox) != 4:
        return False
    if any(not isinstance(value, int) or value < 0 for value in bbox):
        return False
    x1, y1, x2, y2 = bbox
    width, height = image_size
    return x2 > x1 and y2 > y1 and x2 <= width and y2 <= height


def _rejected_record(plan: dict, mode: str, seed: int, reason: str) -> dict:
    return {
        "edit_id": plan.get("edit_id"),
        "source_id": plan.get("source_id"),
        "mask_id": plan.get("mask_id"),
        "task_family": plan.get("task_family"),
        "domain": plan.get("domain"),
        "edit_type": plan.get("edit_type"),
        "required_change": plan.get("required_change"),
        "original_image_path": plan.get("image_path") or plan.get("original_image_path"),
        "edited_image_path": None,
        "mask_source_info": {"mask_path": plan.get("mask_path"), "label_id": plan.get("label_id")},
        "planned_params": plan.get("planned_params") or {},
        "actual_params": {},
        "generation_status": "rejected",
        "evidence_status": "GENERATED_EDIT_ONLY",
        "generator_mode": mode,
        "seed": seed,
        "edited_sha256": None,
        "quality_gate_status": "not_run",
        "rejection_reason": reason,
        "zero_cost": True,
        "vlm_inference_run": False,
        "paper_evidence": False,
    }


def _assert_diffusers_mode_available(model_id: str | None) -> None:
    if importlib.util.find_spec("torch") is None or importlib.util.find_spec("diffusers") is None:
        raise EditGenerationError(
            "diffusers_inpaint mode requires optional local vision dependencies; simple mode remains available."
        )
    if not model_id:
        raise EditGenerationError(
            "diffusers_inpaint mode requires an explicit local/pre-cached --diffusers-model-id. "
            "CertVIC will not download model weights automatically."
        )
    path = Path(model_id)
    if not path.exists():
        raise EditGenerationError(
            f"diffusers_inpaint model/cache path not found: {model_id}. "
            "Prepare local weights explicitly; network downloads are disabled by policy."
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edit-plan", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--rejected-out", required=True)
    parser.add_argument("--summary-out", required=True)
    parser.add_argument("--max-items", type=int, default=20)
    parser.add_argument("--mode", default="simple", choices=["simple", "diffusers_inpaint"])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--quality-config-json")
    parser.add_argument("--diffusers-model-id")
    args = parser.parse_args(argv)
    quality_config = json.loads(args.quality_config_json) if args.quality_config_json else None
    try:
        summary = generate_edits(
            args.edit_plan,
            args.out_dir,
            args.out_manifest,
            args.rejected_out,
            args.summary_out,
            max_items=args.max_items,
            mode=args.mode,
            seed=args.seed,
            quality_config=quality_config,
            diffusers_model_id=args.diffusers_model_id,
        )
    except EditGenerationError as exc:
        raise SystemExit(f"Edit generation failed: {exc}") from None
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
