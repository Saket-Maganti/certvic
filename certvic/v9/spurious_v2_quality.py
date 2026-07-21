from __future__ import annotations

from collections import Counter
from statistics import mean, median
from typing import Any


def _num(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def summarize_quality(rows: list[dict[str, Any]], *, min_distance_px: float) -> dict[str, Any]:
    distances = [_num(row.get("patch_object_bbox_distance_px")) for row in rows]
    salience = [
        float(row["detectability_score"])
        for row in rows
        if row.get("detectability_score") is not None and row.get("detectability_score") != ""
    ]
    object_region_diff = [_num(row.get("patch_target_mask_overlap_pixels")) for row in rows]
    bbox_overlap_count = sum(bool(row.get("patch_bbox_intersects_object_bbox")) for row in rows)
    mask_overlap_count = sum(_num(row.get("patch_target_mask_overlap_pixels")) > 0 for row in rows)
    split_counts = Counter(row.get("split", "unknown") for row in rows)
    class_counts = Counter(row.get("target_object", "unknown") for row in rows)
    return {
        "n_items": len(rows),
        "class_distribution": dict(sorted(class_counts.items())),
        "split_distribution": dict(sorted(split_counts.items())),
        "object_region_diff_summary": {
            "max_target_mask_overlap_pixels": max(object_region_diff) if object_region_diff else 0,
            "mean_target_mask_overlap_pixels": mean(object_region_diff) if object_region_diff else 0,
        },
        "patch_salience_summary": {
            "n_with_detectability_score": len(salience),
            "max_detectability_score": max(salience) if salience else None,
            "median_detectability_score": median(salience) if salience else None,
            "policy": "scores above 0.12 are excluded when scores exist; missing scores are retained but reported",
        },
        "bbox_distance_summary": {
            "min_distance_px": min(distances) if distances else None,
            "median_distance_px": median(distances) if distances else None,
            "max_distance_px": max(distances) if distances else None,
            "enforced_min_distance_px": min_distance_px,
        },
        "bbox_overlap_count": bbox_overlap_count,
        "mask_overlap_count": mask_overlap_count,
        "quality_pass": bool(rows)
        and bbox_overlap_count == 0
        and mask_overlap_count == 0
        and all(distance >= min_distance_px for distance in distances),
    }

