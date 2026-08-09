"""Unified image-pair quality, balance, and endpoint-detectability audit."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy.stats import ks_2samp
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import (  # noqa: E402
    REPO,
    REPORT_ROOT,
    artifact_manifest,
    read_jsonl,
    resolve_repository_path,
    write_csv,
    write_json,
)
from local_operator.cvpr2027_pilot_analysis import (  # noqa: E402
    IRRELEVANT_TASKS,
    RELEVANT_TASKS,
)


FEATURES = [
    "difference_area_fraction",
    "mean_absolute_difference",
    "psnr",
    "ssim_global",
    "histogram_distance",
    "edge_density_change",
    "luminance_change",
    "contrast_change",
]
DETECTABILITY_THRESHOLD = 0.80
SEED = 12013
V1_CACHE = (
    REPO
    / "data/results/main_real_200/v8_1_qwen_spurious_forensics/"
    "spurious_control_quality_audit.csv"
)


def _rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.mode != "RGB":
            raise ValueError(f"image is not RGB: {path}")
        return np.asarray(image, dtype=np.uint8)


def _gray(array: np.ndarray) -> np.ndarray:
    return (
        0.2126 * array[..., 0].astype(float)
        + 0.7152 * array[..., 1].astype(float)
        + 0.0722 * array[..., 2].astype(float)
    )


def _edge_density(gray: np.ndarray) -> float:
    horizontal = np.abs(np.diff(gray, axis=1))
    vertical = np.abs(np.diff(gray, axis=0))
    count = horizontal.size + vertical.size
    return float(((horizontal > 20).sum() + (vertical > 20).sum()) / max(count, 1))


def _ssim_global(left: np.ndarray, right: np.ndarray) -> float:
    left_gray = _gray(left)
    right_gray = _gray(right)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    left_mean = left_gray.mean()
    right_mean = right_gray.mean()
    left_variance = left_gray.var(ddof=1)
    right_variance = right_gray.var(ddof=1)
    covariance = np.cov(left_gray.reshape(-1), right_gray.reshape(-1), ddof=1)[0, 1]
    numerator = (2 * left_mean * right_mean + c1) * (2 * covariance + c2)
    denominator = (
        (left_mean**2 + right_mean**2 + c1)
        * (left_variance + right_variance + c2)
    )
    return float(numerator / denominator) if denominator else 1.0


def _histogram_distance(left: np.ndarray, right: np.ndarray) -> float:
    distances = []
    for channel in range(3):
        left_hist = np.bincount(left[..., channel].reshape(-1), minlength=256).astype(float)
        right_hist = np.bincount(right[..., channel].reshape(-1), minlength=256).astype(float)
        left_hist /= left_hist.sum()
        right_hist /= right_hist.sum()
        distances.append(np.abs(left_hist - right_hist).sum())
    return float(np.mean(distances))


def _bbox(mask: np.ndarray) -> list[int] | None:
    positions = np.argwhere(mask)
    if not positions.size:
        return None
    y_min, x_min = positions.min(axis=0)
    y_max, x_max = positions.max(axis=0)
    return [int(x_min), int(y_min), int(x_max + 1), int(y_max + 1)]


def _bbox_overlap(left: list[int] | None, right: list[int] | None) -> tuple[int, float | None]:
    if left is None or right is None:
        return 0, None
    x_overlap = max(0, min(left[2], right[2]) - max(left[0], right[0]))
    y_overlap = max(0, min(left[3], right[3]) - max(left[1], right[1]))
    area = x_overlap * y_overlap
    target_area = max(1, (right[2] - right[0]) * (right[3] - right[1]))
    return area, area / target_area


def _bbox_distance(left: list[int] | None, right: list[int] | None) -> float | None:
    if left is None or right is None:
        return None
    horizontal = max(right[0] - left[2], left[0] - right[2], 0)
    vertical = max(right[1] - left[3], left[1] - right[3], 0)
    return float(math.hypot(horizontal, vertical))


def _v1_cache() -> dict[str, dict[str, str]]:
    with V1_CACHE.open(encoding="utf-8", newline="") as handle:
        return {row["item_id"]: row for row in csv.DictReader(handle)}


def _main_bbox_cache() -> dict[str, list[int]]:
    path = REPO / "data/results/main_real_200/ade20k_masks.jsonl"
    return {
        str(row["mask_id"]): [int(value) for value in row["bbox_xyxy"]]
        for row in read_jsonl(path)
        if row.get("bbox_xyxy")
    }


def _resolve_pair(task: dict[str, Any], arm: str) -> tuple[Path, Path]:
    base = IRRELEVANT_TASKS.parent if arm == "irrelevant" else REPO
    original = resolve_repository_path(task.get("original_image_path"), base=base)
    edited = resolve_repository_path(task.get("edited_image_path"), base=base)
    if original is None or edited is None or not original.is_file() or not edited.is_file():
        raise FileNotFoundError(f"pair bytes missing for {task.get('item_id')}: {original}, {edited}")
    return original, edited


def audit_pair(
    task: dict[str, Any],
    *,
    arm: str,
    main_boxes: dict[str, list[int]],
    v1: dict[str, dict[str, str]],
) -> dict[str, Any]:
    original_path, edited_path = _resolve_pair(task, arm)
    original = _rgb(original_path)
    edited = _rgb(edited_path)
    if original.shape != edited.shape:
        raise ValueError(f"dimension mismatch for {task['item_id']}")
    difference = np.any(original != edited, axis=2)
    difference_bbox = _bbox(difference)
    difference_pixels = int(difference.sum())
    mean_squared_error = float(np.square(original.astype(float) - edited.astype(float)).mean())
    psnr = float("inf") if mean_squared_error == 0 else 20 * math.log10(255 / math.sqrt(mean_squared_error))
    original_gray = _gray(original)
    edited_gray = _gray(edited)
    item_id = str(task["item_id"])
    target_bbox: list[int] | None = None
    target_mask_overlap_pixels: int | None = None
    cached_geometry_source = None
    if arm == "relevant":
        target_bbox = main_boxes.get(str(task.get("mask_id")))
        cached_geometry_source = "ade20k_masks_manifest_bbox"
    elif item_id in v1:
        cached = v1[item_id]
        try:
            target_bbox = [int(value) for value in ast.literal_eval(cached["target_bbox_xyxy"])]
        except (ValueError, SyntaxError):
            target_bbox = None
        target_mask_overlap_pixels = int(cached["patch_target_mask_overlap_pixels"])
        cached_geometry_source = "frozen_v8_1_annotation_derived_quality_cache"
    overlap_pixels, overlap_fraction = _bbox_overlap(difference_bbox, target_bbox)
    metadata = task.get("metadata") or {}
    quality = task.get("quality") or {}
    return {
        "item_id": item_id,
        "source_id": str(
            task.get("source_id")
            or (task.get("source") or {}).get("source_id")
            or item_id
        ),
        "endpoint_arm": arm,
        "category": str(metadata.get("object") or task.get("question_object") or task.get("task_family")),
        "perturbation_family": str(
            task.get("edit_type")
            or (task.get("edit") or {}).get("edit_type")
            or "UNSPECIFIED"
        ),
        "original_path": original_path.relative_to(REPO).as_posix(),
        "edited_path": edited_path.relative_to(REPO).as_posix(),
        "original_sha256": hashlib.sha256(original_path.read_bytes()).hexdigest(),
        "edited_sha256": hashlib.sha256(edited_path.read_bytes()).hexdigest(),
        "width": original.shape[1],
        "height": original.shape[0],
        "channels": original.shape[2],
        "decodable": True,
        "rgb_valid": True,
        "equal_dimensions": True,
        "difference_bbox_xyxy": difference_bbox,
        "difference_pixels": difference_pixels,
        "difference_area_fraction": difference_pixels / difference.size,
        "target_bbox_xyxy": target_bbox,
        "target_box_overlap_pixels": overlap_pixels,
        "target_box_overlap_fraction": overlap_fraction,
        "target_mask_overlap_pixels": target_mask_overlap_pixels,
        "minimum_distance_to_target_px": _bbox_distance(difference_bbox, target_bbox),
        "geometry_source": cached_geometry_source,
        "mean_absolute_difference": float(
            np.abs(original.astype(float) - edited.astype(float)).mean()
        ),
        "psnr": psnr,
        "ssim_global": _ssim_global(original, edited),
        "histogram_distance": _histogram_distance(original, edited),
        "edge_density_change": abs(_edge_density(original_gray) - _edge_density(edited_gray)),
        "luminance_change": abs(float(original_gray.mean() - edited_gray.mean())),
        "contrast_change": abs(float(original_gray.std() - edited_gray.std())),
        "stored_total_changed_fraction": quality.get("total_changed_fraction"),
        "stored_mask_area_fraction": quality.get("mask_area_fraction"),
        "evidence_class": "HISTORICAL_IMAGE_DIAGNOSTIC",
        "paper_evidence": False,
    }


def balance_diagnostics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for feature in FEATURES:
        relevant = np.asarray(
            [float(row[feature]) for row in rows if row["endpoint_arm"] == "relevant"]
        )
        irrelevant = np.asarray(
            [float(row[feature]) for row in rows if row["endpoint_arm"] == "irrelevant"]
        )
        pooled = math.sqrt((relevant.var(ddof=1) + irrelevant.var(ddof=1)) / 2)
        smd = float((relevant.mean() - irrelevant.mean()) / pooled) if pooled else 0.0
        ks = ks_2samp(relevant, irrelevant, method="auto")
        output.append(
            {
                "feature": feature,
                "relevant_n": len(relevant),
                "irrelevant_n": len(irrelevant),
                "relevant_mean": float(relevant.mean()),
                "irrelevant_mean": float(irrelevant.mean()),
                "standardized_mean_difference": smd,
                "absolute_smd": abs(smd),
                "relevant_q05": float(np.quantile(relevant, 0.05)),
                "relevant_q50": float(np.quantile(relevant, 0.50)),
                "relevant_q95": float(np.quantile(relevant, 0.95)),
                "irrelevant_q05": float(np.quantile(irrelevant, 0.05)),
                "irrelevant_q50": float(np.quantile(irrelevant, 0.50)),
                "irrelevant_q95": float(np.quantile(irrelevant, 0.95)),
                "ks_statistic_diagnostic": float(ks.statistic),
                "ks_p_value_diagnostic": float(ks.pvalue),
                "threshold_tuned_from_outcomes": False,
            }
        )
    return output


def _models() -> dict[str, Any]:
    return {
        "logistic_regression": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=2000, random_state=SEED)
        ),
        "linear_svm": make_pipeline(StandardScaler(), LinearSVC(random_state=SEED)),
        "random_forest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=3, random_state=SEED, n_jobs=1
        ),
        "gradient_boosting": GradientBoostingClassifier(random_state=SEED),
    }


def _score(model: Any, values: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(values)[:, 1], dtype=float)
    return np.asarray(model.decision_function(values), dtype=float)


def detectability_cv(rows: list[dict[str, Any]], repeats: int) -> tuple[list[dict[str, Any]], dict[str, np.ndarray]]:
    values = np.asarray([[float(row[feature]) for feature in FEATURES] for row in rows])
    labels = np.asarray([int(row["endpoint_arm"] == "irrelevant") for row in rows])
    groups = np.asarray([str(row["source_id"]) for row in rows])
    output = []
    aggregate_predictions: dict[str, list[np.ndarray]] = defaultdict(list)
    for model_name, base_model in _models().items():
        for repeat in range(repeats):
            splitter = StratifiedGroupKFold(
                n_splits=5, shuffle=True, random_state=SEED + repeat
            )
            predictions = np.full(len(rows), np.nan)
            fold_aucs = []
            for fold, (train, test) in enumerate(splitter.split(values, labels, groups), start=1):
                model = clone(base_model).fit(values[train], labels[train])
                predictions[test] = _score(model, values[test])
                raw_auc = float(roc_auc_score(labels[test], predictions[test]))
                fold_aucs.append(max(raw_auc, 1 - raw_auc))
                output.append(
                    {
                        "classifier": model_name,
                        "repeat": repeat,
                        "fold": fold,
                        "train_n": len(train),
                        "test_n": len(test),
                        "source_group_overlap": len(set(groups[train]) & set(groups[test])),
                        "raw_auc": raw_auc,
                        "symmetric_auc": max(raw_auc, 1 - raw_auc),
                        "seed": SEED + repeat,
                    }
                )
            aggregate_predictions[model_name].append(predictions)
            raw_auc = float(roc_auc_score(labels, predictions))
            output.append(
                {
                    "classifier": model_name,
                    "repeat": repeat,
                    "fold": "ALL_OOF",
                    "train_n": None,
                    "test_n": len(rows),
                    "source_group_overlap": 0,
                    "raw_auc": raw_auc,
                    "symmetric_auc": max(raw_auc, 1 - raw_auc),
                    "mean_fold_symmetric_auc": float(np.mean(fold_aucs)),
                    "seed": SEED + repeat,
                }
            )
    averaged = {
        name: np.mean(np.column_stack(predictions), axis=1)
        for name, predictions in aggregate_predictions.items()
    }
    return output, averaged


def permutation_test(rows: list[dict[str, Any]], permutations: int) -> list[dict[str, Any]]:
    values = np.asarray([[float(row[feature]) for feature in FEATURES] for row in rows])
    labels = np.asarray([int(row["endpoint_arm"] == "irrelevant") for row in rows])
    groups = np.asarray([str(row["source_id"]) for row in rows])
    splitter = list(
        StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED).split(
            values, labels, groups
        )
    )
    rng = np.random.default_rng(SEED + 100)

    def auc_for(outcomes: np.ndarray) -> float:
        predictions = np.full(len(rows), np.nan)
        for train, test in splitter:
            model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
            model.fit(values[train], outcomes[train])
            predictions[test] = model.predict_proba(values[test])[:, 1]
        raw = float(roc_auc_score(outcomes, predictions))
        return max(raw, 1 - raw)

    observed = auc_for(labels)
    output = [
        {
            "permutation": "OBSERVED",
            "symmetric_auc": observed,
            "seed": SEED + 100,
        }
    ]
    for index in range(permutations):
        permuted = rng.permutation(labels)
        output.append(
            {
                "permutation": index,
                "symmetric_auc": auc_for(permuted),
                "seed": SEED + 100,
            }
        )
    exceed = sum(row["symmetric_auc"] >= observed for row in output[1:])
    output[0]["permutation_p_value"] = (exceed + 1) / (permutations + 1)
    return output


def bootstrap_auc(
    rows: list[dict[str, Any]], predictions: np.ndarray, draws: int
) -> tuple[float, float]:
    labels = np.asarray([int(row["endpoint_arm"] == "irrelevant") for row in rows])
    groups = np.asarray([str(row["source_id"]) for row in rows])
    unique = np.unique(groups)
    indices = {group: np.where(groups == group)[0] for group in unique}
    rng = np.random.default_rng(SEED + 200)
    values = []
    while len(values) < draws:
        selected = rng.choice(unique, size=len(unique), replace=True)
        sample = np.concatenate([indices[group] for group in selected])
        if len(np.unique(labels[sample])) < 2:
            continue
        raw = float(roc_auc_score(labels[sample], predictions[sample]))
        values.append(max(raw, 1 - raw))
    return float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))


def leave_category_out(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values = np.asarray([[float(row[feature]) for feature in FEATURES] for row in rows])
    labels = np.asarray([int(row["endpoint_arm"] == "irrelevant") for row in rows])
    categories = np.asarray([str(row["category"]) for row in rows])
    output = []
    for category in sorted(set(categories)):
        test = np.where(categories == category)[0]
        train = np.where(categories != category)[0]
        if len(np.unique(labels[test])) < 2 or len(np.unique(labels[train])) < 2:
            output.append(
                {
                    "left_out_category": category,
                    "train_n": len(train),
                    "test_n": len(test),
                    "status": "NOT_ESTIMABLE_SINGLE_CLASS",
                }
            )
            continue
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(
            values[train], labels[train]
        )
        predictions = model.predict_proba(values[test])[:, 1]
        raw = float(roc_auc_score(labels[test], predictions))
        output.append(
            {
                "left_out_category": category,
                "train_n": len(train),
                "test_n": len(test),
                "raw_auc": raw,
                "symmetric_auc": max(raw, 1 - raw),
                "status": "COMPLETE",
            }
        )
    return output


def run(output_root: Path = REPORT_ROOT, *, mode: str = "full") -> dict[str, Any]:
    started = time.perf_counter()
    audit_root = output_root / "audits"
    statistics_root = output_root / "statistics"
    tables = output_root / "tables"
    main_boxes = _main_bbox_cache()
    v1 = _v1_cache()
    rows = [
        audit_pair(task, arm="relevant", main_boxes=main_boxes, v1=v1)
        for task in read_jsonl(RELEVANT_TASKS)
    ] + [
        audit_pair(task, arm="irrelevant", main_boxes=main_boxes, v1=v1)
        for task in read_jsonl(IRRELEVANT_TASKS)
    ]
    balance = balance_diagnostics(rows)
    repeats = 10 if mode == "full" else 3
    permutations = 1000 if mode == "full" else 100
    bootstrap_draws = 2000 if mode == "full" else 300
    cv_rows, predictions = detectability_cv(rows, repeats)
    permutation = permutation_test(rows, permutations)
    leave_out = leave_category_out(rows)
    logistic_predictions = predictions["logistic_regression"]
    raw_logistic_auc = float(
        roc_auc_score(
            [int(row["endpoint_arm"] == "irrelevant") for row in rows],
            logistic_predictions,
        )
    )
    primary_auc = max(raw_logistic_auc, 1 - raw_logistic_auc)
    lower, upper = bootstrap_auc(rows, logistic_predictions, bootstrap_draws)
    permutation_p = permutation[0]["permutation_p_value"]
    verdict = {
        "schema": "certvic.cvpr2027.detectability_verdict.v1",
        "status": (
            "DETECTABILITY_GATE_PASS" if primary_auc <= DETECTABILITY_THRESHOLD else "DETECTABILITY_GATE_FAIL"
        ),
        "gate_classifier": "logistic_regression_repeated_grouped_cv",
        "symmetric_auc": primary_auc,
        "bootstrap_95": [lower, upper],
        "permutation_p_value": permutation_p,
        "threshold": DETECTABILITY_THRESHOLD,
        "threshold_changed_after_results": False,
        "source_group_leakage": False,
        "diagnostic_scope": "historical_relevant_vs_irrelevant_pair_features",
        "prospective_gate_satisfied": False,
        "evidence_class": "RETROSPECTIVE_DIAGNOSTIC",
        "paper_evidence": False,
    }
    quality_verdict = {
        "schema": "certvic.cvpr2027.image_quality_audit.v1",
        "status": "COMPLETE_HISTORICAL_DIAGNOSTIC",
        "pairs": len(rows),
        "relevant_pairs": sum(row["endpoint_arm"] == "relevant" for row in rows),
        "irrelevant_pairs": sum(row["endpoint_arm"] == "irrelevant" for row in rows),
        "all_decodable_rgb_equal_dimensions": all(
            row["decodable"] and row["rgb_valid"] and row["equal_dimensions"] for row in rows
        ),
        "target_mask_note": (
            "V1 target-mask overlap uses the frozen annotation-derived cache; the external "
            "ADE annotation tree is absent, so relevant-mask overlap is unavailable."
        ),
        "balance_features_with_absolute_smd_above_0_2": [
            row["feature"] for row in balance if row["absolute_smd"] > 0.2
        ],
        "thresholds_tuned_from_model_outcomes": False,
        "evidence_class": "HISTORICAL_IMAGE_DIAGNOSTIC",
        "paper_evidence": False,
    }
    output_paths = [
        write_csv(audit_root / "image_pair_quality.csv", rows),
        write_csv(audit_root / "relevant_irrelevant_balance.csv", balance),
        write_json(audit_root / "IMAGE_QUALITY_AUDIT.json", quality_verdict),
        write_csv(statistics_root / "detectability_cv.csv", cv_rows),
        write_csv(statistics_root / "detectability_permutation.csv", permutation),
        write_json(
            statistics_root / "detectability_ci.json",
            {
                "classifier": "logistic_regression_repeated_grouped_cv",
                "symmetric_auc": primary_auc,
                "bootstrap_95": [lower, upper],
                "bootstrap_draws": bootstrap_draws,
                "cluster": "source_id",
                "seed": SEED + 200,
                "paper_evidence": False,
            },
        ),
        write_csv(statistics_root / "detectability_leave_category_out.csv", leave_out),
        write_json(statistics_root / "DETECTABILITY_VERDICT.json", verdict),
        write_csv(tables / "image_quality_balance_table.csv", balance),
    ]
    output_paths.append(
        write_json(audit_root / "IMAGE_AUDIT_ARTIFACT_MANIFEST.json", artifact_manifest(output_paths))
    )
    return {
        "status": "COMPLETE",
        "runtime_seconds": time.perf_counter() - started,
        "mode": mode,
        "pairs": len(rows),
        "detectability": verdict,
        "quality": quality_verdict,
        "outputs": [path.relative_to(REPO).as_posix() for path in output_paths],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPORT_ROOT)
    parser.add_argument("--mode", choices=["quick", "full"], default="full")
    args = parser.parse_args(argv)
    print(run(args.output_root, mode=args.mode))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
