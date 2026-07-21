# Spurious V2 Blocked: Missing Predictions

No complete Spurious V2 provider prediction set was found. No results were fabricated, and no paper evidence was created.

## Missing Providers

- `qwen2_5_vl_7b`
- `internvl_8b`
- `llava_onevision_7b`

## Required Files

- `pred_qwen2_5_vl_7b_spurious_v2_merged.jsonl` or `qwen2_5_vl_7b_spurious_v2_preds.zip`
- `pred_internvl_8b_spurious_v2_merged.jsonl` or `internvl_8b_spurious_v2_preds.zip`
- `pred_llava_onevision_7b_spurious_v2_merged.jsonl` or `llava_onevision_7b_spurious_v2_preds.zip`

## Run Instructions

Run the notebooks listed in `docs/runbooks/KAGGLE_SPURIOUS_V2_T4X2_RUNBOOK.md`, download the three zip files to `kaggleoutputs/v9_spurious_v2/`, then run:

```bash
python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2
```
