# CertVIC Codex V3 Prompt 05 — Edit Detectability Probe


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

Build a CPU-only artifact-risk probe: can cheap low-level features distinguish original from edited images? If yes, VLM gap may be artifact-confounded.

## Inspect first

Quality gates, materialized tasks, failure gallery, review reports.

## Build / modify

Create `certvic/validation/edit_detectability.py` and `certvic/reporting/edit_detectability_report.py`. Use file size, histogram distance, edge density, blur/sharpness, color stats, outside-mask change, sklearn classifier if available, deterministic fallback if not.

## CLI commands to add or verify

`python3 -m certvic.validation.edit_detectability --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --out-dir data/results/edit_detectability`

## Outputs / behavior

Outputs: detectability_summary.json, features.csv, report.md, highly_detectable_items.jsonl. Mark descriptive construct-validity diagnostic, never evidence by itself.

## Tests

Create or update:

`tests/test_v3_edit_detectability.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/EDIT_DETECTABILITY_PROBE.md`, `docs/V3_EDIT_DETECTABILITY_REPORT.md`; update risk register and claim ledger.

## Extra notes

This is one of the most important CVPR reviewer defenses.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
