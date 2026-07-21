"""Build absent-category controls with an executable protected-scene policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

from certvic.cvpr.contracts import load_yaml
from certvic.cvpr.task_schema import TASK_SCHEMA, require_task, with_task_hash
from certvic.cvpr.transactional import read_jsonl


class NegativeItemError(ValueError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(root: Path, value: Any) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else root / path


def _bbox(mask: np.ndarray, value: Any) -> None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise NegativeItemError("protected annotation bbox must contain four coordinates")
    x0, y0, x1, y1 = [int(round(float(part))) for part in value]
    height, width = mask.shape
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise NegativeItemError("protected annotation bbox is outside the source image")
    mask[y0:y1, x0:x1] = True


def _protected_mask(root: Path, source: dict[str, Any], size: tuple[int, int]) -> tuple[np.ndarray, list[str]]:
    width, height = size
    protected = np.zeros((height, width), dtype=bool)
    annotation_ids: list[str] = []
    annotations = source.get("annotations")
    if not isinstance(annotations, list):
        raise NegativeItemError("complete source annotations are required")
    for index, annotation in enumerate(annotations):
        annotation_ids.append(str(annotation.get("annotation_id", index)))
        mask_value = annotation.get("mask_path")
        if mask_value:
            path = _path(root, mask_value)
            if not path.is_file():
                raise NegativeItemError(f"protected annotation mask is missing: {path}")
            with Image.open(path) as opened:
                if opened.size != size:
                    raise NegativeItemError("protected annotation mask dimensions differ from source")
                protected |= np.asarray(opened.convert("L")) > 0
        else:
            _bbox(protected, annotation.get("bbox"))
    text_status = str(source.get("text_protection_status", ""))
    text_value = source.get("protected_text_mask_path")
    if text_status not in {"OCR_VERIFIED_NO_TEXT", "ANNOTATION_VERIFIED_NO_TEXT"}:
        if not text_value:
            raise NegativeItemError("protected text mask or verified no-text status is required")
        path = _path(root, text_value)
        if not path.is_file():
            raise NegativeItemError("protected text mask is missing")
        with Image.open(path) as opened:
            if opened.size != size:
                raise NegativeItemError("protected text mask dimensions differ from source")
            protected |= np.asarray(opened.convert("L")) > 0
    return protected, annotation_ids


def _region(
    image: Image.Image,
    protected: np.ndarray,
    *,
    identity: str,
    area_fraction: float,
    distance: int,
    boundary: int,
    minimum_stddev: float,
) -> tuple[list[int], dict[str, Any]]:
    width, height = image.size
    side = max(4, int(round(math.sqrt(width * height * area_fraction))))
    if side + 2 * boundary > min(width, height):
        raise NegativeItemError("requested background region does not fit inside image boundaries")
    expanded = Image.fromarray((protected.astype(np.uint8) * 255), "L")
    remaining = max(0, distance)
    while remaining:
        radius = min(49, remaining)
        expanded = expanded.filter(ImageFilter.MaxFilter(2 * radius + 1))
        remaining -= radius
    forbidden = np.asarray(expanded) > 0
    pixels = np.asarray(image.convert("RGB"), dtype=np.float64)
    candidates: list[tuple[str, list[int], float]] = []
    step = max(1, side // 4)
    for y in range(boundary, height - boundary - side + 1, step):
        for x in range(boundary, width - boundary - side + 1, step):
            if forbidden[y:y + side, x:x + side].any():
                continue
            stddev = float(pixels[y:y + side, x:x + side].std())
            if stddev < minimum_stddev:
                continue
            box = [x, y, x + side, y + side]
            order = hashlib.sha256(f"{identity}:{box}".encode()).hexdigest()
            candidates.append((order, box, stddev))
    if not candidates:
        raise NegativeItemError("no verified background-only region satisfies the frozen policy")
    _, box, stddev = min(candidates)
    x0, y0, x1, y1 = box
    return box, {
        "status": "PASS", "protected_overlap_pixels": int(protected[y0:y1, x0:x1].sum()),
        "boundary_margin_px": boundary, "minimum_protected_distance_px": distance,
        "region_stddev": stddev, "low_information_rejected": False,
        "selection": "DETERMINISTIC_OUTCOME_UNSEEN_SHA256_ORDER",
    }


def build_negative_item(
    source_root: str | Path,
    source: dict[str, Any],
    queried_category: str,
    out_dir: str | Path,
    *,
    config: dict[str, Any],
    seed: int,
) -> dict[str, Any]:
    root, out = Path(source_root), Path(out_dir)
    image_path = _path(root, source.get("source_image_path", source.get("image_path", "")))
    if not image_path.is_file():
        raise NegativeItemError("source image is missing")
    if source.get("license_eligible") is not True:
        raise NegativeItemError("source image license is not verified eligible")
    categories = {str(row.get("category", "")) for row in source.get("annotations", [])}
    if queried_category in categories:
        raise NegativeItemError("queried category is present; absent-category assertion failed")
    with Image.open(image_path) as opened:
        opened.load()
        image = opened.convert("RGB")
    protected, annotation_ids = _protected_mask(root, source, image.size)
    policy = config.get("negative_item_policy", config)
    identity = f"negative-{source.get('source_image_id', source.get('source_id'))}-{queried_category}"
    box, validation = _region(
        image, protected, identity=identity,
        area_fraction=float(policy.get("perturbation_area_fraction", 0.01)),
        distance=int(policy.get("minimum_distance_from_any_protected_region_px", 75)),
        boundary=int(policy.get("image_boundary_margin_px", 4)),
        minimum_stddev=float(policy.get("minimum_background_stddev", 2.0)),
    )
    out.mkdir(parents=True, exist_ok=True)
    protected_path = out / f"{identity}.protected_scene.png"
    Image.fromarray(protected.astype(np.uint8) * 255, "L").save(
        protected_path, format="PNG", compress_level=9
    )
    task = {
        "task_schema_version": TASK_SCHEMA,
        "study": "specificity_confirmatory_cvpr",
        "task_id": identity, "item_id": identity,
        "source_dataset": source.get("source_dataset", source.get("dataset", "ADE20K")),
        "source_split": source.get("source_split", source.get("split", "validation")),
        "source_image_id": str(source.get("source_image_id", source.get("source_id"))),
        "source_image_path": str(image_path), "source_image_hash": _sha(image_path),
        "license_status": source.get("license_status", "VERIFIED_ELIGIBLE"),
        "question": f"Is there a {queried_category} in the image?",
        "original_expected_answer": "no", "edited_expected_answer": "no",
        "required_change": False, "semantic_edit_family": None,
        "control_edit_family": policy.get("control_edit_family", "structured_texture_patch"),
        "target_category": None, "queried_category": queried_category,
        "queried_category_absent": True, "target_bbox": box,
        "target_mask_path": None, "target_mask_hash": None,
        "protected_scene_mask_path": str(protected_path),
        "protected_scene_mask_hash": _sha(protected_path),
        "attribute_name": None, "original_attribute": None, "edited_attribute": None,
        "attribute_transform": None, "original_attribute_verified": None,
        "edit_engine_policy": str(policy.get("policy_id", "absent_category_protected_scene_v1")),
        "selected_engine": policy.get("control_edit_family", "structured_texture_patch"),
        "engine_fallbacks": [], "engine_parameters": {
            "background_edit_region": box, "minimum_distance_px": int(
                policy.get("minimum_distance_from_any_protected_region_px", 75)
            )
        },
        "seed": seed, "primary_or_reserve": None,
        "strata": source.get("strata", {}), "review_status": "HUMAN_REVIEW_PENDING",
        "qa_status": "PROTECTED_SCENE_GEOMETRY_PASS",
        "absence_verification": {
            "status": "PASS", "method": "COMPLETE_ANNOTATION_CATEGORY_CENSUS",
            "observed_categories": sorted(categories),
        },
        "protected_annotation_ids": annotation_ids,
        "category": queried_category, "expected_answer": "no",
        "target_size_stratum": "background_control",
        "target_position_stratum": "protected_scene_safe",
        "placement_proposals": {"protected_background": box},
        "background_edit_region": box,
        "background_region_validation": validation,
        "runtime_class": "PLANNED_NOT_EXECUTED",
        "paper_evidence": False,
    }
    return require_task(with_task_hash(task), verify_files=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build protected-scene absent-category tasks")
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--queried-category", action="append", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=12013)
    args = parser.parse_args(argv)
    config = load_yaml(args.config)
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for source in read_jsonl(args.source_manifest):
        for category in args.queried_category:
            try:
                rows.append(build_negative_item(
                    args.source_root, source, category, args.out_dir, config=config, seed=args.seed
                ))
            except NegativeItemError as exc:
                rejected.append({"source_image_id": str(source.get("source_image_id", "")),
                                 "queried_category": category, "reason": str(exc)})
    Path(args.out).write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    report = {"status": "NEGATIVE_ITEMS_BUILT" if rows else "BLOCKED_NO_VALID_NEGATIVES",
              "built": len(rows), "rejected": rejected, "paper_evidence": False}
    Path(args.out).with_suffix(".report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
