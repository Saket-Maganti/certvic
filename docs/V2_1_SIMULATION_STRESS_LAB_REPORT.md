# CertVIC V2.1 Simulation Stress Lab Report

Date: 2026-06-22

Verdict: PASS for pre-run simulation and stress-test readiness.

V2.1 adds a zero-cost simulation lab that creates synthetic CertVIC-like tasks,
predictions, pair scores, reports, and certification inputs. It does not
download data, use GPU, run VLM inference, generate ADE20K edits, or enable
evidence claims.

## What Changed

- Added `certvic.sim` package.
- Added seeded outcome profiles for realistic failure modes.
- Added single-run simulation CLI:
  - `python3 -m certvic.sim.generate_synthetic_run`
- Added stress-matrix CLI:
  - `python3 -m certvic.sim.stress_scenarios`
- Added schema-compatible synthetic task, prediction, and pair-score artifacts.
- Added V2 report compatibility for simulation-only runs.
- Added claim blocking for `SIMULATED_ONLY`.
- Added `configs/v2_1_simulation.yaml`.

## Outputs

Single scenario:

```text
simulated_tasks.jsonl
simulated_predictions.jsonl
simulated_pair_scores.jsonl
simulated_run_metadata.json
scenario_config.json
```

Scenario matrix:

```text
scenario_matrix_summary.csv
scenario_matrix_summary.json
scenario_matrix_report.md
<scenario>/v2_report/
```

All artifacts are marked `SIMULATED_ONLY`, `simulated=true`, `zero_cost=true`,
and `not_for_paper_claims=true`.

## Tests Run

```bash
python3 -m pytest -q
```

Result: 216 passed.

Focused coverage:

```text
tests/test_v2_1_simulation_lab.py
```

## Small Matrix Command

```bash
python3 -m certvic.sim.stress_scenarios \
  --out-dir data/results/v2_1_sim_matrix \
  --n-items 200 \
  --seed 0
```

Observed matrix status:

- scenarios: 11
- all simulated only: true
- all claim gates blocked: true
- high_accuracy_low_consistency descriptive gap: 0.225
- null_gap descriptive gap: 0.000
- parse_failure_heavy parse failure rate: 0.350
- spurious_control_flipper control spurious flip rate: 0.580
- small_gap_borderline descriptive gap: -0.045 and not certified

## Current Non-Evidence Status

- no real data
- no real VLM outputs
- no ADE20K edits
- no GPU
- no paid services
- no certification claims
- no paper result claims

## Remaining Blockers Before Real Runs

- run ADE20K commands on a local reviewed root
- generate and inspect real tiny edits
- pass quality and human validity gates
- pass VLM preflight for a zero-cost/local provider
- run model inference only after explicit readiness gates
- parse, score, certify, and audit real outputs before any evidence claims
