# CertVIC Codex V3 Prompt 18 — Main Study Orchestrator Dry Run


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

Plan the full 200/1k/2k study without executing GPU/VLM jobs.

## Inspect first

Tiny pilot orchestrator, main runbook, gate checks, model matrix, scale planner.

## Build / modify

Create `certvic/pipeline/main_study_plan.py` and `main_study_dry_run.py`.

## CLI commands to add or verify

`python3 -m certvic.pipeline.main_study_dry_run --scale 200 --out-dir data/results/main_study_dry_run_200`

`python3 -m certvic.pipeline.main_study_dry_run --scale 2000 --out-dir data/results/main_study_dry_run_2000`

## Outputs / behavior

Outputs stage_plan.json, commands.sh, required_inputs.md, expected_outputs.md, gate_sequence.md, runtime_estimates.md, report.md.

## Tests

Create or update:

`tests/test_v3_main_study_dry_run.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/MAIN_STUDY_DRY_RUN.md`, `docs/V3_MAIN_STUDY_DRY_RUN_REPORT.md`; update main pilot runbook.

## Extra notes

No execution, only planning.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
