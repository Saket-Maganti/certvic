# CertVIC Codex V4 Prompt 01 — Real Run Command Generator

Do not initialize git. Do not create commits/tags. Do not use paid services. Do not download datasets/model weights. Do not run GPU jobs. Do not run VLM inference in tests. Do not fabricate results or paper claims.

## Goal

Create a command-generation system that emits exact shell scripts for V3/V4 execution stages without running them.

This is V4 run-later infrastructure. It should help the user execute real ADE20K/diffusion/VLM work after coding limits expire.

## Inspect first

Before editing, inspect the nearest existing modules and docs from V2/V3, especially:
- `docs/V3_COMMAND_INDEX.md`
- `docs/V3_STOP_BUILDING_START_RUNNING.md`
- `certvic/v3/final_pre_real_run_audit.py`
- relevant modules for this subsystem

## Build

Create or update:
- `certvic/commands/__init__.py`
- `certvic/commands/generate_real_run_commands.py`
- `certvic/commands/command_manifest.py`

## CLI commands

Add CLI support for:
- `python3 -m certvic.commands.generate_real_run_commands --stage tiny_pilot --out-dir commands/tiny_pilot`
- `python3 -m certvic.commands.generate_real_run_commands --stage main_200 --out-dir commands/main_200`
- `python3 -m certvic.commands.generate_real_run_commands --stage full_2000 --out-dir commands/full_2000`

## Expected outputs

Produce:
- `commands.sh`
- `commands.md`
- `command_manifest.json`
- `expected_inputs.md`
- `expected_outputs.md`
- `resume_notes.md`

## Required behavior

- Preserve backward compatibility.
- Never execute real GPU/model/data jobs during tests.
- Mark planned/simulated outputs as non-evidence.
- Keep private paths anonymizable.
- Keep heavy imports optional and lazy.
- Provide clear failure messages and dry-run behavior where appropriate.

## Tests

Add a test file named approximately:

`tests/test_v4_v4_real_run_command_generator.py`

Tests must verify:
- commands include max-items/resume/safety flags
- no command executes during generation
- paid providers rejected
- absolute private paths parameterized
- all stages represented

## Docs

Create a handoff doc:

`docs/V4_V4_REAL_RUN_COMMAND_GENERATOR_REPORT.md`

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
