# CertVIC Codex V3 Prompt 14 — Rebuttal and Reviewer Simulation Kit


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

Generate harsh simulated reviews and rebuttal prep from current artifacts, complaining honestly about missing results when absent.

## Inspect first

Reviewer attacks docs, paper scaffold, reports root.

## Build / modify

Create `certvic/review/simulate_reviews.py` and `rebuttal_pack.py`.

## CLI commands to add or verify

`python3 -m certvic.review.simulate_reviews --paper-dir paper --reports-root data/results --out-dir docs/reviewer_simulation`

`python3 -m certvic.review.rebuttal_pack --reviews docs/reviewer_simulation/reviews.json --out docs/rebuttal_pack.md`

## Outputs / behavior

Reviewer profiles: benchmark skeptic, stats reviewer, vision/editing reviewer, reproducibility reviewer, construct-validity reviewer, open-model-scope reviewer.

## Tests

Create or update:

`tests/test_v3_reviewer_simulation.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/REBUTTAL_PREP.md`, `docs/V3_REVIEWER_SIMULATION_REPORT.md`; update reviewer attacks doc.

## Extra notes

If results missing, reviewer must complain, not hallucinate.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
