# CertVIC Codex V3 Prompt 11 — Static Local Run Dashboard


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

Generate a local static HTML dashboard for runs, metrics, quality gates, review progress, artifact status, and claim eligibility.

## Inspect first

Reporting modules, dashboard-like artifacts, run ledger if present.

## Build / modify

Create `certvic/dashboard/build_dashboard.py`. Static HTML/JSON only, no external services, no JS framework required.

## CLI commands to add or verify

`python3 -m certvic.dashboard.build_dashboard --results-root data/results --out-dir data/dashboard`

## Outputs / behavior

Pages: index, runs, quality, review, metrics, claims, artifacts. Highlight missing gates and non-evidence flags.

## Tests

Create or update:

`tests/test_v3_dashboard.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/LOCAL_DASHBOARD.md`, `docs/V3_DASHBOARD_REPORT.md`; update `docs/REPRO.md`.

## Extra notes

No pixel copying by default.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
