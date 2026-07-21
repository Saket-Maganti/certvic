# CertVIC Codex V4 Prompt 12 — Statistical Sensitivity Suite

Do not initialize git. Do not create commits/tags. Do not use paid services. Do not download datasets/model weights. Do not run GPU jobs. Do not run VLM inference in tests. Do not fabricate results or paper claims.

## Goal

Add post-score sensitivity checks around thresholds, alpha, parse handling, clustering, and optional stopping.

This is V4 run-later infrastructure. It should help the user execute real ADE20K/diffusion/VLM work after coding limits expire.

## Inspect first

Before editing, inspect the nearest existing modules and docs from V2/V3, especially:
- `docs/V3_COMMAND_INDEX.md`
- `docs/V3_STOP_BUILDING_START_RUNNING.md`
- `certvic/v3/final_pre_real_run_audit.py`
- relevant modules for this subsystem

## Build

Create or update:
- `certvic/metrics/sensitivity_suite.py`
- `certvic/reporting/sensitivity_report.py`

## CLI commands

Add CLI support for:
- `python3 -m certvic.metrics.sensitivity_suite --scores data/results/pair_scores.jsonl --out-dir data/results/stat_sensitivity`

## Expected outputs

Produce:
- `alpha grid`
- `gap threshold grid`
- `parse handling sensitivity`
- `cluster sensitivity summary`

## Required behavior

- Preserve backward compatibility.
- Never execute real GPU/model/data jobs during tests.
- Mark planned/simulated outputs as non-evidence.
- Keep private paths anonymizable.
- Keep heavy imports optional and lazy.
- Provide clear failure messages and dry-run behavior where appropriate.

## Tests

Add a test file named approximately:

`tests/test_v4_v4_statistical_sensitivity_suite.py`

Tests must verify:
- bootstrap never certification
- CS status clear
- simulated/mock blocked
- threshold conclusions labeled

## Docs

Create a handoff doc:

`docs/V4_V4_STATISTICAL_SENSITIVITY_SUITE_REPORT.md`

Also update relevant docs:
- `docs/REPRO.md`
- `docs/V3_COMMAND_INDEX.md` or create/update `docs/V4_COMMAND_INDEX.md`
- any subsystem-specific doc needed for future execution

## Run

Run:

`python3 -m pytest -q`

If available and relevant, smoke-test the new CLI in dry-run mode.

## Final response

Report:
- files changed
- tests added/updated
- commands added
- docs added/updated
- exact tests run
- whether this V4 prompt passed
- next prompt to run
