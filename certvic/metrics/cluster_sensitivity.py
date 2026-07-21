"""Cluster-dependence sensitivity primitives (V3 prompt 06).

Core math for cluster-aware *descriptive* diagnostics: intraclass correlation /
design effect / effective-n, cluster bootstrap percentile CIs, and
leave-one-cluster-out influence. These quantify how sensitive the
intervention-consistency gap Delta = mean(a_i - C_i) is to clustered dependence
(repeated source images, labels, engines, ...).

**These are descriptive only and are NOT anytime-valid certification.** The
primary certified result must still come from the anytime-valid CS. Nothing here
makes an evidence claim.
"""

from __future__ import annotations

import numpy as np


def gap(d: np.ndarray) -> float:
    """Delta = mean(a_i - C_i); d_i already equals a_i - C_i in {-1,0,1}."""
    return float(np.mean(d)) if len(d) else 0.0


def icc_and_design_effect(d: np.ndarray, cluster_ids: list) -> dict:
    """One-way ANOVA ICC and design effect for a clustering of the d_i values."""
    n = len(d)
    clusters: dict = {}
    for value, cid in zip(d, cluster_ids):
        clusters.setdefault(cid, []).append(float(value))
    k = len(clusters)
    if n == 0 or k <= 1 or k == n:
        # No clustering structure (or one item per cluster): treat as independent.
        return {"n": n, "n_clusters": k, "mean_cluster_size": (n / k) if k else 0.0, "icc": 0.0, "design_effect": 1.0, "n_eff": float(n)}

    grand = float(np.mean(d))
    sizes = np.array([len(v) for v in clusters.values()], dtype=float)
    cluster_means = np.array([float(np.mean(v)) for v in clusters.values()])
    ss_between = float(np.sum(sizes * (cluster_means - grand) ** 2))
    ss_within = float(sum(np.sum((np.array(v) - cluster_means[i]) ** 2) for i, v in enumerate(clusters.values())))
    ms_between = ss_between / (k - 1)
    ms_within = ss_within / (n - k) if n > k else 0.0
    # Size-adjusted average cluster size (Hartley-style m0).
    m0 = (n - float(np.sum(sizes ** 2)) / n) / (k - 1) if k > 1 else 1.0
    m0 = max(m0, 1.0)
    denom = ms_between + (m0 - 1.0) * ms_within
    icc = ((ms_between - ms_within) / denom) if denom > 0 else 0.0
    icc = float(min(max(icc, 0.0), 1.0))
    mean_size = n / k
    design_effect = 1.0 + (mean_size - 1.0) * icc
    design_effect = max(design_effect, 1.0)
    return {
        "n": n,
        "n_clusters": k,
        "mean_cluster_size": round(mean_size, 4),
        "icc": round(icc, 4),
        "design_effect": round(design_effect, 4),
        "n_eff": round(n / design_effect, 2),
    }


def cluster_bootstrap_ci(d: np.ndarray, cluster_ids: list, *, alpha: float = 0.05, n_boot: int = 2000, seed: int = 0) -> dict:
    """Percentile CI for Delta resampling whole clusters with replacement.

    DESCRIPTIVE ONLY — not an anytime-valid confidence sequence.
    """
    n = len(d)
    by_cluster: dict = {}
    for value, cid in zip(d, cluster_ids):
        by_cluster.setdefault(cid, []).append(float(value))
    cluster_keys = list(by_cluster.keys())
    k = len(cluster_keys)
    if n == 0 or k == 0:
        return {"method": "cluster_bootstrap_percentile", "is_certification": False, "available": False, "point": 0.0, "lo": None, "hi": None}

    rng = np.random.default_rng(seed)
    arrays = [np.array(by_cluster[c]) for c in cluster_keys]
    estimates = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, k, size=k)
        pooled = np.concatenate([arrays[i] for i in pick])
        estimates[b] = pooled.mean()
    lo = float(np.quantile(estimates, alpha / 2))
    hi = float(np.quantile(estimates, 1 - alpha / 2))
    return {
        "method": "cluster_bootstrap_percentile",
        "is_certification": False,
        "descriptive_only": True,
        "available": True,
        "alpha": alpha,
        "n_boot": n_boot,
        "n_clusters": k,
        "point": round(gap(d), 5),
        "lo": round(lo, 5),
        "hi": round(hi, 5),
    }


def leave_one_cluster_out(d: np.ndarray, cluster_ids: list) -> dict:
    """Recompute Delta with each cluster removed; report influence per cluster."""
    n = len(d)
    full = gap(d)
    by_cluster: dict = {}
    for idx, cid in enumerate(cluster_ids):
        by_cluster.setdefault(cid, []).append(idx)
    rows = []
    for cid, idxs in by_cluster.items():
        mask = np.ones(n, dtype=bool)
        mask[idxs] = False
        without = gap(d[mask]) if mask.sum() else 0.0
        rows.append({
            "cluster": str(cid),
            "size": len(idxs),
            "cluster_gap": round(gap(d[idxs]), 5),
            "gap_without": round(without, 5),
            "influence": round(full - without, 5),
        })
    rows.sort(key=lambda r: abs(r["influence"]), reverse=True)
    influences = [r["influence"] for r in rows] or [0.0]
    return {
        "full_gap": round(full, 5),
        "n_clusters": len(by_cluster),
        "max_abs_influence": round(max(abs(i) for i in influences), 5),
        "most_influential": rows[0] if rows else None,
        "per_cluster": rows,
        "is_certification": False,
        "descriptive_only": True,
    }
