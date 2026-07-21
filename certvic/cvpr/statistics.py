"""Frozen confirmatory specificity statistics without a SciPy dependency."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable


def _binomial_cdf(k: int, n: int, p: float) -> float:
    return sum(
        math.comb(n, i) * (p**i) * ((1.0 - p) ** (n - i))
        for i in range(k + 1)
    )


def clopper_pearson_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided exact binomial upper bound found by monotone bisection."""
    if not 0 <= k <= n or n <= 0 or not 0 < alpha < 1:
        raise ValueError("require 0 <= k <= n, n > 0, and alpha in (0, 1)")
    if k == n:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if _binomial_cdf(k, n, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def clopper_pearson_lower(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided exact binomial lower bound found by monotone bisection."""
    if not 0 <= k <= n or n <= 0 or not 0 < alpha < 1:
        raise ValueError("require 0 <= k <= n, n > 0, and alpha in (0, 1)")
    if k == 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        survival = 1.0 - _binomial_cdf(k - 1, n, mid)
        if survival < alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def specificity_decision(
    flips: int,
    total: int,
    *,
    alpha: float = 0.05,
    threshold: float = 0.10,
) -> dict[str, object]:
    upper = clopper_pearson_upper(flips, total, alpha)
    return {
        "flips": flips,
        "total": total,
        "observed_rate": flips / total,
        "one_sided_clopper_pearson_upper": upper,
        "alpha": alpha,
        "threshold": threshold,
        "pass": upper <= threshold,
    }


def exact_mcnemar(discordant_a: int, discordant_b: int) -> float:
    n = discordant_a + discordant_b
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(discordant_a, discordant_b) + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def holm_adjust(p_values: Iterable[float]) -> list[float]:
    values = list(p_values)
    order = sorted(range(len(values)), key=values.__getitem__)
    adjusted = [0.0] * len(values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(values) - rank) * values[index])
        adjusted[index] = min(1.0, running)
    return adjusted


def specificity_operating_characteristic(
    n: int,
    true_rate: float,
    *,
    alpha: float,
    threshold: float = 0.10,
) -> dict[str, float | int]:
    """Probability that the exact upper-bound rule passes under a planning rate."""
    if not 0 <= true_rate <= 1:
        raise ValueError("true_rate must be in [0, 1]")
    lower, upper = -1, n + 1
    while lower + 1 < upper:
        midpoint = (lower + upper) // 2
        if clopper_pearson_upper(midpoint, n, alpha) <= threshold:
            lower = midpoint
        else:
            upper = midpoint
    maximum_passing_flips = lower
    probability = sum(
        math.comb(n, k) * (true_rate**k) * ((1.0 - true_rate) ** (n - k))
        for k in range(maximum_passing_flips + 1)
    )
    return {
        "n": n,
        "true_rate": true_rate,
        "alpha": alpha,
        "threshold": threshold,
        "maximum_passing_flips": maximum_passing_flips,
        "pass_probability": probability,
    }


def confidence_sequence(
    observations: Iterable[bool], *, alpha: float = 0.05
) -> list[dict[str, float | int]]:
    """Conservative anytime sequence using a summable exact-binomial alpha schedule."""
    values = list(observations)
    if not values or not 0 < alpha < 1:
        raise ValueError("observations must be nonempty and alpha must be in (0, 1)")
    flips = 0
    sequence: list[dict[str, float | int]] = []
    for index, value in enumerate(values, start=1):
        flips += int(bool(value))
        scheduled_alpha = alpha / (index * (index + 1))
        sequence.append({
            "n": index,
            "flips": flips,
            "observed_rate": flips / index,
            "upper": clopper_pearson_upper(flips, index, scheduled_alpha),
            "scheduled_alpha": scheduled_alpha,
        })
    return sequence


def _breakdown(rows: list[dict[str, object]], field: str) -> dict[str, dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(field, "UNSPECIFIED"))].append(row)
    result: dict[str, dict[str, object]] = {}
    for key, values in sorted(groups.items()):
        flips = sum(bool(row.get("flip")) for row in values if row.get("flip") is not None)
        missing = sum(row.get("flip") is None for row in values)
        result[key] = {
            "rows": len(values),
            "observed_flips": flips,
            "missing": missing,
            "primary_missing_as_failure_rate": (flips + missing) / len(values),
        }
    return result


def hardened_specificity_analysis(
    rows: list[dict[str, object]],
    *,
    alpha: float = 0.05,
    threshold: float = 0.10,
    family_size: int = 3,
) -> dict[str, object]:
    """Raw/filtered denominators, missingness, anytime bounds, and claim eligibility."""
    if not rows or family_size <= 0:
        raise ValueError("analysis rows must be nonempty and family_size positive")
    per_model_alpha = alpha / family_size
    raw_flips = sum(bool(row.get("flip")) for row in rows if row.get("flip") is not None)
    missing = sum(row.get("flip") is None for row in rows)
    primary_flips = raw_flips + missing
    valid = [row for row in rows if row.get("valid") is True and row.get("flip") is not None]
    filtered_flips = sum(bool(row.get("flip")) for row in valid)
    primary = specificity_decision(
        primary_flips, len(rows), alpha=per_model_alpha, threshold=threshold
    )
    filtered = (
        specificity_decision(filtered_flips, len(valid), alpha=per_model_alpha, threshold=threshold)
        if valid else None
    )
    ordered_primary = [True if row.get("flip") is None else bool(row.get("flip")) for row in rows]
    exclusions: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.get("valid") is not True:
            exclusions[str(row.get("exclusion_reason", "UNSPECIFIED"))] += 1
    provider_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        provider_counts[str(row.get("provider", "UNSPECIFIED"))] += 1
    return {
        "schema": "certvic.cvpr.hardened_statistics.v1",
        "bonferroni": {
            "family_alpha": alpha,
            "family_size": family_size,
            "per_model_alpha": per_model_alpha,
            "declared": True,
        },
        "raw_primary": {
            **primary,
            "denominator": len(rows),
            "observed_flips": raw_flips,
            "missing_counted_as_failure": missing,
        },
        "validity_filtered": {
            **(filtered or {}),
            "available": filtered is not None,
            "denominator": len(valid),
            "filtered_flips": filtered_flips,
        },
        "confidence_sequence": confidence_sequence(ordered_primary, alpha=per_model_alpha),
        "exclusion_sensitivity": {
            "excluded": len(rows) - len(valid),
            "reasons": dict(sorted(exclusions.items())),
            "all_excluded_as_failure_rate": (primary_flips + len(rows) - len(valid)) / len(rows),
        },
        "breakdowns": {
            field: _breakdown(rows, field) for field in ("family", "category", "stratum")
        },
        "missingness_audit": {
            "missing": missing,
            "fraction": missing / len(rows),
            "primary_treatment": "COUNT_AS_FLIP",
        },
        "provider_completion_audit": {
            "counts": dict(sorted(provider_counts.items())),
            "complete": len(provider_counts) == family_size and len(set(provider_counts.values())) == 1,
        },
        "decision_trace": {
            "rule": "all predeclared Bonferroni one-sided upper bounds <= frozen threshold",
            "primary_pass": primary["pass"],
            "threshold": threshold,
            "post_outcome_tuning": False,
        },
        "claim_eligibility": {
            "machine_readable": True,
            "eligible": bool(primary["pass"]) and missing == 0 and len(valid) == len(rows),
            "requires_genuine_human_review": True,
        },
        "paper_evidence": False,
    }


def mcnemar_holm_matrix(
    provider_vectors: dict[str, dict[str, bool]],
) -> dict[str, object]:
    """Exact paired provider matrix with Holm-adjusted exploratory p-values."""
    providers = sorted(provider_vectors)
    pairs: list[dict[str, object]] = []
    p_values: list[float] = []
    for left_index, left in enumerate(providers):
        for right in providers[left_index + 1:]:
            common = sorted(set(provider_vectors[left]) & set(provider_vectors[right]))
            left_only = sum(provider_vectors[left][item] and not provider_vectors[right][item] for item in common)
            right_only = sum(provider_vectors[right][item] and not provider_vectors[left][item] for item in common)
            p_value = exact_mcnemar(left_only, right_only)
            p_values.append(p_value)
            pairs.append({
                "left": left,
                "right": right,
                "paired_items": len(common),
                "left_flip_right_no_flip": left_only,
                "right_flip_left_no_flip": right_only,
                "exact_p": p_value,
            })
    adjusted = holm_adjust(p_values)
    for row, value in zip(pairs, adjusted, strict=True):
        row["holm_adjusted_p"] = value
    return {
        "schema": "certvic.cvpr.mcnemar_holm_matrix.v1",
        "exploratory": True,
        "pairs": pairs,
        "paper_evidence": False,
    }
