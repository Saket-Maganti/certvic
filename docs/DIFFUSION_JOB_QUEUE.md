# Diffusion Edit-Generation Job Queue (V3)

Free GPU sessions die often. This turns a planned edit plan into a shardable,
resumable, retry-aware job queue so generation can be split across sessions,
resumed after a crash, and kept duplicate-free. Bookkeeping only — no image
generation, no GPU, no heavy imports (no torch/diffusers/cv2). Queue entries are
`JOB_PLANNED_ONLY` and never evidence.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.edit.job_queue` | Build queue, compute status, emit per-shard jobs. |
| `certvic.edit.diffusion_resume` | Compute the (re)run set after a crash; retry bookkeeping. |
| `certvic.edit.edit_generation_plan` | Combined progress report (completion, per-shard, by edit type). |

## Queue entry fields

`job_id`, `edit_id`, `source_id`, `mask_id`, `edit_type`, `engine`, `priority`,
`shard_id`, `retry_count`, `status`, `expected_output_path`, `config_hash`,
`evidence_status` (`JOB_PLANNED_ONLY`).

Sharding is deterministic (`stable_int_hash(edit_id) % num_shards`), so it is
**complete** (every job assigned) and **non-overlapping** (one shard per job) by
construction; `verify_sharding` checks this. Priority runs core interventions
(remove → occlude → displace) before controls.

## Statuses

`pending`, `generated`, `rejected`, `failed`, `duplicate`, `missing_output`,
`hash_mismatch`. Incomplete statuses (`pending`, `failed`, `missing_output`,
`hash_mismatch`) are what the resume planner re-queues; `rejected` and
`duplicate` are terminal. `hash_mismatch` / `missing_output` catch a partially
written or corrupted output from a killed session.

## Commands

```bash
# Build a 4-shard queue from the edit plan.
python3 -m certvic.edit.job_queue build \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --out data/manifests/diffusion_job_queue.jsonl --shards 4

# Emit one shard for a single GPU worker/session.
python3 -m certvic.edit.job_queue next-shard \
  --queue data/manifests/diffusion_job_queue.jsonl \
  --shard-index 0 --num-shards 4 \
  --out data/manifests/diffusion_job_shard_0.jsonl

# After (or during) a run, compute completion.
python3 -m certvic.edit.job_queue status \
  --queue data/manifests/diffusion_job_queue.jsonl \
  --generated data/manifests/pilot_generated_edits.jsonl \
  --rejected data/manifests/pilot_generated_edits_rejected.jsonl \
  --out data/results/diffusion_job_status.json

# Compute the (re)run set after a crash (retries capped).
python3 -m certvic.edit.diffusion_resume \
  --queue data/manifests/diffusion_job_queue.jsonl \
  --generated data/manifests/pilot_generated_edits.jsonl \
  --max-retries 3 --out data/manifests/diffusion_resume.jsonl

# Human-readable progress report.
python3 -m certvic.edit.edit_generation_plan \
  --queue data/manifests/diffusion_job_queue.jsonl \
  --generated data/manifests/pilot_generated_edits.jsonl \
  --num-shards 4 --out data/results/edit_generation_progress.md
```

Duplicate detection is handled by the generator (`certvic.edit.engines`), which
flags `duplicate_of` on identical outputs; the queue surfaces those as
`duplicate`. Record each session's outputs with `certvic.provenance.run_ledger
add` so progress is hash-tracked across sessions.
