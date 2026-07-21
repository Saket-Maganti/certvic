# Codex Prompt 17 — V1 End-to-End Smoke Audit

Run and harden the complete smoke pipeline.

## Goal

At this point, the full project should work in smoke mode from task creation to audit report.

Run the entire smoke pipeline and fix all failures.

## Required commands

Run, in order:

```bash
python -m pytest -q

python -m certvic.data.build_tasks \
  --smoke \
  --out data/manifests/smoke_tasks.jsonl

python -m certvic.data.manifest_checks \
  --tasks data/manifests/smoke_tasks.jsonl \
  --strict

python -m certvic.eval.run_eval \
  --config configs/smoke.yaml \
  --tasks data/manifests/smoke_tasks.jsonl \
  --out data/predictions/smoke_mock_inconsistent.jsonl \
  --provider mock_inconsistent \
  --run-id smoke_mock_inconsistent_v1 \
  --max-items 10

python -m certvic.metrics.score_predictions \
  --tasks data/manifests/smoke_tasks.jsonl \
  --preds data/predictions/smoke_mock_inconsistent.jsonl \
  --out-scores data/results/smoke_pair_scores.jsonl \
  --out-summary data/results/smoke_summary.json

python -m certvic.reporting.build_report \
  --tasks data/manifests/smoke_tasks.jsonl \
  --scores data/results/smoke_pair_scores.jsonl \
  --preds data/predictions/smoke_mock_inconsistent.jsonl \
  --out-dir data/results/smoke_report \
  --alpha 0.05 \
  --gap-threshold 0.05

python -m certvic.audit \
  --config configs/smoke.yaml \
  --tasks data/manifests/smoke_tasks.jsonl \
  --preds data/predictions/smoke_mock_inconsistent.jsonl \
  --scores data/results/smoke_pair_scores.jsonl \
  --paper paper/main.tex \
  --strict
```

## Fixes to make

If anything fails:
- fix the code
- add regression tests
- rerun the failed stage
- do not skip audit gates

## Required final artifact

Create:
```text
docs/V1_SMOKE_AUDIT_REPORT.md
```

Include:
- date
- commands run
- pass/fail status
- item counts
- prediction counts
- metrics summary
- certification status
- known limitations
- next real-pilot steps

## Hard requirements

The smoke audit must say:
- MOCK_ONLY
- no evidence claims
- no paid services used
- smoke images are synthetic fixtures only
- real pilot still required

## Finish

Report:
- tests run
- commands run
- smoke audit verdict
- remaining blockers
- recommended next action: start ADE20K pilot only after V1 smoke audit passes
