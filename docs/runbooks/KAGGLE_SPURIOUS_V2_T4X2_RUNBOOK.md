# Kaggle Spurious V2 T4x2 Runbook

## Purpose

Run the 30-item retrospective stricter-control diagnostic across Qwen2.5-VL-7B,
InternVL2-8B, and LLaVA-OneVision-7B on Kaggle T4x2. These items were selected
from the V1 pool after V1 outcomes existed, so this run is diagnostic and cannot
serve as an independent confirmatory Spurious V2. No local predictions were created.

## Required Kaggle Inputs

- `dist/certvic_kaggle_main200_bundle.zip` as a Kaggle dataset containing CertVIC code.
- `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip` as a Kaggle dataset containing V2 tasks/images.

## Notebooks

- `notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb`
- `notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb`
- `notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb`

## Output Files

- `pred_<provider>_spurious_v2_merged.jsonl`
- `<provider>_spurious_v2_preds.zip`
- `summary_<provider>_spurious_v2.json`
- `runtime_manifest_<provider>_spurious_v2.json`

## Local Import

Download the three `*_spurious_v2_preds.zip` files to `kaggleoutputs/v9_spurious_v2/`, then run:

```bash
python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2 --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest
python3 -m pytest -q tests/test_v9_spurious_v2_ingest_decision.py
```

## Runtime Estimates

| Provider | T4x2 estimate | Single-GPU fallback | Notes |
| --- | ---: | ---: | --- |
| `qwen2_5_vl_7b` | 12-25 min | 25-45 min | 30 V2 items |
| `internvl_8b` | 10-20 min | 20-40 min | 30 V2 items |
| `llava_onevision_7b` | 15-30 min | 30-60 min | 30 V2 items |

Resume is safe at shard-file granularity. If a session times out, rerun setup and execution; completed shard outputs are skipped.

Regardless of the numerical outcome, this retrospective run remains
`paper_evidence=false`. An independently sourced, outcome-unseen control set is
required for a confirmatory specificity claim.
