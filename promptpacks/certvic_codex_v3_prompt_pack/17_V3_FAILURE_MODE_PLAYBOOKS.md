# CertVIC Codex V3 Prompt 17 — Failure Mode Playbooks


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

Create operational playbooks for what to do when real runs fail.

## Inspect first

Risk register, next actions, existing report outputs.

## Build / modify

Create docs/playbooks for edit realism failure, no gap, high parse failure, high control flips, low human agreement, Kaggle failure, label policy failure, claim gate failure. Create `certvic/playbooks/diagnose_failure.py`.

## CLI commands to add or verify

`python3 -m certvic.playbooks.diagnose_failure --report-dir data/results/tiny_real_pilot --out docs/playbooks/DIAGNOSIS.md`

## Outputs / behavior

Map symptoms to playbooks: low quality pass, high detectability, high parse failure, high control flip, no certified gap, low original accuracy, low human agreement, too few candidates, GPU preflight failure.

## Tests

Create or update:

`tests/test_v3_failure_playbooks.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/V3_FAILURE_PLAYBOOKS_REPORT.md`; update risk register and next-actions.

## Extra notes

This prevents panic during real runs.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
