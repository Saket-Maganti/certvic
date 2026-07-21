"""Power-plan CLI: sample-size planning and optional-stopping diagnostics."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml

from certvic.metrics.power import (
    estimate_n_for_gap,
    minimum_detectable_gap_grid,
    simulate_optional_stopping,
)


def _load_cfg(path: str | None) -> dict:
    if path and Path(path).exists():
        return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {}


def build_power_plan(config_path: str | None, out_dir: str, gaps: list[float] | None = None, n_values: list[int] | None = None, run_optional_stopping: bool = False) -> dict:
    cfg = _load_cfg(config_path)
    alpha = float(cfg.get("alpha", 0.05))
    threshold = float(cfg.get("gap_threshold", 0.05))
    gaps = gaps or [0.10, 0.15, 0.20, 0.25, 0.30]
    n_values = n_values or [50, 100, 150, 200, 300, 500]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    n_for_gap = [estimate_n_for_gap(gap, threshold=threshold, alpha=alpha) for gap in gaps]
    mdg = minimum_detectable_gap_grid(n_values, threshold=threshold, alpha=alpha)

    with (out / "n_vs_gap.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["gap", "threshold", "alpha", "feasible", "required_n"])
        for row in n_for_gap:
            writer.writerow([row["gap"], row["threshold"], alpha, row.get("feasible"), row.get("n")])

    optional_stopping = None
    if run_optional_stopping:
        optional_stopping = simulate_optional_stopping(n=max(n_values), n_sims=100, alpha=alpha, true_gap=0.0, threshold=threshold)
        with (out / "optional_stopping_sim.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["n", "n_sims", "true_gap", "threshold", "available", "type_i_error"])
            writer.writerow([optional_stopping.get("n"), optional_stopping.get("n_sims"), 0.0, threshold, optional_stopping.get("available"), optional_stopping.get("type_i_error")])

    plan = {
        "config": config_path,
        "alpha": alpha,
        "gap_threshold": threshold,
        "n_for_gap": n_for_gap,
        "minimum_detectable_gap_grid": mdg,
        "optional_stopping": optional_stopping,
        "note": "Planning estimates use a normal approximation; certification uses the anytime-valid CS.",
    }
    (out / "power_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")

    lines = ["# Power Plan", "", f"alpha={alpha}, gap_threshold={threshold}", "", "## Required n to detect a gap (normal-approx planning)", "", "| gap | feasible | required n |", "| --- | --- | --- |"]
    for row in n_for_gap:
        lines.append(f"| {row['gap']} | {row.get('feasible')} | {row.get('n')} |")
    lines += ["", "## Minimum detectable gap by n", "", "| n | implied gap |", "| --- | --- |"]
    for row in mdg:
        lines.append(f"| {row['n']} | {row['implied_gap']:.3f} |")
    if optional_stopping is not None:
        lines += ["", "## Optional-stopping Type-I (peeking under null)", "", f"type_i_error={optional_stopping.get('type_i_error')} (available={optional_stopping.get('available')})"]
    (out / "power_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return plan


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC power planning")
    parser.add_argument("--config")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--gaps", type=float, nargs="*")
    parser.add_argument("--n-values", type=int, nargs="*")
    parser.add_argument("--optional-stopping", action="store_true")
    args = parser.parse_args(argv)
    plan = build_power_plan(args.config, args.out_dir, gaps=args.gaps, n_values=args.n_values, run_optional_stopping=args.optional_stopping)
    print(json.dumps({"out_dir": args.out_dir, "n_for_gap": len(plan["n_for_gap"]), "optional_stopping": plan["optional_stopping"] is not None}, sort_keys=True))


if __name__ == "__main__":
    main()
