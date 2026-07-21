# Scale & Budget Plan — 2000 items

Generated: 2026-06-22

Conservative estimate under free Kaggle/Colab limits. No inference run; no claims.

**Bottleneck: `free_gpu_quota`**

## GPU

- Edit generation: 11.11 GPU-h (5000 candidates)
- VLM inference: 15.0 GPU-h (3 models × 2 variants × 1.5× ablations)
- Total: 26.11 GPU-h
- Free GPU quota: 30.0 h/week → **0.87 week(s)** wall-clock

## Human review

- 16.67 h at 30.0 s/item
- At 3.0 h/day → 5.6 day(s) (~0.79 week(s))

## CPU & storage

- CPU work: 0.278 h
- Working storage: 1.776 GB (fits Kaggle ~20 GB: True)
- WARNING: rejected-edit pixels exceed kept-edit pixels; record hashes then delete rejected pixels to reclaim disk

## Recommended per-session batch sizes

- Edit items / Kaggle session: 5175
- VLM images / Kaggle session: 13800
- VLM images / Colab session: 9600
