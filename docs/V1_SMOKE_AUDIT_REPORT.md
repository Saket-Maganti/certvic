# CertVIC V1 Smoke Audit Report

Date: 2026-06-21

Verdict: PASS

This audit is `MOCK_ONLY`. It uses synthetic smoke fixtures and deterministic
mock-provider outputs. It is an engineering smoke test only, not empirical
evidence for a paper claim.

## Commands Run

```bash
python3 -m pytest -q
python3 -m certvic.data.build_tasks --smoke --out data/manifests/smoke_tasks.jsonl
python3 -m certvic.data.manifest_checks --tasks data/manifests/smoke_tasks.jsonl --strict
python3 -m certvic.eval.run_eval --config configs/smoke.yaml --tasks data/manifests/smoke_tasks.jsonl --out data/predictions/smoke_mock_inconsistent.jsonl --provider mock_inconsistent --run-id smoke_mock_inconsistent_v1 --max-items 10
python3 -m certvic.metrics.score_predictions --tasks data/manifests/smoke_tasks.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --out-scores data/results/smoke_pair_scores.jsonl --out-summary data/results/smoke_summary.json
python3 -m certvic.reporting.build_report --tasks data/manifests/smoke_tasks.jsonl --scores data/results/smoke_pair_scores.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --out-dir data/results/smoke_report --alpha 0.05 --gap-threshold 0.05
python3 -m certvic.audit --config configs/smoke.yaml --tasks data/manifests/smoke_tasks.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --scores data/results/smoke_pair_scores.jsonl --paper paper/main.tex --strict
```

## Status

- Tests: 47 passed.
- Task manifest: 12 synthetic smoke items.
- Evaluated task pairs: 10.
- Predictions: 20, covering original and edited variants.
- Pair scores: 10.
- Strict audit: passed.
- Paid services used: no.
- Smoke image source: synthetic fixtures only.
- Evidence status: `MOCK_ONLY`.

## Metrics Summary

- Original accuracy: 1.000.
- Edited accuracy: 0.400.
- Consistency rate: 0.400.
- Intervention-consistency gap: 0.600.
- Parse failure rate: 0.000.
- Spurious flip rate on no-change items: 0.000.

By required change:

- `change`: n=6, consistency=0.000, gap=1.000.
- `no_change`: n=4, consistency=1.000, gap=0.000.

## Certification Status

Certification status: not certified.

Reason: the smoke run is `MOCK_ONLY`, and the optional `confseq` dependency is
not required for V1 smoke mode. The implementation records confidence-sequence
unavailability explicitly and does not silently replace anytime-valid
certification with a normal interval.

## Artifacts

- `data/manifests/smoke_tasks.jsonl`
- `data/predictions/smoke_mock_inconsistent.jsonl`
- `data/predictions/smoke_mock_inconsistent.jsonl.run_manifest.json`
- `data/results/smoke_pair_scores.jsonl`
- `data/results/smoke_summary.json`
- `data/results/smoke_report/summary.json`
- `data/results/smoke_report/report.md`
- `data/results/smoke_report/failure_gallery.jsonl`
- `data/results/smoke_report/claim_ledger.json`

## Known Limitations

- Smoke fixtures are synthetic and are not evidence.
- Mock-provider behavior is deterministic by design and should not be reported
  as model behavior.
- Real data licensing, edit quality, human validity, and open-model execution
  are still required.
- No paper result claim is certified from this audit.
- Real pilot/main runs should install optional stats dependencies if
  anytime-valid certification is needed.

## Next Steps

Start the ADE20K pilot preparation only after preserving this V1 smoke audit
state:

1. Provide a local ADE20K root path.
2. Build source and mask manifests without automatic downloads.
3. Select approximately 200 pilot items.
4. Run edit quality gates and human validity sheets.
5. Run open local VLMs on free Kaggle GPU only.
6. Keep all claims blocked until real artifacts and certification gates support
   them.
