# V10.1 Exact Spurious V2 Kaggle Checklist

One next action: run Spurious V2 on Kaggle. Start with Qwen.

## Upload Files

- `dist/certvic_kaggle_main200_bundle.zip`
- `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip`
- The provider notebook you are running first.

## Attach Kaggle Datasets

- Attach the CertVIC code/config dataset made from `dist/certvic_kaggle_main200_bundle.zip`.
- Attach the strict Spurious V2 control dataset made from `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip`.
- Use Kaggle T4x2. Internet may be enabled unless a model/cache dataset is attached.
- Do not attach paid API credentials.

## Run Order

| Order | Provider | Notebook | RUN_TAG | Expected zip | Expected merged JSONL |
| ---: | --- | --- | --- | --- | --- |
| 1 | `qwen2_5_vl_7b` | `notebooks/kaggle/vlm_qwen2_5_vl_7b_spurious_v2_T4x2.ipynb` | `spurious_v2` | `qwen2_5_vl_7b_spurious_v2_preds.zip` | `pred_qwen2_5_vl_7b_spurious_v2_merged.jsonl` |
| 2 | `internvl_8b` | `notebooks/kaggle/vlm_internvl_8b_spurious_v2_T4x2.ipynb` | `spurious_v2` | `internvl_8b_spurious_v2_preds.zip` | `pred_internvl_8b_spurious_v2_merged.jsonl` |
| 3 | `llava_onevision_7b` | `notebooks/kaggle/vlm_llava_onevision_7b_spurious_v2_T4x2.ipynb` | `spurious_v2` | `llava_onevision_7b_spurious_v2_preds.zip` | `pred_llava_onevision_7b_spurious_v2_merged.jsonl` |

## Provider Settings

- `RUN_TAG = "spurious_v2"`
- Qwen: `PROVIDER = "qwen2_5_vl_7b"`
- InternVL: `PROVIDER = "internvl_8b"`
- LLaVA-OneVision: `PROVIDER = "llava_onevision_7b"`
- T4x2 sharding: `shard0` uses `CUDA_VISIBLE_DEVICES=0`; `shard1` uses `CUDA_VISIBLE_DEVICES=1`.

## Download Outputs

Download these files from Kaggle and place them locally in `kaggleoutputs/v9_spurious_v2/`:

- `qwen2_5_vl_7b_spurious_v2_preds.zip`
- `internvl_8b_spurious_v2_preds.zip`
- `llava_onevision_7b_spurious_v2_preds.zip`

The zip must contain the provider merged JSONL, summary, runtime manifest, and shard outputs created by the notebook.

## Local Import

```bash
mkdir -p kaggleoutputs/v9_spurious_v2
python3 scripts/import_v9_spurious_v2_outputs.py --input-dir kaggleoutputs/v9_spurious_v2 --out-dir data/results/main_real_200/v9_mega_upgrade/spurious_v2_ingest --canonical-dir data/results/main_real_200/kaggle_spurious_v2 --report-dir data/results/main_real_200/v9_mega_upgrade
```

## Local Validation

```bash
python3 -m pytest -q tests/test_v9_spurious_v2_runbooks.py tests/test_remaining_kaggle_runbooks.py tests/test_open_vlm_import_safety.py tests/test_v9_main500_go_nogo.py tests/test_v9_qwen_spurious_human_review_packet.py tests/test_v9_spurious_v2_ingest_decision.py
```

```bash
python3 -m certvic.validation.claim_language_guard --root docs paper data/results/main_real_200/v10_1_correction --out data/results/main_real_200/v10_1_correction/claim_guard_v10_1.json
```

```bash
python3 -m certvic.security.release_privacy_audit --root . --out data/results/main_real_200/v10_1_correction/privacy_audit_v10_1.md --json-out data/results/main_real_200/v10_1_correction/privacy_audit_v10_1.json
```

## Expected Runtime Range

| Provider | T4x2 estimate | Single-GPU fallback |
| --- | ---: | ---: |
| `qwen2_5_vl_7b` | 12-25 min | 25-45 min |
| `internvl_8b` | 10-20 min | 20-40 min |
| `llava_onevision_7b` | 15-30 min | 30-60 min |

## Partial-Shard Recovery

- If only one shard finishes, rerun the same provider notebook in the same Kaggle output workspace.
- Preserve completed shard files; the notebook is designed to resume at shard-file granularity.
- Do not hand-edit, hand-create, or relabel predictions.
- Import only after the provider zip or merged JSONL exists for all three providers.

## Do Not Run Yet

- Do not start Main-500 diffusion.
- Do not start Main-500 VLM evaluation.
- Do not run second-domain experiments.
- Do not promote `paper_evidence`.
- Do not claim real human validation until real labels exist.

## Current Package Audit

- Spurious V2 rows: `30`
- Package verdict: `READY_TO_RUN_ON_KAGGLE`
- Missing provider outputs: `qwen2_5_vl_7b, internvl_8b, llava_onevision_7b`
