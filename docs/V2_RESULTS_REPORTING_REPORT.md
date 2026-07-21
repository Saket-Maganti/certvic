# V2 Results Reporting Report

Date: 2026-06-22
Prompt: `08_V2_RESULTS_REPORTING_FIGURES_TABLES.md`

## What was added

- `certvic/reporting/build_v2_report.py` — CLI producing main_results_table,
  by_family_table, by_domain_table, by_edit_type_table, control_edit_table,
  parser_sensitivity_table, certification_table (CSV + LaTeX where applicable),
  claim_ledger.json, report.md.
- Figures (matplotlib Agg, guarded): consistency_gap_bar, cs_trajectory,
  by_family_heatmap, parse_failure, control_spurious_flip, sample_count, plus
  figure_manifest.json (figure_id, source_data, command, claim_status,
  paper_ready).

## Honesty

Unavailable cells render as `--`; descriptive and certified results are kept
separate; a smoke/mock run is never certified. Now wired into run_tiny_eval's
build_v2_report stage.

## Tests

- `tests/test_v2_reporting_figures.py` — 4 tests (tables written, smoke not
  certified, unavailable -> `--`, figures + manifest). Full suite: **182 passed**
  (was 178).

## Status: PASS. Next: `09_V2_FAILURE_TAXONOMY_AND_GALLERY.md`.
