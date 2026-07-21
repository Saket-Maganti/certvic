"""Anytime-valid confidence sequence wrappers.

Backends, in order of preference:

* ``confseq`` betting CS (optional ``certvic[stats]`` dependency) - tightest.
* native Hoeffding mixture CS (``certvic.metrics.anytime_cs``) - always available,
  zero extra dependencies, provably valid (verified empirically in
  ``certvic/sim/anytime_validity.py``).

The ``backend`` argument controls selection:

* ``"auto"`` (default): use ``confseq`` if importable, otherwise the native CS.
  The result is therefore *always* available on zero-cost compute.
* ``"confseq"``: require ``confseq``; honour ``allow_unavailable`` (legacy path).
* ``"native"``: always use the native CS (useful for reproducibility/tests).
"""

from __future__ import annotations

import numpy as np

from certvic.exceptions import MissingOptionalDependencyError
from certvic.metrics.anytime_cs import hoeffding_mixture_cs_01


def _unavailable(alpha: float, method: str) -> dict:
    return {
        "available": False,
        "alpha": alpha,
        "lo": [],
        "hi": [],
        "latest": {"lo": None, "hi": None},
        "method": method,
        "reason": "confseq optional dependency is not installed or adapter call failed",
    }


def _confseq_cs(values: np.ndarray, alpha: float) -> dict:
    """Run the confseq betting CS; raises if confseq is unavailable/failing."""
    from confseq.betting import betting_cs

    result = betting_cs(values, alpha=alpha)
    if isinstance(result, tuple) and len(result) >= 2:
        lo, hi = result[0], result[1]
    elif isinstance(result, dict):
        lo, hi = result["l"], result["u"]
    else:
        raise TypeError(f"Unexpected confseq result type: {type(result)}")
    lo = [float(v) for v in lo]
    hi = [float(v) for v in hi]
    return {
        "available": True,
        "alpha": alpha,
        "lo": lo,
        "hi": hi,
        "latest": {"lo": lo[-1], "hi": hi[-1]},
        "method": "confseq.betting.betting_cs",
    }


def bounded_mean_cs_01(
    x,
    alpha: float = 0.05,
    breaks: int = 1000,
    allow_unavailable: bool = False,
    backend: str = "auto",
    t_opt: int | None = None,
) -> dict:
    values = np.asarray(x, dtype=float)
    if values.size and (np.any(values < 0) or np.any(values > 1)):
        raise ValueError("bounded_mean_cs_01 expects values in [0, 1]")

    if backend == "native":
        return hoeffding_mixture_cs_01(values, alpha=alpha, t_opt=t_opt)

    if backend in ("auto", "confseq"):
        try:
            return _confseq_cs(values, alpha)
        except Exception as exc:
            if backend == "auto":
                # Zero-cost native fallback keeps the method runnable everywhere.
                return hoeffding_mixture_cs_01(values, alpha=alpha, t_opt=t_opt)
            if allow_unavailable:
                return _unavailable(alpha, "confseq.betting.betting_cs")
            raise MissingOptionalDependencyError(
                "confseq is required for backend='confseq'; install certvic[stats] "
                "or use backend='auto'/'native'."
            ) from exc

    raise ValueError(f"unknown CS backend: {backend}")


def consistency_cs(
    C,
    alpha: float = 0.05,
    breaks: int = 1000,
    allow_unavailable: bool = False,
    backend: str = "auto",
    t_opt: int | None = None,
) -> dict:
    return bounded_mean_cs_01(
        C, alpha=alpha, breaks=breaks, allow_unavailable=allow_unavailable, backend=backend, t_opt=t_opt
    )


def gap_cs(
    a,
    C,
    alpha: float = 0.05,
    breaks: int = 1000,
    allow_unavailable: bool = False,
    backend: str = "auto",
    t_opt: int | None = None,
) -> dict:
    a_arr = np.asarray(a, dtype=float)
    c_arr = np.asarray(C, dtype=float)
    if len(a_arr) != len(c_arr):
        raise ValueError("a and C must have the same length")
    d = (a_arr - c_arr + 1.0) / 2.0
    result = bounded_mean_cs_01(
        d, alpha=alpha, breaks=breaks, allow_unavailable=allow_unavailable, backend=backend, t_opt=t_opt
    )
    if not result["available"]:
        return result
    lo = [2 * value - 1 for value in result["lo"]]
    hi = [2 * value - 1 for value in result["hi"]]
    result["lo"] = lo
    result["hi"] = hi
    # Empty input (n=0): bounds exist as a valid (empty) sequence but there is no
    # latest interval to report, so callers/reports treat it as unavailable data.
    result["latest"] = {"lo": lo[-1], "hi": hi[-1]} if lo else {"lo": None, "hi": None}
    return result
