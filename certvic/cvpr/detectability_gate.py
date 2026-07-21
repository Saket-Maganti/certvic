"""Leakage-safe set-level edit detectability gate for frozen task bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from certvic.cvpr.contracts import canonical_json_bytes, load_yaml, sha256_bytes
from certvic.cvpr.task_schema import require_task_matrix, resolve_task_path
from certvic.cvpr.transactional import read_jsonl


GATE_SCHEMA = "certvic.cvpr.detectability_gate.v2"


class DetectabilityGateError(ValueError):
    """The frozen set cannot be evaluated prospectively and leakage-safely."""


def _features(path: Path) -> np.ndarray:
    if not path.is_file():
        raise DetectabilityGateError(f"detectability image is missing: {path}")
    with Image.open(path) as opened:
        rgb = np.asarray(
            opened.convert("RGB").resize((96, 96), Image.Resampling.BILINEAR), dtype=float
        )
    rgb /= 255.0
    gray = rgb.mean(axis=2)
    values: list[float] = []
    for channel in range(3):
        layer = rgb[:, :, channel]
        values.extend(
            [
                float(layer.mean()),
                float(layer.std()),
                *map(float, np.quantile(layer, [0.1, 0.25, 0.5, 0.75, 0.9])),
            ]
        )
        histogram, _ = np.histogram(layer, bins=8, range=(0.0, 1.0), density=True)
        values.extend(map(float, histogram / max(float(histogram.sum()), 1.0)))
    dx, dy = np.diff(gray, axis=1), np.diff(gray, axis=0)
    values.extend(
        [
            float(np.abs(dx).mean()),
            float(np.abs(dy).mean()),
            float(dx.std()),
            float(dy.std()),
            float((np.abs(dx) > 0.08).mean()),
            float((np.abs(dy) > 0.08).mean()),
        ]
    )
    return np.asarray(values, dtype=float)


def _symmetric_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    auc = float(roc_auc_score(labels, scores))
    return max(auc, 1.0 - auc)


def evaluate(
    tasks: list[dict[str, Any]],
    *,
    bundle_root: str | Path | None = None,
    threshold: float = 0.80,
    folds: int = 5,
    bootstrap_samples: int = 1000,
    seed: int = 17031,
    provider_outputs_present: bool = False,
    final_task_manifest: str | Path | None = None,
    task_bundle_manifest: str | Path | None = None,
    study_config: str | Path | None = None,
    qa_manifest: str | Path | None = None,
) -> dict[str, Any]:
    if provider_outputs_present:
        raise DetectabilityGateError(
            "detectability must run before provider outputs; prospective reconstruction is required"
        )
    if not 0.5 <= threshold <= 1.0 or folds < 2 or bootstrap_samples < 1:
        raise DetectabilityGateError("invalid threshold, fold count, or bootstrap count")
    rows = require_task_matrix(tasks, verify_files=True, bundle_root=bundle_root)
    features: list[np.ndarray] = []
    labels: list[int] = []
    groups: list[str] = []
    families: list[str] = []
    item_ids: list[str] = []
    for row in rows:
        group = str(row.get("source_family", row.get("source_image_id", row["task_id"])))
        family = str(row.get("control_edit_family") or row.get("semantic_edit_family") or "unknown")
        original = row.get("original_image_path", row.get("source_image_path"))
        edited = row.get("edited_image_path")
        if not original or not edited:
            raise DetectabilityGateError(f"{row['task_id']}: original/edited paths are required")
        original_path = resolve_task_path(
            {**row, "_path": original},
            "original_image_path" if row.get("original_image_path") else "source_image_path",
            bundle_root=bundle_root,
        )
        edited_path = resolve_task_path(row, "edited_image_path", bundle_root=bundle_root)
        assert original_path is not None and edited_path is not None
        for path, label in ((original_path, 0), (edited_path, 1)):
            features.append(_features(path))
            labels.append(label)
            groups.append(group)
            families.append(family)
            item_ids.append(str(row["task_id"]))
    unique_groups = sorted(set(groups))
    n_splits = min(folds, len(unique_groups))
    if n_splits < 2:
        raise DetectabilityGateError(
            "at least two source groups are required for leakage-safe folds"
        )
    x = np.vstack(features)
    y = np.asarray(labels, dtype=int)
    group_array = np.asarray(groups)
    scores = np.full(len(y), np.nan, dtype=float)
    fold_rows: list[dict[str, Any]] = []
    splitter = GroupKFold(n_splits=n_splits)
    for fold, (train, test) in enumerate(splitter.split(x, y, group_array), start=1):
        if len(set(y[train])) < 2 or len(set(y[test])) < 2:
            raise DetectabilityGateError("a grouped fold lacks both original and edited classes")
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(solver="liblinear", random_state=seed, max_iter=1000),
        )
        model.fit(x[train], y[train])
        scores[test] = model.predict_proba(x[test])[:, 1]
        fold_rows.append(
            {
                "fold": fold,
                "train_groups": len(set(group_array[train])),
                "test_groups": len(set(group_array[test])),
                "rows": len(test),
                "auc": float(roc_auc_score(y[test], scores[test])),
                "symmetric_auc": _symmetric_auc(y[test], scores[test]),
            }
        )
    if np.isnan(scores).any():
        raise DetectabilityGateError("grouped cross-validation did not predict every row")
    auc = float(roc_auc_score(y, scores))
    symmetric = max(auc, 1.0 - auc)
    family_results: dict[str, dict[str, Any]] = {}
    family_array = np.asarray(families)
    for family in sorted(set(families)):
        indexes = np.flatnonzero(family_array == family)
        family_auc = float(roc_auc_score(y[indexes], scores[indexes]))
        family_results[family] = {
            "rows": len(indexes),
            "groups": len(set(group_array[indexes])),
            "auc": family_auc,
            "symmetric_auc": max(family_auc, 1.0 - family_auc),
        }
    by_group: dict[str, list[int]] = defaultdict(list)
    for index, group in enumerate(groups):
        by_group[group].append(index)
    rng = np.random.default_rng(seed)
    bootstrap: list[float] = []
    for _ in range(bootstrap_samples):
        sampled = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        indexes = np.asarray([index for group in sampled for index in by_group[str(group)]])
        if len(set(y[indexes])) == 2:
            bootstrap.append(_symmetric_auc(y[indexes], scores[indexes]))
    if not bootstrap:
        raise DetectabilityGateError("grouped bootstrap produced no valid resamples")
    interval = [float(np.quantile(bootstrap, 0.025)), float(np.quantile(bootstrap, 0.975))]
    passed = symmetric <= threshold
    task_universe_hash = sha256_bytes(
        canonical_json_bytes(sorted(str(row["task_id"]) for row in rows))
    )
    task_identity_hash = sha256_bytes(canonical_json_bytes(sorted(
        ({"task_id": str(row["task_id"]), "task_hash": str(row["task_hash"])} for row in rows),
        key=lambda value: value["task_id"],
    )))
    exact_inputs = {
        "final_task_manifest": final_task_manifest,
        "task_bundle_manifest": task_bundle_manifest,
        "study_config": study_config,
        "qa_manifest": qa_manifest,
    }
    supplied = {name for name, value in exact_inputs.items() if value is not None}
    if supplied and supplied != set(exact_inputs):
        raise DetectabilityGateError(
            "exact-byte binding requires final tasks, task bundle, study config, and QA manifest"
        )
    exact_byte_binding: dict[str, Any] | None = None
    if supplied:
        paths = {name: Path(str(value)) for name, value in exact_inputs.items()}
        missing = [name for name, path in paths.items() if not path.is_file()]
        if missing:
            raise DetectabilityGateError(f"exact-byte binding inputs are missing: {missing}")
        if bundle_root is None:
            raise DetectabilityGateError("exact-byte binding requires the verified task bundle root")
        from certvic.cvpr.task_bundle import verify_bundle

        bundle = verify_bundle(bundle_root, paths["task_bundle_manifest"])
        if Path(bundle["tasks_path"]).resolve() != paths["final_task_manifest"].resolve():
            raise DetectabilityGateError(
                "final task manifest is not the task matrix from the verified task bundle"
            )
        byte_rows: list[dict[str, Any]] = []
        for row in sorted(rows, key=lambda value: str(value["task_id"])):
            original_key = (
                "original_image_path" if row.get("original_image_path") else "source_image_path"
            )
            original_path = resolve_task_path(row, original_key, bundle_root=bundle_root)
            edited_path = resolve_task_path(row, "edited_image_path", bundle_root=bundle_root)
            assert original_path is not None and edited_path is not None
            family = row.get("control_edit_family") or row.get("semantic_edit_family")
            placement = (
                row.get("placement_geometry")
                or row.get("placement")
                or row.get("placement_proposals")
                or row.get("target_bbox")
                or row.get("bbox")
            )
            if family is None or placement is None:
                raise DetectabilityGateError(
                    f"{row['task_id']}: control family and placement geometry are required"
                )
            byte_rows.append(
                {
                    "task_id": str(row["task_id"]),
                    "task_hash": str(row["task_hash"]),
                    "source_image_sha256": hashlib.sha256(original_path.read_bytes()).hexdigest(),
                    "edited_image_sha256": hashlib.sha256(edited_path.read_bytes()).hexdigest(),
                    "control_family": str(family),
                    "placement_geometry": placement,
                }
            )
        edited_hashes = [row["edited_image_sha256"] for row in byte_rows]
        exact_byte_binding = {
            "binding_schema": "certvic.cvpr.detectability_exact_bytes.v1",
            "final_task_manifest_sha256": hashlib.sha256(
                paths["final_task_manifest"].read_bytes()
            ).hexdigest(),
            "task_bundle_manifest_sha256": hashlib.sha256(
                paths["task_bundle_manifest"].read_bytes()
            ).hexdigest(),
            "task_bundle_hash": bundle["bundle_hash"],
            "task_bundle_content_hash": bundle["manifest_content_hash"],
            "study_config_sha256": hashlib.sha256(paths["study_config"].read_bytes()).hexdigest(),
            "qa_manifest_sha256": hashlib.sha256(paths["qa_manifest"].read_bytes()).hexdigest(),
            "task_byte_bindings": byte_rows,
            "task_hashes_sha256": sha256_bytes(
                canonical_json_bytes([row["task_hash"] for row in byte_rows])
            ),
            "edited_image_hashes_sha256": sha256_bytes(canonical_json_bytes(edited_hashes)),
        }
        exact_byte_binding["binding_hash"] = sha256_bytes(
            canonical_json_bytes(exact_byte_binding)
        )
    result = {
        "schema": GATE_SCHEMA,
        "status": "DETECTABILITY_GATE_PASS" if passed else "DETECTABILITY_GATE_FAIL",
        "execution_allowed": passed,
        "decision_rule": "symmetric_detectability_auc <= frozen_threshold",
        "threshold": threshold,
        "auc": auc,
        "symmetric_detectability_auc": symmetric,
        "grouped_bootstrap_95_interval": interval,
        "bootstrap_samples": len(bootstrap),
        "folds": fold_rows,
        "perturbation_families": family_results,
        "grouping_key": "source_family_or_source_image_id",
        "groups": len(unique_groups),
        "tasks": len(rows),
        "classifier": {
            "features": "fixed_global_color_quantile_histogram_and_edge_statistics_v1",
            "model": "standardized_logistic_regression_liblinear",
            "random_state": seed,
            "provider_outputs_used": False,
        },
        "timing": "AFTER_FINAL_SELECTION_BEFORE_PROVIDER_OUTPUTS",
        "failure_action": None if passed else "PROSPECTIVE_RECONSTRUCTION_REQUIRED",
        "task_universe_sha256": task_universe_hash,
        "task_identity_sha256": task_identity_hash,
        "exact_byte_binding": exact_byte_binding,
        "exact_byte_binding_verified": exact_byte_binding is not None,
        "paper_evidence": False,
    }
    result["gate_hash"] = sha256_bytes(canonical_json_bytes(result))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the frozen set-level detectability gate")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--bundle-root")
    parser.add_argument("--config")
    parser.add_argument("--threshold", type=float)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=17031)
    parser.add_argument("--provider-output-root")
    parser.add_argument("--task-bundle-manifest")
    parser.add_argument("--study-config")
    parser.add_argument("--qa-manifest")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    threshold = args.threshold
    if threshold is None and args.config:
        config = load_yaml(args.config)
        threshold = float(
            config.get("design", {}).get("set_level_symmetric_detectability_auc_max", 0.80)
        )
    threshold = 0.80 if threshold is None else threshold
    provider_present = bool(
        args.provider_output_root
        and Path(args.provider_output_root).exists()
        and any(Path(args.provider_output_root).rglob("*"))
    )
    try:
        result = evaluate(
            read_jsonl(args.tasks),
            bundle_root=args.bundle_root,
            threshold=threshold,
            folds=args.folds,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
            provider_outputs_present=provider_present,
            final_task_manifest=args.tasks if args.task_bundle_manifest else None,
            task_bundle_manifest=args.task_bundle_manifest,
            study_config=args.study_config,
            qa_manifest=args.qa_manifest,
        )
    except (DetectabilityGateError, ValueError, OSError) as exc:
        print(
            json.dumps(
                {
                    "status": "DETECTABILITY_GATE_BLOCKED",
                    "reason": str(exc),
                    "paper_evidence": False,
                },
                sort_keys=True,
            )
        )
        return 2
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "out": str(destination),
                "symmetric_detectability_auc": result["symmetric_detectability_auc"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "DETECTABILITY_GATE_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
