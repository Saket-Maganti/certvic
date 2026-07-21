# Spurious V2 Next Action Card

Next action: run Qwen Spurious V2 on Kaggle.

## Upload

- `dist/certvic_kaggle_main200_bundle.zip`
- `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip`
- `notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb`

## Run

- Kaggle accelerator: T4x2
- `PROVIDER = "qwen2_5_vl_7b"`
- `RUN_TAG = "spurious_v2"`
- Expected output: `qwen2_5_vl_7b_spurious_v2_preds.zip`

## Then

- Run InternVL and LLaVA-OneVision Spurious V2 notebooks.
- Put all three zip outputs in `kaggleoutputs/v9_spurious_v2/`.
- Run `python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2 --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest --canonical-dir data/results/main_real_200/kaggle_spurious_v2 --report-dir data/results/main_real_200/v9_mega_upgrade`.

Main-500 is not allowed from the current state.
