"""Deterministic C11 statistical design and confidence-sequence validation suite."""

from __future__ import annotations

import argparse
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.stats import beta, binom

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import (  # noqa: E402
    REPORT_ROOT,
    artifact_manifest,
    write_csv,
    write_json,
    write_text,
)


FAMILY_ALPHA = 0.05
FAMILY_SIZE = 6
GATE_ALPHA = FAMILY_ALPHA / FAMILY_SIZE
TAU_UPDATE = 0.50
TAU_SPURIOUS = 0.10
SEED = 12013
SAMPLE_SIZES = [60, 80, 100, 120, 150, 180, 240, 300, 400, 500, 600]
UPDATE_RATES = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
SPURIOUS_RATES = [0.00, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20]


@dataclass(frozen=True)
class GateRule:
    endpoint: str
    threshold: float
    direction: str
    alpha: float = GATE_ALPHA


RESPONSIVENESS = GateRule("semantic_update_success", TAU_UPDATE, "lower_above")
SPECIFICITY = GateRule("irrelevant_flip", TAU_SPURIOUS, "upper_at_most")


def cp_lower(successes: int | np.ndarray, n: int, alpha: float = GATE_ALPHA) -> np.ndarray:
    values = np.asarray(successes, dtype=int)
    if n <= 0 or np.any(values < 0) or np.any(values > n) or not 0 < alpha < 1:
        raise ValueError("invalid Clopper-Pearson lower-bound arguments")
    result = np.where(values == 0, 0.0, beta.ppf(alpha, values, n - values + 1))
    return np.asarray(result, dtype=float)


def cp_upper(failures: int | np.ndarray, n: int, alpha: float = GATE_ALPHA) -> np.ndarray:
    values = np.asarray(failures, dtype=int)
    if n <= 0 or np.any(values < 0) or np.any(values > n) or not 0 < alpha < 1:
        raise ValueError("invalid Clopper-Pearson upper-bound arguments")
    result = np.where(values == n, 1.0, beta.ppf(1 - alpha, values + 1, n - values))
    return np.asarray(result, dtype=float)


def critical_count(n: int, rule: GateRule) -> int:
    counts = np.arange(n + 1)
    if rule.direction == "lower_above":
        passing = counts[cp_lower(counts, n, rule.alpha) > rule.threshold]
        return int(passing.min()) if passing.size else n + 1
    passing = counts[cp_upper(counts, n, rule.alpha) <= rule.threshold]
    return int(passing.max()) if passing.size else -1


def certification_probability(n: int, true_rate: float, rule: GateRule) -> float:
    cutoff = critical_count(n, rule)
    if rule.direction == "lower_above":
        return float(binom.sf(cutoff - 1, n, true_rate)) if cutoff <= n else 0.0
    return float(binom.cdf(cutoff, n, true_rate)) if cutoff >= 0 else 0.0


def power_grid() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rule, rates in ((RESPONSIVENESS, UPDATE_RATES), (SPECIFICITY, SPURIOUS_RATES)):
        for n in SAMPLE_SIZES:
            cutoff = critical_count(n, rule)
            for rate in rates:
                rows.append(
                    {
                        "endpoint": rule.endpoint,
                        "n": n,
                        "true_rate": rate,
                        "threshold": rule.threshold,
                        "family_alpha": FAMILY_ALPHA,
                        "gate_alpha": rule.alpha,
                        "direction": rule.direction,
                        "critical_count": cutoff,
                        "certification_probability": certification_probability(n, rate, rule),
                        "method": "exact_binomial_under_frozen_one_sided_clopper_pearson_rule",
                    }
                )
    return rows


def sample_size_sensitivity(maximum_n: int = 2500) -> list[dict[str, Any]]:
    scenarios = [
        (RESPONSIVENESS, rate) for rate in [0.60, 0.65, 0.70, 0.75, 0.80]
    ] + [(SPECIFICITY, rate) for rate in [0.00, 0.01, 0.02, 0.03, 0.05]]
    rows = []
    for rule, rate in scenarios:
        probabilities = [certification_probability(n, rate, rule) for n in range(1, maximum_n + 1)]
        for target in [0.70, 0.80, 0.90, 0.95]:
            eligible = [index + 1 for index, value in enumerate(probabilities) if value >= target]
            rows.append(
                {
                    "endpoint": rule.endpoint,
                    "true_rate": rate,
                    "target_power": target,
                    "minimum_n": eligible[0] if eligible else None,
                    "search_maximum_n": maximum_n,
                    "gate_alpha": rule.alpha,
                }
            )
    return rows


def familywise_simulation(iterations: int) -> list[dict[str, Any]]:
    scenarios = {
        "global_null_boundary": ([0.50] * 3, [0.10] * 3),
        "weak_alternative": ([0.60] * 3, [0.075] * 3),
        "design_alternative": ([0.70] * 3, [0.03] * 3),
        "heterogeneous_alternative": ([0.60, 0.70, 0.80], [0.01, 0.05, 0.075]),
        "qwen_like_specificity": ([0.70] * 3, [0.125, 0.02, 0.03]),
    }
    rng = np.random.default_rng(SEED)
    n = 120
    update_cutoff = critical_count(n, RESPONSIVENESS)
    spurious_cutoff = critical_count(n, SPECIFICITY)
    rows = []
    for scenario, (update_rates, spurious_rates) in scenarios.items():
        update_counts = np.column_stack(
            [rng.binomial(n, rate, size=iterations) for rate in update_rates]
        )
        spurious_counts = np.column_stack(
            [rng.binomial(n, rate, size=iterations) for rate in spurious_rates]
        )
        gate_pass = np.column_stack(
            [update_counts >= update_cutoff, spurious_counts <= spurious_cutoff]
        )
        boundary_null = np.asarray(update_rates + spurious_rates) == np.asarray(
            [TAU_UPDATE] * 3 + [TAU_SPURIOUS] * 3
        )
        false_any = (
            np.any(gate_pass[:, boundary_null], axis=1)
            if boundary_null.any()
            else np.zeros(iterations, dtype=bool)
        )
        row: dict[str, Any] = {
            "scenario": scenario,
            "n_per_endpoint": n,
            "iterations": iterations,
            "seed": SEED,
            "update_rates": update_rates,
            "spurious_rates": spurious_rates,
            "update_critical_successes": update_cutoff,
            "spurious_maximum_flips": spurious_cutoff,
            "familywise_false_certification_rate": float(false_any.mean()),
            "joint_six_gate_certification_power": float(np.all(gate_pass, axis=1).mean()),
            "monte_carlo_standard_error_joint": float(
                math.sqrt(np.all(gate_pass, axis=1).mean() * (1 - np.all(gate_pass, axis=1).mean()) / iterations)
            ),
        }
        for index in range(6):
            row[f"gate_{index + 1}_pass_probability"] = float(gate_pass[:, index].mean())
        rows.append(row)
    return rows


def boundary_curves() -> list[dict[str, Any]]:
    rows = []
    for n in [60, 80, 100, 120, 150, 180, 240, 300, 400, 500, 600]:
        for rule, rates in (
            (RESPONSIVENESS, np.linspace(0.40, 0.65, 51)),
            (SPECIFICITY, np.linspace(0.02, 0.18, 65)),
        ):
            for rate in rates:
                rows.append(
                    {
                        "endpoint": rule.endpoint,
                        "n": n,
                        "true_rate": float(rate),
                        "threshold": rule.threshold,
                        "certification_probability": certification_probability(n, float(rate), rule),
                        "critical_count": critical_count(n, rule),
                    }
                )
    return rows


def missingness_sensitivity() -> list[dict[str, Any]]:
    rows = []
    for rule, true_rates in (
        (RESPONSIVENESS, [0.60, 0.70, 0.80]),
        (SPECIFICITY, [0.01, 0.03, 0.05]),
    ):
        for n in [120, 240]:
            for rate in true_rates:
                for missing in [0.00, 0.01, 0.02, 0.05, 0.10, 0.20]:
                    effective = (
                        (1 - missing) * rate
                        if rule is RESPONSIVENESS
                        else missing + (1 - missing) * rate
                    )
                    fail_closed = certification_probability(n, effective, rule)
                    complete_case_n = max(1, int(round(n * (1 - missing))))
                    complete_case = certification_probability(complete_case_n, rate, rule)
                    rows.append(
                        {
                            "endpoint": rule.endpoint,
                            "n_frozen": n,
                            "true_rate_among_parseable": rate,
                            "missing_fraction": missing,
                            "fail_closed_effective_rate": effective,
                            "fail_closed_certification_probability": fail_closed,
                            "naive_complete_case_n": complete_case_n,
                            "naive_complete_case_certification_probability": complete_case,
                            "naive_minus_fail_closed_optimism": complete_case - fail_closed,
                            "method": "exact_binomial_missing_independent_planning_model",
                        }
                    )
    return rows


def _cs_bounds(streams: np.ndarray, *, alpha: float, t_opt: int) -> tuple[np.ndarray, np.ndarray]:
    horizon = streams.shape[1]
    time_index = np.arange(1, horizon + 1, dtype=float)
    sigma_squared = 4.0 / max(t_opt, 1)
    a_value = time_index / 8.0 + 1.0 / (2.0 * sigma_squared)
    radius = np.sqrt(
        4.0 * a_value * np.log(np.sqrt(sigma_squared * 2.0 * a_value) / alpha)
    ) / time_index
    means = np.cumsum(streams, axis=1) / time_index
    return np.maximum(means - radius, 0.0), np.minimum(means + radius, 1.0)


def cs_coverage_simulation(iterations: int) -> list[dict[str, Any]]:
    rows = []
    rng = np.random.default_rng(SEED + 1)
    for horizon in [60, 120, 240, 500]:
        for true_rate in [0.01, 0.10, 0.50, 0.90]:
            for multiplier in [0.5, 1.0, 2.0]:
                failures = 0
                processed = 0
                batch_size = min(2000, iterations)
                while processed < iterations:
                    current = min(batch_size, iterations - processed)
                    streams = rng.binomial(1, true_rate, size=(current, horizon))
                    lower, upper = _cs_bounds(
                        streams, alpha=FAMILY_ALPHA, t_opt=max(1, round(horizon * multiplier))
                    )
                    failures += int(np.any((lower > true_rate) | (upper < true_rate), axis=1).sum())
                    processed += current
                failure_rate = failures / iterations
                standard_error = math.sqrt(failure_rate * (1 - failure_rate) / iterations)
                rows.append(
                    {
                        "process": "bernoulli_mean",
                        "true_rate": true_rate,
                        "horizon": horizon,
                        "t_opt": max(1, round(horizon * multiplier)),
                        "alpha": FAMILY_ALPHA,
                        "iterations": iterations,
                        "seed": SEED + 1,
                        "simultaneous_noncoverage_rate": failure_rate,
                        "empirical_coverage": 1 - failure_rate,
                        "monte_carlo_standard_error": standard_error,
                        "upper_three_se": failure_rate + 3 * standard_error,
                        "material_undercoverage": failure_rate - 3 * standard_error > FAMILY_ALPHA,
                        "method": "certvic_native_hoeffding_normal_mixture_closed_form",
                    }
                )
    return rows


def _fixed_two_sided_bounds(streams: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    successes = np.cumsum(streams, axis=1)
    n = np.arange(1, streams.shape[1] + 1)
    lower = np.where(successes == 0, 0.0, beta.ppf(alpha / 2, successes, n - successes + 1))
    upper = np.where(successes == n, 1.0, beta.ppf(1 - alpha / 2, successes + 1, n - successes))
    return lower, upper


def optional_stopping_stress(iterations: int) -> list[dict[str, Any]]:
    rows = []
    horizon = 240
    rng = np.random.default_rng(SEED + 2)
    for true_rate in [0.10, 0.50, 0.80]:
        streams = rng.binomial(1, true_rate, size=(iterations, horizon))
        cs_lower, cs_upper = _cs_bounds(streams, alpha=FAMILY_ALPHA, t_opt=horizon)
        fixed_lower, fixed_upper = _fixed_two_sided_bounds(streams, FAMILY_ALPHA)
        means = np.cumsum(streams, axis=1) / np.arange(1, horizon + 1)
        consecutive = np.zeros_like(streams, dtype=int)
        for index in range(horizon):
            consecutive[:, index] = np.where(
                streams[:, index] == 1,
                (consecutive[:, index - 1] + 1) if index else 1,
                0,
            )
        conditions = {
            "cs_lower_crosses_truth": cs_lower > true_rate,
            "cs_upper_crosses_truth": cs_upper < true_rate,
            "five_consecutive_successes": consecutive >= 5,
            "large_interim_point_estimate": means >= min(1.0, true_rate + 0.10),
            "fixed_maximum_horizon": np.zeros_like(streams, dtype=bool),
        }
        conditions["fixed_maximum_horizon"][:, -1] = True
        for rule_name, condition in conditions.items():
            has_crossing = condition.any(axis=1)
            stop = np.where(has_crossing, condition.argmax(axis=1), horizon - 1)
            row_index = np.arange(iterations)
            cs_failure = (cs_lower[row_index, stop] > true_rate) | (
                cs_upper[row_index, stop] < true_rate
            )
            fixed_failure = (fixed_lower[row_index, stop] > true_rate) | (
                fixed_upper[row_index, stop] < true_rate
            )
            rows.append(
                {
                    "true_rate": true_rate,
                    "stopping_rule": rule_name,
                    "iterations": iterations,
                    "horizon": horizon,
                    "mean_stopping_time": float((stop + 1).mean()),
                    "probability_stopped_before_horizon": float((stop < horizon - 1).mean()),
                    "anytime_cs_noncoverage_at_stop": float(cs_failure.mean()),
                    "fixed_sample_cp_noncoverage_at_stop": float(fixed_failure.mean()),
                    "fixed_interval_optional_stopping_valid": False,
                    "seed": SEED + 2,
                }
            )
    return rows


def adversarial_ordering_stress() -> list[dict[str, Any]]:
    rows = []
    rng = np.random.default_rng(SEED + 3)
    for successes, n in [(30, 60), (72, 120), (180, 240)]:
        base = np.array([1] * successes + [0] * (n - successes), dtype=int)
        alternating_values: list[int] = []
        ones_remaining = successes
        zeros_remaining = n - successes
        next_value = 1 if ones_remaining >= zeros_remaining else 0
        while ones_remaining or zeros_remaining:
            if next_value == 1 and ones_remaining:
                alternating_values.append(1)
                ones_remaining -= 1
            elif next_value == 0 and zeros_remaining:
                alternating_values.append(0)
                zeros_remaining -= 1
            elif ones_remaining:
                alternating_values.append(1)
                ones_remaining -= 1
            else:
                alternating_values.append(0)
                zeros_remaining -= 1
            next_value = 1 - next_value
        orderings = {
            "successes_early": base,
            "failures_early": base[::-1],
            "alternating": np.array(alternating_values, dtype=int),
            "clustered": np.concatenate([base[: successes // 2], base[successes:], base[successes // 2 : successes]]),
            "random": rng.permutation(base),
        }
        for name, stream in orderings.items():
            lower, upper = _cs_bounds(stream.reshape(1, -1), alpha=FAMILY_ALPHA, t_opt=n)
            rows.append(
                {
                    "n": n,
                    "successes": successes,
                    "ordering": name,
                    "final_mean": successes / n,
                    "final_lower": float(lower[0, -1]),
                    "final_upper": float(upper[0, -1]),
                    "minimum_lower": float(lower.min()),
                    "maximum_upper": float(upper.max()),
                    "bounds_within_support": bool((lower >= 0).all() and (upper <= 1).all()),
                }
            )
    return rows


def cs_vs_fixed_efficiency(iterations: int) -> list[dict[str, Any]]:
    rows = []
    rng = np.random.default_rng(SEED + 4)
    scenarios = [
        ("responsiveness_above", 0.65, TAU_UPDATE),
        ("responsiveness_below", 0.35, TAU_UPDATE),
        ("specificity_below", 0.03, TAU_SPURIOUS),
        ("specificity_above", 0.20, TAU_SPURIOUS),
    ]
    horizon = 600
    for scenario, true_rate, threshold in scenarios:
        streams = rng.binomial(1, true_rate, size=(iterations, horizon))
        cs_lower, cs_upper = _cs_bounds(streams, alpha=GATE_ALPHA, t_opt=horizon)
        fixed_lower, fixed_upper = _fixed_two_sided_bounds(streams, 2 * GATE_ALPHA)
        if scenario.endswith("above"):
            cs_decision = cs_lower > threshold
            fixed_decision = fixed_lower > threshold
        else:
            cs_decision = cs_upper < threshold
            fixed_decision = fixed_upper < threshold
        for method, decision, lower, upper in [
            ("anytime_cs", cs_decision, cs_lower, cs_upper),
            ("fixed_sample_cp_peeked_diagnostic", fixed_decision, fixed_lower, fixed_upper),
        ]:
            decided = decision.any(axis=1)
            stop = np.where(decided, decision.argmax(axis=1) + 1, horizon + 1)
            finite = stop[stop <= horizon]
            rows.append(
                {
                    "scenario": scenario,
                    "true_rate": true_rate,
                    "threshold": threshold,
                    "method": method,
                    "iterations": iterations,
                    "horizon": horizon,
                    "probability_decision_by_n": float(decided.mean()),
                    "median_stopping_time": float(np.median(finite)) if finite.size else None,
                    "mean_stopping_time": float(finite.mean()) if finite.size else None,
                    "median_final_width": float(np.median(upper[:, -1] - lower[:, -1])),
                    "fixed_sample_optional_stopping_valid": method == "anytime_cs",
                }
            )
    return rows


def _save_figure(figure: plt.Figure, stem: Path) -> list[Path]:
    paths = []
    for suffix in ["png", "svg", "pdf"]:
        path = stem.with_suffix(f".{suffix}")
        figure.savefig(path, bbox_inches="tight", dpi=180 if suffix == "png" else None)
        if suffix == "svg":
            payload = path.read_text(encoding="utf-8")
            write_text(path, "\n".join(line.rstrip() for line in payload.splitlines()) + "\n")
        paths.append(path)
    plt.close(figure)
    return paths


def make_figures(
    grid: list[dict[str, Any]],
    familywise: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    missingness: list[dict[str, Any]],
    output: Path,
) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    for endpoint, axis in zip(
        [RESPONSIVENESS.endpoint, SPECIFICITY.endpoint], axes, strict=True
    ):
        for n in [120, 240, 500]:
            subset = [row for row in grid if row["endpoint"] == endpoint and row["n"] == n]
            axis.plot(
                [row["true_rate"] for row in subset],
                [row["certification_probability"] for row in subset],
                marker="o",
                label=f"n={n}",
            )
        axis.set(title=endpoint, xlabel="True rate", ylabel="Certification probability", ylim=(0, 1))
        axis.legend()
    figure.suptitle("Frozen exact-rule operating characteristics")
    paths.extend(_save_figure(figure, output / "power_curves"))

    figure, axis = plt.subplots(figsize=(8, 4))
    names = [row["scenario"] for row in familywise]
    values = [row["joint_six_gate_certification_power"] for row in familywise]
    axis.bar(range(len(names)), values)
    axis.set_xticks(range(len(names)), names, rotation=25, ha="right")
    axis.set(ylabel="Joint six-gate certification probability", ylim=(0, 1))
    paths.extend(_save_figure(figure, output / "fwer_validation"))

    figure, axis = plt.subplots(figsize=(8, 4))
    selected = [row for row in coverage if row["t_opt"] == row["horizon"]]
    for rate in sorted({row["true_rate"] for row in selected}):
        subset = [row for row in selected if row["true_rate"] == rate]
        axis.plot(
            [row["horizon"] for row in subset],
            [row["empirical_coverage"] for row in subset],
            marker="o",
            label=f"p={rate:g}",
        )
    axis.axhline(1 - FAMILY_ALPHA, color="black", linestyle="--", linewidth=1)
    axis.set(xlabel="Horizon", ylabel="Simultaneous empirical coverage", ylim=(0.9, 1.005))
    axis.legend()
    paths.extend(_save_figure(figure, output / "cs_coverage"))

    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    for endpoint, axis in zip(
        [RESPONSIVENESS.endpoint, SPECIFICITY.endpoint], axes, strict=True
    ):
        subset = [
            row
            for row in missingness
            if row["endpoint"] == endpoint and row["n_frozen"] == 120
            and row["true_rate_among_parseable"] in ({0.70} if endpoint == RESPONSIVENESS.endpoint else {0.03})
        ]
        axis.plot(
            [row["missing_fraction"] for row in subset],
            [row["fail_closed_certification_probability"] for row in subset],
            marker="o",
            label="fail closed",
        )
        axis.plot(
            [row["missing_fraction"] for row in subset],
            [row["naive_complete_case_certification_probability"] for row in subset],
            marker="s",
            label="complete case",
        )
        axis.set(title=endpoint, xlabel="Missing fraction", ylabel="Certification probability", ylim=(0, 1))
        axis.legend()
    paths.extend(_save_figure(figure, output / "missingness_sensitivity"))
    return paths


def run(output_root: Path = REPORT_ROOT, *, mode: str = "full") -> dict[str, Any]:
    started = time.perf_counter()
    statistics = output_root / "statistics"
    figures = output_root / "figures"
    statistics.mkdir(parents=True, exist_ok=True)
    simulation_iterations = 250_000 if mode == "full" else 50_000
    coverage_iterations = 20_000 if mode == "full" else 4_000
    stopping_iterations = 20_000 if mode == "full" else 4_000
    efficiency_iterations = 10_000 if mode == "full" else 2_000

    grid = power_grid()
    sample_sizes = sample_size_sensitivity()
    familywise = familywise_simulation(simulation_iterations)
    boundaries = boundary_curves()
    missingness = missingness_sensitivity()
    coverage = cs_coverage_simulation(coverage_iterations)
    optional = optional_stopping_stress(stopping_iterations)
    adversarial = adversarial_ordering_stress()
    efficiency = cs_vs_fixed_efficiency(efficiency_iterations)

    output_paths = [
        write_csv(statistics / "power_grid.csv", grid),
        write_csv(statistics / "sample_size_sensitivity.csv", sample_sizes),
        write_csv(statistics / "familywise_error_simulation.csv", familywise),
        write_csv(statistics / "boundary_curves.csv", boundaries),
        write_csv(statistics / "missingness_sensitivity.csv", missingness),
        write_csv(statistics / "cs_coverage_simulation.csv", coverage),
        write_csv(statistics / "optional_stopping_stress.csv", optional),
        write_csv(statistics / "cs_adversarial_orderings.csv", adversarial),
        write_csv(statistics / "cs_vs_fixed_efficiency.csv", efficiency),
    ]
    maximum_noncoverage = max(row["upper_three_se"] for row in coverage)
    verdict = {
        "schema": "certvic.cvpr2027.cs_validation_verdict.v1",
        "status": (
            "PASS_EMPIRICAL_VALIDATION" if not any(row["material_undercoverage"] for row in coverage)
            else "FAIL_MATERIAL_UNDERCOVERAGE"
        ),
        "method": "certvic_native_hoeffding_normal_mixture_closed_form",
        "nominal_alpha": FAMILY_ALPHA,
        "maximum_noncoverage_plus_three_mc_se": maximum_noncoverage,
        "coverage_iterations_per_cell": coverage_iterations,
        "optional_stopping_iterations_per_rate": stopping_iterations,
        "tuning_scales": ["0.5xhorizon", "1xhorizon", "2xhorizon"],
        "fixed_sample_warning": "Clopper-Pearson intervals are not optional-stopping-valid.",
        "paper_evidence": False,
        "evidence_class": "SOFTWARE_STATISTICAL_VALIDATION",
    }
    output_paths.append(write_json(statistics / "CS_VALIDATION_VERDICT.json", verdict))
    summary = {
        "schema": "certvic.cvpr2027.power_summary.v1",
        "analysis_rule": {
            "family_alpha": FAMILY_ALPHA,
            "family_size": FAMILY_SIZE,
            "per_gate_alpha": GATE_ALPHA,
            "responsiveness": "one-sided CP lower bound strictly above 0.50",
            "specificity": "one-sided CP upper bound at most 0.10",
        },
        "n_120_critical_values": {
            "minimum_semantic_update_successes": critical_count(120, RESPONSIVENESS),
            "maximum_irrelevant_flips": critical_count(120, SPECIFICITY),
        },
        "selected_operating_characteristics": {
            "update_p_0_70_n_120": certification_probability(120, 0.70, RESPONSIVENESS),
            "spurious_p_0_03_n_120": certification_probability(120, 0.03, SPECIFICITY),
            "joint_three_model_independent_design_scenario": next(
                row["joint_six_gate_certification_power"]
                for row in familywise
                if row["scenario"] == "design_alternative"
            ),
        },
        "simulation": {
            "mode": mode,
            "familywise_iterations": simulation_iterations,
            "coverage_iterations_per_cell": coverage_iterations,
            "stopping_iterations_per_rate": stopping_iterations,
            "seed": SEED,
        },
        "evidence_class": "DESIGN_VALIDATION_NOT_MODEL_EVIDENCE",
        "paper_evidence": False,
    }
    output_paths.append(write_json(statistics / "power_summary.json", summary))
    design_validation = {
        "schema": "certvic.cvpr2027.statistics_design_validation.v1",
        "status": "STATISTICAL_DESIGN_VALIDATED",
        "frozen_rule_used": True,
        "post_outcome_threshold_tuning": False,
        "power_rows": len(grid),
        "boundary_rows": len(boundaries),
        "sample_size_rows": len(sample_sizes),
        "missingness_rows": len(missingness),
        "cs_verdict": verdict["status"],
        "paper_evidence": False,
    }
    output_paths.append(
        write_json(statistics / "statistics_design_validation.json", design_validation)
    )
    output_paths.extend(make_figures(grid, familywise, coverage, missingness, figures))
    manifest = artifact_manifest(output_paths)
    output_paths.append(write_json(statistics / "STATISTICS_ARTIFACT_MANIFEST.json", manifest))
    return {
        "status": "COMPLETE",
        "runtime_seconds": time.perf_counter() - started,
        "mode": mode,
        "outputs": [path.relative_to(output_root.parent.parent).as_posix() for path in output_paths],
        "cs_verdict": verdict["status"],
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["quick", "full"], default="full")
    parser.add_argument("--output-root", type=Path, default=REPORT_ROOT)
    args = parser.parse_args(argv)
    result = run(args.output_root, mode=args.mode)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
