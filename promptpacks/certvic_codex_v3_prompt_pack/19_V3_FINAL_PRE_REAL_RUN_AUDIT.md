# CertVIC Codex V3 Prompt 19 — Final Pre-Real-Run Audit


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

Create final V3 audit. After this passes, stop building and run real data.

## Inspect first

All V3 modules and V2 audits.

## Build / modify

Create `certvic/v3/final_pre_real_run_audit.py` and package init. Check imports, handoff docs, zero-cost policy, paper guard, reviewer harness, no paid providers, no fake numbers, no evidence from simulated artifacts.

## CLI commands to add or verify

`python3 -m certvic.v3.final_pre_real_run_audit --out docs/V3_FINAL_PRE_REAL_RUN_AUDIT_REPORT.md --json-out data/results/v3_final_pre_real_run_audit.json`

## Outputs / behavior

Output exact stop/build guidance and exact next real-run command.

## Tests

Create or update:

`tests/test_v3_final_pre_real_run_audit.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/V3_FINAL_PRE_REAL_RUN_AUDIT_REPORT.md`, `docs/V3_STOP_BUILDING_START_RUNNING.md`, `docs/V3_COMMAND_INDEX.md`; update next actions.

## Extra notes

This is the final infrastructure gate.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
