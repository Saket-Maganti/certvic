# Codex Prompt 10 — Scoring Reports and Failure Gallery

Build the reporting layer for model scores, certified claims, tables, and failure galleries.

## Goal

Turn predictions into:
- pair scores
- metrics JSON
- CSV tables
- LaTeX tables
- markdown report
- failure gallery manifest
- claim ledger entries

## Files to create/update

```text
certvic/metrics/score_predictions.py
certvic/reporting/tables.py
certvic/reporting/figures.py
certvic/reporting/failure_gallery.py
certvic/reporting/build_report.py
certvic/reporting/claim_ledger.py
tests/test_score_predictions.py
tests/test_reporting_tables.py
tests/test_failure_gallery.py
tests/test_claim_ledger.py
docs/CLAIM_LEDGER.md
paper/tables/.gitkeep
paper/figures/.gitkeep
```

## Score predictions CLI

Implement:
```bash
python -m certvic.metrics.score_predictions \
  --tasks data/manifests/smoke_tasks.jsonl \
  --preds data/predictions/smoke_mock.jsonl \
  --out-scores data/results/smoke_pair_scores.jsonl \
  --out-summary data/results/smoke_summary.json
```

It should:
- pair original/edited predictions by item_id
- compute correctness
- compute consistency
- handle parse failures
- save PairScore JSONL
- save summary JSON

## Report builder CLI

Implement:
```bash
python -m certvic.reporting.build_report \
  --tasks data/manifests/smoke_tasks.jsonl \
  --scores data/results/smoke_pair_scores.jsonl \
  --preds data/predictions/smoke_mock.jsonl \
  --out-dir data/results/smoke_report \
  --alpha 0.05 \
  --gap-threshold 0.05
```

Outputs:
```text
summary.json
metrics_by_family.csv
metrics_by_domain.csv
metrics_by_required_change.csv
main_table.tex
certification.json
claim_ledger.json
report.md
failure_gallery.jsonl
```

## Tables

Generate:
- main model table
- by-family table
- by-domain table
- control-edit table

Columns:
- model/provider
- n
- original acc
- consistency
- gap
- bootstrap CI
- CS lower bound if available
- certified? yes/no/unavailable

## Failure gallery

Select failure cases:
- original_correct = true
- consistent = false
- parse_ok = true
- include task family/domain/edit type
- include paths/pointers
- include raw outputs
- include safe notes

Do not copy non-rehostable pixels. Gallery should be a manifest; actual rendering can happen locally.

## Claim ledger

Produce entries:
- claim_id
- claim_text
- evidence_files
- metric_values
- certification_status
- allowed/safe flag
- limitations

If certification unavailable, claims must be marked “not certified.”

## Markdown report

Write a clear `report.md`:
- run summary
- zero-cost statement
- metric definitions
- main results
- certification status
- failure patterns
- limitations
- forbidden claims not made

## Tests

Test:
- score predictions expected values on smoke data
- table generation writes CSV/TeX
- failure gallery only includes valid failures
- uncertified claim is not marked safe
- report builder outputs all required files

## Finish

Run:
```bash
python -m pytest -q
python -m certvic.metrics.score_predictions --tasks data/manifests/smoke_tasks.jsonl --preds data/predictions/smoke_mock.jsonl --out-scores data/results/smoke_pair_scores.jsonl --out-summary data/results/smoke_summary.json
python -m certvic.reporting.build_report --tasks data/manifests/smoke_tasks.jsonl --scores data/results/smoke_pair_scores.jsonl --preds data/predictions/smoke_mock.jsonl --out-dir data/results/smoke_report --alpha 0.05 --gap-threshold 0.05
```

Report:
- files changed
- tests run
- report path
- next prompt: `11_BASELINES_AND_ABLATIONS.md`
