# CertVIC Codex V3 Prompt 08 — Model Run Orchestration Matrix


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

Plan future open-model eval runs: providers × shards × prompts × tasks with resume commands and status tracking.

## Inspect first

Run eval, VLM preflight, provider registry, Kaggle VLM config.

## Build / modify

Create `certvic/eval/model_matrix.py`, `run_matrix_planner.py`, `run_status.py`. Include provider metadata, memory estimates, shard plan, commands, sidecar expectations, no paid providers.

## CLI commands to add or verify

`python3 -m certvic.eval.run_matrix_planner --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --providers qwen2_5_vl_7b internvl_8b llava_onevision_7b --out-dir data/results/model_run_matrix --max-items 200 --num-shards 4`

`python3 -m certvic.eval.run_status --matrix data/results/model_run_matrix/run_matrix.json --pred-root data/predictions --out data/results/model_run_matrix/status.json`

## Outputs / behavior

Generate commands with resume/max-items/shard flags. Detect missing/completed predictions.

## Tests

Create or update:

`tests/test_v3_model_run_matrix.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/MODEL_RUN_MATRIX.md`, `docs/V3_MODEL_RUN_MATRIX_REPORT.md`; update Kaggle VLM docs.

## Extra notes

This reduces wasted free GPU inference sessions.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
