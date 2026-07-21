# Kaggle shard plan template — main_500 (PROJECTION, free-tier only)

Target reviewed-approved items: **500** (projection).
- Source candidates to select: ~1100
- Planned edits: ~924
- Diffusion GPU sessions (T4, ~9.0h each): **1**
- VLM GPU sessions per model: **1** (×3 models = 3)
- Human review: ~23.6 h · Storage: ~121.9 MB · Cost: $0

## Diffusion shards
Split ~924 edits across 1 session(s); reuse scripts/split_edit_plan_by_shard.py and notebooks/kaggle/certvic_main200_diffusion_T4x2.ipynb.

## VLM shards (per provider)
Reuse notebooks/kaggle/certvic_main200_vlm_T4x2_AFTER_GATES.ipynb; one shard plan per provider in {qwen2_5_vl_7b, internvl_8b, llava_onevision_7b}.

## Gate order (do not skip)
1. detectability + quality gate (GO/conditional/confounded per detectability_gate)
2. human visual review + residual-cue review
3. spurious-flip specificity control MUST pass before treating scale as evidence
4. result-ledger hash audit
