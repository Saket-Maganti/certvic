"""Deterministic confirmatory-control QA enrichment.

This is the only supported bridge from generated controls to candidate selection.
PASS fields are computed from image bytes, geometry, and the frozen study contract;
they are never copied from an input manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from certvic.cvpr.contracts import canonical_json_bytes, load_yaml, sha256_bytes
from certvic.cvpr.transactional import read_jsonl


class ConfirmatoryQAError(ValueError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bbox_mask(size: tuple[int, int], bbox: list[float] | tuple[float, ...]) -> np.ndarray:
    width, height = size
    if len(bbox) != 4:
        raise ConfirmatoryQAError("target_bbox must contain four coordinates")
    x0, y0, x1, y1 = [int(round(float(value))) for value in bbox]
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ConfirmatoryQAError("target_bbox is outside the source image")
    mask = np.zeros((height, width), dtype=bool)
    mask[y0:y1, x0:x1] = True
    return mask


def _target_mask(candidate: dict[str, Any], size: tuple[int, int]) -> np.ndarray:
    path_value = (
        candidate.get("protected_scene_mask_path")
        if candidate.get("queried_category_absent") is True
        else candidate.get("target_mask_path") or candidate.get("mask_path")
    )
    if path_value:
        path = Path(str(path_value))
        if not path.is_file():
            raise ConfirmatoryQAError(f"missing target mask: {path}")
        with Image.open(path) as opened:
            if opened.size != size:
                raise ConfirmatoryQAError("target mask dimensions differ from source")
            return np.asarray(opened.convert("L")) > 0
    return _bbox_mask(size, candidate.get("target_bbox", []))


def _edge_energy(array: np.ndarray) -> float:
    gray = array.astype(np.float64).mean(axis=2)
    dx = np.abs(np.diff(gray, axis=1)).mean() if gray.shape[1] > 1 else 0.0
    dy = np.abs(np.diff(gray, axis=0)).mean() if gray.shape[0] > 1 else 0.0
    return float((dx + dy) / (2 * 255.0))


def _ssim_equivalent(left: np.ndarray, right: np.ndarray) -> float:
    a = left.astype(np.float64).mean(axis=2)
    b = right.astype(np.float64).mean(axis=2)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mu_a, mu_b = float(a.mean()), float(b.mean())
    var_a, var_b = float(a.var()), float(b.var())
    covariance = float(((a - mu_a) * (b - mu_b)).mean())
    numerator = (2 * mu_a * mu_b + c1) * (2 * covariance + c2)
    denominator = (mu_a**2 + mu_b**2 + c1) * (var_a + var_b + c2)
    return float(max(-1.0, min(1.0, numerator / denominator)))


def _minimum_distance(changed: np.ndarray, target: np.ndarray) -> float:
    changed_y, changed_x = np.where(changed)
    target_y, target_x = np.where(target)
    if not len(changed_x) or not len(target_x):
        return math.inf
    changed_box = (changed_x.min(), changed_y.min(), changed_x.max(), changed_y.max())
    target_box = (target_x.min(), target_y.min(), target_x.max(), target_y.max())
    dx = max(target_box[0] - changed_box[2] - 1, changed_box[0] - target_box[2] - 1, 0)
    dy = max(target_box[1] - changed_box[3] - 1, changed_box[1] - target_box[3] - 1, 0)
    return float(math.hypot(dx, dy))


def _records(root: Path) -> list[dict[str, Any]]:
    canonical = root / "generation_records.jsonl"
    if canonical.is_file():
        return read_jsonl(canonical)
    manifests = sorted(root.rglob("generation_manifest.json"))
    if manifests:
        rows: list[dict[str, Any]] = []
        for path in manifests:
            value = json.loads(path.read_text(encoding="utf-8"))
            records = value.get("records", value.get("rows"))
            if not isinstance(records, list):
                raise ConfirmatoryQAError(f"generation manifest has no records list: {path}")
            rows.extend(records)
        return rows
    sidecars = sorted(root.rglob("*.generation_record.json"))
    if sidecars:
        return [json.loads(path.read_text(encoding="utf-8")) for path in sidecars]
    raise ConfirmatoryQAError("generation root has no canonical generation records")


def enrich(
    candidates: list[dict[str, Any]],
    generation_root: str | Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute a deterministic, hash-locked QA manifest for every candidate."""
    root = Path(generation_root)
    records = _records(root)
    by_id: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    for record in records:
        identity = str(record.get("item_id", record.get("edit_id", "")))
        if not identity or identity in by_id:
            duplicates.append(identity or "<blank>")
        by_id[identity] = record
    candidate_ids = [str(row.get("item_id", row.get("edit_id", ""))) for row in candidates]
    if not candidate_ids or any(not value for value in candidate_ids):
        raise ConfirmatoryQAError("candidate manifest has blank item IDs")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ConfirmatoryQAError("candidate manifest has duplicate item IDs")
    missing = sorted(set(candidate_ids) - set(by_id))
    extras = sorted(set(by_id) - set(candidate_ids))
    if duplicates or missing or extras:
        raise ConfirmatoryQAError(
            f"generation universe mismatch: duplicates={duplicates}, missing={missing}, extras={extras}"
        )

    design = config.get("design", {})
    area = design.get("perturbation_area_fraction", {})
    minimum_area = float(area.get("minimum", 0.0))
    maximum_area = float(area.get("maximum", 1.0))
    minimum_distance = float(design.get("minimum_distance_from_target_px", 0))
    salience = design.get("salience_score_range", {})
    salience_minimum = float(salience.get("minimum", 0.0))
    salience_maximum = float(salience.get("maximum", 1.0))
    enriched: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for candidate in sorted(candidates, key=lambda row: str(row.get("item_id", row.get("edit_id")))):
        identity = str(candidate.get("item_id", candidate.get("edit_id")))
        record = by_id[identity]
        source = Path(str(candidate.get("source_image_path", candidate.get("image_path", ""))))
        output_value = (record.get("output_path") or record.get("output_image_path")
                        or record.get("edited_image_path"))
        output = Path(str(output_value))
        if not output.is_absolute():
            output = root / output
        reasons: list[str] = []
        corruption_status = "PASS"
        try:
            if not source.is_file() or not output.is_file():
                raise OSError("source or output image is missing")
            with Image.open(source) as source_opened, Image.open(output) as output_opened:
                source_opened.load()
                output_opened.load()
                source_mode, output_mode = source_opened.mode, output_opened.mode
                source_size, output_size = source_opened.size, output_opened.size
                before = np.asarray(source_opened.convert("RGB"), dtype=np.float64)
                after = np.asarray(output_opened.convert("RGB"), dtype=np.float64)
        except (OSError, ValueError) as exc:
            corruption_status = "FAIL"
            reasons.append(f"corrupt_or_missing_image:{exc}")
            source_mode = output_mode = "UNKNOWN"
            source_size = output_size = (0, 0)
            before = after = np.zeros((1, 1, 3), dtype=np.float64)
        same_geometry = source_size == output_size and source_mode == output_mode
        if not same_geometry:
            reasons.append("image_dimensions_or_mode_changed")
        target = _target_mask(candidate, source_size) if source_size != (0, 0) else np.ones((1, 1), bool)
        absolute = np.abs(after - before)
        changed = np.any(absolute > 0, axis=2)
        changed_fraction = float(changed.mean())
        target_overlap_pixels = int(np.logical_and(changed, target).sum())
        target_pixels = max(1, int(target.sum()))
        target_overlap_fraction = target_overlap_pixels / target_pixels
        distance = _minimum_distance(changed, target)
        mean_absolute_difference = float(absolute.mean() / 255.0)
        similarity = _ssim_equivalent(before, after)
        contrast_delta = float(abs(before.std() - after.std()) / 255.0)
        edge_delta = abs(_edge_energy(before) - _edge_energy(after))
        perceptual_distance = float(np.sqrt(np.mean((after - before) ** 2)) / 255.0)
        salience_score = float((mean_absolute_difference + perceptual_distance + edge_delta) / 3)
        if not minimum_area <= changed_fraction <= maximum_area:
            reasons.append("changed_pixel_fraction_outside_frozen_range")
        if target_overlap_pixels:
            reasons.append("protected_target_touched")
        if distance < minimum_distance:
            reasons.append("minimum_target_distance_not_met")
        if not salience_minimum <= salience_score <= salience_maximum:
            reasons.append("salience_outside_frozen_range")
        generation_status = "PASS" if not reasons else "FAIL"
        engine_family = str(record.get("engine_family", record.get("engine", "")))
        engine_version = str(record.get("engine_version", ""))
        engine_parameters = record.get(
            "engine_parameters", record.get("parameters", record.get("settings", {}))
        )
        if not engine_family or not engine_version or not isinstance(engine_parameters, dict):
            reasons.append("engine_provenance_incomplete")
            generation_status = "FAIL"
        output_hash = _sha(output) if output.is_file() else ""
        declared_hash = str(record.get("output_sha256", record.get("edited_sha256", "")))
        if declared_hash and declared_hash != output_hash:
            reasons.append("output_hash_mismatch")
            generation_status = "FAIL"
        row = {
            **candidate,
            "qa_enrichment_schema": "certvic.cvpr.confirmatory_qa.v1",
            "qa_status_source": "COMPUTED_FROM_BYTES_AND_FROZEN_CONTRACT",
            "source_image_sha256": _sha(source) if source.is_file() else "",
            "output_image_sha256": output_hash,
            "output_image_path": str(output),
            "engine_family": engine_family,
            "engine_version": engine_version,
            "engine_parameters": engine_parameters,
            "placement_box": record.get("placement_box", record.get(
                "placement_rectangle", record.get("placement_xyxy")
            )),
            "target_box": candidate.get("target_bbox"),
            "target_mask_overlap_pixels": target_overlap_pixels,
            "target_mask_overlap_fraction": target_overlap_fraction,
            "target_box_overlap_fraction": target_overlap_fraction,
            "minimum_target_distance_px": None if math.isinf(distance) else distance,
            "changed_pixel_fraction": changed_fraction,
            "mean_absolute_difference": mean_absolute_difference,
            "ssim_equivalent": similarity,
            "local_contrast_delta": contrast_delta,
            "edge_energy_delta": edge_delta,
            "perceptual_distance": perceptual_distance,
            "salience_score": salience_score,
            "detectability_features": {
                "changed_pixel_fraction": changed_fraction,
                "mean_absolute_difference": mean_absolute_difference,
                "edge_energy_delta": edge_delta,
                "perceptual_distance": perceptual_distance,
            },
            "corruption_status": corruption_status,
            "image_dimensions": list(output_size),
            "image_mode": output_mode,
            "generation_qa_status": generation_status,
            "salience_review_status": "PASS" if not any(
                value == "salience_outside_frozen_range" for value in reasons
            ) else "FAIL",
            "detectability_review_status": "PASS" if generation_status == "PASS" else "FAIL",
            "target_safety_status": "PASS" if target_overlap_pixels == 0 and distance >= minimum_distance else "FAIL",
            "rejection_reason": "|".join(sorted(set(reasons))) or None,
            "paper_evidence": False,
        }
        enriched.append(row)
        if row["generation_qa_status"] != "PASS":
            rejected.append({"item_id": identity, "reason": str(row["rejection_reason"])})
    manifest_hash = sha256_bytes(canonical_json_bytes(enriched))
    return {
        "schema": "certvic.cvpr.confirmatory_qa_report.v1",
        "status": "QA_ENRICHMENT_COMPLETE" if not rejected else "QA_ENRICHMENT_COMPLETE_WITH_REJECTIONS",
        "items": len(enriched),
        "passed": len(enriched) - len(rejected),
        "rejected": rejected,
        "qa_enriched_manifest_sha256": manifest_hash,
        "rows": enriched,
        "deterministic": True,
        "paper_evidence": False,
    }


def write_outputs(result: dict[str, Any], out: str | Path, report: str | Path) -> None:
    rows = result.pop("rows")
    out_path = Path(out)
    report_path = Path(report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrich generated confirmatory controls with strict QA")
    parser.add_argument("--candidate-manifest", required=True)
    parser.add_argument("--generation-root", required=True)
    parser.add_argument("--study-config", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    result = enrich(read_jsonl(args.candidate_manifest), args.generation_root,
                    load_yaml(args.study_config))
    status = result["status"]
    write_outputs(result, args.out, args.report)
    print(json.dumps({"status": status, "out": args.out, "report": args.report}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
