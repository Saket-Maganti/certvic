"""Edit detectability probe (V3 prompt 05).

A CPU-only construct-validity diagnostic. It asks: can cheap low-level image
features tell an *edited* image apart from its *original*? If a trivial
classifier separates them with high AUC, then a VLM's apparent
intervention-consistency gap may be confounded by the edit *artifact* rather than
the intended semantic single-factor change. This probe is **descriptive only**
and is never evidence by itself.

No GPU, no downloads, no paid services. Uses numpy/PIL (core deps) and, if
available, a scikit-learn classifier; otherwise a deterministic rank-AUC fallback.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path

import numpy as np

from certvic.edit.quality_gates import (
    _as_arr,
    outside_mask_change_fraction,
    sharpness_score,
    uniform_pixel_fraction,
)
from certvic.io import ensure_parent, read_jsonl

EVIDENCE_STATUS = "DIAGNOSTIC_ONLY"

PER_IMAGE_FEATURES = ["file_size", "edge_density", "sharpness", "mean_r", "mean_g", "mean_b", "std_gray", "uniform_fraction"]


def _have_sklearn() -> bool:
    return importlib.util.find_spec("sklearn") is not None


def _edge_density(gray: np.ndarray, thresh: int = 20) -> float:
    gx = np.abs(np.diff(gray.astype(int), axis=1))
    gy = np.abs(np.diff(gray.astype(int), axis=0))
    n = gx.size + gy.size
    if n == 0:
        return 0.0
    return float(((gx > thresh).sum() + (gy > thresh).sum()) / n)


def per_image_features(path: str) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    arr = _as_arr(path)
    gray = arr.mean(axis=-1) if arr.ndim == 3 else arr
    return {
        "file_size": float(p.stat().st_size),
        "edge_density": _edge_density(gray),
        "sharpness": sharpness_score(arr),
        "mean_r": float(arr[..., 0].mean()) if arr.ndim == 3 else float(arr.mean()),
        "mean_g": float(arr[..., 1].mean()) if arr.ndim == 3 else float(arr.mean()),
        "mean_b": float(arr[..., 2].mean()) if arr.ndim == 3 else float(arr.mean()),
        "std_gray": float(gray.std()),
        "uniform_fraction": uniform_pixel_fraction(arr),
    }


def _hist_distance(orig: np.ndarray, edit: np.ndarray) -> float:
    """L1 distance between normalized grayscale histograms (0..2)."""
    go = orig.mean(axis=-1).astype(np.uint8) if orig.ndim == 3 else orig.astype(np.uint8)
    ge = edit.mean(axis=-1).astype(np.uint8) if edit.ndim == 3 else edit.astype(np.uint8)
    ho = np.bincount(go.reshape(-1), minlength=256).astype(float)
    he = np.bincount(ge.reshape(-1), minlength=256).astype(float)
    ho /= max(ho.sum(), 1.0)
    he /= max(he.sum(), 1.0)
    return float(np.abs(ho - he).sum())


def _load_mask(mask_path: str | None, shape) -> np.ndarray | None:
    if not mask_path or not Path(mask_path).exists():
        return None
    try:
        m = _as_arr(mask_path)
        m = m.mean(axis=-1) if m.ndim == 3 else m
        if m.shape[:2] != tuple(shape[:2]):
            return None
        return (m > 0)
    except Exception:
        return None


def paired_features(original_path: str, edited_path: str, mask_path: str | None = None) -> dict | None:
    if not (Path(original_path).exists() and Path(edited_path).exists()):
        return None
    orig = _as_arr(original_path)
    edit = _as_arr(edited_path)
    if orig.shape != edit.shape:
        # Resized edits are themselves a detectable artifact; record max distance.
        return {
            "hist_distance": 2.0,
            "mean_abs_diff": 255.0,
            "edge_density_delta": 1.0,
            "sharpness_delta": 0.0,
            "outside_mask_change": 1.0,
            "shape_mismatch": True,
        }
    go = orig.mean(axis=-1)
    ge = edit.mean(axis=-1)
    mask = _load_mask(mask_path, orig.shape)
    return {
        "hist_distance": _hist_distance(orig, edit),
        "mean_abs_diff": float(np.abs(orig.astype(int) - edit.astype(int)).mean()),
        "edge_density_delta": abs(_edge_density(go) - _edge_density(ge)),
        "sharpness_delta": abs(sharpness_score(orig) - sharpness_score(edit)),
        "outside_mask_change": (outside_mask_change_fraction(orig, edit, mask) if mask is not None else None),
        "shape_mismatch": False,
    }


def detectability_score(pf: dict) -> float:
    """Composite paired-distance score; larger = more low-level detectable."""
    outside = pf.get("outside_mask_change") or 0.0
    return float(
        pf["hist_distance"]
        + pf["mean_abs_diff"] / 255.0
        + pf["edge_density_delta"]
        + min(pf["sharpness_delta"] / 50.0, 1.0)
        + outside
    )


# Backward-compatible private alias for historical callers/tests.
_detectability_score = detectability_score


def _rank_auc(values: list[float], labels: list[int]) -> float:
    """Mann-Whitney rank AUC for a single feature; 0.5 = chance."""
    pos = [v for v, y in zip(values, labels) if y == 1]
    neg = [v for v, y in zip(values, labels) if y == 0]
    if not pos or not neg:
        return 0.5
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    rank_pos = sum(ranks[i] for i in range(len(values)) if labels[i] == 1)
    u = rank_pos - len(pos) * (len(pos) + 1) / 2.0
    auc = u / (len(pos) * len(neg))
    return float(max(auc, 1.0 - auc))  # symmetric separability


def classify(per_image_rows: list[dict], *, use_sklearn: bool = True) -> dict:
    labels = [int(r["label"]) for r in per_image_rows]
    feats = {f: [float(r[f]) for r in per_image_rows] for f in PER_IMAGE_FEATURES}
    per_feature_auc = {f: round(_rank_auc(feats[f], labels), 4) for f in PER_IMAGE_FEATURES}
    best_feature = max(per_feature_auc, key=per_feature_auc.get) if per_feature_auc else None

    backend = "rank_auc_fallback"
    multivariate_auc = None
    raw_multivariate_auc = None
    accuracy = None
    raw_accuracy = None
    cv_grouped_by_item = False
    n = len(per_image_rows)
    can_sklearn = use_sklearn and _have_sklearn() and n >= 8 and len(set(labels)) == 2

    if can_sklearn:
        try:
            from sklearn.base import clone
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import roc_auc_score
            from sklearn.model_selection import GroupKFold, StratifiedKFold
            from sklearn.pipeline import make_pipeline
            from sklearn.preprocessing import StandardScaler

            x = np.array([[r[f] for f in PER_IMAGE_FEATURES] for r in per_image_rows], dtype=float)
            y = np.array(labels)
            item_groups = [r.get("item_id") for r in per_image_rows]
            clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
            unique_groups = {str(g) for g in item_groups if g is not None}
            complete_item_groups = bool(item_groups) and all(g is not None for g in item_groups)
            if complete_item_groups and len(unique_groups) >= 2:
                groups = np.asarray([str(g) for g in item_groups])
                n_splits = min(5, len(unique_groups))
                split_iter = GroupKFold(n_splits=n_splits).split(x, y, groups)
                cv_grouped_by_item = True
                backend = "sklearn_logreg_group_cv"
            else:
                n_splits = min(5, Counter(labels).most_common()[-1][1])
                split_iter = StratifiedKFold(
                    n_splits=n_splits, shuffle=True, random_state=0
                ).split(x, y)
                backend = "sklearn_logreg_stratified_cv"
            if n_splits >= 2:
                proba = np.zeros(n, dtype=float)
                for train_idx, test_idx in split_iter:
                    fitted = clone(clf).fit(x[train_idx], y[train_idx])
                    proba[test_idx] = fitted.predict_proba(x[test_idx])[:, 1]
                raw_auc = float(roc_auc_score(y, proba))
                # Detectability is separability, not a directional class score.
                # Use the symmetric AUC just as the rank-AUC fallback does.
                raw_multivariate_auc = round(raw_auc, 4)
                multivariate_auc = round(max(raw_auc, 1.0 - raw_auc), 4)
                raw_acc = float(((proba >= 0.5).astype(int) == y).mean())
                raw_accuracy = round(raw_acc, 4)
                accuracy = round(max(raw_acc, 1.0 - raw_acc), 4)
        except Exception:
            backend = "rank_auc_fallback"

    auc = multivariate_auc if multivariate_auc is not None else per_feature_auc.get(best_feature, 0.5)
    return {
        "backend": backend,
        "n_images": n,
        "auc": auc,
        "multivariate_auc": multivariate_auc,
        "raw_multivariate_auc": raw_multivariate_auc,
        "accuracy": accuracy,
        "raw_accuracy": raw_accuracy,
        "cv_grouped_by_item": cv_grouped_by_item,
        "auc_orientation": "symmetric_separability_max_auc_or_one_minus_auc",
        "best_single_feature": best_feature,
        "per_feature_auc": per_feature_auc,
    }


def run_detectability(
    tasks_path: str,
    *,
    max_items: int | None = None,
    flag_auc: float = 0.8,
    flag_top_fraction: float = 0.2,
    use_sklearn: bool = True,
) -> dict:
    tasks = read_jsonl(tasks_path)
    task_base = Path(tasks_path).parent
    if max_items is not None:
        tasks = tasks[:max_items]

    per_image_rows: list[dict] = []
    paired_rows: list[dict] = []
    skipped = 0
    for t in tasks:
        item_id = str(t.get("item_id") or t.get("edit_id") or "")
        orig = _resolve_task_image_path(t.get("original_image_path"), task_base)
        edited = _resolve_task_image_path(t.get("edited_image_path"), task_base)
        edit_type = (t.get("edit") or {}).get("edit_type") if isinstance(t.get("edit"), dict) else t.get("edit_type")
        mask_path = (t.get("mask") or {}).get("mask_path") if isinstance(t.get("mask"), dict) else t.get("mask_path")

        of = per_image_features(orig) if orig else None
        ef = per_image_features(edited) if edited else None
        if of is None or ef is None:
            skipped += 1
            continue
        per_image_rows.append({"item_id": item_id, "variant": "original", "label": 0, **of})
        per_image_rows.append({"item_id": item_id, "variant": "edited", "label": 1, **ef})

        pf = paired_features(orig, edited, mask_path)
        if pf is not None:
            score = detectability_score(pf)
            paired_rows.append({"item_id": item_id, "edit_type": edit_type, "detectability_score": round(score, 5), **pf})

    cls = classify(per_image_rows, use_sklearn=use_sklearn) if per_image_rows else {"backend": "none", "n_images": 0, "auc": None}

    # Flag the most-detectable items (top fraction by paired score).
    flagged: list[dict] = []
    if paired_rows:
        ordered = sorted(paired_rows, key=lambda r: r["detectability_score"], reverse=True)
        n_flag = max(1, int(round(len(ordered) * flag_top_fraction)))
        flagged = ordered[:n_flag]

    auc = cls.get("auc")
    return {
        "probe": "edit_detectability",
        "tasks_path": tasks_path,
        "n_items": len(paired_rows),
        "n_skipped": skipped,
        "classifier": cls,
        "artifact_risk": (auc is not None and auc >= flag_auc),
        "flag_auc": flag_auc,
        "per_image_rows": per_image_rows,
        "paired_rows": paired_rows,
        "highly_detectable_items": flagged,
        "evidence_status": EVIDENCE_STATUS,
        "evidence_claims_made": False,
        "downloads_attempted": False,
        "paid_services": False,
        "gpu_required": False,
    }


def _resolve_task_image_path(path: str | None, task_base: Path) -> str | None:
    if not path:
        return None
    marker = "__CTRL__/"
    if path.startswith(marker):
        return str(task_base / path[len(marker):])
    return path


def write_outputs(result: dict, out_dir: str) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary": str(out / "detectability_summary.json"),
        "features": str(out / "features.csv"),
        "report": str(out / "report.md"),
        "highly_detectable": str(out / "highly_detectable_items.jsonl"),
    }
    summary = {k: v for k, v in result.items() if k not in {"per_image_rows", "paired_rows", "highly_detectable_items"}}
    Path(paths["summary"]).write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    # features.csv (per-image rows).
    header = ["item_id", "variant", "label", *PER_IMAGE_FEATURES]
    lines = [",".join(header)]
    for r in result["per_image_rows"]:
        lines.append(",".join(str(r.get(c, "")) for c in header))
    Path(paths["features"]).write_text("\n".join(lines) + "\n", encoding="utf-8")

    with Path(paths["highly_detectable"]).open("w", encoding="utf-8") as h:
        for r in result["highly_detectable_items"]:
            h.write(json.dumps(r, sort_keys=True) + "\n")

    from certvic.reporting.edit_detectability_report import render_report

    Path(paths["report"]).write_text(render_report(result), encoding="utf-8")
    return paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC edit detectability probe (construct validity)")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--flag-auc", type=float, default=0.8)
    parser.add_argument("--no-sklearn", action="store_true")
    args = parser.parse_args(argv)
    result = run_detectability(args.tasks, max_items=args.max_items, flag_auc=args.flag_auc, use_sklearn=not args.no_sklearn)
    ensure_parent(Path(args.out_dir) / "x")
    paths = write_outputs(result, args.out_dir)
    print(json.dumps({
        "n_items": result["n_items"],
        "backend": result["classifier"].get("backend"),
        "auc": result["classifier"].get("auc"),
        "artifact_risk": result["artifact_risk"],
        "n_flagged": len(result["highly_detectable_items"]),
        **paths,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
