# V10.1 Final Handoff

Verdict: correction pass complete; run Spurious V2 on Kaggle next.

## Direct Answers

- Privacy clean now: `true`
- Spurious V2 execution package ready: `true`
- First Kaggle notebook: `notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb`
- Upload files: `dist/certvic_kaggle_main200_bundle.zip` and `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip`
- Download outputs: `qwen2_5_vl_7b_spurious_v2_preds.zip`, `internvl_8b_spurious_v2_preds.zip`, `llava_onevision_7b_spurious_v2_preds.zip`
- Import command: `python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2 --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest --canonical-dir data/results/main_real_200/kaggle_spurious_v2 --report-dir data/results/main_real_200/v9_mega_upgrade`
- Main-500 allowed now: `false`
- `paper_evidence` changed: `false`

## Remaining Blockers

- Spurious V2 provider predictions are missing.
- Real human labels are missing.
- Spurious V2 ingest/gate decision has not run on real provider outputs.
- Main-500 remains blocked.
- Second domain remains plan-only.

## Validation Snapshot

- Selected pytest log exists: `true`; last line: `20 passed in 4.93s`
- Full pytest log exists: `true`; last line: `657 passed in 42.72s`
- Claim guard passed: `True`; findings: `0`
- Privacy audit passed: `True`; findings: `0`

Do not start Main-500 from this state.
