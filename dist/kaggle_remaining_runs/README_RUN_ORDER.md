# Remaining Kaggle runs -- run order

This package prepares executable runbooks. It does not contain model predictions
and does not make evidence claims.

## Kaggle settings for every VLM notebook

- Accelerator: GPU T4 x2
- Internet: ON for model self-download
- One provider notebook per session
- One task bundle per session
- Output directory: `/kaggle/working`

## Priority order

1. Spurious-flip / control_irrelevant: run each VLM notebook with `certvic_spurious_flip_control.zip`, `RUN_TAG=spurious`.
2. Scaled held-out perception control: run each VLM notebook with `certvic_perception_control_scaled.zip`, `RUN_TAG=perception_scaled`.
3. Prompt-polarity ablations: run each VLM notebook with `certvic_polarity_ablations.zip`, `RUN_TAG=polarity`.
4. Mechanism probes: run each VLM notebook with `certvic_mechanism_probes.zip`, `RUN_TAG=mechanism`; `original_vs_edited` is SPEC_BLOCKED and excluded.
5. Later Main-500: only after the above and go/no-go gates, use `diffusion_main_scale_T4x2_TEMPLATE.ipynb`.

Provider notebooks:

- `notebooks/kaggle/vlm_qwen2_5_vl_7b_T4x2_parallel.ipynb`
- `notebooks/kaggle/vlm_internvl_8b_T4x2_parallel.ipynb`
- `notebooks/kaggle/vlm_llava_onevision_7b_T4x2_parallel.ipynb`

Every VLM notebook writes shard predictions, shard logs, a deterministic merged
prediction JSONL, `summary_<provider>_<run_tag>.json`,
`runtime_manifest_<provider>_<run_tag>.json`, and `<provider>_<run_tag>_preds.zip`.
