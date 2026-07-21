"""Cluster-aware certification diagnostics (V3 prompt 06).

Quantifies how sensitive the intervention-consistency gap is to clustered
dependence from repeated source images, labels, edit engines, prompts, or
domains -- WITHOUT replacing the primary anytime-valid CS. It computes effective-n
heuristics, cluster bootstrap descriptive CIs, leave-one-source-out and
leave-one-label-out, and per-cluster influence.

Every output here is **descriptive only and not certification.** Claim gates must
never treat these as a confidence sequence.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np

from certvic.io import ensure_parent, read_jsonl
from certvic.metrics.cluster_sensitivity import (
    cluster_bootstrap_ci,
    gap,
    icc_and_design_effect,
    leave_one_cluster_out,
)

# Cluster dimensions we try to extract, in priority order of reviewer interest.
DEFAULT_DIMENSIONS = ("source", "label", "engine", "edit_type", "task_family", "domain", "model")


def _meta(row: dict) -> dict:
    return row.get("metadata") or {}


def cluster_value(row: dict, dim: str, task: dict | None = None) -> str | None:
    """Best-effort cluster key for ``dim`` from a score row, enriched by its task."""
    m = _meta(row)
    tmeta = (task or {}).get("metadata") if task else {}
    tmeta = tmeta or {}
    edit = (task or {}).get("edit") if task else {}
    edit = edit or {}
    if dim == "source":
        return m.get("source_id") or (task or {}).get("source", {}).get("source_id")
    if dim == "label":
        return m.get("label_id") or m.get("label_name") or tmeta.get("label_id") or tmeta.get("label_name") or row.get("task_family")
    if dim == "engine":
        return m.get("engine") or m.get("generator_mode") or tmeta.get("engine") or edit.get("params", {}).get("engine") or m.get("edit_type")
    if dim == "edit_type":
        return m.get("edit_type") or edit.get("edit_type")
    if dim == "task_family":
        return row.get("task_family") or m.get("task_family")
    if dim == "domain":
        return row.get("domain") or m.get("domain")
    if dim == "model":
        return row.get("model_name") or row.get("provider_name")
    return None


def _d_values(scores: list[dict]) -> np.ndarray:
    """d_i = a_i - C_i in {-1,0,1}; a_i=original_correct, C_i=consistent."""
    return np.array([float(bool(s.get("original_correct"))) - float(bool(s.get("consistent"))) for s in scores])


def run_cluster_diagnostics(
    scores_path: str,
    tasks_path: str | None = None,
    *,
    dimensions: tuple[str, ...] = DEFAULT_DIMENSIONS,
    alpha: float = 0.05,
    n_boot: int = 2000,
    seed: int = 0,
) -> dict:
    scores = read_jsonl(scores_path)
    tasks_by_id = {}
    if tasks_path and Path(tasks_path).exists():
        tasks_by_id = {str(t.get("item_id")): t for t in read_jsonl(tasks_path)}

    d = _d_values(scores)
    overall_gap = gap(d)

    per_dimension: dict[str, dict] = {}
    for dim in dimensions:
        cluster_ids = [cluster_value(s, dim, tasks_by_id.get(str(s.get("item_id")))) for s in scores]
        # Skip dimensions with no usable keys.
        if all(c is None for c in cluster_ids):
            continue
        cluster_ids = [str(c) if c is not None else "<none>" for c in cluster_ids]
        if len(set(cluster_ids)) <= 1:
            # Only one cluster -> no dependence structure to report for this dim.
            per_dimension[dim] = {"skipped": "single_cluster", "n_clusters": 1}
            continue
        per_dimension[dim] = {
            "effective_n": icc_and_design_effect(d, cluster_ids),
            "cluster_bootstrap_ci": cluster_bootstrap_ci(d, cluster_ids, alpha=alpha, n_boot=n_boot, seed=seed),
            "leave_one_cluster_out": leave_one_cluster_out(d, cluster_ids),
        }

    # Highlight the dimension that most shrinks effective-n (worst dependence).
    worst = None
    worst_neff = None
    for dim, info in per_dimension.items():
        eff = info.get("effective_n")
        if eff and (worst_neff is None or eff["n_eff"] < worst_neff):
            worst_neff = eff["n_eff"]
            worst = dim

    return {
        "diagnostics": "cluster_dependence",
        "scores_path": scores_path,
        "tasks_path": tasks_path,
        "n_items": len(scores),
        "overall_gap": round(overall_gap, 5),
        "dimensions_analyzed": sorted(per_dimension),
        "per_dimension": per_dimension,
        "worst_dimension_by_effective_n": worst,
        "worst_effective_n": worst_neff,
        # Discipline markers: these are NEVER certification.
        "is_certification": False,
        "descriptive_only": True,
        "replaces_anytime_valid_cs": False,
        "evidence_claims_made": False,
        "downloads_attempted": False,
        "paid_services": False,
    }


def render_report(result: dict) -> str:
    lines = [
        "# Cluster-Dependence Diagnostics",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Scores: `{result['scores_path']}`",
        f"Items: {result['n_items']}  |  overall gap Delta = {result['overall_gap']}",
        "",
        "**Descriptive only. NOT an anytime-valid confidence sequence and NOT certification.**",
        "The primary certified result must come from the anytime-valid CS; these diagnostics",
        "only show how robust the gap is to clustered dependence.",
        "",
        f"Most dependence-affected dimension (smallest effective-n): "
        f"`{result['worst_dimension_by_effective_n']}` (n_eff={result['worst_effective_n']})",
        "",
        "## Per-dimension",
        "",
        "| Dimension | Clusters | ICC | Design effect | n_eff | Bootstrap CI (descriptive) | Max |influence| |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for dim in result["dimensions_analyzed"]:
        info = result["per_dimension"][dim]
        if "skipped" in info:
            lines.append(f"| `{dim}` | {info.get('n_clusters')} | - | - | - | skipped ({info['skipped']}) | - |")
            continue
        eff = info["effective_n"]
        ci = info["cluster_bootstrap_ci"]
        loo = info["leave_one_cluster_out"]
        ci_str = f"[{ci.get('lo')}, {ci.get('hi')}]" if ci.get("available") else "n/a"
        lines.append(
            f"| `{dim}` | {eff['n_clusters']} | {eff['icc']} | {eff['design_effect']} | {eff['n_eff']} | {ci_str} | {loo['max_abs_influence']} |"
        )
    lines += [
        "",
        "## Reading these",
        "",
        "- **ICC / design effect**: higher ICC means items within a cluster are correlated;",
        "  effective-n shrinks accordingly. A small n_eff warns that nominal n overstates evidence.",
        "- **Cluster bootstrap CI**: a descriptive interval resampling whole clusters. Wider than",
        "  the i.i.d. bootstrap when dependence is real. Never used as certification.",
        "- **Leave-one-cluster-out influence**: how much one source/label moves the gap; large",
        "  values flag a result driven by a single cluster.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(result: dict, out_dir: str) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary": str(out / "cluster_diagnostics.json"),
        "report": str(out / "cluster_diagnostics_report.md"),
    }
    Path(paths["summary"]).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    Path(paths["report"]).write_text(render_report(result), encoding="utf-8")
    return paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC cluster-dependence diagnostics (descriptive, not certification)")
    parser.add_argument("--scores", required=True)
    parser.add_argument("--tasks")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    result = run_cluster_diagnostics(args.scores, args.tasks, alpha=args.alpha, n_boot=args.n_boot, seed=args.seed)
    ensure_parent(Path(args.out_dir) / "x")
    paths = write_outputs(result, args.out_dir)
    print(json.dumps({
        "n_items": result["n_items"],
        "overall_gap": result["overall_gap"],
        "dimensions_analyzed": result["dimensions_analyzed"],
        "worst_dimension_by_effective_n": result["worst_dimension_by_effective_n"],
        "is_certification": result["is_certification"],
        **paths,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
