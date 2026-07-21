# V4 Full Pack Report

Status: implemented as run-later infrastructure.

The V4 pass adds command generation, notebook generation, model-cache manifests,
fallback dataset planning, CC0 showcase tooling, edit-sweep planning, static
visual QA review, run recovery, prediction merge/dedup, model comparison,
statistical sensitivity, qualitative figure planning, LaTeX/supplement tooling,
capsule validation, result lockfiles, submission planning, troubleshooting,
license expansion, reviewer quality control, ablation planning, internal review
packet assembly, and the final V4 all-system audit.

No V4 tool downloads datasets/model weights, runs GPU jobs, runs VLM inference,
uses paid services, or fabricates paper results during tests or generation.

## Verification

```bash
python3 -m pytest -q
python3 -m ruff check certvic/commands certvic/notebooks certvic/models certvic/data/fallback_sources.py certvic/data/openimages_adapter_stub.py certvic/data/wikimedia_adapter_stub.py certvic/data/license_matrix.py certvic/data/license_expansion.py certvic/data/showcase_split.py certvic/release/showcase_package.py certvic/release/capsule_validator.py certvic/edit/parameter_sweep.py certvic/edit/sweep_report.py certvic/review_app certvic/recovery certvic/eval/prediction_dedup.py certvic/eval/merge_predictions.py certvic/reporting/model_rankings.py certvic/reporting/model_comparison.py certvic/metrics/sensitivity_suite.py certvic/reporting/sensitivity_report.py certvic/paper/figure_contact_sheet.py certvic/paper/qualitative_figures.py certvic/paper/latex_audit.py certvic/paper/build_paper_check.py certvic/paper/supplement_generator.py certvic/results certvic/submission certvic/troubleshoot certvic/validation/sentinel_items.py certvic/validation/reviewer_quality.py certvic/planning/ablation_plan.py certvic/v4 tests/test_v4_full_pack.py tests/test_v4_v4_real_run_command_generator.py
python3 -m certvic.v4.final_all_system_audit --out docs/V4_FINAL_ALL_SYSTEM_AUDIT_REPORT.md --json-out data/results/v4_final_all_system_audit.json
```

Latest result: full pytest passed (`451 passed`), scoped ruff passed, and the
V4 final all-system audit passed (`6/6`).
