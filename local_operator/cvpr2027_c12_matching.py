"""Outcome-blind prospective arm matching and multi-classifier detectability checks."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import (  # noqa: E402
    REPO,
    artifact_manifest,
    read_jsonl,
    write_csv,
    write_json,
)


REPORT_ROOT = REPO / "reports/cvpr2027_c12"
FEATURES = (
    "difference_area_fraction",
    "mean_absolute_pixel_difference",
    "ssim",
    "psnr",
    "histogram_distance",
    "luminance_change",
    "contrast_change",
    "edge_density_change",
    "spatial_distance_to_target",
    "spatial_distance_to_protected_region",
    "salience",
)
STRATA = (
    "category",
    "expected_answer_polarity",
    "target_size_stratum",
    "target_position_stratum",
    "perturbation_family",
)
FORBIDDEN = {
    "provider",
    "provider_name",
    "model_output",
    "raw_output",
    "parsed_answer",
    "prediction",
    "semantic_update_success",
    "irrelevant_flip",
    "correct",
}


def _recursive_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_recursive_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_recursive_keys(item) for item in value), set())
    return set()


def reject_outcome_contamination(rows: Iterable[dict[str, Any]]) -> None:
    contaminated = []
    for index, row in enumerate(rows):
        overlap = FORBIDDEN & {key.lower() for key in _recursive_keys(row)}
        if overlap:
            contaminated.append({"row": index, "fields": sorted(overlap)})
    if contaminated:
        raise ValueError(f"provider outcomes are forbidden from matching/detectability: {contaminated[:5]}")


def _vector(row: dict[str, Any]) -> np.ndarray:
    missing = [field for field in FEATURES if row.get(field) is None]
    if missing:
        raise ValueError(f"{row.get('item_id')}: matching features missing: {missing}")
    values = np.asarray([float(row[field]) for field in FEATURES], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"{row.get('item_id')}: non-finite matching feature")
    return values


def _smd(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    relevant = [row for row in rows if row.get("endpoint_arm") == "relevant_intervention"]
    controls = [row for row in rows if row.get("endpoint_arm") == "irrelevant_control"]
    for feature in FEATURES:
        left = np.asarray([float(row[feature]) for row in relevant], dtype=float)
        right = np.asarray([float(row[feature]) for row in controls], dtype=float)
        if not len(left) or not len(right):
            mean_left = mean_right = pooled = smd = math.nan
        else:
            mean_left, mean_right = float(left.mean()), float(right.mean())
            pooled = math.sqrt((float(left.var(ddof=1)) + float(right.var(ddof=1))) / 2)
            smd = (mean_left - mean_right) / pooled if pooled > 0 else 0.0
        result.append({
            "feature": feature,
            "relevant_mean": mean_left,
            "irrelevant_mean": mean_right,
            "pooled_sd": pooled,
            "standardized_mean_difference": smd,
            "absolute_smd": abs(smd),
        })
    return result


def match_controls(
    rows: list[dict[str, Any]], *, controls_per_relevant: int = 2, seed: int = 12013
) -> dict[str, Any]:
    reject_outcome_contamination(rows)
    relevant = [row for row in rows if row.get("endpoint_arm") == "relevant_intervention"]
    controls = [row for row in rows if row.get("endpoint_arm") == "irrelevant_control"]
    if not relevant or len(controls) < controls_per_relevant * len(relevant):
        raise ValueError("candidate pool cannot satisfy the amended 1:2 endpoint allocation")
    matrix = np.vstack([_vector(row) for row in [*relevant, *controls]])
    scale = np.std(matrix, axis=0, ddof=1)
    scale[scale == 0] = 1.0
    expanded = [row for row in relevant for _ in range(controls_per_relevant)]
    distance = np.full((len(expanded), len(controls)), 1e12, dtype=float)
    for left_index, left in enumerate(expanded):
        left_vector = _vector(left)
        for right_index, right in enumerate(controls):
            if all(str(left.get(field)) == str(right.get(field)) for field in STRATA):
                tie = int.from_bytes(
                    __import__("hashlib").sha256(
                        f"{seed}:{left.get('item_id')}:{right.get('item_id')}".encode()
                    ).digest()[:4],
                    "big",
                ) / 2**64
                distance[left_index, right_index] = float(
                    np.square((left_vector - _vector(right)) / scale).sum()
                ) + tie
    chosen_left, chosen_right = linear_sum_assignment(distance)
    if len(chosen_left) != len(expanded) or np.any(distance[chosen_left, chosen_right] >= 1e11):
        raise ValueError("no exact-stratum outcome-blind matching solution exists")
    selected_controls = [controls[index] for index in chosen_right]
    selected = [*relevant, *selected_controls]
    trace = [{
        "relevant_item_id": expanded[left_index].get("item_id"),
        "control_item_id": controls[right_index].get("item_id"),
        "standardized_squared_distance": float(distance[left_index, right_index]),
        "stratum": {field: expanded[left_index].get(field) for field in STRATA},
    } for left_index, right_index in zip(chosen_left, chosen_right, strict=True)]
    return {
        "selected": selected,
        "trace": trace,
        "balance_before": _smd(rows),
        "balance_after": _smd(selected),
        "provider_outputs_used": False,
        "deterministic_seed": seed,
    }


def _models(seed: int) -> dict[str, Any]:
    return {
        "standardized_logistic": make_pipeline(
            StandardScaler(), LogisticRegression(solver="liblinear", random_state=seed)
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200, min_samples_leaf=3, random_state=seed, n_jobs=1
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=200, min_samples_leaf=3, random_state=seed, n_jobs=1
        ),
    }


def prospective_detectability(
    rows: list[dict[str, Any]],
    *,
    threshold: float = 0.80,
    repeats: int = 5,
    folds: int = 5,
    bootstrap_samples: int = 1000,
    permutations: int = 1000,
    seed: int = 12013,
) -> dict[str, Any]:
    reject_outcome_contamination(rows)
    x = np.vstack([_vector(row) for row in rows])
    y = np.asarray([
        1 if row.get("endpoint_arm") == "relevant_intervention" else 0 for row in rows
    ])
    groups = np.asarray([str(row.get("source_image_id", row.get("item_id"))) for row in rows])
    if len(set(y)) != 2 or len(set(groups)) < folds:
        raise ValueError("detectability requires both arms and enough distinct source groups")
    model_results: dict[str, Any] = {}
    oof_by_model: dict[str, np.ndarray] = {}
    for model_name in _models(seed):
        repeat_scores = []
        fold_rows = []
        for repeat in range(repeats):
            scores = np.full(len(rows), np.nan)
            splitter = StratifiedGroupKFold(
                n_splits=folds, shuffle=True, random_state=seed + repeat
            )
            for fold, (train, test) in enumerate(splitter.split(x, y, groups), start=1):
                model = _models(seed + repeat)[model_name]
                model.fit(x[train], y[train])
                scores[test] = model.predict_proba(x[test])[:, 1]
                fold_rows.append({
                    "repeat": repeat + 1,
                    "fold": fold,
                    "train_groups": len(set(groups[train])),
                    "test_groups": len(set(groups[test])),
                    "source_group_overlap": bool(set(groups[train]) & set(groups[test])),
                })
            if np.isnan(scores).any():
                raise ValueError("group-safe repeated CV did not score every candidate")
            repeat_scores.append(scores)
        mean_scores = np.mean(np.vstack(repeat_scores), axis=0)
        auc = float(roc_auc_score(y, mean_scores))
        symmetric = max(auc, 1 - auc)
        model_results[model_name] = {
            "auc": auc,
            "symmetric_auc": symmetric,
            "folds": fold_rows,
            "source_leakage": any(row["source_group_overlap"] for row in fold_rows),
        }
        oof_by_model[model_name] = mean_scores
    worst_name = max(model_results, key=lambda name: model_results[name]["symmetric_auc"])
    scores = oof_by_model[worst_name]
    by_group: dict[str, list[int]] = defaultdict(list)
    for index, group in enumerate(groups):
        by_group[group].append(index)
    unique_groups = sorted(by_group)
    rng = np.random.default_rng(seed)
    bootstrap = []
    for _ in range(bootstrap_samples):
        sampled = rng.choice(unique_groups, len(unique_groups), replace=True)
        indexes = np.asarray([index for group in sampled for index in by_group[str(group)]])
        if len(set(y[indexes])) == 2:
            auc = float(roc_auc_score(y[indexes], scores[indexes]))
            bootstrap.append(max(auc, 1 - auc))
    observed = model_results[worst_name]["symmetric_auc"]
    permutation = []
    for _ in range(permutations):
        permuted = rng.permutation(y)
        auc = float(roc_auc_score(permuted, scores))
        permutation.append(max(auc, 1 - auc))
    leave_out = {}
    for field in ("category", "perturbation_family"):
        leave_out[field] = []
        values = np.asarray([str(row.get(field, "unknown")) for row in rows])
        for value in sorted(set(values)):
            indexes = np.flatnonzero(values != value)
            if len(set(y[indexes])) == 2:
                auc = float(roc_auc_score(y[indexes], scores[indexes]))
                leave_out[field].append({
                    "left_out": value,
                    "rows": len(indexes),
                    "symmetric_auc": max(auc, 1 - auc),
                })
    passed = max(value["symmetric_auc"] for value in model_results.values()) <= threshold
    return {
        "schema": "certvic.cvpr2027.c12.prospective_arm_detectability.v1",
        "status": "DETECTABILITY_GATE_PASS" if passed else "DETECTABILITY_GATE_FAIL",
        "execution_authorization": (
            "ELIGIBLE_FOR_NEXT_PRE_MODEL_GATE" if passed else "MODEL_EXECUTION_NOT_AUTHORIZED"
        ),
        "threshold": threshold,
        "threshold_tuned": False,
        "classifiers": model_results,
        "worst_classifier": worst_name,
        "worst_symmetric_auc": observed,
        "group_bootstrap_95": [
            float(np.quantile(bootstrap, 0.025)),
            float(np.quantile(bootstrap, 0.975)),
        ],
        "permutation_p_value": (1 + sum(value >= observed for value in permutation))
        / (1 + len(permutation)),
        "leave_one_group_out": leave_out,
        "source_group_leakage": False,
        "provider_outputs_used": False,
        "paper_evidence": False,
    }


def run(output_root: Path = REPORT_ROOT, *, candidate_manifest: Path | None = None) -> dict[str, Any]:
    root = output_root / "design"
    if candidate_manifest is None or not candidate_manifest.is_file():
        before = [{"status": "SOURCE_BYTES_MISSING"}]
        after = [{"status": "SOURCE_BYTES_MISSING"}]
        trace = {
            "schema": "certvic.cvpr2027.c12.matching_trace.v1",
            "status": "SOFTWARE_READY_SOURCE_BYTES_REQUIRED",
            "provider_outputs_used": False,
            "forbidden_fields": sorted(FORBIDDEN),
            "features": list(FEATURES),
            "strata": list(STRATA),
            "paper_evidence": False,
        }
        readiness = {
            "schema": "certvic.cvpr2027.c12.matching_detectability_readiness.v1",
            "status": "SOFTWARE_READY_SOURCE_BYTES_REQUIRED",
            "model_execution_authorized": False,
            "frozen_symmetric_auc_threshold": 0.80,
            "provider_outputs_used": False,
            "paper_evidence": False,
        }
    else:
        rows = read_jsonl(candidate_manifest)
        matched = match_controls(rows)
        before, after = matched["balance_before"], matched["balance_after"]
        trace = {
            "schema": "certvic.cvpr2027.c12.matching_trace.v1",
            "status": "MATCHING_COMPLETE",
            "matches": matched["trace"],
            "provider_outputs_used": False,
            "paper_evidence": False,
        }
        readiness = prospective_detectability(matched["selected"])
    paths = [
        write_csv(root / "selection_balance_before.csv", before),
        write_csv(root / "selection_balance_after.csv", after),
        write_json(root / "matching_trace.json", trace),
        write_json(root / "MATCHING_DETECTABILITY_READINESS.json", readiness),
    ]
    manifest = write_json(root / "MATCHING_ARTIFACT_MANIFEST.json", artifact_manifest(paths))
    return {**readiness, "artifacts": [path.resolve().relative_to(REPO).as_posix() for path in [*paths, manifest]]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPORT_ROOT)
    parser.add_argument("--candidate-manifest", type=Path)
    args = parser.parse_args(argv)
    result = run(args.output_root, candidate_manifest=args.candidate_manifest)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
