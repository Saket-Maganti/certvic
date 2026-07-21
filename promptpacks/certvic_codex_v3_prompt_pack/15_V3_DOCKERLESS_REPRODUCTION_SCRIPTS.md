# CertVIC Codex V3 Prompt 15 — Dockerless Reproduction Scripts


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

Prepare normal-shell reproduction scripts for smoke, simulation, dry-run, and reports without Docker or downloads by default.

## Inspect first

Release/repro docs and commands.

## Build / modify

Create scripts: `scripts/reproduce_smoke.sh`, `scripts/reproduce_simulation.sh`, `scripts/reproduce_tiny_pilot_dry_run.sh`, `scripts/reproduce_reports.sh`; create `certvic/release/reproduction_audit.py`.

## CLI commands to add or verify

`python3 -m certvic.release.reproduction_audit --scripts scripts --out docs/REPRODUCTION_AUDIT.md`

## Outputs / behavior

Scripts use `set -euo pipefail`, avoid paid markers, no destructive rm -rf, and document required user-provided paths.

## Tests

Create or update:

`tests/test_v3_reproduction_scripts.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/DOCKERLESS_REPRODUCTION.md`, `docs/V3_DOCKERLESS_REPRODUCTION_REPORT.md`; update `docs/REPRO.md`.

## Extra notes

No Docker requirement; Kaggle-friendly.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
