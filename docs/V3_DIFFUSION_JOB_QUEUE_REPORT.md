# V3 Prompt 04 — Diffusion Job Queue and Resume Planner Report

## Goal

Plan future diffusion edit generation so free GPU sessions can shard, resume,
retry, and avoid duplicates.

## What was built

- `certvic/edit/job_queue.py` — `QueueEntry` schema (job_id, edit_id, source_id, mask_id, edit_type, engine, priority, shard_id, retry_count, status, expected_output_path, config_hash, evidence_status=`JOB_PLANNED_ONLY`); `build_queue` (deterministic hash sharding), `verify_sharding` (complete + no-overlap), `queue_status` (all seven statuses from generated/rejected manifests + on-disk hash checks), `next_shard`; CLI subcommands `build` / `status` / `next-shard`.
- `certvic/edit/diffusion_resume.py` — `resume_plan` re-queues incomplete jobs (pending/failed/missing_output/hash_mismatch), increments `retry_count`, and flags retry-exhausted jobs; orders by priority then shard.
- `certvic/edit/edit_generation_plan.py` — combined progress report (completion %, per-shard, per-edit-type, sharding check) + markdown renderer.

## Tests

`tests/test_v3_diffusion_job_queue.py` — 11 tests: build positive path, unknown-engine rejection, sharding complete + no overlap, next-shard partition + bad-index error, all seven statuses exercised (generated/duplicate/missing_output/hash_mismatch/failed/rejected/pending), pending-when-empty, resume picks incomplete + increments retry, resume gives up after max retries, progress report renders, and a no-heavy-import guard.

## Verification

- `python3 -m pytest -q` — full suite green (297 passed; was 286).
- CLI smoke on a 13-row synthetic edit plan: `build` (4 shards, complete/no-overlap), `next-shard 0` (5 jobs), `status` (13 pending), `diffusion_resume` (13 to run), `edit_generation_plan` (progress report). All clean.

## Evidence / cost discipline

No generation, no GPU, no downloads, no paid services, no evidence claims. No
heavy imports (torch/diffusers/cv2 absent). Importing `certvic.edit.engines` for
engine constants pulls only core numpy/PIL, never the heavy stack.

## Status

**PASSED.**

## Remaining blockers

None. The queue is exercised against a synthetic plan; it operates on the real
`data/manifests/pilot_edit_plan.jsonl` once a pilot edit plan is generated.
