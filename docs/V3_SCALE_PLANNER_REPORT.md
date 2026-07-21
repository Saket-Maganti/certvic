# V3 Prompt 10 — Scale Planner and Free-Compute Budget Report

## Goal

Estimate runtime/storage/human bottlenecks for 200/1k/2k studies under free
Kaggle/Colab limits.

## What was built

- `certvic/planning/free_compute_budget.py` — free-tier envelopes (Kaggle ~30 GPU-h/week, ~11.5 h sessions; Colab ~8 h), conservative per-stage rate defaults, and `wall_clock_weeks` / `session_batch_size` helpers.
- `certvic/planning/scale_planner.py` — `plan_scale` combining GPU (edit + VLM), CPU, human time/days, wall-clock-under-quota, storage (reuses `certvic.storage.plan_storage`), bottleneck identification (free GPU quota / human review / storage), and recommended per-session batch sizes; configurable overrides; markdown + JSON report.

## Tests

`tests/test_v3_scale_planner.py` — 10 tests: param merge (None ignored), wall-clock/batch helpers, scale monotonicity, components present, override changes GPU estimate, human-review bottleneck, storage bottleneck at huge scale, report rendering, CLI md+json output, no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (356 passed; was 346).
- CLI smoke: 200 items ≈ 2.6 GPU-h / ~1.7 human-h / 0.18 GB; 2000 items ≈ 26.1 GPU-h (~0.87 weeks at 30 h/week) / ~16.7 human-h (~5.6 days) / 1.8 GB; bottleneck `free_gpu_quota` in both.

## Evidence / cost discipline

Conservative (not optimistic) estimates. No inference, no downloads, no paid
services; `evidence_claims_made=false`, `vlm_inference_run=false`. No heavy imports.

## Status

**PASSED.**

## Remaining blockers

None. Re-run with measured per-item rates after the first tiny real run for a
precise budget.
