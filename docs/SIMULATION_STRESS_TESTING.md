# CertVIC Simulation Stress Testing

V2.1 adds a pre-run simulation lab for exercising the metrics, certification,
reporting, parser-sensitivity, control-warning, and claim-gate pipeline before
real ADE20K, GPU, or model runs.

Simulation exists to find implementation bugs and weak assumptions early. It
does not validate ADE20K data, generated edit quality, human validity, VLM
behavior, or any paper result.

## What It Generates

Each synthetic run writes:

- `simulated_tasks.jsonl`
- `simulated_predictions.jsonl`
- `simulated_pair_scores.jsonl`
- `simulated_run_metadata.json`
- `scenario_config.json`

Every row is marked:

- `evidence_status=SIMULATED_ONLY`
- `simulated=true`
- `zero_cost=true`
- `not_for_paper_claims=true`

## Built-In Scenarios

- `perfect_consistent`
- `high_accuracy_low_consistency`
- `low_accuracy_high_consistency`
- `spurious_control_flipper`
- `parse_failure_heavy`
- `family_specific_failure`
- `domain_specific_failure`
- `edit_type_specific_failure`
- `small_gap_borderline`
- `null_gap`
- `noisy_realistic_mixed`

## Single Scenario

```bash
python3 -m certvic.sim.generate_synthetic_run \
  --out-dir data/results/v2_1_sim/high_accuracy_low_consistency \
  --scenario high_accuracy_low_consistency \
  --n-items 500 \
  --seed 0
```

## Scenario Matrix

```bash
python3 -m certvic.sim.stress_scenarios \
  --out-dir data/results/v2_1_sim_matrix \
  --n-items 500 \
  --seed 0
```

Outputs:

- `scenario_matrix_summary.csv`
- `scenario_matrix_summary.json`
- `scenario_matrix_report.md`
- one subdirectory per scenario

Each scenario also builds a V2 report in `v2_report/`. Simulation-aware reports
state `SIMULATED_ONLY`, not real data, not model evidence, and no paper claims.

## What It Tests

- scoring compatibility with schema-valid tasks and predictions
- descriptive gap behavior under known outcome profiles
- parse-failure sensitivity
- control spurious-flip warnings
- report and figure generation
- certification behavior when CS is available or unavailable
- claim-gate blocking for simulated artifacts

## What It Cannot Prove

- real ADE20K manifest quality
- edit photorealism
- human validity
- VLM accuracy or consistency
- certified evidence claims
- paper-ready results

Use this lab before real runs to harden code paths and review assumptions. Treat
all outputs as engineering diagnostics only.
