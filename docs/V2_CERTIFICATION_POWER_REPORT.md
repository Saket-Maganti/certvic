# V2 Certification, Power, and Optional-Stopping Report

Date: 2026-06-22
Prompt: `07_V2_CERTIFICATION_POWER_AND_OPTIONAL_STOPPING.md`

## What was added

- `certvic/metrics/power.py` — `estimate_n_for_gap`,
  `minimum_detectable_gap_grid`, `simulate_consistency_gap`,
  `simulate_optional_stopping`, with a dependency-free normal quantile
  (`_norm_ppf`, Acklam). CS-based simulations degrade gracefully without confseq.
- `certvic/metrics/power_plan.py` — CLI emitting power_plan.json, n_vs_gap.csv,
  optional_stopping_sim.csv, power_plan.md.
- `configs/certification_policy.yaml` + `certvic/metrics/certification_policy.py`
  — the certification gate: min_n_overall, min_n_by_family, parse_failure_max,
  control_spurious_flip_max, evidence_status_required, provider_type_disallowed,
  plus an available CS lower bound above gap_threshold.

## Why this matters for CVPR

This makes the statistical core the headline. Power planning shows the chosen n
is deliberate; the optional-stopping simulation demonstrates the anytime-valid CS
controls Type-I error under continuous peeking (a fixed-n bootstrap does not); the
policy gate enforces the descriptive-vs-certified separation in code.

## Tests

- `tests/test_v2_certification_power.py` — 10 tests (norm quantile, n-for-gap
  monotonicity + infeasibility, MDG grid, CS simulation graceful degrade, power
  CLI files, policy blocks mock / small-n / CS-unavailable, policy passes on clean
  evidence). Full suite: **163 passed** (was 153).

## Status: PASS. Next: `12_V2_END_TO_END_TINY_REAL_PILOT.md`.
