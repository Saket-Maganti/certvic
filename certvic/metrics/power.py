"""Power planning and optional-stopping diagnostics for the consistency gap.

The gap is Delta = a - p where a = E[a_i], p = E[C_i]. We certify via an
anytime-valid CS on the bounded transform d_i = (a_i - C_i + 1)/2 in [0, 1].
Analytic n estimates use a normal approximation (planning only); optional-stopping
and CS-based simulations use the `confseq` dependency and degrade gracefully when
it is unavailable. None of this makes evidence claims.
"""

from __future__ import annotations

import math

import numpy as np

from certvic.metrics.confseq_wrappers import gap_cs


def _norm_ppf(p: float) -> float:
    """Standard-normal quantile via Acklam's rational approximation (no scipy)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def estimate_n_for_gap(gap: float, threshold: float = 0.05, alpha: float = 0.05, power: float = 0.8, variance: float = 0.25) -> dict:
    """Approximate sample size to detect that the gap exceeds `threshold`.

    Works on the bounded transform d in [0,1] (variance bounded by 0.25). This is
    a normal-approximation planning estimate, NOT the anytime-valid guarantee.
    """
    mu_d = (gap + 1.0) / 2.0
    t_d = (threshold + 1.0) / 2.0
    effect = mu_d - t_d
    if effect <= 0:
        return {"gap": gap, "threshold": threshold, "feasible": False, "n": None, "note": "gap does not exceed threshold"}
    z_alpha = _norm_ppf(1 - alpha)
    z_power = _norm_ppf(power)
    n = ((z_alpha + z_power) ** 2) * variance / (effect ** 2)
    return {
        "gap": gap,
        "threshold": threshold,
        "alpha": alpha,
        "power": power,
        "feasible": True,
        "n": int(math.ceil(n)),
        "method": "normal_approximation_planning",
        "note": "Planning estimate only; anytime-valid CS may require more.",
    }


def minimum_detectable_gap_grid(n_values: list[int], threshold: float = 0.05, alpha: float = 0.05, power: float = 0.8, variance: float = 0.25) -> list[dict]:
    """For each n, the smallest gap whose normal-approx detection power reaches `power`."""
    z_alpha = _norm_ppf(1 - alpha)
    z_power = _norm_ppf(power)
    grid = []
    for n in n_values:
        if n <= 0:
            continue
        effect = (z_alpha + z_power) * math.sqrt(variance / n)
        mdg = 2 * effect  # back to original gap scale (d range 1 -> gap range 2)
        grid.append({"n": n, "minimum_detectable_gap_over_threshold": mdg, "implied_gap": threshold + mdg})
    return grid


def simulate_consistency_gap(n: int, accuracy: float, consistency: float, alpha: float = 0.05, threshold: float = 0.05, seed: int = 0, allow_unavailable: bool = True) -> dict:
    """Simulate one run with given marginals and return the final CS on the gap."""
    rng = np.random.RandomState(seed)
    a = (rng.rand(n) < accuracy).astype(float)
    c = (rng.rand(n) < consistency).astype(float)
    cs = gap_cs(a, c, alpha=alpha, allow_unavailable=allow_unavailable)
    latest = cs.get("latest", {})
    lo = latest.get("lo")
    return {
        "n": n,
        "empirical_gap": float(a.mean() - c.mean()),
        "cs_available": cs.get("available", False),
        "cs_lower": lo,
        "cs_upper": latest.get("hi"),
        "certified": bool(cs.get("available") and lo is not None and lo > threshold),
        "threshold": threshold,
    }


def simulate_optional_stopping(n: int, n_sims: int = 200, alpha: float = 0.05, true_gap: float = 0.0, threshold: float = 0.0, seed: int = 0, allow_unavailable: bool = True) -> dict:
    """Estimate Type-I error of sequential peeking under a null gap.

    Generates streams with E[a_i - C_i] = true_gap and checks how often the CS
    lower bound ever exceeds `threshold` (a false certification under the null).
    """
    base = 0.7
    accuracy = min(1.0, max(0.0, base))
    consistency = min(1.0, max(0.0, base - true_gap))
    false_certifications = 0
    available = True
    for sim in range(n_sims):
        rng = np.random.RandomState(seed + sim)
        a = (rng.rand(n) < accuracy).astype(float)
        c = (rng.rand(n) < consistency).astype(float)
        cs = gap_cs(a, c, alpha=alpha, allow_unavailable=allow_unavailable)
        if not cs.get("available"):
            available = False
            break
        lo = cs.get("lo") or []
        if any(value > threshold for value in lo):  # peeking at every step
            false_certifications += 1
    if not available:
        return {"available": False, "n": n, "n_sims": n_sims, "reason": "confseq unavailable", "type_i_error": None}
    return {
        "available": True,
        "n": n,
        "n_sims": n_sims,
        "alpha": alpha,
        "true_gap": true_gap,
        "threshold": threshold,
        "type_i_error": false_certifications / n_sims,
        "note": "Anytime-valid CS controls this even under continuous peeking.",
    }
