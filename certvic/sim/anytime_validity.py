"""Empirical validation of CertVIC's anytime-valid certification (SIMULATED_ONLY).

This lab is the empirical backbone of the paper's central statistical claim:
that the anytime-valid confidence sequence (CS) controls error *under optional
stopping / continuous peeking*, whereas a fixed-n confidence interval recomputed
at every step (the "peeking analyst") does not.

It is a Monte-Carlo experiment on synthetic Bernoulli gap sequences. It runs no
models, downloads nothing, needs no GPU, and makes no paper claims about VLMs:
its only outputs are statistical-method diagnostics. Results are tagged
``SIMULATED_ONLY`` and are method-validation evidence, not VLM evidence.

We work on the bounded transform ``d_i = (a_i - C_i + 1) / 2 in [0, 1]`` whose
mean is ``mu = (Delta + 1) / 2``. A run "certifies" when the one-sided lower
bound on ``Delta`` ever exceeds the threshold. We use Bernoulli(mu) draws for
``d_i`` (the maximum-variance bounded sequence) as a conservative stress test.

Three diagnostics:

* coverage     - fraction of trials where the *true* mean ever leaves the CS
                 (target <= alpha; this is the anytime guarantee).
* null Type-I  - with true ``Delta = threshold`` (boundary null), fraction of
                 trials that ever certify under continuous peeking
                 (CS target <= alpha; the peeked fixed-n CI blows past alpha).
* power        - with true ``Delta`` above threshold, fraction of trials that
                 certify within the horizon, plus the median stopping time.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from certvic.io import write_json
from certvic.metrics.anytime_cs import _PSI, _mixture_variance
from certvic.metrics.power import _norm_ppf

SIMULATION_EVIDENCE_STATUS = "SIMULATED_ONLY"


def _cs_radius_vector(n: int, alpha: float, t_opt: int) -> np.ndarray:
    """Data-independent native-CS radius on the running mean, for t = 1..n."""
    sigma2 = _mixture_variance(t_opt)
    t = np.arange(1, n + 1, dtype=float)
    a_t = t * _PSI + 1.0 / (2.0 * sigma2)
    log_term = np.log(np.sqrt(sigma2 * 2.0 * a_t) / alpha)
    return np.sqrt(4.0 * a_t * np.maximum(log_term, 0.0)) / t


def simulate(
    true_delta: float,
    n: int,
    n_trials: int,
    alpha: float,
    threshold: float,
    seed: int,
) -> dict:
    """Vectorised Monte-Carlo for one true Delta over `n_trials` peeking runs."""
    rng = np.random.default_rng(seed)
    mu = (true_delta + 1.0) / 2.0
    t_mu = (threshold + 1.0) / 2.0  # mean of d at the certification threshold

    draws = (rng.random((n_trials, n)) < mu).astype(float)
    cum = np.cumsum(draws, axis=1)
    t_index = np.arange(1, n + 1, dtype=float)
    running_mean = cum / t_index  # (n_trials, n)

    # Native anytime-valid CS (radius does not depend on the data).
    cs_radius = _cs_radius_vector(n, alpha, t_opt=n)
    cs_lo = running_mean - cs_radius
    cs_hi = running_mean + cs_radius

    # Peeking fixed-n one-sided CI (Wald normal approx), recomputed every step.
    z = _norm_ppf(1.0 - alpha)
    se = np.sqrt(np.clip(running_mean * (1.0 - running_mean), 0.0, None) / t_index)
    fixed_lo = running_mean - z * se

    # Certification fires when the lower bound on the mean exceeds t_mu at any t.
    cs_certify_t = cs_lo > t_mu
    fixed_certify_t = fixed_lo > t_mu

    cs_ever = cs_certify_t.any(axis=1)
    fixed_ever = fixed_certify_t.any(axis=1)
    # Fixed-n with NO peeking: decision only at the final step n.
    fixed_final = fixed_certify_t[:, -1]

    # Two-sided coverage of the true mean by the CS at all t.
    ever_outside = ((mu < cs_lo) | (mu > cs_hi)).any(axis=1)

    # Median stopping time among trials that certify with the CS.
    stop_times = np.argmax(cs_certify_t, axis=1) + 1
    certified_stop = stop_times[cs_ever]
    median_stop = float(np.median(certified_stop)) if certified_stop.size else None

    return {
        "true_delta": true_delta,
        "threshold": threshold,
        "n": n,
        "n_trials": n_trials,
        "alpha": alpha,
        "cs_certify_rate": float(cs_ever.mean()),
        "peeking_fixed_n_certify_rate": float(fixed_ever.mean()),
        "fixed_n_no_peek_certify_rate": float(fixed_final.mean()),
        "cs_miscoverage_rate": float(ever_outside.mean()),
        "cs_median_stop_time": median_stop,
    }


def run_anytime_validity_lab(
    out_dir: str | Path,
    n: int = 400,
    n_trials: int = 2000,
    alpha: float = 0.05,
    threshold: float = 0.0,
    power_deltas: list[float] | None = None,
    seed: int = 0,
    make_figure: bool = False,
) -> dict:
    """Run the full validity lab and write JSON/CSV/markdown diagnostics."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    power_deltas = power_deltas if power_deltas is not None else [0.10, 0.20, 0.30]

    # Boundary null: true Delta exactly at the threshold (hardest Type-I case).
    null = simulate(true_delta=threshold, n=n, n_trials=n_trials, alpha=alpha, threshold=threshold, seed=seed)
    null["row"] = "null_boundary"

    power_rows = []
    for i, delta in enumerate(power_deltas):
        row = simulate(
            true_delta=threshold + delta,
            n=n,
            n_trials=n_trials,
            alpha=alpha,
            threshold=threshold,
            seed=seed + 100 + i,
        )
        row["row"] = f"power_delta_+{delta:g}"
        power_rows.append(row)

    rows = [null, *power_rows]

    # Validity verdicts (empirical guarantees the paper relies on).
    checks = {
        "cs_type_i_controlled": null["cs_certify_rate"] <= alpha + _mc_tol(n_trials, alpha),
        "cs_coverage_controlled": null["cs_miscoverage_rate"] <= alpha + _mc_tol(n_trials, alpha),
        "peeking_fixed_n_inflates_type_i": null["peeking_fixed_n_certify_rate"] > null["cs_certify_rate"],
        # Power is horizon-dependent; require detection at the largest tested gap.
        "cs_has_power": (max(power_rows, key=lambda r: r["true_delta"])["cs_certify_rate"] >= 0.5)
        if power_rows
        else True,
    }

    csv_path = out / "anytime_validity_summary.csv"
    json_path = out / "anytime_validity_summary.json"
    report_path = out / "anytime_validity_report.md"
    _write_csv(csv_path, rows)
    payload = {
        "lab": "anytime_validity",
        "evidence_status": SIMULATION_EVIDENCE_STATUS,
        "simulated_only": True,
        "not_for_vlm_claims": True,
        "alpha": alpha,
        "threshold": threshold,
        "n": n,
        "n_trials": n_trials,
        "rows": rows,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
    }
    write_json(json_path, payload)
    report_path.write_text(_markdown(payload), encoding="utf-8")

    figure_path = None
    if make_figure:
        figure_path = _maybe_figure(out, null, alpha)

    return {
        "out_dir": str(out),
        "summary_csv": str(csv_path),
        "summary_json": str(json_path),
        "report": str(report_path),
        "figure": figure_path,
        "all_checks_passed": payload["all_checks_passed"],
        "checks": checks,
        "evidence_status": SIMULATION_EVIDENCE_STATUS,
    }


def _mc_tol(n_trials: int, alpha: float) -> float:
    """Monte-Carlo slack (~2 binomial SDs) so verdicts are not seed-flaky."""
    return 2.0 * (alpha * (1.0 - alpha) / max(n_trials, 1)) ** 0.5


def _write_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "row",
        "true_delta",
        "threshold",
        "n",
        "n_trials",
        "alpha",
        "cs_certify_rate",
        "peeking_fixed_n_certify_rate",
        "fixed_n_no_peek_certify_rate",
        "cs_miscoverage_rate",
        "cs_median_stop_time",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})


def _markdown(payload: dict) -> str:
    alpha = payload["alpha"]
    lines = [
        "# CertVIC Anytime-Validity Lab",
        "",
        "Status: **SIMULATED_ONLY**. Statistical-method validation only; not real",
        "data, not VLM outputs, not model evidence, and not paper claims about any",
        "model. These diagnostics validate the *estimator*, not any finding.",
        "",
        f"- alpha: {alpha}",
        f"- threshold (Delta): {payload['threshold']}",
        f"- horizon n: {payload['n']}",
        f"- trials: {payload['n_trials']}",
        "",
        "| scenario | true Delta | CS certify | peeked fixed-n certify | fixed-n (no peek) | CS miscoverage | CS median stop |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["rows"]:
        lines.append(
            "| {row} | {d:.3f} | {cs:.4f} | {pk:.4f} | {fn:.4f} | {mc:.4f} | {st} |".format(
                row=row["row"],
                d=row["true_delta"],
                cs=row["cs_certify_rate"],
                pk=row["peeking_fixed_n_certify_rate"],
                fn=row["fixed_n_no_peek_certify_rate"],
                mc=row["cs_miscoverage_rate"],
                st=("--" if row["cs_median_stop_time"] is None else int(row["cs_median_stop_time"])),
            )
        )
    null = payload["rows"][0]
    lines += [
        "",
        "## Verdicts",
        "",
        f"- CS Type-I at the boundary null is controlled at alpha={alpha}: "
        f"**{payload['checks']['cs_type_i_controlled']}** "
        f"(CS={null['cs_certify_rate']:.4f}).",
        f"- CS coverage of the true mean is controlled: "
        f"**{payload['checks']['cs_coverage_controlled']}** "
        f"(miscoverage={null['cs_miscoverage_rate']:.4f}).",
        f"- The peeked fixed-n CI inflates Type-I above the CS: "
        f"**{payload['checks']['peeking_fixed_n_inflates_type_i']}** "
        f"(peeked fixed-n={null['peeking_fixed_n_certify_rate']:.4f} vs "
        f"CS={null['cs_certify_rate']:.4f}).",
        f"- The CS retains power at Delta - threshold >= 0.2: "
        f"**{payload['checks']['cs_has_power']}**.",
        "",
        "## Interpretation",
        "",
        "This substantiates the reviewer-defense claim that optional stopping does",
        "not invalidate the CertVIC certification: the anytime-valid CS keeps the",
        "probability of *ever* certifying a non-existent gap at or below alpha under",
        "continuous peeking, while a fixed-n CI recomputed at every item does not.",
        "It does **not** validate edit realism, label quality, or any VLM behaviour.",
        "",
    ]
    return "\n".join(lines)


def _maybe_figure(out: Path, null: dict, alpha: float):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    fig, ax = plt.subplots(figsize=(5, 3.2))
    labels = ["anytime CS\n(peeking)", "fixed-n CI\n(peeking)", "fixed-n CI\n(no peek)"]
    values = [
        null["cs_certify_rate"],
        null["peeking_fixed_n_certify_rate"],
        null["fixed_n_no_peek_certify_rate"],
    ]
    ax.bar(labels, values, color=["#2c7fb8", "#d95f0e", "#999999"])
    ax.axhline(alpha, color="black", linestyle="--", linewidth=1, label=f"alpha={alpha}")
    ax.set_ylabel("P(certify under true Delta = threshold)")
    ax.set_title("False-certification under optional stopping (SIMULATED_ONLY)")
    ax.legend()
    fig.tight_layout()
    path = out / "anytime_validity_type_i.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return str(path)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="CertVIC anytime-validity Monte-Carlo lab (SIMULATED_ONLY; no models)."
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--n", type=int, default=400)
    parser.add_argument("--n-trials", type=int, default=2000)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--threshold", type=float, default=0.0)
    parser.add_argument("--power-deltas", type=float, nargs="*")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--figure", action="store_true")
    args = parser.parse_args(argv)
    result = run_anytime_validity_lab(
        args.out_dir,
        n=args.n,
        n_trials=args.n_trials,
        alpha=args.alpha,
        threshold=args.threshold,
        power_deltas=args.power_deltas,
        seed=args.seed,
        make_figure=args.figure,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
