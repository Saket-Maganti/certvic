# CertVIC Codex V4 Prompt 09 — Real Run Recovery and Repair

Do not initialize git. Do not create commits/tags. Do not use paid services. Do not download datasets/model weights. Do not run GPU jobs. Do not run VLM inference in tests. Do not fabricate results or paper claims.

## Goal

Add tools to repair partial runs, missing sidecars, interrupted shards, broken manifests, and duplicate outputs.

This is V4 run-later infrastructure. It should help the user execute real ADE20K/diffusion/VLM work after coding limits expire.

## Inspect first

Before editing, inspect the nearest existing modules and docs from V2/V3, especially:
- `docs/V3_COMMAND_INDEX.md`
- `docs/V3_STOP_BUILDING_START_RUNNING.md`
- `certvic/v3/final_pre_real_run_audit.py`
- relevant modules for this subsystem

## Build

Create or update:
- `certvic/recovery/__init__.py`
- `certvic/recovery/inspect_run.py`
- `certvic/recovery/repair_manifests.py`
- `certvic/recovery/rebuild_sidecars.py`

## CLI commands

Add CLI support for:
- `python3 -m certvic.recovery.inspect_run --run-dir data/results/tiny_real_pilot --out data/results/recovery_report.json`
- `python3 -m certvic.recovery.repair_manifests --input broken.jsonl --out repaired.jsonl --dry-run`

## Expected outputs

Produce:
- `recovery report`
- `repair plan`
- `sidecar rebuild dry-run`

## Required behavior

- Preserve backward compatibility.
- Never execute real GPU/model/data jobs during tests.
- Mark planned/simulated outputs as non-evidence.
- Keep private paths anonymizable.
- Keep heavy imports optional and lazy.
- Provide clear failure messages and dry-run behavior where appropriate.

## Tests

Add a test file named approximately:

`tests/test_v4_v4_real_run_recovery_and_repair.py`

Tests must verify:
- dry-run default
- hash mismatches not silently fixed
- duplicates detected
- sidecars reconstructed only from available metadata

## Docs

Create a handoff doc:

`docs/V4_V4_REAL_RUN_RECOVERY_AND_REPAIR_REPORT.md`

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
