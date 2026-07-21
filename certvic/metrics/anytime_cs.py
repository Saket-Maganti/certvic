"""Native, dependency-free anytime-valid confidence sequence for bounded means.

CertVIC's central statistical claim is an *anytime-valid* (time-uniform) lower
bound on the intervention-consistency gap that remains valid under optional
stopping. The gold-standard backend for this is the betting confidence sequence
in the optional ``confseq`` package (see ``certvic.metrics.confseq_wrappers``).

However, ``confseq`` is an optional dependency that is frequently *not* installed
on free CPU/Kaggle/Colab environments. Without a native fallback the entire
method silently degrades to "CS unavailable", which would make the paper's core
contribution unrunnable on zero-cost compute. This module provides a fully
self-contained, provably valid confidence sequence so the method always runs.

Construction (Robbins normal/conjugate mixture, Howard et al. 2021):

For observations ``X_i in [0, 1]`` with conditional mean ``m`` under the null,
let ``Y_i = X_i - m`` (range width 1). By Hoeffding's lemma,
``E[exp(lambda Y_i) | past] <= exp(lambda^2 / 8)``, so

    M_t(lambda) = exp(lambda * S_t - t * lambda^2 / 8),   S_t = sum_i Y_i

is a non-negative supermartingale with ``E[M_0] = 1``. Mixing ``lambda`` over a
mean-zero Gaussian prior ``N(0, sigma^2)`` yields the closed-form mixture
supermartingale

    M_t = (1 / (sigma * sqrt(2 A))) * exp(S_t^2 / (4 A)),   A = t/8 + 1/(2 sigma^2).

Ville's inequality gives ``P(exists t: M_t >= 1/alpha) <= alpha``. Inverting
``M_t < 1/alpha`` produces the two-sided confidence radius on the running mean

    r_t = (1 / t) * sqrt(4 A * log(sigma * sqrt(2 A) / alpha)),

so ``[mean_t - r_t, mean_t + r_t]`` is a ``(1 - alpha)`` confidence sequence:
the probability that the *true* mean ever leaves the interval is at most alpha,
**simultaneously over all t** (hence valid under optional stopping).

The mixture scale ``sigma^2`` is a tuning constant chosen up front from the
*planned* sample size (data-independent, so validity is preserved). We default to
the variance-balancing choice ``sigma^2 = 4 / t_opt``.

This is the same family of bound that ``confseq`` implements with a tighter
betting strategy; the betting CS is preferred when available because it is
narrower, but the two agree in validity. ``certvic/sim/anytime_validity.py``
empirically verifies the coverage / Type-I guarantee of this native CS under
continuous peeking, which is the safety net against any algebra error here.
"""

from __future__ import annotations

import math

import numpy as np

NATIVE_METHOD = "certvic.anytime_cs.hoeffding_mixture"

# Hoeffding sub-Gaussian variance proxy per step for X in [0, 1] (range width 1):
# E[exp(lambda Y)] <= exp(lambda^2 * c^2 / 8) with c = 1, i.e. proxy = 1/8.
_PSI = 1.0 / 8.0


def _mixture_variance(t_opt: int) -> float:
    """Up-front (data-independent) mixture scale, balancing the two terms in A."""
    t_opt = max(int(t_opt), 1)
    # Balance t/8 against 1/(2 sigma^2) near t_opt: 1/(2 sigma^2) = t_opt/8.
    return 4.0 / t_opt


def hoeffding_mixture_cs_01(
    x,
    alpha: float = 0.05,
    t_opt: int | None = None,
) -> dict:
    """Native anytime-valid CS for the mean of values in ``[0, 1]``.

    Returns the same dict shape as :func:`confseq_wrappers.bounded_mean_cs_01`:
    ``available``, ``alpha``, ``lo`` (list), ``hi`` (list), ``latest``,
    ``method``. ``lo``/``hi`` are the running two-sided bounds for prefixes of
    increasing length; ``latest`` holds the final bound.
    """
    values = np.asarray(x, dtype=float)
    if values.ndim != 1:
        values = values.reshape(-1)
    if values.size and (np.any(values < 0) or np.any(values > 1)):
        raise ValueError("hoeffding_mixture_cs_01 expects values in [0, 1]")

    n = int(values.size)
    if n == 0:
        return {
            "available": True,
            "alpha": alpha,
            "lo": [],
            "hi": [],
            "latest": {"lo": None, "hi": None},
            "method": NATIVE_METHOD,
            "t_opt": t_opt,
        }

    sigma2 = _mixture_variance(t_opt if t_opt is not None else n)
    cumsum = np.cumsum(values)
    lo: list[float] = []
    hi: list[float] = []
    for t in range(1, n + 1):
        mean_t = cumsum[t - 1] / t
        a_t = t * _PSI + 1.0 / (2.0 * sigma2)
        # log argument is >= 1/alpha > 1 since sigma*sqrt(2A) >= 1, so log > 0.
        log_term = math.log(math.sqrt(sigma2 * 2.0 * a_t) / alpha)
        radius = math.sqrt(4.0 * a_t * max(log_term, 0.0)) / t
        lo.append(float(min(max(mean_t - radius, 0.0), 1.0)))
        hi.append(float(min(max(mean_t + radius, 0.0), 1.0)))

    return {
        "available": True,
        "alpha": alpha,
        "lo": lo,
        "hi": hi,
        "latest": {"lo": lo[-1], "hi": hi[-1]},
        "method": NATIVE_METHOD,
        "t_opt": int(t_opt if t_opt is not None else n),
    }
