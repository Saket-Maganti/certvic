# CertVIC Codex V2 Prompt 07 — Certification, Power Planning, and Optional Stopping

Do not make evidence claims from mock/smoke/non-reviewed artifacts. Do not silently replace anytime-valid CS with descriptive CIs.

## Goal

Make the statistical core paper-grade.

## Tasks

1. Add module:
   - `certvic/metrics/power.py`

   Functions:
   - estimate_n_for_gap
   - simulate_optional_stopping
   - simulate_consistency_gap
   - minimum_detectable_gap_grid

2. Add CLI:

   `python3 -m certvic.metrics.power_plan --config configs/real_pilot_ade20k.yaml --out-dir data/results/power_plan`

   Outputs:
   - power_plan.json
   - n_vs_gap.csv
   - optional_stopping_sim.csv
   - power_plan.md

3. Upgrade certification report:
   - overall gap CS
   - by-family CS when n is sufficient
   - descriptive summaries by domain
   - control edit spurious flip report
   - parse-failure sensitivity
   - explicit descriptive-vs-certified separation

4. Add config:
   - `configs/certification_policy.yaml`

   Fields:
   - alpha
   - gap_threshold
   - min_n_overall
   - min_n_by_family
   - parse_failure_max
   - control_spurious_flip_max
   - evidence_status_required
   - provider_type_disallowed

5. Add claim gate:
   - eligible only if certification policy passes
   - CS unavailable means not certified
   - bootstrap CI is never certification

6. Add tests:
   - `tests/test_v2_certification_power.py`

7. Update docs:
   - `docs/METRICS_SPEC.md`
   - `docs/CLAIM_LEDGER.md`
   - `docs/REPRO.md`

8. Create:
   - `docs/V2_CERTIFICATION_POWER_REPORT.md`

9. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, commands added, whether certification/power upgrade passed, and next prompt: `08_V2_RESULTS_REPORTING_FIGURES_TABLES.md`.
