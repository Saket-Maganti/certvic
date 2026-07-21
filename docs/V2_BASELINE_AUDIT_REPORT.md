# V2 Baseline Audit Report

Generated: 2026-06-22

Overall status: **PASS** (9/9 checks passed)

This audit confirms that V1-V1.5 guarantees still hold before V2 upgrades.
It performs no downloads, runs no GPU jobs, runs no VLM inference, and makes
no evidence claims.

## Checks

| Check | Status | Detail |
| --- | --- | --- |
| `handoff_docs_exist` | pass | expected=6 |
| `core_command_modules_import` | pass | checked=11 |
| `schema_modules_import` | pass | checked=7 |
| `core_configs_exist` | pass | expected=5 |
| `no_paid_providers_enabled_by_default` | pass | configs_checked=5 |
| `v1_5_non_evidence_statuses_recognized` | pass | required=['CANDIDATE_ONLY', 'EDIT_READY_NON_EVIDENCE', 'GENERATED_EDIT_ONLY', 'NOT_GENERATED', 'PLANNED_ONLY', 'PREVIEW_ONLY']; recognized=['CANDIDATE_ONLY', 'EDIT_READY_NON_EVIDENCE', 'GENERATED_EDIT_ONLY', 'NOT_GENE... |
| `paper_contains_no_fake_results` | pass | results_placeholder_present=True |
| `zero_cost_policy_exists` | pass | path=docs/ZERO_COST_POLICY.md |
| `no_forbidden_claim_phrases` | pass | scanned=['paper/main.tex', 'paper/sections/01_intro.tex', 'paper/sections/02_related.tex', 'paper/sections/03_method.tex', 'paper/sections/04_experiments.tex', 'paper/sections/05_results.tex', 'paper/sections/06_limit... |

## Invariants asserted

- V1-V1.5 handoff docs are present.
- Core command and schema modules import without heavy optional deps.
- Core configs exist and parse.
- No paid provider is registered or enabled by default; free-tier reference is off by default.
- V1.5 non-evidence statuses remain recognized by the claim gate.
- Paper result sections remain `[RESULT REQUIRED]` with no fabricated numbers.
- Zero-cost policy doc exists.
- No forbidden claim phrases appear in paper/result docs.

## Next prompt

`02_V2_VISUAL_REVIEW_AND_APPROVAL_WORKFLOW.md`
