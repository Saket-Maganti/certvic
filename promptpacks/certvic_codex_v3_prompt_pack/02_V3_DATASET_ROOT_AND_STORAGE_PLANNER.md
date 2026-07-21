# CertVIC Codex V3 Prompt 02 — Dataset Root and Storage Planner


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

Prevent disk blowups, private-path leaks, broken symlinks, duplicate output roots, and release packaging mistakes before large studies.

## Inspect first

ADE20K adapter, release artifact builder, license policy, real pilot config, data card.

## Build / modify

Create `certvic/storage/plan_storage.py`, `path_policy.py`, `dataset_roots.py`. Estimate storage for masks, edits, rejected edits, review galleries, predictions, reports, release artifacts, and checkpoints.

## CLI commands to add or verify

`python3 -m certvic.storage.plan_storage --config configs/real_pilot_ade20k.yaml --scale 200 --out data/results/storage_plan_200.json`

`python3 -m certvic.storage.plan_storage --config configs/real_pilot_ade20k.yaml --scale 2000 --out data/results/storage_plan_2000.json`

`python3 -m certvic.storage.dataset_roots --out data/results/dataset_root_policy.md`

## Outputs / behavior

Detect absolute private paths, symlink escapes, unsafe overwrite roots, special characters that break Kaggle, release path leaks, and scale-dependent storage warnings.

## Tests

Create or update:

`tests/test_v3_storage_planner.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/STORAGE_AND_PATH_POLICY.md`, `docs/V3_STORAGE_PLANNING_REPORT.md`; update `docs/DATA_CARD.md`, `docs/ZERO_COST_POLICY.md`, `docs/REPRO.md`.

## Extra notes

No real dataset scanning unless a root is explicitly passed later.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
