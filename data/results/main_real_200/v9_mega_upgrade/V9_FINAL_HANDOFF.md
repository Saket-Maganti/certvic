# V9 Final Handoff

- Status: `FINAL_LOCAL_AUTORUN_COMPLETE_WITH_DEFERRED_HEAVY_RUNS`
- Tests: `657 passed`
- Claim guard passed: `true`
- Privacy audit passed: `true`
- Final recommendation: `HOLD_FOR_SPURIOUS_V2`

## Evidence Status

Main-200/V8 imported evidence plus V9 scaffolds; Spurious V2/Main-500/second-domain are deferred or blocked.

## Qwen Specificity

V1 failed 12/94 = 0.1277; Spurious V2 built as 30-item strict local set but predictions missing.

## Main-500

HOLD_FOR_SPURIOUS_V2; no Main-500 planning/images/predictions/results exist.

## Human Review

Qwen failed-12 review packet created and blank; Main-500 rater sheets are blank/no rows.

## Next Commands

- `Run Kaggle notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb`
- `Run Kaggle notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb`
- `Run Kaggle notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb`
- `Download *_spurious_v2_preds.zip to kaggleoutputs/v9_spurious_v2/`
- `python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2`
- `Fill data/annotations/v9_qwen_spurious_human_review/qwen_failed_12_human_review.csv if using human exclusions`

## Do Not Claim

- CVPR-ready
- all-model specificity
- real human validation
- Main-500 results
- Spurious V2 results
- second-domain evidence
