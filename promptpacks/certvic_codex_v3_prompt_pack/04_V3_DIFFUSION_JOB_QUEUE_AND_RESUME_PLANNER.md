# CertVIC Codex V3 Prompt 04 — Diffusion Job Queue and Resume Planner


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

Plan future diffusion edit generation so free GPU sessions can shard, resume, retry, and avoid duplicates.

## Inspect first

Edit generation, edit engines, diffusion preflight, quality gates, provenance if present.

## Build / modify

Create `certvic/edit/job_queue.py`, `diffusion_resume.py`, `edit_generation_plan.py`. Queue fields: job_id, edit_id, source_id, mask_id, edit_type, engine, priority, shard_id, retry_count, status, expected_output_path, config_hash, evidence_status=JOB_PLANNED_ONLY.

## CLI commands to add or verify

`python3 -m certvic.edit.job_queue build --edit-plan data/manifests/pilot_edit_plan.jsonl --out data/manifests/diffusion_job_queue.jsonl --shards 4`

`python3 -m certvic.edit.job_queue status --queue data/manifests/diffusion_job_queue.jsonl --generated data/manifests/pilot_generated_edits.jsonl --out data/results/diffusion_job_status.json`

`python3 -m certvic.edit.job_queue next-shard --queue data/manifests/diffusion_job_queue.jsonl --shard-index 0 --num-shards 4 --out data/manifests/diffusion_job_shard_0.jsonl`

## Outputs / behavior

Statuses: pending, generated, rejected, failed, duplicate, missing_output, hash_mismatch. Sharding complete/no-overlap. Heavy imports forbidden.

## Tests

Create or update:

`tests/test_v3_diffusion_job_queue.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/DIFFUSION_JOB_QUEUE.md`, `docs/V3_DIFFUSION_JOB_QUEUE_REPORT.md`; update `docs/PILOT_ADE20K.md`.

## Extra notes

Critical before Kaggle because free sessions die often.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
