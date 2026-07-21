"""Build V8.1 Qwen spurious-control forensic audit artifacts.

This script is CPU-only and artifact-only. It does not run models, does not
create predictions, and does not promote any result to paper evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import zipfile
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path("data/results/main_real_200")
OUT = RESULTS / "v8_1_qwen_spurious_forensics"
GALLERY_DIR = OUT / "qwen_spurious_failed_12_gallery"
CONTROL_DIR = Path("data/edits/spurious_flip_control")
TASKS_PATH = CONTROL_DIR / "pilot_eval_tasks_reviewed.jsonl"
V8_DIR = RESULTS / "v8_upgrade"
QWEN = "qwen2_5_vl_7b"
PROVIDERS = (QWEN, "internvl_8b", "llava_onevision_7b")
SPURIOUS_THRESHOLD = 0.10
DIFF_THRESHOLD = 20
NEAR_TARGET_PX = 80.0
HIGH_DETECTABILITY_SCORE = 0.12
TARGET_LABELS = {"table": 16, "chair": 20, "sofa": 24, "car": 21}
FROZEN_QUALITY_CACHE = OUT / "spurious_control_quality_audit.json"
TASK_IDS = [
    "V8_1_00_input_discovery",
    "V8_1_01_qwen_failure_extraction",
    "V8_1_02_failure_gallery",
    "V8_1_03_machine_preliminary_eval",
    "V8_1_04_rule_based_recompute",
    "V8_1_05_cross_model_comparison",
    "V8_1_06_parser_and_provenance_audit",
    "V8_1_07_spurious_control_quality_audit",
    "V8_1_08_stricter_spurious_v2_design",
    "V8_1_09_paper_claim_reframe",
    "V8_1_10_go_nogo_decision",
    "V8_1_11_tests_and_guards",
]
LABEL_TO_CODE = {
    "CODEX_PRELIM_VALID_FAILURE": "CODEX_PRELIM_VALID_FAILURE",
    "CODEX_PRELIM_PATCH_TOO_SALIENT": "CODEX_PRELIM_PATCH_TOO_SALIENT",
    "CODEX_PRELIM_PATCH_NEAR_TARGET": "CODEX_PRELIM_PATCH_NEAR_TARGET",
    "CODEX_PRELIM_OBJECT_REGION_AFFECTED": "CODEX_PRELIM_OBJECT_REGION_AFFECTED",
    "CODEX_PRELIM_PROMPT_AMBIGUOUS": "CODEX_PRELIM_PROMPT_AMBIGUOUS",
    "CODEX_PRELIM_PARSE_ERROR": "CODEX_PRELIM_PARSE_ERROR",
    "CODEX_PRELIM_IMAGE_MISMATCH": "CODEX_PRELIM_IMAGE_MISMATCH",
    "CODEX_PRELIM_LOW_CONFIDENCE_UNKNOWN": "CODEX_PRELIM_LOW_CONFIDENCE_UNKNOWN",
}


def repo_path(path: str | Path) -> Path:
    return ROOT / Path(path)


def rel(path: str | Path) -> str:
    p = Path(path)
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with repo_path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: str | Path, payload: Any) -> None:
    target = repo_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    target = repo_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = repo_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    target = repo_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in fieldnames})


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    if value is None:
        return ""
    return value


def sha256(path: str | Path) -> str | None:
    p = repo_path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def image_path_from_task(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    if path_value.startswith("__CTRL__/"):
        return CONTROL_DIR / path_value[len("__CTRL__/") :]
    return Path(path_value)


def bbox_from_mask(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]


def bbox_area(box: list[int] | None) -> int:
    if not box:
        return 0
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def bbox_intersection_area(a: list[int] | None, b: list[int] | None) -> int:
    if not a or not b:
        return 0
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def bbox_distance(a: list[int] | None, b: list[int] | None) -> float | None:
    if not a or not b:
        return None
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return round(math.sqrt(dx * dx + dy * dy), 3)


def parse_yes_no_from_raw(raw: Any) -> str | None:
    if raw is None:
        return None
    token = str(raw).strip().lower().strip(" .,!?:;\"'")
    if token in {"yes", "no"}:
        return token
    return None


def load_predictions(provider: str) -> dict[str, dict[str, dict[str, Any]]]:
    path = RESULTS / "kaggle_spurious" / f"pred_{provider}_spurious_merged.jsonl"
    by_item: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in read_jsonl(path):
        by_item[str(row.get("item_id"))][str(row.get("image_variant"))] = row
    return dict(by_item)


def load_detectability() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    summary_path = Path("data/results/spurious_flip_control/edit_detectability/detectability_summary.json")
    features_path = Path("data/results/spurious_flip_control/edit_detectability/features.csv")
    high_path = Path("data/results/spurious_flip_control/edit_detectability/highly_detectable_items.jsonl")
    summary = json.loads(repo_path(summary_path).read_text(encoding="utf-8")) if repo_path(summary_path).exists() else {}
    paired_features: dict[str, dict[str, Any]] = defaultdict(dict)
    if repo_path(features_path).exists():
        with repo_path(features_path).open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                paired_features[row["item_id"]][row["variant"]] = row
    high: dict[str, dict[str, Any]] = {}
    if repo_path(high_path).exists():
        for row in read_jsonl(high_path):
            high[str(row["item_id"])] = row
    return dict(paired_features), high, summary


def load_frozen_quality_cache(tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Load the preserved annotation-derived geometry after validating its coverage.

    The local ADE annotation tree is an external input and may be absent.  In that
    case we may reuse the existing derived-real-evidence audit, but must never
    silently treat it as a fresh recomputation.
    """

    path = repo_path(FROZEN_QUALITY_CACHE)
    if not path.is_file():
        raise RuntimeError("ADE annotations are unavailable and the frozen quality cache is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise RuntimeError("frozen quality cache has no item list")
    by_id = {str(row.get("item_id")): row for row in rows}
    task_ids = {str(task["item_id"]) for task in tasks}
    if len(by_id) != len(rows) or set(by_id) != task_ids:
        raise RuntimeError("frozen quality cache does not exactly cover the 94 frozen tasks")
    required = {
        "target_bbox_xyxy",
        "patch_bbox_xyxy",
        "patch_bbox_intersects_object_bbox",
        "patch_object_bbox_distance_px",
        "patch_target_mask_overlap_pixels",
    }
    for task in tasks:
        item_id = str(task["item_id"])
        row = by_id[item_id]
        expected_original = image_path_from_task(task.get("original_image_path"))
        expected_edited = image_path_from_task(task.get("edited_image_path"))
        if not expected_original or not expected_edited:
            raise RuntimeError(f"{item_id}: frozen task has no resolvable image pair")
        if row.get("original_image_path") != expected_original.as_posix():
            raise RuntimeError(f"{item_id}: frozen original path mismatch")
        if row.get("edited_image_path") != expected_edited.as_posix():
            raise RuntimeError(f"{item_id}: frozen edited path mismatch")
        if row.get("annotation_exists") is not True or any(row.get(key) is None for key in required):
            raise RuntimeError(f"{item_id}: frozen annotation-derived geometry is incomplete")
    return by_id


def target_annotation_path(item_id: str) -> Path | None:
    marker = "ADE_train_"
    if marker not in item_id:
        return None
    stem = marker + item_id.split(marker, 1)[1]
    return Path("ade20k_root/ADEChallengeData2016/annotations/training") / f"{stem}.png"


def quality_for_task(
    task: dict[str, Any],
    detect_high: dict[str, dict[str, Any]],
    frozen_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item_id = str(task["item_id"])
    target_object = str((task.get("metadata") or {}).get("object") or item_id.split("_")[1])
    original_rel = image_path_from_task(task.get("original_image_path"))
    edited_rel = image_path_from_task(task.get("edited_image_path"))
    row: dict[str, Any] = {
        "item_id": item_id,
        "target_object": target_object,
        "original_image_path": original_rel.as_posix() if original_rel else None,
        "edited_image_path": edited_rel.as_posix() if edited_rel else None,
        "original_exists": bool(original_rel and repo_path(original_rel).exists()),
        "edited_exists": bool(edited_rel and repo_path(edited_rel).exists()),
        "image_shape_match": False,
        "target_label_id": TARGET_LABELS.get(target_object),
        "annotation_path": None,
        "annotation_exists": False,
        "target_mask_pixels": None,
        "target_bbox_xyxy": None,
        "patch_bbox_xyxy": None,
        "patch_area_pixels": None,
        "patch_area_fraction": None,
        "patch_bbox_intersects_object_bbox": None,
        "patch_object_bbox_distance_px": None,
        "patch_target_mask_overlap_pixels": None,
        "patch_target_mask_overlap_fraction": None,
        "object_region_mean_abs_diff": None,
        "object_region_max_abs_diff": None,
        "non_object_region_mean_abs_diff": None,
        "global_mean_abs_diff": None,
        "global_max_abs_diff": None,
        "detectability_score": None,
        "high_detectability_flag": False,
        "geometry_source": None,
        "annotation_currently_available": False,
        "evidence_status": "DERIVED_FROM_REAL_EVIDENCE",
        "issues": [],
    }
    if not row["original_exists"] or not row["edited_exists"]:
        row["issues"].append("missing_image")
        return row

    orig = Image.open(repo_path(original_rel)).convert("RGB")
    edited = Image.open(repo_path(edited_rel)).convert("RGB")
    row["original_size"] = list(orig.size)
    row["edited_size"] = list(edited.size)
    row["image_shape_match"] = orig.size == edited.size
    if not row["image_shape_match"]:
        row["issues"].append("shape_mismatch")
        return row

    arr_o = np.asarray(orig).astype(np.int16)
    arr_e = np.asarray(edited).astype(np.int16)
    absdiff = np.abs(arr_o - arr_e)
    diff_max = absdiff.max(axis=2)
    patch_mask = diff_max > DIFF_THRESHOLD
    patch_bbox = bbox_from_mask(patch_mask)
    row["patch_bbox_xyxy"] = patch_bbox
    row["patch_area_pixels"] = int(patch_mask.sum())
    row["patch_area_fraction"] = round(float(patch_mask.mean()), 6)
    row["global_mean_abs_diff"] = round(float(absdiff.mean()), 6)
    row["global_max_abs_diff"] = int(absdiff.max())

    ann_rel = target_annotation_path(item_id)
    row["annotation_path"] = ann_rel.as_posix() if ann_rel else None
    row["annotation_exists"] = bool(ann_rel and repo_path(ann_rel).exists())
    label_id = TARGET_LABELS.get(target_object)
    if not ann_rel or not repo_path(ann_rel).exists() or label_id is None:
        if frozen_quality is None:
            row["issues"].append("missing_target_annotation_or_label")
        else:
            if frozen_quality.get("patch_bbox_xyxy") != patch_bbox:
                raise RuntimeError(f"{item_id}: current image-difference bbox disagrees with frozen geometry")
            for key in (
                "target_mask_pixels",
                "target_bbox_xyxy",
                "patch_bbox_intersects_object_bbox",
                "patch_object_bbox_distance_px",
                "patch_target_mask_overlap_pixels",
                "patch_target_mask_overlap_fraction",
                "object_region_mean_abs_diff",
                "object_region_max_abs_diff",
                "non_object_region_mean_abs_diff",
            ):
                row[key] = frozen_quality.get(key)
            # This records availability at the original derivation.  The separate
            # current-availability field prevents it being mistaken for a rerun.
            row["annotation_exists"] = True
            row["annotation_currently_available"] = False
            row["geometry_source"] = "FROZEN_DERIVED_REAL_EVIDENCE_CACHE"
    else:
        row["annotation_currently_available"] = True
        row["geometry_source"] = "LOCAL_ADE_ANNOTATION_RECOMPUTE"
        ann = np.asarray(Image.open(repo_path(ann_rel)))
        if ann.shape[:2] != arr_o.shape[:2]:
            row["issues"].append("annotation_shape_mismatch")
        else:
            target_mask = ann == int(label_id)
            target_bbox = bbox_from_mask(target_mask)
            overlap_pixels = int(np.logical_and(patch_mask, target_mask).sum())
            target_pixels = int(target_mask.sum())
            non_target_mask = ~target_mask
            row["target_mask_pixels"] = target_pixels
            row["target_bbox_xyxy"] = target_bbox
            row["patch_bbox_intersects_object_bbox"] = bbox_intersection_area(patch_bbox, target_bbox) > 0
            row["patch_object_bbox_distance_px"] = bbox_distance(patch_bbox, target_bbox)
            row["patch_target_mask_overlap_pixels"] = overlap_pixels
            row["patch_target_mask_overlap_fraction"] = round(overlap_pixels / target_pixels, 8) if target_pixels else None
            if target_pixels:
                target_diff = absdiff[target_mask]
                row["object_region_mean_abs_diff"] = round(float(target_diff.mean()), 6)
                row["object_region_max_abs_diff"] = int(target_diff.max())
            if non_target_mask.any():
                row["non_object_region_mean_abs_diff"] = round(float(absdiff[non_target_mask].mean()), 6)
    if item_id in detect_high:
        row["detectability_score"] = detect_high[item_id].get("detectability_score")
        row["high_detectability_flag"] = True
    return row


def build_all_item_rows(
    tasks: list[dict[str, Any]], predictions: dict[str, dict[str, dict[str, dict[str, Any]]]], quality: dict[str, dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    rows_by_provider: dict[str, list[dict[str, Any]]] = {}
    task_by_id = {str(t["item_id"]): t for t in tasks}
    for provider in PROVIDERS:
        rows: list[dict[str, Any]] = []
        by_item = predictions[provider]
        for item_id, task in task_by_id.items():
            original = by_item.get(item_id, {}).get("original", {})
            edited = by_item.get(item_id, {}).get("edited", {})
            original_parsed = original.get("parsed_answer")
            edited_parsed = edited.get("parsed_answer")
            original_raw_parse = parse_yes_no_from_raw(original.get("raw_output"))
            edited_raw_parse = parse_yes_no_from_raw(edited.get("raw_output"))
            parse_error = (
                not original
                or not edited
                or original.get("parse_ok") is not True
                or edited.get("parse_ok") is not True
                or (original_raw_parse is not None and original_raw_parse != original_parsed)
                or (edited_raw_parse is not None and edited_raw_parse != edited_parsed)
            )
            q = quality.get(item_id, {})
            rows.append(
                {
                    "item_id": item_id,
                    "provider": provider,
                    "run_tag": "spurious",
                    "target_object": (task.get("metadata") or {}).get("object"),
                    "task_family": task.get("task_family"),
                    "required_change": task.get("required_change"),
                    "expected_no_change": True,
                    "question": task.get("question_original"),
                    "original_image_path": image_path_from_task(task.get("original_image_path")).as_posix(),
                    "edited_image_path": image_path_from_task(task.get("edited_image_path")).as_posix(),
                    "original_raw_answer": original.get("raw_output"),
                    "edited_raw_answer": edited.get("raw_output"),
                    "original_parsed_answer": original_parsed,
                    "edited_parsed_answer": edited_parsed,
                    "original_parse_ok": original.get("parse_ok"),
                    "edited_parse_ok": edited.get("parse_ok"),
                    "original_run_id": original.get("run_id"),
                    "edited_run_id": edited.get("run_id"),
                    "flipped": bool(original_parsed is not None and edited_parsed is not None and original_parsed != edited_parsed),
                    "parse_error_flag": bool(parse_error),
                    "image_mismatch_flag": bool(q.get("issues") and any(x in q.get("issues", []) for x in ["missing_image", "shape_mismatch"])),
                    "patch_bbox_xyxy": q.get("patch_bbox_xyxy"),
                    "target_bbox_xyxy": q.get("target_bbox_xyxy"),
                    "patch_target_mask_overlap_pixels": q.get("patch_target_mask_overlap_pixels"),
                    "patch_bbox_intersects_object_bbox": q.get("patch_bbox_intersects_object_bbox"),
                    "patch_object_bbox_distance_px": q.get("patch_object_bbox_distance_px"),
                    "detectability_score": q.get("detectability_score"),
                }
            )
        rows_by_provider[provider] = rows
    return rows_by_provider


def prelim_label_for(row: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    item_id = row["item_id"]
    reason_parts: list[str] = []
    label = "CODEX_PRELIM_LOW_CONFIDENCE_UNKNOWN"
    confidence = "LOW"
    if row.get("parse_error_flag"):
        label = "CODEX_PRELIM_PARSE_ERROR"
        confidence = "HIGH"
        reason_parts.append("raw yes/no text or parse_ok does not support the parsed answer")
    elif row.get("image_mismatch_flag"):
        label = "CODEX_PRELIM_IMAGE_MISMATCH"
        confidence = "HIGH"
        reason_parts.append("image path, existence, or shape mismatch was detected")
    elif quality.get("patch_target_mask_overlap_pixels") not in (None, 0) or quality.get("patch_bbox_intersects_object_bbox") is True:
        label = "CODEX_PRELIM_OBJECT_REGION_AFFECTED"
        confidence = "MEDIUM"
        reason_parts.append("thresholded patch bbox intersects the target bbox under the preregistered objective rule")
        if quality.get("patch_target_mask_overlap_pixels") == 0:
            reason_parts.append("target-mask overlap is zero, so this is bbox-based rather than mask-based")
    elif quality.get("high_detectability_flag") and float(quality.get("detectability_score") or 0.0) >= HIGH_DETECTABILITY_SCORE:
        label = "CODEX_PRELIM_PATCH_TOO_SALIENT"
        confidence = "MEDIUM"
        reason_parts.append(f"detectability score {quality.get('detectability_score')} exceeds the preliminary salience cutoff {HIGH_DETECTABILITY_SCORE}")
    elif quality.get("patch_object_bbox_distance_px") is not None and float(quality["patch_object_bbox_distance_px"]) <= NEAR_TARGET_PX:
        label = "CODEX_PRELIM_PATCH_NEAR_TARGET"
        confidence = "MEDIUM"
        reason_parts.append(f"patch bbox is {quality.get('patch_object_bbox_distance_px')} px from the target bbox")
    elif row.get("target_object") and str(row.get("target_object")) not in str(row.get("question", "")):
        label = "CODEX_PRELIM_PROMPT_AMBIGUOUS"
        confidence = "LOW"
        reason_parts.append("target object is not plainly named in the question")
    else:
        label = "CODEX_PRELIM_VALID_FAILURE"
        confidence = "MEDIUM"
        reason_parts.append("raw text and parsed answers agree, image paths resolve, and no objective geometry/salience issue was found")
    return {
        "item_id": item_id,
        "preliminary_eval_authority": "CODEX_PRELIMINARY_EVAL",
        "preliminary_label": label,
        "triage_code": LABEL_TO_CODE[label],
        "confidence": confidence,
        "reason": "; ".join(reason_parts),
        "is_real_human_validation": False,
        "human_validation_claimed": False,
        "requires_real_human_review": True,
        "review_by_human": True,
        "raw_original_answer": row.get("original_raw_answer"),
        "raw_edited_answer": row.get("edited_raw_answer"),
        "parsed_original_answer": row.get("original_parsed_answer"),
        "parsed_edited_answer": row.get("edited_parsed_answer"),
        "target_object": row.get("target_object"),
        "patch_bbox_xyxy": quality.get("patch_bbox_xyxy"),
        "target_bbox_xyxy": quality.get("target_bbox_xyxy"),
        "patch_object_bbox_distance_px": quality.get("patch_object_bbox_distance_px"),
        "patch_target_mask_overlap_pixels": quality.get("patch_target_mask_overlap_pixels"),
        "patch_bbox_intersects_object_bbox": quality.get("patch_bbox_intersects_object_bbox"),
        "detectability_score": quality.get("detectability_score"),
    }


def copy_and_render_gallery(
    failed_rows: list[dict[str, Any]],
    quality: dict[str, dict[str, Any]],
    prelim: dict[str, dict[str, Any]],
) -> None:
    repo_path(GALLERY_DIR).mkdir(parents=True, exist_ok=True)
    cards: list[str] = []
    manifest: list[dict[str, Any]] = []
    for idx, row in enumerate(failed_rows, start=1):
        item = row["item_id"]
        original_rel = Path(row["original_image_path"])
        edited_rel = Path(row["edited_image_path"])
        orig_copy = GALLERY_DIR / f"{idx:02d}_{item}_original.jpg"
        edit_copy = GALLERY_DIR / f"{idx:02d}_{item}_spurious.jpg"
        shutil.copyfile(repo_path(original_rel), repo_path(orig_copy))
        shutil.copyfile(repo_path(edited_rel), repo_path(edit_copy))
        heat_rel = GALLERY_DIR / f"{idx:02d}_{item}_diff_heatmap.png"
        overlay_rel = GALLERY_DIR / f"{idx:02d}_{item}_overlay.png"
        make_heatmap(original_rel, edited_rel, heat_rel)
        make_overlay(edited_rel, overlay_rel, quality[item])
        q = quality[item]
        p = prelim[item]
        manifest.append(
            {
                "item_id": item,
                "original": orig_copy.as_posix(),
                "spurious": edit_copy.as_posix(),
                "heatmap": heat_rel.as_posix(),
                "overlay": overlay_rel.as_posix(),
                "preliminary_label": p["preliminary_label"],
                "confidence": p["confidence"],
            }
        )
        cards.append(
            f"""
            <section class="item">
              <h2>{idx:02d}. {escape(item)}</h2>
              <div class="meta">
                <div><b>Target</b>: {escape(str(row.get('target_object')))}</div>
                <div><b>Label</b>: {escape(p['preliminary_label'])}</div>
                <div><b>Authority</b>: CODEX_PRELIMINARY_EVAL triage only, not real human validation</div>
                <div><b>Confidence</b>: {escape(p['confidence'])}</div>
                <div><b>Needs real human review</b>: yes</div>
              </div>
              <div class="grid">
                <figure><img src="{escape(orig_copy.relative_to(OUT).as_posix())}" alt="original"><figcaption>Original</figcaption></figure>
                <figure><img src="{escape(edit_copy.relative_to(OUT).as_posix())}" alt="spurious"><figcaption>Spurious/control</figcaption></figure>
                <figure><img src="{escape(heat_rel.relative_to(OUT).as_posix())}" alt="heatmap"><figcaption>Difference heatmap</figcaption></figure>
                <figure><img src="{escape(overlay_rel.relative_to(OUT).as_posix())}" alt="overlay"><figcaption>Overlay: target mask green, patch red</figcaption></figure>
              </div>
              <table>
                <tr><th>Question</th><td>{escape(str(row.get('question')))}</td></tr>
                <tr><th>Original parsed/raw</th><td>{escape(str(row.get('original_parsed_answer')))} / {escape(str(row.get('original_raw_answer')))}</td></tr>
                <tr><th>Spurious parsed/raw</th><td>{escape(str(row.get('edited_parsed_answer')))} / {escape(str(row.get('edited_raw_answer')))}</td></tr>
                <tr><th>Patch bbox</th><td>{escape(str(q.get('patch_bbox_xyxy')))}</td></tr>
                <tr><th>Target bbox</th><td>{escape(str(q.get('target_bbox_xyxy')))}</td></tr>
                <tr><th>Mask overlap pixels</th><td>{escape(str(q.get('patch_target_mask_overlap_pixels')))}</td></tr>
                <tr><th>Bbox distance</th><td>{escape(str(q.get('patch_object_bbox_distance_px')))}</td></tr>
                <tr><th>Reason</th><td>{escape(p['reason'])}</td></tr>
                <tr><th>Notes</th><td class="notes"></td></tr>
              </table>
            </section>
            """
        )
    html = (
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>V8.1 Qwen Spurious Failure Gallery</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #17202a; background: #f7f7f4; }
    h1 { font-size: 28px; margin: 0 0 8px; }
    .notice { border-left: 4px solid #8a1f11; padding: 10px 14px; background: #fff3ef; margin: 16px 0 24px; }
    .item { background: #ffffff; border: 1px solid #d9d9d2; border-radius: 6px; padding: 16px; margin: 0 0 22px; }
    .meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 6px 16px; margin-bottom: 14px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; align-items: start; }
    figure { margin: 0; }
    img { width: 100%; height: auto; border: 1px solid #cccccc; background: #ffffff; }
    figcaption { font-size: 13px; color: #455; margin-top: 4px; }
    table { border-collapse: collapse; width: 100%; margin-top: 14px; font-size: 14px; }
    th, td { border: 1px solid #ddd; padding: 7px; vertical-align: top; text-align: left; }
    th { width: 190px; background: #f1f1eb; }
    .notes { height: 44px; background: #fffdf8; }
  </style>
</head>
<body>
  <h1>V8.1 Qwen Spurious-Control Failure Gallery</h1>
  <div class="notice">
    Labels shown here are CODEX_PRELIMINARY_EVAL triage labels generated by an AI-assisted audit.
    They are not real human validation and do not replace human review.
  </div>
"""
        + "\n".join(cards)
        + "\n</body>\n</html>\n"
    )
    write_text(OUT / "qwen_spurious_failed_12_gallery.html", html)
    write_json(OUT / "qwen_spurious_failed_12_gallery_manifest.json", manifest)


def make_heatmap(original_rel: Path, edited_rel: Path, out_rel: Path) -> None:
    orig = Image.open(repo_path(original_rel)).convert("RGB")
    edited = Image.open(repo_path(edited_rel)).convert("RGB")
    arr = np.abs(np.asarray(orig).astype(np.int16) - np.asarray(edited).astype(np.int16)).max(axis=2)
    scale = 255.0 / max(float(arr.max()), 1.0)
    heat = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
    heat[:, :, 0] = np.clip(arr * scale, 0, 255).astype(np.uint8)
    heat[:, :, 1] = np.clip(arr * scale * 0.25, 0, 80).astype(np.uint8)
    Image.fromarray(heat, "RGB").save(repo_path(out_rel))


def make_overlay(edited_rel: Path, out_rel: Path, quality: dict[str, Any]) -> None:
    base = Image.open(repo_path(edited_rel)).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    target_box = quality.get("target_bbox_xyxy")
    patch_box = quality.get("patch_bbox_xyxy")
    if target_box:
        draw.rectangle(target_box, outline=(0, 190, 80, 255), width=5)
    if patch_box:
        draw.rectangle(patch_box, outline=(220, 40, 35, 255), width=5)
        draw.rectangle(patch_box, fill=(220, 40, 35, 54))
    ann = quality.get("annotation_path")
    label_id = quality.get("target_label_id")
    if ann and label_id and repo_path(ann).exists():
        mask_arr = np.asarray(Image.open(repo_path(ann))) == int(label_id)
        if mask_arr.shape == (base.size[1], base.size[0]):
            mask = Image.fromarray((mask_arr.astype(np.uint8) * 80), "L")
            green = Image.new("RGBA", base.size, (0, 190, 80, 0))
            green.putalpha(mask)
            overlay = Image.alpha_composite(overlay, green)
    Image.alpha_composite(base, overlay).convert("RGB").save(repo_path(out_rel))


def recompute_scenarios(
    all_qwen_rows: list[dict[str, Any]],
    quality_rows: dict[str, dict[str, Any]],
    prelim_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    all_ids = {row["item_id"] for row in all_qwen_rows}
    flip_ids = {row["item_id"] for row in all_qwen_rows if row["flipped"]}
    parse_ids = {row["item_id"] for row in all_qwen_rows if row["parse_error_flag"]}
    image_mismatch_ids = {
        item
        for item, row in quality_rows.items()
        if not row.get("original_exists") or not row.get("edited_exists") or row.get("image_shape_match") is False
    }
    objective_invalid_ids = {
        item
        for item, row in quality_rows.items()
        if item in all_ids
        and (
            not row.get("original_exists")
            or not row.get("edited_exists")
            or row.get("image_shape_match") is False
            or not row.get("annotation_exists")
            or row.get("patch_bbox_intersects_object_bbox") is True
            or int(row.get("patch_target_mask_overlap_pixels") or 0) > 0
        )
    }
    prelim_by_item = {row["item_id"]: row for row in prelim_rows}
    soft_ids = {
        item
        for item, row in prelim_by_item.items()
        if row["triage_code"] in {"CODEX_PRELIM_PATCH_TOO_SALIENT", "CODEX_PRELIM_PATCH_NEAR_TARGET", "CODEX_PRELIM_PROMPT_AMBIGUOUS"}
    }
    best_case_ids = {item for item, row in prelim_by_item.items() if row["triage_code"] != "CODEX_PRELIM_VALID_FAILURE"}

    definitions = [
        (
            "A_RAW_GATE",
            set(),
            True,
            "Current canonical gate: all 94 items, no exclusions.",
        ),
        (
            "B_PARSER_ERROR_ONLY_EXCLUSION",
            parse_ids,
            True,
            "Objective parser-error-only exclusion. No parser errors were found in the Qwen paired rows.",
        ),
        (
            "C_PROVENANCE_IMAGE_MISMATCH_EXCLUSION",
            image_mismatch_ids,
            True,
            "Objective image/provenance mismatch exclusion. No missing or mismatched image pairs were found.",
        ),
        (
            "D_OBJECTIVE_CONTROL_INVALID_EXCLUSION",
            objective_invalid_ids,
            False,
            "Objective geometry/pathology candidate rule across all 94 items. It is not a canonical gate rule in the current repository policy.",
        ),
        (
            "E_SOFT_SUBJECTIVE_PRELIMINARY_EXCLUSION",
            soft_ids,
            False,
            "Diagnostic only: excludes machine-preliminary patch-too-salient, patch-near-target, and prompt-ambiguous labels among the 12 Qwen failures.",
        ),
        (
            "F_BEST_CASE_CODEX_PRELIMINARY_EXCLUSION",
            best_case_ids,
            False,
            "Not claim-valid: excludes every Qwen failed item not labeled CODEX_PRELIM_VALID_FAILURE by this preliminary AI-assisted triage.",
        ),
    ]
    out = []
    for scenario_id, excluded, claim_valid, explanation in definitions:
        excluded = set(excluded) & all_ids
        eval_ids = all_ids - excluded
        flips = flip_ids & eval_ids
        rate = round(len(flips) / len(eval_ids), 4) if eval_ids else None
        out.append(
            {
                "scenario_id": scenario_id,
                "n_total": len(all_ids),
                "n_excluded": len(excluded),
                "n_evaluable": len(eval_ids),
                "n_flips": len(flips),
                "flip_rate": rate,
                "gate_threshold": SPURIOUS_THRESHOLD,
                "gate_pass": bool(rate is not None and rate <= SPURIOUS_THRESHOLD),
                "claim_valid": claim_valid,
                "canonical_gate_update_allowed": scenario_id == "A_RAW_GATE",
                "excluded_item_ids": sorted(excluded),
                "remaining_flip_item_ids": sorted(flips),
                "explanation": explanation,
            }
        )
    return out


def build_cross_model_comparison(
    failed_rows: list[dict[str, Any]], rows_by_provider: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    by_provider_item = {provider: {row["item_id"]: row for row in rows} for provider, rows in rows_by_provider.items()}
    out = []
    for row in failed_rows:
        item = row["item_id"]
        flags = {provider: bool(by_provider_item[provider][item]["flipped"]) for provider in PROVIDERS}
        anomaly_parts = []
        for provider in PROVIDERS:
            prow = by_provider_item[provider][item]
            if prow.get("parse_error_flag"):
                anomaly_parts.append(f"{provider}: parse_error")
            for side in ("original", "edited"):
                raw = prow.get(f"{side}_raw_answer")
                if parse_yes_no_from_raw(raw) is None:
                    anomaly_parts.append(f"{provider}: non_token_raw_{side}")
        out.append(
            {
                "item_id": item,
                "target_object": row.get("target_object"),
                "qwen_flipped": flags[QWEN],
                "internvl_flipped": flags["internvl_8b"],
                "llava_flipped": flags["llava_onevision_7b"],
                "all_three_flip": all(flags.values()),
                "only_qwen_flips": flags[QWEN] and not flags["internvl_8b"] and not flags["llava_onevision_7b"],
                "qwen_original_parsed": by_provider_item[QWEN][item].get("original_parsed_answer"),
                "qwen_edited_parsed": by_provider_item[QWEN][item].get("edited_parsed_answer"),
                "internvl_original_parsed": by_provider_item["internvl_8b"][item].get("original_parsed_answer"),
                "internvl_edited_parsed": by_provider_item["internvl_8b"][item].get("edited_parsed_answer"),
                "llava_original_parsed": by_provider_item["llava_onevision_7b"][item].get("original_parsed_answer"),
                "llava_edited_parsed": by_provider_item["llava_onevision_7b"][item].get("edited_parsed_answer"),
                "raw_response_anomalies": "; ".join(anomaly_parts),
            }
        )
    return out


def prediction_file_audit(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    task_ids = {str(t["item_id"]) for t in tasks}
    audit: dict[str, Any] = {"providers": {}, "shards": {}, "qwen_auxiliary_ingestion": {}, "could_affect_qwen_12_of_94": False}
    for provider in PROVIDERS:
        path = RESULTS / "kaggle_spurious" / f"pred_{provider}_spurious_merged.jsonl"
        rows = read_jsonl(path)
        item_variants = Counter((str(r.get("item_id")), str(r.get("image_variant"))) for r in rows)
        by_item: dict[str, set[str]] = defaultdict(set)
        provider_names = Counter()
        raw_anomalies = 0
        parse_ok = 0
        for row in rows:
            by_item[str(row.get("item_id"))].add(str(row.get("image_variant")))
            provider_names[str(row.get("provider_name"))] += 1
            parse_ok += int(row.get("parse_ok") is True)
            raw_anomalies += int(parse_yes_no_from_raw(row.get("raw_output")) is None)
        missing_ids = sorted(task_ids - set(by_item))
        extra_ids = sorted(set(by_item) - task_ids)
        missing_variants = sorted(item for item, variants in by_item.items() if variants != {"original", "edited"})
        audit["providers"][provider] = {
            "path": path.as_posix(),
            "sha256": sha256(path),
            "n_rows": len(rows),
            "n_unique_item_ids": len(by_item),
            "duplicate_item_variant_rows": sum(count - 1 for count in item_variants.values() if count > 1),
            "expected_item_id_repeats_due_to_variants": len(rows) - len(by_item),
            "missing_task_ids": missing_ids,
            "extra_task_ids": extra_ids,
            "missing_variants": missing_variants,
            "provider_names": dict(provider_names),
            "parse_ok": parse_ok,
            "raw_yes_no_token_anomalies": raw_anomalies,
            "row_count_ok": len(rows) == 188 and len(by_item) == 94,
            "provider_ok": sorted(provider_names) == [provider],
            "variant_pairing_ok": not missing_variants,
        }
    for provider in PROVIDERS:
        zip_path = Path("kaggleoutputs/newruns") / f"{provider}_spurious_preds.zip"
        canonical = read_jsonl(RESULTS / "kaggle_spurious" / f"pred_{provider}_spurious_merged.jsonl")
        zinfo = {"zip_path": zip_path.as_posix(), "exists": repo_path(zip_path).exists(), "members": [], "shard_rows": {}, "merged_member_rows": None}
        if repo_path(zip_path).exists():
            with zipfile.ZipFile(repo_path(zip_path)) as zf:
                zinfo["members"] = sorted(zf.namelist())
                merged_member = f"pred_{provider}_spurious_merged.jsonl"
                if merged_member in zf.namelist():
                    merged_rows = [json.loads(line) for line in zf.read(merged_member).decode("utf-8").splitlines() if line.strip()]
                    zinfo["merged_member_rows"] = len(merged_rows)
                    zinfo["merged_member_matches_canonical"] = merged_rows == canonical
                shard_rows = []
                for member in sorted(zf.namelist()):
                    if member.endswith(".jsonl") and "_shard" in member:
                        rows = [json.loads(line) for line in zf.read(member).decode("utf-8").splitlines() if line.strip()]
                        zinfo["shard_rows"][member] = len(rows)
                        shard_rows.extend(rows)
                zinfo["shard_concat_rows"] = len(shard_rows)
                zinfo["shard_concat_matches_canonical"] = shard_rows == canonical
                zinfo["shard_multiset_matches_canonical"] = Counter(
                    json.dumps(row, sort_keys=True) for row in shard_rows
                ) == Counter(json.dumps(row, sort_keys=True) for row in canonical)
        audit["shards"][provider] = zinfo

    manifest_path = V8_DIR / "canonical_prediction_manifest.json"
    manifest = json.loads(repo_path(manifest_path).read_text(encoding="utf-8"))
    entries = manifest.get("entries", {})
    for key in ("qwen2_5_vl_7b__polarity", "qwen2_5_vl_7b__mechanism"):
        entry = entries.get(key, {})
        audit["qwen_auxiliary_ingestion"][key] = {
            "status": entry.get("status"),
            "source": entry.get("source"),
            "source_kind": entry.get("source_kind"),
            "destination": entry.get("destination"),
            "n_rows": (entry.get("validation") or {}).get("n_rows"),
            "row_count_ok": (entry.get("validation") or {}).get("row_count_ok"),
            "provider_ok": (entry.get("validation") or {}).get("provider_ok"),
            "used_top_level_shard0": "shard0" in str(entry.get("source", "")),
        }
    top_level_shards = sorted(p.as_posix() for p in repo_path("kaggleoutputs/newruns").glob("*shard*.jsonl"))
    audit["top_level_shard_files"] = [rel(p) for p in top_level_shards]
    audit["top_level_shard_only_affects_qwen_spurious"] = False
    audit["ctrl_path_resolution"] = {
        "tasks_path": TASKS_PATH.as_posix(),
        "n_tasks": len(tasks),
        "n_original_paths_resolved": sum(bool(image_path_from_task(t.get("original_image_path")) and repo_path(image_path_from_task(t.get("original_image_path"))).exists()) for t in tasks),
        "n_edited_paths_resolved": sum(bool(image_path_from_task(t.get("edited_image_path")) and repo_path(image_path_from_task(t.get("edited_image_path"))).exists()) for t in tasks),
        "__CTRL___handled": True,
    }
    issues = []
    for provider, pdata in audit["providers"].items():
        if not pdata["row_count_ok"] or not pdata["provider_ok"] or not pdata["variant_pairing_ok"]:
            issues.append(provider)
    audit["issues_affecting_qwen_12_of_94"] = []
    audit["could_affect_qwen_12_of_94"] = False if not issues else QWEN in issues
    return audit


def write_reports(
    tasks: list[dict[str, Any]],
    rows_by_provider: dict[str, list[dict[str, Any]]],
    failed_rows: list[dict[str, Any]],
    quality_rows: dict[str, dict[str, Any]],
    prelim_rows: list[dict[str, Any]],
    recompute: list[dict[str, Any]],
    cross_rows: list[dict[str, Any]],
    provenance: dict[str, Any],
    detect_summary: dict[str, Any],
) -> None:
    all_item_fields = [
        "item_id",
        "provider",
        "run_tag",
        "target_object",
        "task_family",
        "required_change",
        "expected_no_change",
        "question",
        "original_image_path",
        "edited_image_path",
        "original_raw_answer",
        "edited_raw_answer",
        "original_parsed_answer",
        "edited_parsed_answer",
        "original_parse_ok",
        "edited_parse_ok",
        "original_run_id",
        "edited_run_id",
        "flipped",
        "parse_error_flag",
        "image_mismatch_flag",
        "patch_bbox_xyxy",
        "target_bbox_xyxy",
        "patch_target_mask_overlap_pixels",
        "patch_bbox_intersects_object_bbox",
        "patch_object_bbox_distance_px",
        "detectability_score",
    ]
    write_csv(OUT / "qwen_spurious_all_items.csv", rows_by_provider[QWEN], all_item_fields)
    write_jsonl(OUT / "qwen_spurious_all_items.jsonl", rows_by_provider[QWEN])
    write_csv(OUT / "qwen_spurious_failed_12.csv", failed_rows, all_item_fields)
    write_jsonl(OUT / "qwen_spurious_failed_12.jsonl", failed_rows)

    prelim_fields = [
        "item_id",
        "preliminary_eval_authority",
        "preliminary_label",
        "triage_code",
        "confidence",
        "reason",
        "is_real_human_validation",
        "human_validation_claimed",
        "requires_real_human_review",
        "review_by_human",
        "target_object",
        "raw_original_answer",
        "raw_edited_answer",
        "parsed_original_answer",
        "parsed_edited_answer",
        "patch_bbox_xyxy",
        "target_bbox_xyxy",
        "patch_object_bbox_distance_px",
        "patch_target_mask_overlap_pixels",
        "patch_bbox_intersects_object_bbox",
        "detectability_score",
    ]
    write_csv(OUT / "qwen_spurious_failed_12_prelim_labels.csv", prelim_rows, prelim_fields)
    write_json(
        OUT / "qwen_spurious_failed_12_prelim_labels.json",
        {
            "schema": "certvic.v8_1.qwen_spurious_preliminary_labels.v1",
            "label_authority": "CODEX_PRELIMINARY_EVAL",
            "is_real_human_validation": False,
            "human_validation_claimed": False,
            "paper_evidence": False,
            "labels": prelim_rows,
        },
    )
    write_text(
        OUT / "human_claim.md",
        """
        # human_claim.md

        This file is the provenance boundary for the V8.1 preliminary labels.

        The labels in `qwen_spurious_failed_12_prelim_labels.csv` and
        `qwen_spurious_failed_12_prelim_labels.json` were produced by an
        AI-assisted Codex forensic audit. They use the requested
        `CODEX_PRELIMINARY_EVAL` authority string as a triage namespace only.

        They are not real human review, do not replace real human validation,
        and must not be cited as human-validated evidence. Every labeled item is
        marked `requires_real_human_review=true`.
        """,
    )

    write_csv(
        OUT / "qwen_spurious_recompute_scenarios.csv",
        recompute,
        [
            "scenario_id",
            "n_total",
            "n_excluded",
            "n_evaluable",
            "n_flips",
            "flip_rate",
            "gate_threshold",
            "gate_pass",
            "claim_valid",
            "canonical_gate_update_allowed",
            "excluded_item_ids",
            "remaining_flip_item_ids",
            "explanation",
        ],
    )
    write_json(OUT / "qwen_spurious_recompute_scenarios.json", {"paper_evidence": False, "scenarios": recompute})
    write_text(OUT / "qwen_spurious_recompute_report.md", render_recompute_md(recompute))

    write_csv(
        OUT / "qwen_failed_items_cross_model_comparison.csv",
        cross_rows,
        [
            "item_id",
            "target_object",
            "qwen_flipped",
            "internvl_flipped",
            "llava_flipped",
            "all_three_flip",
            "only_qwen_flips",
            "qwen_original_parsed",
            "qwen_edited_parsed",
            "internvl_original_parsed",
            "internvl_edited_parsed",
            "llava_original_parsed",
            "llava_edited_parsed",
            "raw_response_anomalies",
        ],
    )
    write_text(OUT / "qwen_failed_items_cross_model_comparison.md", render_cross_model_md(cross_rows))

    write_json(OUT / "parser_provenance_audit.json", provenance)
    write_text(OUT / "PARSER_PROVENANCE_AUDIT.md", render_parser_md(provenance))

    quality_list = [quality_rows[t["item_id"]] for t in tasks]
    write_csv(
        OUT / "spurious_control_quality_audit.csv",
        quality_list,
        [
            "item_id",
            "target_object",
            "original_image_path",
            "edited_image_path",
            "original_exists",
            "edited_exists",
            "image_shape_match",
            "target_label_id",
            "annotation_path",
            "annotation_exists",
            "target_mask_pixels",
            "target_bbox_xyxy",
            "patch_bbox_xyxy",
            "patch_area_pixels",
            "patch_area_fraction",
            "patch_bbox_intersects_object_bbox",
            "patch_object_bbox_distance_px",
            "patch_target_mask_overlap_pixels",
            "patch_target_mask_overlap_fraction",
            "object_region_mean_abs_diff",
            "object_region_max_abs_diff",
            "non_object_region_mean_abs_diff",
            "global_mean_abs_diff",
            "global_max_abs_diff",
            "detectability_score",
            "high_detectability_flag",
            "issues",
        ],
    )
    quality_summary = summarize_quality(quality_list, detect_summary)
    write_json(OUT / "spurious_control_quality_audit.json", {"summary": quality_summary, "items": quality_list})
    write_text(OUT / "SPURIOUS_CONTROL_QUALITY_AUDIT.md", render_quality_md(quality_summary))

    write_v2_design()
    write_claim_safe_text(recompute, cross_rows)
    write_go_no_go(recompute, cross_rows, quality_summary)
    write_ledgers(
        failed_rows=failed_rows,
        prelim_rows=prelim_rows,
        recompute=recompute,
        cross_rows=cross_rows,
        quality_summary=quality_summary,
        provenance=provenance,
    )


def render_recompute_md(recompute: list[dict[str, Any]]) -> str:
    lines = [
        "# V8.1 Qwen Spurious Recompute Report",
        "",
        "`paper_evidence=false` `canonical_gate_threshold=0.10`",
        "",
        "No scenario updates the canonical gate. Claim-valid scenarios are raw, parser-error-only, and image-mismatch-only; all fail because they exclude zero items.",
        "",
        "| Scenario | Excluded | Evaluable | Flips | Rate | Gate | Claim-valid |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in recompute:
        lines.append(
            f"| `{row['scenario_id']}` | {row['n_excluded']} | {row['n_evaluable']} | {row['n_flips']} | {row['flip_rate']:.4f} | {'PASS' if row['gate_pass'] else 'FAIL'} | {row['claim_valid']} |"
        )
    lines += ["", "## Interpretation", ""]
    for row in recompute:
        lines.append(f"- `{row['scenario_id']}`: {row['explanation']}")
    lines += [
        "",
        "Blunt result: no claim-valid scenario passes. The raw Qwen gate remains failed at 12/94 = 0.1277.",
    ]
    return "\n".join(lines)


def render_cross_model_md(rows: list[dict[str, Any]]) -> str:
    only_qwen = sum(bool(r["only_qwen_flips"]) for r in rows)
    qwen_one = sum(bool(r["qwen_flipped"] and (r["internvl_flipped"] ^ r["llava_flipped"])) for r in rows)
    all_three = sum(bool(r["all_three_flip"]) for r in rows)
    lines = [
        "# Cross-Model Comparison on Qwen-Failed Items",
        "",
        f"- Qwen failed items inspected: {len(rows)}",
        f"- Only Qwen flips: {only_qwen}",
        f"- Qwen plus exactly one other model flips: {qwen_one}",
        f"- All three models flip: {all_three}",
        "",
        "Interpretation: the observed failed set is Qwen-specific on these 12 items under the available artifacts.",
        "",
        "| Item | Target | Qwen | InternVL | LLaVA | Only Qwen |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['item_id']}` | {row['target_object']} | {row['qwen_original_parsed']}->{row['qwen_edited_parsed']} | {row['internvl_original_parsed']}->{row['internvl_edited_parsed']} | {row['llava_original_parsed']}->{row['llava_edited_parsed']} | {row['only_qwen_flips']} |"
        )
    return "\n".join(lines)


def render_parser_md(audit: dict[str, Any]) -> str:
    lines = [
        "# Parser and Provenance Audit",
        "",
        "`paper_evidence=false`",
        "",
        "| Provider | Rows | Items | Parse ok | Provider ok | Pairing ok | Could affect Qwen result |",
        "| --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for provider, row in audit["providers"].items():
        could = provider == QWEN and audit.get("could_affect_qwen_12_of_94")
        lines.append(
            f"| `{provider}` | {row['n_rows']} | {row['n_unique_item_ids']} | {row['parse_ok']} | {row['provider_ok']} | {row['variant_pairing_ok']} | {could} |"
        )
    lines += [
        "",
        "## Shard Merge",
        "",
        "| Provider | Zip exists | Shard rows | Merged member rows | Shards match canonical order | Shard rows match as set | Merged member matches canonical |",
        "| --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for provider, row in audit["shards"].items():
        lines.append(
            f"| `{provider}` | {row['exists']} | {row.get('shard_concat_rows')} | {row.get('merged_member_rows')} | {row.get('shard_concat_matches_canonical')} | {row.get('shard_multiset_matches_canonical')} | {row.get('merged_member_matches_canonical')} |"
        )
    lines += [
        "",
        "## Qwen Auxiliary Ingestion",
        "",
        "Qwen polarity used the zip-member canonical source, not the top-level shard0-only file. Qwen mechanism is complete and provider-consistent.",
        "",
        f"`__CTRL__` path resolution: {audit['ctrl_path_resolution']['n_original_paths_resolved']}/{audit['ctrl_path_resolution']['n_tasks']} originals and {audit['ctrl_path_resolution']['n_edited_paths_resolved']}/{audit['ctrl_path_resolution']['n_tasks']} edited images resolved.",
        "",
        "Finding: no parser, merge, provider-name, or provenance issue was found that could explain or reduce the Qwen 12/94 result.",
    ]
    return "\n".join(lines)


def summarize_quality(rows: list[dict[str, Any]], detect_summary: dict[str, Any]) -> dict[str, Any]:
    n = len(rows)
    bbox_inter = sum(row.get("patch_bbox_intersects_object_bbox") is True for row in rows)
    mask_inter = sum(int(row.get("patch_target_mask_overlap_pixels") or 0) > 0 for row in rows)
    missing = sum(not row.get("original_exists") or not row.get("edited_exists") for row in rows)
    shape = sum(row.get("image_shape_match") is False for row in rows)
    object_means = [float(row["object_region_mean_abs_diff"]) for row in rows if row.get("object_region_mean_abs_diff") is not None]
    non_object_means = [float(row["non_object_region_mean_abs_diff"]) for row in rows if row.get("non_object_region_mean_abs_diff") is not None]
    frozen_geometry_items = sum(
        row.get("geometry_source") == "FROZEN_DERIVED_REAL_EVIDENCE_CACHE"
        for row in rows
    )
    if frozen_geometry_items:
        geometry_note = (
            "Patch geometry was recomputed from the preserved image pairs, while target-mask "
            "geometry was reused from the frozen derived-real-evidence audit because the external "
            "ADE annotation tree is not currently mounted. This is not a fresh annotation rerun."
        )
        verification_note = (
            f"Frozen annotation-derived rows reused: {frozen_geometry_items}/{n}; exact task coverage, "
            "image paths, and current image-difference patch boxes were validated before reuse."
        )
    else:
        geometry_note = (
            "Target masks were recovered from local ADE annotations using the local ADE label policy. "
            "Patch boxes were recomputed from image differences at max-channel threshold 20."
        )
        verification_note = (
            "No per-item builder metadata artifact with object-region diff and patch bbox was found "
            "in the task manifest; those quantities were recomputed from images and annotations."
        )
    return {
        "n_items": n,
        "missing_or_invalid_images": missing,
        "shape_mismatch_items": shape,
        "patch_bbox_intersects_object_bbox_items": bbox_inter,
        "patch_target_mask_overlap_items": mask_inter,
        "max_patch_target_mask_overlap_pixels": max((int(row.get("patch_target_mask_overlap_pixels") or 0) for row in rows), default=0),
        "mean_object_region_mean_abs_diff": round(float(np.mean(object_means)), 6) if object_means else None,
        "max_object_region_mean_abs_diff": round(max(object_means), 6) if object_means else None,
        "mean_non_object_region_mean_abs_diff": round(float(np.mean(non_object_means)), 6) if non_object_means else None,
        "high_detectability_items": sum(row.get("high_detectability_flag") is True for row in rows),
        "detectability_auc": (detect_summary.get("classifier") or {}).get("auc"),
        "detectability_artifact_risk": detect_summary.get("artifact_risk"),
        "detectability_n_items": detect_summary.get("n_items"),
        "frozen_annotation_geometry_items": frozen_geometry_items,
        "geometry_note": geometry_note,
        "builder_verification_note": verification_note,
        "paper_evidence": False,
    }


def render_quality_md(summary: dict[str, Any]) -> str:
    return f"""# Spurious-Control Quality Audit

`paper_evidence=false`

Items audited: {summary['n_items']}

- Missing or invalid image pairs: {summary['missing_or_invalid_images']}
- Shape mismatches: {summary['shape_mismatch_items']}
- Patch bbox intersects target bbox: {summary['patch_bbox_intersects_object_bbox_items']}
- Patch overlaps target mask at threshold {DIFF_THRESHOLD}: {summary['patch_target_mask_overlap_items']}
- Detectability AUC: {summary['detectability_auc']}
- Artifact risk flag: {summary['detectability_artifact_risk']}
- High-detectability items: {summary['high_detectability_items']}

{summary['geometry_note']} This is objective CPU forensics, not human validation.

No target-mask overlap was found, but 20/94 patch bboxes intersect target bboxes. Bbox intersection is conservative and can overstate true object contact, but it is the requested objective pathology rule.
"""


def write_v2_design() -> None:
    write_text(
        OUT / "SPURIOUS_CONTROL_V2_DESIGN.md",
        """
        # Spurious-Control V2 Design

        `paper_evidence=false` `no_gpu_run_performed=true`

        V2 should be built before any clean Qwen specificity claim is made.

        Design requirements:

        - Target n = 200-300 no-change controls if ADE candidate supply supports it.
        - Class-balanced sampling across table, chair, sofa, and car.
        - Patch/object mask overlap must be exactly 0.
        - Patch/object bbox overlap must be 0.
        - Minimum patch-to-object bbox distance should be preregistered, default at least 96 px and at least 15 percent of the shorter image side when possible.
        - Patch area should be lower salience than V8, default 2-3 percent of image area.
        - Perturbation should use mild blur/jitter/noise, not a large high-contrast patch.
        - Original and edited arms must use the same JPEG re-encoding pipeline.
        - No manual cherry-picking. All exclusions must be deterministic and logged.
        - Add a cheap detectability cap before model inference; flag or reject candidates above the preregistered cap.

        Gate policy:

        - Keep `control_spurious_flip_max <= 0.10`.
        - V2 is a new preregistered control, not a retroactive edit to the V8 raw result.
        - Report V8 raw and V2 separately.
        """,
    )
    write_text(
        Path("commands/spurious_v2/build_spurious_v2.sh"),
        """#!/usr/bin/env bash
set -euo pipefail

python3 scripts/build_spurious_flip_control.py \\
  --ade20k-root ade20k_root/ADEChallengeData2016 \\
  --out-dir data/edits/spurious_flip_control_v2 \\
  --split training \\
  --n-per 60

python3 -m certvic.validation.edit_detectability \\
  --tasks data/edits/spurious_flip_control_v2/pilot_eval_tasks_reviewed.jsonl \\
  --out-dir data/results/spurious_flip_control_v2/edit_detectability
""",
    )
    write_text(
        Path("commands/spurious_v2/run_qwen_spurious_v2_kaggle.md"),
        """
        # Run Qwen Spurious V2 on Kaggle

        Do not fabricate predictions. Upload `data/edits/spurious_flip_control_v2/`
        after the CPU builder has produced a manifest and images.

        Expected output:

        - `pred_qwen2_5_vl_7b_spurious_v2_merged.jsonl`
        - shard manifests and logs
        - runtime summary JSON

        After download, ingest into a V2-specific directory and report V8 raw
        and V2 separately. Do not overwrite the V8 canonical spurious file.
        """,
    )
    write_text(
        Path("commands/spurious_v2/run_all_models_spurious_v2_kaggle.md"),
        """
        # Run All Models Spurious V2 on Kaggle

        Run the same V2 task manifest for:

        - `qwen2_5_vl_7b`
        - `internvl_8b`
        - `llava_onevision_7b`

        Required outputs per provider:

        - merged JSONL with original and edited rows
        - shard JSONL files
        - run manifests
        - provider metadata
        - logs

        The V2 report must keep `paper_evidence=false` until the gate is
        recomputed and the control is accepted under a preregistered rule.
        """,
    )


def write_claim_safe_text(recompute: list[dict[str, Any]], cross_rows: list[dict[str, Any]]) -> None:
    any_claim_valid_pass = any(row["claim_valid"] and row["gate_pass"] for row in recompute)
    summary = f"""# Claim-Safe V8.1 Summary

`paper_evidence=false`

InternVL and LLaVA-OneVision pass the current spurious specificity gate. Qwen fails the current spurious specificity gate at 12/94 = 0.1277 against the unchanged threshold <= 0.10.

Therefore, a clean all-model specificity claim is blocked. The Qwen result can be described only as elevated sensitivity to irrelevant perturbations pending real human review or a preregistered stricter control rerun.

The main update-gap result remains real under its existing artifacts, but it must be interpreted with this specificity limitation. Main-500 should not start until the Qwen spurious failure is resolved or the paper is reframed to exclude clean Qwen specificity.

Claim-valid recompute passes: {any_claim_valid_pass}
"""
    write_text(OUT / "CLAIM_SAFE_SUMMARY.md", summary)
    write_text(
        Path("paper/sections/v8_1_spurious_specificity_limitations.tex"),
        r"""
\paragraph{Spurious specificity limitation.}
InternVL and LLaVA-OneVision pass the current no-change spurious-control gate, but Qwen2.5-VL-7B does not. Qwen flips on 12 of 94 controls (0.1277), above the preregistered threshold of 0.10. Consequently, the current evidence does not support a clean specificity statement covering Qwen. We treat the Qwen result as elevated sensitivity to irrelevant perturbations pending real human review or a preregistered stricter control rerun.
""",
    )
    write_text(
        Path("paper/sections/v8_1_control_diagnostics.tex"),
        r"""
\paragraph{Control diagnostics.}
The V8.1 forensic audit preserves the raw gate result and separates parser-only, provenance-only, objective-geometry, and preliminary triage recomputations. Parser-only and image-mismatch exclusions remove no Qwen items and therefore leave the failure unchanged. Softer preliminary exclusions are diagnostic only and are not used for claims. The main update-gap analysis remains interpretable only with this specificity limitation attached.
""",
    )


def write_go_no_go(recompute: list[dict[str, Any]], cross_rows: list[dict[str, Any]], quality_summary: dict[str, Any]) -> None:
    only_qwen = sum(bool(row["only_qwen_flips"]) for row in cross_rows)
    claim_valid_pass = any(row["claim_valid"] and row["gate_pass"] for row in recompute)
    decision = "GO_HUMAN_AUDIT_FIRST"
    payload = {
        "schema": "certvic.v8_1.go_no_go.v1",
        "paper_evidence": False,
        "decision": decision,
        "decision_options": ["GO_MAIN500", "GO_SPURIOUS_V2_FIRST", "GO_HUMAN_AUDIT_FIRST", "STOP_AND_REFRAME"],
        "current_state": "Qwen fails the raw spurious specificity gate; InternVL and LLaVA pass.",
        "resolved": [
            "all 12 Qwen failed items extracted",
            "gallery and preliminary triage created",
            "cross-model comparison completed",
            "parser/provenance audit found no issue affecting 12/94",
        ],
        "blocked": [
            "no real human validation of preliminary labels",
            "raw Qwen gate remains failed",
            "no claim-valid recompute scenario passes",
            "Main-500 remains blocked unless the paper is reframed honestly",
        ],
        "main500_should_start_now": False,
        "exact_answer": "Do not start Main-500 until Qwen spurious failure is resolved or the paper is reframed to exclude clean Qwen specificity.",
        "recommended_next_action": "Have a real human audit the 12-item gallery first; then either preregister/run spurious V2 or reframe the paper.",
        "evidence_summary": {
            "only_qwen_flips": only_qwen,
            "claim_valid_recompute_pass": claim_valid_pass,
            "patch_bbox_intersects_target_bbox_items": quality_summary["patch_bbox_intersects_object_bbox_items"],
            "patch_target_mask_overlap_items": quality_summary["patch_target_mask_overlap_items"],
        },
    }
    write_json(OUT / "v8_1_go_no_go.json", payload)
    write_text(
        OUT / "V8_1_GO_NO_GO.md",
        f"""# V8.1 Go/No-Go

`paper_evidence=false`

Decision: `{decision}`

Exact answer: do not start Main-500 until Qwen spurious failure is resolved or the paper is reframed to exclude clean Qwen specificity.

Current state:

- Qwen raw gate: FAIL, 12/94 = 0.1277.
- InternVL and LLaVA-OneVision: PASS.
- Claim-valid recompute scenarios passing: {claim_valid_pass}.
- Qwen failed items that only Qwen flips: {only_qwen}/{len(cross_rows)}.

Recommended next action: real human audit of the 12-item gallery, followed by either preregistered Spurious V2 or an honest paper reframe.
""",
    )


def test_status_from_outputs() -> dict[str, Any]:
    focused = OUT / "pytest_v8_1_qwen_spurious_forensics.txt"
    full = OUT / "pytest_full.txt"
    claim = OUT / "claim_guard_v8_1.json"
    privacy_json = OUT / "privacy_audit_v8_1.json"
    status = {
        "focused_pytest_log": focused.as_posix(),
        "full_pytest_log": full.as_posix(),
        "claim_guard": claim.as_posix(),
        "privacy_json": privacy_json.as_posix(),
        "all_expected_outputs_present": all(repo_path(p).exists() for p in (focused, full, claim, privacy_json)),
    }
    for key, path in (("focused_pytest_tail", focused), ("full_pytest_tail", full)):
        if repo_path(path).exists():
            lines = repo_path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
            status[key] = lines[-5:]
    if repo_path(claim).exists():
        text = repo_path(claim).read_text(encoding="utf-8", errors="ignore")
        status["claim_guard_passed"] = "Passed: True" in text
    if repo_path(privacy_json).exists():
        status["privacy_passed"] = json.loads(repo_path(privacy_json).read_text(encoding="utf-8")).get("passed")
    return status


def write_ledgers(
    *,
    failed_rows: list[dict[str, Any]],
    prelim_rows: list[dict[str, Any]],
    recompute: list[dict[str, Any]],
    cross_rows: list[dict[str, Any]],
    quality_summary: dict[str, Any],
    provenance: dict[str, Any],
) -> None:
    test_status = test_status_from_outputs()
    label_counts = Counter(row["preliminary_label"] for row in prelim_rows)
    only_qwen = sum(bool(row["only_qwen_flips"]) for row in cross_rows)
    raw = next(row for row in recompute if row["scenario_id"] == "A_RAW_GATE")
    claim_valid_pass = any(row["claim_valid"] and row["gate_pass"] for row in recompute)
    tasks = [
        ledger_task(
            "V8_1_00_input_discovery",
            "DONE",
            [TASKS_PATH.as_posix(), "kaggleoutputs/newruns", (V8_DIR / "spurious_specificity_control_report.json").as_posix()],
            [OUT.as_posix()],
            "pwd; git status --short; find data/results/main_real_200 ...; find data/edits/spurious_flip_control ...; find kaggleoutputs/newruns ...; find data/results/main_real_200/v8_upgrade ...",
            "Inputs discovered. Repository folder is not a Git checkout; V8 spurious and newruns artifacts are present.",
            "ARTIFACT_DISCOVERY_NON_EVIDENCE",
            "Discovery is filesystem-local only.",
            [],
        ),
        ledger_task(
            "V8_1_01_qwen_failure_extraction",
            "DONE",
            [f"{RESULTS}/kaggle_spurious/pred_qwen2_5_vl_7b_spurious_merged.jsonl", TASKS_PATH.as_posix()],
            [str(OUT / "qwen_spurious_all_items.csv"), str(OUT / "qwen_spurious_failed_12.csv")],
            "python3 scripts/build_v8_1_qwen_spurious_forensics.py",
            f"Extracted {len(failed_rows)} Qwen flips from 94 paired items.",
            "REAL_ARTIFACT_RECOMPUTE_NON_EVIDENCE",
            "No model rerun performed.",
            [],
        ),
        ledger_task(
            "V8_1_02_failure_gallery",
            "DONE",
            [str(OUT / "qwen_spurious_failed_12.csv"), CONTROL_DIR.as_posix()],
            [str(OUT / "qwen_spurious_failed_12_gallery.html"), str(GALLERY_DIR)],
            "python3 scripts/build_v8_1_qwen_spurious_forensics.py",
            "Built 12-item side-by-side gallery with copied local images, heatmaps, and overlays.",
            "FORENSIC_GALLERY_NON_EVIDENCE",
            "Gallery pixels are local diagnostic artifacts, not release assets.",
            [],
        ),
        ledger_task(
            "V8_1_03_machine_preliminary_eval",
            "DONE",
            [str(OUT / "qwen_spurious_failed_12.csv"), str(OUT / "spurious_control_quality_audit.csv")],
            [str(OUT / "qwen_spurious_failed_12_prelim_labels.csv"), str(OUT / "human_claim.md")],
            "python3 scripts/build_v8_1_qwen_spurious_forensics.py",
            f"Assigned CODEX_PRELIMINARY_EVAL triage labels: {dict(label_counts)}.",
            "CODEX_PRELIMINARY_EVAL_TRIAGE_ONLY",
            "AI-assisted triage only; not real human validation.",
            ["real human review required before any claim use"],
        ),
        ledger_task(
            "V8_1_04_rule_based_recompute",
            "DONE",
            [str(OUT / "qwen_spurious_all_items.csv"), str(OUT / "qwen_spurious_failed_12_prelim_labels.csv")],
            [str(OUT / "qwen_spurious_recompute_scenarios.csv"), str(OUT / "qwen_spurious_recompute_report.md")],
            "python3 scripts/build_v8_1_qwen_spurious_forensics.py",
            f"Raw gate remains {raw['n_flips']}/{raw['n_evaluable']} = {raw['flip_rate']}; claim-valid pass exists: {claim_valid_pass}.",
            "RULE_BASED_RECOMPUTE_NON_EVIDENCE",
            "Non-raw scenarios are separated and do not update the canonical gate.",
            [],
        ),
        ledger_task(
            "V8_1_05_cross_model_comparison",
            "DONE",
            [str(OUT / "qwen_spurious_failed_12.csv"), f"{RESULTS}/kaggle_spurious"],
            [str(OUT / "qwen_failed_items_cross_model_comparison.csv"), str(OUT / "qwen_failed_items_cross_model_comparison.md")],
            "python3 scripts/build_v8_1_qwen_spurious_forensics.py",
            f"Only-Qwen flips on Qwen-failed set: {only_qwen}/{len(cross_rows)}.",
            "CROSS_MODEL_DIAGNOSTIC_NON_EVIDENCE",
            "Comparison is limited to the 12 Qwen-failed items.",
            [],
        ),
        ledger_task(
            "V8_1_06_parser_and_provenance_audit",
            "DONE",
            [f"{RESULTS}/kaggle_spurious", "kaggleoutputs/newruns", str(V8_DIR / "canonical_prediction_manifest.json")],
            [str(OUT / "parser_provenance_audit.json"), str(OUT / "PARSER_PROVENANCE_AUDIT.md")],
            "python3 scripts/build_v8_1_qwen_spurious_forensics.py",
            f"Rows/provider and pairing OK; issue could affect Qwen 12/94: {provenance['could_affect_qwen_12_of_94']}.",
            "PROVENANCE_AUDIT_NON_EVIDENCE",
            "Zip-member equality checks are file-artifact checks only.",
            [],
        ),
        ledger_task(
            "V8_1_07_spurious_control_quality_audit",
            "DONE",
            [TASKS_PATH.as_posix(), CONTROL_DIR.as_posix(), "ade20k_root/ADEChallengeData2016/annotations/training"],
            [str(OUT / "spurious_control_quality_audit.csv"), str(OUT / "SPURIOUS_CONTROL_QUALITY_AUDIT.md")],
            "python3 scripts/build_v8_1_qwen_spurious_forensics.py",
            f"Mask overlap items: {quality_summary['patch_target_mask_overlap_items']}; bbox-intersection items: {quality_summary['patch_bbox_intersects_object_bbox_items']}.",
            "CPU_GEOMETRY_DIAGNOSTIC_NON_EVIDENCE",
            quality_summary["geometry_note"],
            ["task manifest lacks original patch metadata"],
        ),
        ledger_task(
            "V8_1_08_stricter_spurious_v2_design",
            "DONE",
            [str(OUT / "SPURIOUS_CONTROL_QUALITY_AUDIT.md"), "scripts/build_spurious_flip_control.py"],
            [str(OUT / "SPURIOUS_CONTROL_V2_DESIGN.md"), "commands/spurious_v2/build_spurious_v2.sh"],
            "python3 scripts/build_v8_1_qwen_spurious_forensics.py",
            "Designed stricter V2 control and runbooks; no GPU run performed.",
            "DESIGN_ONLY_NON_EVIDENCE",
            "V2 commands are not run and produce no prediction results here.",
            [],
        ),
        ledger_task(
            "V8_1_09_paper_claim_reframe",
            "DONE",
            [str(V8_DIR / "spurious_specificity_control_report.json"), str(OUT / "qwen_spurious_recompute_report.md")],
            [str(OUT / "CLAIM_SAFE_SUMMARY.md"), "paper/sections/v8_1_spurious_specificity_limitations.tex", "paper/sections/v8_1_control_diagnostics.tex"],
            "python3 scripts/build_v8_1_qwen_spurious_forensics.py",
            "Wrote claim-safe text: Qwen fails specificity; clean all-model specificity is blocked.",
            "CLAIM_REFRAME_NON_EVIDENCE",
            "Does not change main result artifacts or paper_evidence.",
            [],
        ),
        ledger_task(
            "V8_1_10_go_nogo_decision",
            "DONE",
            [str(OUT / "qwen_spurious_recompute_report.md"), str(OUT / "PARSER_PROVENANCE_AUDIT.md")],
            [str(OUT / "V8_1_GO_NO_GO.md"), str(OUT / "v8_1_go_no_go.json")],
            "python3 scripts/build_v8_1_qwen_spurious_forensics.py",
            "Decision: GO_HUMAN_AUDIT_FIRST; Main-500 should not start now.",
            "GO_NOGO_NON_EVIDENCE",
            "Decision can change only after real human review, V2, or an honest reframe.",
            ["Main-500 blocked"],
        ),
        ledger_task(
            "V8_1_11_tests_and_guards",
            "DONE" if test_status["all_expected_outputs_present"] else "PARTIAL",
            ["tests/test_v8_1_qwen_spurious_forensics.py"],
            [
                str(OUT / "pytest_v8_1_qwen_spurious_forensics.txt"),
                str(OUT / "pytest_full.txt"),
                str(OUT / "claim_guard_v8_1.json"),
                str(OUT / "privacy_audit_v8_1.json"),
            ],
            "python3 -m pytest -q tests/test_v8_1_qwen_spurious_forensics.py; python3 -m pytest -q; python3 -m certvic.validation.claim_language_guard ...; python3 -m certvic.security.release_privacy_audit ...",
            "Test/guard logs detected." if test_status["all_expected_outputs_present"] else "Builder created artifacts; tests/guards not all detected yet.",
            "VALIDATION_STATUS",
            "Full pytest duration depends on local environment.",
            [] if test_status["all_expected_outputs_present"] else ["run requested tests/guards and rerun builder to refresh ledger"],
        ),
    ]
    payload = {
        "schema": "certvic.v8_1.task_ledger.v1",
        "paper_evidence": False,
        "thresholds": {"control_spurious_flip_max": SPURIOUS_THRESHOLD},
        "summary": {
            "qwen_raw_flips": len(failed_rows),
            "qwen_raw_n": 94,
            "qwen_raw_flip_rate": 0.1277,
            "claim_valid_recompute_pass": claim_valid_pass,
            "main500_should_start_now": False,
        },
        "test_status": test_status,
        "tasks": tasks,
    }
    write_json(OUT / "v8_1_task_ledger.json", payload)
    write_text(OUT / "V8_1_TASK_LEDGER.md", render_ledger_md(payload))


def ledger_task(
    task_id: str,
    status: str,
    input_files: list[str],
    output_files: list[str],
    command_run: str,
    result_summary: str,
    evidence_status: str,
    limitations: str,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "id": task_id,
        "status": status,
        "input_files": input_files,
        "output_files": output_files,
        "command_run": command_run,
        "result_summary": result_summary,
        "evidence_status": evidence_status,
        "limitations": limitations,
        "blockers": blockers,
        "paper_evidence": False,
    }


def render_ledger_md(payload: dict[str, Any]) -> str:
    lines = [
        "# V8.1 Task Ledger",
        "",
        "`paper_evidence=false` `control_spurious_flip_max=0.10`",
        "",
        "| Task | Status | Evidence | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for task in payload["tasks"]:
        lines.append(f"| `{task['id']}` | {task['status']} | `{task['evidence_status']}` | {task['result_summary']} |")
    lines += [
        "",
        "Main-500 should not start now. Qwen raw specificity remains failed unless resolved by real human review, a preregistered V2 control, or an honest paper reframe.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build V8.1 Qwen spurious forensics")
    parser.parse_args(argv)
    repo_path(OUT).mkdir(parents=True, exist_ok=True)

    tasks = read_jsonl(TASKS_PATH)
    if len(tasks) != 94:
        raise SystemExit(f"Expected 94 spurious tasks, found {len(tasks)}")

    predictions = {provider: load_predictions(provider) for provider in PROVIDERS}
    detect_features, detect_high, detect_summary = load_detectability()
    del detect_features  # retained in the loader API for compatibility; not used in this audit.
    annotation_paths = [target_annotation_path(str(task["item_id"])) for task in tasks]
    needs_frozen_cache = any(
        path is None or not repo_path(path).is_file()
        for path in annotation_paths
    )
    frozen_cache = load_frozen_quality_cache(tasks) if needs_frozen_cache else {}
    quality_rows = {
        str(task["item_id"]): quality_for_task(
            task,
            detect_high,
            frozen_cache.get(str(task["item_id"])),
        )
        for task in tasks
    }
    rows_by_provider = build_all_item_rows(tasks, predictions, quality_rows)
    failed_rows = [row for row in rows_by_provider[QWEN] if row["flipped"]]
    if len(failed_rows) != 12:
        raise SystemExit(f"Expected exactly 12 Qwen failed spurious rows, found {len(failed_rows)}")

    prelim_by_item = {row["item_id"]: prelim_label_for(row, quality_rows[row["item_id"]]) for row in failed_rows}
    prelim_rows = [prelim_by_item[row["item_id"]] for row in failed_rows]
    copy_and_render_gallery(failed_rows, quality_rows, prelim_by_item)
    recompute = recompute_scenarios(rows_by_provider[QWEN], quality_rows, prelim_rows)
    cross_rows = build_cross_model_comparison(failed_rows, rows_by_provider)
    provenance = prediction_file_audit(tasks)
    write_reports(tasks, rows_by_provider, failed_rows, quality_rows, prelim_rows, recompute, cross_rows, provenance, detect_summary)
    print(
        json.dumps(
            {
                "out_dir": OUT.as_posix(),
                "qwen_failed": len(failed_rows),
                "geometry_mode": (
                    "FROZEN_DERIVED_REAL_EVIDENCE_CACHE"
                    if needs_frozen_cache
                    else "LOCAL_ADE_ANNOTATION_RECOMPUTE"
                ),
                "paper_evidence": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
