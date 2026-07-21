"""Statistical sensitivity + sequential-design plan for the main study (V7 prompt 09).

Builds a power / optional-stopping plan around Delta = E[a_i - C_i], reusing the project's
own anytime-valid machinery (``certvic.metrics.power``). It reports observed pilot effect
sizes, **conservative** planning deltas (deliberately below the observed gap), planning
sample sizes, a minimum-detectable-gap grid, and an optional-stopping Type-I-error check that
shows the anytime-valid CS controls false certification even under continuous peeking.

Hard rules honored: projections are marked as projections; pilot estimates are NOT treated as
guaranteed future effect sizes; the naive fixed-n CI is never the main claim; certification
thresholds (alpha=0.05, gap threshold=0.05) are unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from certvic.io import write_json  # noqa: E402
from certvic.metrics.power import (  # noqa: E402
    estimate_n_for_gap, minimum_detectable_gap_grid, simulate_optional_stopping,
)

RESULTS = REPO / "data/results/main_real_200"
OUT_JSON = RESULTS / "statistical_sensitivity.json"
DOC = REPO / "docs/STATISTICAL_SENSITIVITY_MAIN_STUDY.md"

THRESHOLD = 0.05   # canonical gap threshold -- unchanged
ALPHA = 0.05       # canonical -- unchanged
CONSERVATIVE_DELTAS = [0.20, 0.30, 0.40]   # deliberately << observed pilot gaps
N_GRID = [91, 200, 500, 800, 1000, 2000]


def _observed() -> list[dict]:
    out = []
    for jf in sorted(RESULTS.glob("pilot_report*/pilot_result.json")):
        d = json.loads(jf.read_text())
        ps = d["presence_intervention"]["summary"]
        pc = d["presence_intervention"]["certification"]
        out.append({
            "provider": d.get("provider"), "model": d.get("model"),
            "n": ps.get("n"),
            "original_accuracy_a": round(ps["original_accuracy"], 4),
            "consistency_p": round(ps["consistency_rate"], 4),
            "observed_gap_delta": round(ps["intervention_consistency_gap"], 4),
            "cs_lower_bound": pc.get("lower_bound"),
        })
    return out


def build() -> dict:
    observed = _observed()
    observed_deltas = [m["observed_gap_delta"] for m in observed]

    planning = []
    for dlt in CONSERVATIVE_DELTAS:
        est = estimate_n_for_gap(dlt, threshold=THRESHOLD, alpha=ALPHA, power=0.8)
        planning.append({"conservative_delta": dlt, **est})

    mdg_grid = minimum_detectable_gap_grid(N_GRID, threshold=THRESHOLD, alpha=ALPHA, power=0.8)

    # Optional-stopping Type-I error under the null (continuous peeking). Modest n_sims for CPU.
    optional_stopping = []
    for n in (200, 500):
        optional_stopping.append(simulate_optional_stopping(
            n=n, n_sims=100, alpha=ALPHA, true_gap=0.0, threshold=0.0, seed=0))

    result = {
        "schema": "certvic.statistical_sensitivity.v1",
        "evidence_status": "STATISTICAL_PLAN_NON_EVIDENCE", "paper_evidence": False,
        "metric": "Delta = E[a_i - C_i]; certified via anytime-valid CS on d_i=(a_i-C_i+1)/2 in [0,1]",
        "thresholds_unchanged": {"gap_threshold": THRESHOLD, "alpha": ALPHA},
        "observed_pilot_effect_sizes": observed,
        "observed_gap_range": [min(observed_deltas), max(observed_deltas)],
        "conservative_planning_deltas": {
            "note": "Projections. Pilot gaps (0.71-0.82) are NOT used as guaranteed future "
                    "effect sizes; planning uses these much smaller deltas.",
            "estimates": planning,
        },
        "minimum_detectable_gap_grid": mdg_grid,
        "optional_stopping_plan": {
            "description": "Item-level anytime-valid CS allows checking after every item without "
                           "alpha inflation. Simulation: Type-I error under H0 (true gap=0) with "
                           "peeking at every step should stay <= alpha.",
            "simulations": optional_stopping,
        },
        "policies": _policies(),
        "what_not_to_certify": _what_not_to_certify(),
    }
    write_json(OUT_JSON, result)
    DOC.write_text(_doc_md(result), encoding="utf-8")
    return result


def _policies() -> dict:
    return {
        "multiple_model_reporting": "Report each model's OWN anytime-valid certified CS. "
            "Cross-model agreement is descriptive; do not pool models into a single certified "
            "claim. For a joint claim, pre-register a primary model or apply a multiplicity "
            "adjustment across the model family.",
        "per_family_analysis": "Pre-register the task-family split (support_stability, "
            "affordance_reachability, occlusion_safety). Report per-family gaps descriptively; "
            "do NOT certify families with tiny n (e.g. occlusion n=6). Certification is at the "
            "pooled presence-arm level.",
        "exclusion_sensitivity_for_review_uncertainty": "Define a sensitivity set = items with "
            "rater disagreement (IAA gate) OR residual_target_visible in {yes, uncertain}. "
            "Recompute the CS with that set dropped; report both. Items are not silently removed "
            "from the canonical set.",
        "control_reporting": "Report the absent-object control and (when run) the spurious-flip "
            "specificity control as SEPARATE arms with their own status; a passed intervention "
            "gap is not evidence of specificity until the control passes.",
    }


def _what_not_to_certify() -> list[str]:
    return [
        "tiny task families (n too small for a meaningful CS)",
        "a single pooled cross-model claim (models are reported individually)",
        "anything via a naive fixed-n confidence interval as the primary claim",
        "the affordance arm (original accuracy ~chance => confounded)",
        "any mock/smoke/simulated artifact",
        "specificity, until the spurious-flip control predictions exist and pass",
    ]


def _doc_md(r: dict) -> str:
    L: list[str] = []
    P = L.append
    P("# Statistical Sensitivity & Sequential Design — Main Study")
    P("")
    P("**PLAN, NOT A RESULT** (`evidence_status = STATISTICAL_PLAN_NON_EVIDENCE`). Built around "
      "`Delta = E[a_i - C_i]`, certified via the project's anytime-valid CS. Certification "
      f"thresholds are unchanged (gap > {THRESHOLD}, alpha = {ALPHA}).")
    P("")
    P("## Observed pilot effect sizes (measured)")
    P("")
    P("| model | n | a | p | observed Δ | CS LB |")
    P("|---|---|---|---|---|---|")
    for m in r["observed_pilot_effect_sizes"]:
        P(f"| {m['model']} | {m['n']} | {m['original_accuracy_a']} | {m['consistency_p']} | "
          f"{m['observed_gap_delta']} | {round(m['cs_lower_bound'],4) if m['cs_lower_bound'] else m['cs_lower_bound']} |")
    P("")
    P(f"Observed Δ range: {r['observed_gap_range'][0]}–{r['observed_gap_range'][1]}. These are "
      "**not** used as guaranteed future effect sizes.")
    P("")
    P("## Conservative planning sample sizes (projections)")
    P("")
    P("| conservative Δ | feasible | planning n (per model, normal approx) |")
    P("|---|---|---|")
    for e in r["conservative_planning_deltas"]["estimates"]:
        P(f"| {e['conservative_delta']} | {e['feasible']} | {e.get('n')} |")
    P("")
    P("Planning estimates only (normal approximation); the anytime-valid CS may require more "
      "items. Even the most conservative Δ here is far below the observed pilot gap.")
    P("")
    P("## Minimum detectable gap by n")
    P("")
    P("| n | min detectable gap over threshold | implied gap |")
    P("|---|---|---|")
    for g in r["minimum_detectable_gap_grid"]:
        P(f"| {g['n']} | {round(g['minimum_detectable_gap_over_threshold'],4)} | "
          f"{round(g['implied_gap'],4)} |")
    P("")
    P("## Optional-stopping (anytime-valid) plan")
    P("")
    P(r["optional_stopping_plan"]["description"])
    P("")
    P("| n | Type-I error under H0 (continuous peeking) | available |")
    P("|---|---|---|")
    for s in r["optional_stopping_plan"]["simulations"]:
        P(f"| {s['n']} | {s.get('type_i_error')} | {s.get('available')} |")
    P("")
    P("A Type-I error at or below alpha while peeking at every item is the property that lets us "
      "stop as soon as the CS clears — without a fixed-n penalty.")
    P("")
    P("## Reporting policies")
    P("")
    for k, v in r["policies"].items():
        P(f"- **{k}** — {v}")
    P("")
    P("## What NOT to certify")
    P("")
    for x in r["what_not_to_certify"]:
        P(f"- {x}")
    P("")
    P("## Conservative design recommendation")
    P("")
    P("Plan the main study at a conservative Δ = 0.30 with item-level anytime-valid monitoring "
      "and an optional-stopping rule; report each model individually; pre-register the family "
      "split and the exclusion/sensitivity set; treat specificity as a separate gated arm.")
    P("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    r = build()
    print(json.dumps({
        "observed_gap_range": r["observed_gap_range"],
        "planning_n": {str(e["conservative_delta"]): e.get("n")
                       for e in r["conservative_planning_deltas"]["estimates"]},
        "optional_stopping": [{"n": s["n"], "type_i_error": s.get("type_i_error")}
                              for s in r["optional_stopping_plan"]["simulations"]],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
