# Kaggle T4x2 parallel VLM remaining runs

Use one provider notebook per Kaggle session with GPU T4 x2 and Internet ON.
Attach the CertVIC code bundle plus exactly one remaining task bundle. The
notebooks split rows deterministically into shard0/shard1, launch two subprocess
workers when memory-safe, set `CUDA_VISIBLE_DEVICES=0` for shard0 and
`CUDA_VISIBLE_DEVICES=1` for shard1, resume complete shard outputs, merge with
duplicate checks, write summaries, and zip only predictions/logs/manifests.

Required notebooks:

- `notebooks/kaggle/vlm_qwen2_5_vl_7b_T4x2_parallel.ipynb`
- `notebooks/kaggle/vlm_internvl_8b_T4x2_parallel.ipynb`
- `notebooks/kaggle/vlm_llava_onevision_7b_T4x2_parallel.ipynb`

Supported `RUN_TAG` values: `spurious`, `perception_scaled`, `polarity`, `mechanism`.
The mechanism bundle excludes and the notebooks refuse `original_vs_edited`
when marked SPEC_BLOCKED.

The optional unified router notebook is intentionally not generated; the
provider-specific notebooks are more transparent and easier to debug.
