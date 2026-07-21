# CertVIC Codex V2 Prompt 08 — Results Reporting, Figures, and Tables

Do not fabricate results. Do not modify paper result sections with fake numbers. Use placeholders when real data are absent.

## Goal

Build paper-ready reporting infrastructure so real runs automatically produce CVPR-quality tables, figures, and markdown summaries.

## Tasks

1. Add V2 report builder:

   `python3 -m certvic.reporting.build_v2_report --scores data/results/pair_scores.jsonl --preds data/predictions/run.jsonl --tasks data/manifests/tasks.jsonl --out-dir data/results/v2_report`

2. Outputs:
   - main_results_table.csv / .tex
   - by_family_table.csv / .tex
   - by_domain_table.csv
   - by_edit_type_table.csv
   - control_edit_table.csv
   - parser_sensitivity_table.csv
   - certification_table.csv
   - claim_ledger.json
   - report.md

3. Add figures using matplotlib only:
   - consistency gap bar chart
   - CS trajectory plot
   - by-family heatmap
   - parse failure plot
   - control spurious flip plot
   - sample count / stopping plot

4. Add figure manifest:
   - figure_id
   - source data
   - command used
   - claim status
   - paper_ready bool

5. Add LaTeX export:
   - clean captions
   - unavailable as `--`
   - notes for descriptive vs certified

6. Add tests:
   - `tests/test_v2_reporting_figures.py`

7. Update docs:
   - `docs/REPRO.md`
   - `docs/CLAIM_LEDGER.md`
   - `docs/PAPER_PLAN.md`

8. Create:
   - `docs/V2_RESULTS_REPORTING_REPORT.md`

9. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, commands added, whether reporting upgrade passed, and next prompt: `09_V2_FAILURE_TAXONOMY_AND_GALLERY.md`.
