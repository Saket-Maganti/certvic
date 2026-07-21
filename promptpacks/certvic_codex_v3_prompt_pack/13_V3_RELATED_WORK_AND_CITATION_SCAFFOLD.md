# CertVIC Codex V3 Prompt 13 — Related Work and Citation Scaffold


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

Create a non-fabricating related-work matrix and citation audit. No invented citations or unsupported novelty claims.

## Inspect first

Paper related section and paper plan.

## Build / modify

Create `paper/related_work_matrix.yaml`, `docs/RELATED_WORK_PLAN.md`, `docs/CITATION_TODO.md`, `certvic/paper/related_work_audit.py`.

## CLI commands to add or verify

`python3 -m certvic.paper.related_work_audit --matrix paper/related_work_matrix.yaml --paper paper/sections/02_related.tex --out docs/RELATED_WORK_AUDIT.md`

## Outputs / behavior

Categories: VLM eval, counterfactual/minimal-pair VQA, causal visual reasoning, editing for evaluation, robustness/consistency, anytime-valid inference, licensing/artifacts, budgeted evaluation.

## Tests

Create or update:

`tests/test_v3_related_work_audit.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/V3_RELATED_WORK_SCAFFOLD_REPORT.md`; update `docs/PAPER_PLAN.md`.

## Extra notes

Codex should not browse or fabricate; leave TODOs.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
