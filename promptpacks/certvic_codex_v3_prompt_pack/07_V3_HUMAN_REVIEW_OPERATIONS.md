# CertVIC Codex V3 Prompt 07 — Human Review Operations


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

Scale the visual review process: reviewer batching, overlap for IAA, progress tracking, disagreement resolution, adjudication.

## Inspect first

Visual review export/aggregate/apply modules, IAA.

## Build / modify

Create `certvic/validation/review_batches.py`, `review_progress.py`, `adjudicate_review.py`. Balance by family/edit type; assign overlap; report missing ratings and disagreements.

## CLI commands to add or verify

`python3 -m certvic.validation.review_batches --tasks data/manifests/pilot_eval_tasks_tiny.jsonl --out-dir data/annotations/review_batches --reviewers reviewer_a reviewer_b --overlap-rate 0.2 --seed 0`

`python3 -m certvic.validation.review_progress --ratings-dir data/annotations/review_batches --out data/annotations/review_progress.json`

`python3 -m certvic.validation.adjudicate_review --ratings data/annotations/visual_review_ratings.csv --out data/annotations/visual_review_adjudicated.csv`

## Outputs / behavior

Estimate reviewer workload and wall-clock time. No paid annotation services.

## Tests

Create or update:

`tests/test_v3_human_review_ops.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/HUMAN_REVIEW_OPERATIONS.md`, `docs/V3_HUMAN_REVIEW_OPS_REPORT.md`; update data card and repro docs.

## Extra notes

Human review is likely the bottleneck at 1k–2k scale.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
