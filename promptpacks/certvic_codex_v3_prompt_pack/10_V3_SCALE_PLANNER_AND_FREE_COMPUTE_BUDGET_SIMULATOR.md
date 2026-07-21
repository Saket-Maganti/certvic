# CertVIC Codex V3 Prompt 10 — Scale Planner and Free-Compute Budget Simulator


## Global constraints

- Work in `/Users/saketmaganti/Projects/certVIC`.
- Do not initialize git, commit, or tag.
- Do not use paid APIs, paid cloud, paid datasets, paid annotation, paid credits, or paid tracking.
- Do not download large datasets or model weights.
- Do not run GPU jobs or VLM inference in tests.
- Do not fabricate results or insert fake paper numbers.
- Keep heavy dependencies optional and import-safe.
- Normal tests must run locally without GPU.
- Simulated/pre-run artifacts must be marked non-evidence and blocked from claims.
- Preserve backward compatibility and run `python3 -m pytest -q`.

## Goal

Estimate runtime/storage/human bottlenecks for 200/1k/2k studies under free Kaggle/Colab limits.

## Inspect first

Existing power plan, scale docs, runbooks.

## Build / modify

Create `certvic/planning/scale_planner.py` and `free_compute_budget.py`. Include configurable overgeneration, edit seconds, VLM seconds, models, ablation multiplier, human seconds per item, weekly free GPU hours.

## CLI commands to add or verify

`python3 -m certvic.planning.scale_planner --scale 200 --out data/results/scale_plan_200.md`

`python3 -m certvic.planning.scale_planner --scale 2000 --out data/results/scale_plan_2000.md`

## Outputs / behavior

Outputs CPU time, GPU time, human time, wall-clock under quota, storage estimate, bottleneck, batch sizes.

## Tests

Create or update:

`tests/test_v3_scale_planner.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/SCALE_AND_BUDGET_PLAN.md`, `docs/V3_SCALE_PLANNER_REPORT.md`; update next-actions docs.

## Extra notes

Add realistic estimates, not optimistic ones.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
