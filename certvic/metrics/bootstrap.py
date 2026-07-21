"""Paired bootstrap intervals."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np


def paired_bootstrap_ci(
    values: Sequence,
    statistic_fn: Callable[[list], float],
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> dict:
    if not values:
        return {"estimate": None, "lower": None, "upper": None, "alpha": alpha, "n_boot": n_boot}
    values = list(values)
    rng = np.random.default_rng(seed)
    estimates = []
    n = len(values)
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        estimates.append(float(statistic_fn([values[int(i)] for i in idx])))
    estimate = float(statistic_fn(values))
    lower, upper = np.quantile(estimates, [alpha / 2, 1 - alpha / 2])
    return {
        "estimate": estimate,
        "lower": float(lower),
        "upper": float(upper),
        "alpha": alpha,
        "n_boot": n_boot,
    }
