# CertVIC Codex V4 Prompt 10 — Prediction Merge and Dedup

Do not initialize git. Do not create commits/tags. Do not use paid services. Do not download datasets/model weights. Do not run GPU jobs. Do not run VLM inference in tests. Do not fabricate results or paper claims.

## Goal

Build robust merging/deduplication for sharded VLM prediction outputs.

This is V4 run-later infrastructure. It should help the user execute real ADE20K/diffusion/VLM work after coding limits expire.

## Inspect first

Before editing, inspect the nearest existing modules and docs from V2/V3, especially:
- `docs/V3_COMMAND_INDEX.md`
- `docs/V3_STOP_BUILDING_START_RUNNING.md`
- `certvic/v3/final_pre_real_run_audit.py`
- relevant modules for this subsystem

## Build

Create or update:
- `certvic/eval/merge_predictions.py`
- `certvic/eval/prediction_dedup.py`

## CLI commands

Add CLI support for:
- `python3 -m certvic.eval.merge_predictions --pred-dirs data/predictions/shards --out data/predictions/merged.jsonl --report data/results/merge_report.json`

## Expected outputs

Produce:
- `merged predictions`
- `duplicates.csv`
- `missing_items.csv`
- `merge_report.md`

## Required behavior

- Preserve backward compatibility.
- Never execute real GPU/model/data jobs during tests.
- Mark planned/simulated outputs as non-evidence.
- Keep private paths anonymizable.
- Keep heavy imports optional and lazy.
- Provide clear failure messages and dry-run behavior where appropriate.

## Tests

Add a test file named approximately:

`tests/test_v4_v4_prediction_merge_and_dedup.py`

Tests must verify:
- duplicate policy explicit
- conflicting predictions flagged
- missing tasks detected
- mock/evidence statuses preserved

## Docs

Create a handoff doc:

`docs/V4_V4_PREDICTION_MERGE_AND_DEDUP_REPORT.md`

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
