# V2 Baselines and Ablations Report

Date: 2026-06-22
Prompt: `06_V2_BASELINES_AND_ABLATIONS_UPGRADE.md`

## What was added

- `certvic/eval/ablation_baselines.py` — 8 construct-validity baselines
  (random_seeded, majority_by_family, text_only_heuristic, caption_only_stub,
  original_only, edited_only, answer_prior, prompt_shuffle_control) reusing the
  main scoring rule.
- `certvic/eval/prompt_suite.py` — 6 prompt variants (canonical, terse,
  yes_no_strict, multiple_choice, rationale_forbidden, prompt_leakage_stress)
  with per-variant leakage flags.
- `certvic/eval/run_ablations.py` — runner writing per-baseline predictions +
  index.
- `certvic/reporting/ablations.py` — new `build_ablations_report`:
  baseline_table.csv, parser_sensitivity.csv, prompt_sensitivity.csv,
  construct_validity_flags.json, ablation_summary.md.

## Why this matters for CVPR

This is the construct-validity defense. The flags file marks the task
"gameable_without_vision" if any non-visual baseline (random/majority/prior/
caption/text/shuffle) exceeds a consistency threshold; original_only and
edited_only are shown to fail change items they cannot detect. Parser sensitivity
reports strict vs lenient with ambiguous/recovered/fail buckets and never hides
failures.

## Tests

- `tests/test_v2_baselines_ablations.py` — 6 tests (baseline list, original_only
  never updates, prompt variants + leakage, runner outputs, report outputs +
  flags, answer_prior low consistency). Full suite: **153 passed** (was 147).

## Note

Baselines are NOT evidence (evidence_status=CONSTRUCT_VALIDITY_NON_EVIDENCE).
Prompt sensitivity over a real model requires the open-VLM path.

## Status: PASS. Next: `07_V2_CERTIFICATION_POWER_AND_OPTIONAL_STOPPING.md`.
