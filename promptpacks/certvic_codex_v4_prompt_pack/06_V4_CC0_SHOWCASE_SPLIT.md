# CertVIC Codex V4 Prompt 06 — CC0 Showcase Split

Do not initialize git. Do not create commits/tags. Do not use paid services. Do not download datasets/model weights. Do not run GPU jobs. Do not run VLM inference in tests. Do not fabricate results or paper claims.

## Goal

Build tooling for a small redistributable CC0/PD showcase split for paper figures and artifact demos.

This is V4 run-later infrastructure. It should help the user execute real ADE20K/diffusion/VLM work after coding limits expire.

## Inspect first

Before editing, inspect the nearest existing modules and docs from V2/V3, especially:
- `docs/V3_COMMAND_INDEX.md`
- `docs/V3_STOP_BUILDING_START_RUNNING.md`
- `certvic/v3/final_pre_real_run_audit.py`
- relevant modules for this subsystem

## Build

Create or update:
- `certvic/data/showcase_split.py`
- `certvic/release/showcase_package.py`

## CLI commands

Add CLI support for:
- `python3 -m certvic.data.showcase_split --sources data/manifests/cc0_sources.jsonl --out data/manifests/showcase_split.jsonl`
- `python3 -m certvic.release.showcase_package --split data/manifests/showcase_split.jsonl --out-dir release/showcase`

## Expected outputs

Produce:
- `showcase manifest`
- `release checklist`
- `license summary`

## Required behavior

- Preserve backward compatibility.
- Never execute real GPU/model/data jobs during tests.
- Mark planned/simulated outputs as non-evidence.
- Keep private paths anonymizable.
- Keep heavy imports optional and lazy.
- Provide clear failure messages and dry-run behavior where appropriate.

## Tests

Add a test file named approximately:

`tests/test_v4_v4_cc0_showcase_split.py`

Tests must verify:
- only CC0/PD allowed
- non-redistributable rows rejected
- no pixels copied unless explicit
- figure-use flags

## Docs

Create a handoff doc:

`docs/V4_V4_CC0_SHOWCASE_SPLIT_REPORT.md`

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
