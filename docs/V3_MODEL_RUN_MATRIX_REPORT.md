# V3 Prompt 08 — Model Run Orchestration Matrix Report

## Goal

Plan future open-model eval runs: providers × shards × prompts × tasks with
resume commands and status tracking.

## What was built

- `certvic/eval/model_matrix.py` — `build_matrix` over providers × prompt variants × shards; per-provider metadata + full/4-bit GPU memory estimates; stable run_ids; expected output path + three `run_eval` sidecars; resumable command per cell; paid-provider rejection; evidence-eligibility flag; `commands_sh` renderer.
- `certvic/eval/run_matrix_planner.py` — CLI writing `run_matrix.json`, `commands.sh`, `model_run_matrix_report.md`.
- `certvic/eval/run_status.py` — reads the matrix + predictions root, marks each cell completed (non-empty predictions + all sidecars) or missing, emits resume commands, per-provider breakdown, markdown report.

## Tests

`tests/test_v3_model_run_matrix.py` — 10 tests: matrix dimensions + resumable command flags + sidecar list; prompt variants multiply cells; paid provider rejection; evidence-eligibility flag (open-local vs mock); 4-bit memory estimate; invalid shards/empty providers; planner artifact writing; status detects completed vs missing with resume commands; partial-output-without-sidecars counts as missing; no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (336 passed; was 326).
- CLI smoke: planned a 12-cell matrix (3 providers × 4 shards), all detected missing with resume commands; generated `run_eval` command verified to carry `--max-items`, `--shard-index`, `--num-shards`, `--evidence-run`.

## Evidence / cost discipline

No inference, no downloads, no GPU, no paid providers (rejected at build time).
All result dicts carry `vlm_inference_run=false` / `evidence_claims_made=false`.
No heavy imports.

## Status

**PASSED.**

## Remaining blockers

None. Prompt variants default to `["default"]`; once a prompt suite is finalized
(`certvic.eval.prompt_suite`), pass `--prompt-variants` to expand the matrix.
