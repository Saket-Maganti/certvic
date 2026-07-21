"""Edit quality gates for generated images."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from certvic.edit.masks import bbox_from_mask, mask_area_fraction
from certvic.hashing import sha256_file
from certvic.schema import EditType


DEFAULT_QUALITY_CONFIG = {
    "min_mask_area_fraction": 0.005,
    "max_mask_area_fraction": 0.50,
    "max_outside_allowed_change_fraction": 0.02,
    "min_inside_mask_change_fraction": 0.01,
    "max_control_changed_fraction": 0.25,
    "max_control_mean_abs_diff": 20.0,
    "pixel_change_threshold": 5,
    # V2 additions. Warnings are disabled by default (None / 0.0) so existing
    # solid-color test fixtures are unaffected; real pilots enable them via
    # configs/edit_quality.yaml. The underlying metrics are always reported.
    "max_uniform_pixel_fraction": None,
    "min_sharpness": None,
}


def uniform_pixel_fraction(arr: np.ndarray) -> float:
    """Fraction of pixels equal to the most common grayscale value (0-255)."""
    gray = arr.mean(axis=-1).round().astype(int) if arr.ndim == 3 else arr.astype(int)
    counts = np.bincount(gray.reshape(-1), minlength=256)
    return float(counts.max() / gray.size)


def sharpness_score(arr: np.ndarray) -> float:
    """Simple gradient-magnitude sharpness (higher = sharper)."""
    gray = arr.mean(axis=-1) if arr.ndim == 3 else arr.astype(float)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    parts = [g.mean() for g in (gx, gy) if g.size]
    return float(np.mean(parts)) if parts else 0.0


def is_all_black(arr: np.ndarray, tol: int = 2) -> bool:
    return bool(arr.max() <= tol)


def is_all_white(arr: np.ndarray, tol: int = 2) -> bool:
    return bool(arr.min() >= 255 - tol)


def _as_arr(image_or_path) -> np.ndarray:
    if isinstance(image_or_path, (str, bytes)):
        return np.asarray(Image.open(image_or_path).convert("RGB"))
    if hasattr(image_or_path, "__fspath__"):
        return np.asarray(Image.open(image_or_path).convert("RGB"))
    if isinstance(image_or_path, Image.Image):
        return np.asarray(image_or_path.convert("RGB"))
    return np.asarray(image_or_path)


def outside_mask_change_fraction(original, edited, mask, threshold: float = 0.05) -> float:
    orig = _as_arr(original)
    edit = _as_arr(edited)
    diff = np.any(np.abs(orig.astype(int) - edit.astype(int)) > 5, axis=-1)
    outside = ~mask.astype(bool)
    if outside.sum() == 0:
        return 0.0
    return float((diff & outside).sum() / outside.sum())


def simple_artifact_score(original, edited, mask) -> dict:
    orig = _as_arr(original)
    edit = _as_arr(edited)
    diff = np.abs(orig.astype(int) - edit.astype(int)).mean()
    return {"mean_abs_diff": float(diff), "mask_area_fraction": mask_area_fraction(mask)}


def pass_quality_gates(original, edited, mask, config: dict) -> dict:
    result = evaluate_edit_quality(
        original,
        edited,
        mask,
        edit_type=str(config.get("edit_type", EditType.REMOVE.value)),
        planned_params=config.get("planned_params") or {},
        actual_params=config.get("actual_params") or {},
        config=config,
    )
    return result


def evaluate_edit_quality(
    original,
    edited,
    mask,
    edit_type: str,
    planned_params: dict | None = None,
    actual_params: dict | None = None,
    config: dict | None = None,
) -> dict:
    cfg = {**DEFAULT_QUALITY_CONFIG, **(config or {})}
    planned_params = planned_params or {}
    actual_params = actual_params or {}
    warnings: list[str] = []

    edited_path = _path_or_none(edited)
    edited_file_exists = bool(edited_path and edited_path.exists()) if edited_path else True
    edited_sha256 = sha256_file(edited_path) if edited_path and edited_file_exists else None
    edited_sha256_exists = edited_sha256 is not None

    try:
        orig = _as_arr(original)
    except Exception as exc:
        return _failed_result(warnings + [f"could not read original image: {exc}"])
    try:
        edit = _as_arr(edited)
    except Exception as exc:
        return _failed_result(
            warnings + [f"could not read edited image: {exc}"],
            edited_file_exists=edited_file_exists,
            edited_sha256=edited_sha256,
            edited_sha256_exists=edited_sha256_exists,
        )

    mask_bool = np.asarray(mask).astype(bool)
    image_size_match = orig.shape == edit.shape and orig.shape[:2] == mask_bool.shape
    if not image_size_match:
        warnings.append("image size mismatch")
        return _metrics_result(
            warnings,
            edited_file_exists=edited_file_exists,
            edited_sha256=edited_sha256,
            edited_sha256_exists=edited_sha256_exists,
            image_size_match=False,
        )

    bbox = actual_params.get("bbox") or planned_params.get("bbox") or bbox_from_mask(mask_bool)
    bbox_valid = _valid_bbox(bbox, width=orig.shape[1], height=orig.shape[0])
    area = mask_area_fraction(mask_bool)
    if not edited_file_exists:
        warnings.append("edited file missing")
    if not edited_sha256_exists:
        warnings.append("edited sha256 missing")
    if area < float(cfg["min_mask_area_fraction"]):
        warnings.append("mask area too small")
    if area > float(cfg["max_mask_area_fraction"]):
        warnings.append("mask area too large")
    if not bbox_valid:
        warnings.append("invalid bbox")

    diff = np.abs(orig.astype(int) - edit.astype(int))
    changed = np.any(diff > int(cfg["pixel_change_threshold"]), axis=-1)
    changed_region_nonempty = bool(changed.any())
    if not changed_region_nonempty:
        warnings.append("changed region empty")

    edited_uniform_fraction = uniform_pixel_fraction(edit)
    edited_sharpness = sharpness_score(edit)
    edited_all_black = is_all_black(edit)
    edited_all_white = is_all_white(edit)
    max_uniform = cfg.get("max_uniform_pixel_fraction")
    if max_uniform is not None and edited_uniform_fraction > float(max_uniform):
        warnings.append("edited image nearly uniform (possible all-black/all-white or degenerate edit)")
    min_sharpness = cfg.get("min_sharpness")
    if min_sharpness is not None and float(min_sharpness) > 0 and edited_sharpness < float(min_sharpness):
        warnings.append("edited image too blurry / low detail")

    inside_mask_change = _fraction(changed & mask_bool, mask_bool)
    outside_mask_change = _fraction(changed & ~mask_bool, ~mask_bool)
    total_changed = float(changed.mean())
    mean_abs_diff = float(diff.mean())

    allowed_region = _allowed_change_region(
        mask_bool,
        edit_type=edit_type,
        planned_params=planned_params,
        actual_params=actual_params,
        image_shape=orig.shape[:2],
    )
    outside_allowed_change = _fraction(changed & ~allowed_region, ~allowed_region)
    if outside_allowed_change > float(cfg["max_outside_allowed_change_fraction"]):
        warnings.append("outside allowed change too large")

    if edit_type in {EditType.REMOVE.value, EditType.OCCLUDE.value, EditType.DISPLACE.value}:
        if inside_mask_change < float(cfg["min_inside_mask_change_fraction"]):
            warnings.append("inside-mask change too small")
    elif edit_type == EditType.CONTROL_IRRELEVANT.value:
        if total_changed > float(cfg["max_control_changed_fraction"]):
            warnings.append("control edit changed too much of the image")
        if mean_abs_diff > float(cfg["max_control_mean_abs_diff"]):
            warnings.append("control edit mean difference too large")
    else:
        warnings.append(f"unsupported edit type for quality gates: {edit_type}")

    return _metrics_result(
        warnings,
        edited_file_exists=edited_file_exists,
        edited_sha256=edited_sha256,
        edited_sha256_exists=edited_sha256_exists,
        image_size_match=image_size_match,
        bbox_valid=bbox_valid,
        mask_area_fraction_value=area,
        inside_mask_change_fraction=inside_mask_change,
        outside_mask_change_fraction=outside_mask_change,
        outside_allowed_change_fraction=outside_allowed_change,
        total_changed_fraction=total_changed,
        changed_region_nonempty=changed_region_nonempty,
        mean_abs_diff=mean_abs_diff,
        allowed_region_fraction=float(allowed_region.mean()),
        edited_uniform_fraction=edited_uniform_fraction,
        edited_sharpness=edited_sharpness,
        edited_all_black=edited_all_black,
        edited_all_white=edited_all_white,
    )


def _allowed_change_region(
    mask: np.ndarray,
    edit_type: str,
    planned_params: dict,
    actual_params: dict,
    image_shape: tuple[int, int],
) -> np.ndarray:
    if edit_type == EditType.DISPLACE.value:
        offset = actual_params.get("offset_xy") or planned_params.get("offset_xy") or [16, 0]
        return mask | _shift_mask(mask, int(offset[0]), int(offset[1]))
    if edit_type == EditType.OCCLUDE.value:
        bbox = actual_params.get("occluder_bbox") or actual_params.get("bbox") or planned_params.get("bbox")
        return _bbox_region(bbox, image_shape) if bbox else mask
    if edit_type == EditType.CONTROL_IRRELEVANT.value:
        bbox = actual_params.get("control_region_bbox")
        return _bbox_region(bbox, image_shape) if bbox else ~mask
    return mask


def _shift_mask(mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
    shifted = np.zeros_like(mask, dtype=bool)
    height, width = mask.shape
    ys, xs = np.where(mask)
    ny = ys + dy
    nx = xs + dx
    ok = (ny >= 0) & (ny < height) & (nx >= 0) & (nx < width)
    shifted[ny[ok], nx[ok]] = True
    return shifted


def _bbox_region(bbox: Any, image_shape: tuple[int, int]) -> np.ndarray:
    height, width = image_shape
    region = np.zeros((height, width), dtype=bool)
    if not _valid_bbox(bbox, width=width, height=height):
        return region
    x1, y1, x2, y2 = [int(value) for value in bbox]
    region[y1:y2, x1:x2] = True
    return region


def _valid_bbox(value: Any, width: int | None = None, height: int | None = None) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    if any(not isinstance(coord, int) or coord < 0 for coord in value):
        return False
    x1, y1, x2, y2 = value
    if x2 <= x1 or y2 <= y1:
        return False
    if width is not None and x2 > width:
        return False
    if height is not None and y2 > height:
        return False
    return True


def _fraction(numerator_mask: np.ndarray, denominator_mask: np.ndarray) -> float:
    denominator = int(denominator_mask.sum())
    if denominator == 0:
        return 0.0
    return float(numerator_mask.sum() / denominator)


def _path_or_none(value) -> Path | None:
    if isinstance(value, (str, bytes)) or hasattr(value, "__fspath__"):
        return Path(value)
    return None


def _failed_result(warnings: list[str], **extra) -> dict:
    return _metrics_result(warnings, **extra)


def _metrics_result(
    warnings: list[str],
    edited_file_exists: bool | None = None,
    edited_sha256: str | None = None,
    edited_sha256_exists: bool = False,
    image_size_match: bool = True,
    bbox_valid: bool | None = None,
    mask_area_fraction_value: float | None = None,
    inside_mask_change_fraction: float | None = None,
    outside_mask_change_fraction: float | None = None,
    outside_allowed_change_fraction: float | None = None,
    total_changed_fraction: float | None = None,
    changed_region_nonempty: bool | None = None,
    mean_abs_diff: float | None = None,
    allowed_region_fraction: float | None = None,
    edited_uniform_fraction: float | None = None,
    edited_sharpness: float | None = None,
    edited_all_black: bool | None = None,
    edited_all_white: bool | None = None,
) -> dict:
    passed = not warnings
    return {
        "mask_area_fraction": mask_area_fraction_value,
        "bbox_valid": bbox_valid,
        "outside_mask_change_fraction": outside_mask_change_fraction,
        "inside_mask_change_fraction": inside_mask_change_fraction,
        "outside_allowed_change_fraction": outside_allowed_change_fraction,
        "changed_region_nonempty": changed_region_nonempty,
        "image_size_match": image_size_match,
        "edited_file_exists": edited_file_exists,
        "edited_sha256": edited_sha256,
        "edited_sha256_exists": edited_sha256_exists,
        "simple_artifact_warnings": warnings,
        "warnings": warnings,
        "pass": passed,
        "quality_gate_status": "pass" if passed else "fail",
        "total_changed_fraction": total_changed_fraction,
        "mean_abs_diff": mean_abs_diff,
        "allowed_region_fraction": allowed_region_fraction,
        "edited_uniform_fraction": edited_uniform_fraction,
        "edited_sharpness": edited_sharpness,
        "edited_all_black": edited_all_black,
        "edited_all_white": edited_all_white,
    }
