# CertVIC Codex V2 Prompt 06 — Baselines and Ablations Upgrade

Do not use paid APIs. Do not run large inference in tests. Do not make evidence claims.

## Goal

Build paper-critical baselines and ablations that defend construct validity.

## Tasks

1. Add baseline providers:
   - random_seeded
   - majority_by_family
   - text_only_heuristic
   - caption_only_stub
   - original_only
   - edited_only
   - answer_prior
   - prompt_shuffle_control

2. Add prompt suite:
   - canonical prompt
   - terse prompt
   - yes/no strict prompt
   - multiple-choice prompt where applicable
   - rationale-forbidden prompt
   - prompt leakage stress test

3. Add parser sensitivity:
   - strict parser
   - lenient parser
   - ambiguous output bucket
   - parse-failure-as-wrong option
   - parse-failure-excluded option
   - report both; never hide failures

4. Add ablation runner:

   `python3 -m certvic.eval.run_ablations --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/predictions/ablations --max-items 50 --seed 0`

5. Add ablation report:

   `python3 -m certvic.reporting.ablations --pred-dir data/predictions/ablations --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/ablation_report`

   Outputs:
   - ablation_summary.md
   - baseline_table.csv
   - parser_sensitivity.csv
   - prompt_sensitivity.csv
   - construct_validity_flags.json

6. Add tests:
   - `tests/test_v2_baselines_ablations.py`

7. Update docs:
   - `docs/METRICS_SPEC.md`
   - `docs/REPRO.md`
   - `docs/PILOT_ADE20K.md`

8. Create:
   - `docs/V2_BASELINES_ABLATIONS_REPORT.md`

9. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, commands added, whether baselines/ablations passed, and next prompt: `07_V2_CERTIFICATION_POWER_AND_OPTIONAL_STOPPING.md`.
