# CertVIC — Kaggle T4×2 GPU Runbooks

These runbooks drive the **two GPU stages** of the CertVIC pilot on free Kaggle
**T4×2** notebooks. Everything else (planning, manifests, quality/detectability
gates, scoring, certification) runs on the local CPU and is **already done** by
the time you open a runbook here.

> The CertVIC repo ships the **plan, coordination (job queue / resume / shards),
> validation (quality, detectability, leakage) and schema**. The actual GPU
> compute — diffusion inpainting and VLM inference — is intentionally *not* in the
> repo (`generate_edits` rejects non-`simple` modes; `OpenVLMProvider.answer`
> raises "fill in before real runs"). Each runbook supplies that code and feeds
> the results back into CertVIC's pipeline unchanged.

## Dataset

`ade20kdataset/ade20k.zip` → **`ADEChallengeData2016/`** (MIT Scene Parsing
benchmark: 20,210 train + 2,000 val images, each with a semantic-PNG annotation).
This is the **only** one of the three archives the code accepts — see
[`DATASET_DECISION.md`](DATASET_DECISION.md). The other two are wrong format:
`ADE20K-main.zip` is the CSAILVision toolkit (per-instance JSON/PNG, tiny sample);
`ade20k-DatasetNinja.tar` is Supervisely JSON polygons, not semantic PNG.

## The two GPU sessions

| Session | Runbook | What it does | Input from CPU | Output to CPU |
| --- | --- | --- | --- | --- |
| **1 — Diffusion edits** | [`KAGGLE_T4x2_DIFFUSION_EDITS.md`](KAGGLE_T4x2_DIFFUSION_EDITS.md) | Generate 168 photorealistic single-factor edits | `pilot_edit_plan*.jsonl` (sharded) | `pilot_generated_edits.jsonl` + edited PNGs |
| **2 — VLM eval** | [`KAGGLE_T4x2_VLM_EVAL.md`](KAGGLE_T4x2_VLM_EVAL.md) | Run open VLMs on original/edited pairs | `pilot_eval_tasks_reviewed.jsonl` | prediction JSONLs (per provider/shard) |

## The T4×2 parallel model: `gpu0 → session 1`, `gpu1 → session 2`

A Kaggle **T4×2** notebook exposes two physical GPUs (`cuda:0`, `cuda:1`). Each
runbook runs **two workers in parallel inside one notebook**, one pinned per GPU,
each processing a disjoint, deterministic shard:

```
            ┌──────────────────────── one Kaggle T4×2 notebook ───────────────────────┐
            │                                                                          │
  shard 0 ──┼──►  CUDA_VISIBLE_DEVICES=0   "Session 1"  (GPU 0)  ──► outputs/shard0   │
            │                                  ‖ in parallel (&) ‖                     │
  shard 1 ──┼──►  CUDA_VISIBLE_DEVICES=1   "Session 2"  (GPU 1)  ──► outputs/shard1   │
            │                                                                          │
            └──────────────────► wait; merge shard0 + shard1 ─────────────────────────┘
```

Shards are disjoint and resumable, so if the notebook dies you re-launch and each
worker skips finished items. Sharding is deterministic
(`certvic.eval.sharding.shard_for_item`), identical to the diffusion job queue, so
shard files line up exactly with the queue and its resume planner.

> Rebalancing: to push more onto GPU 1 (e.g. "1 session on gpu0, 2 on gpu1"),
> re-split with `--num-shards 3` and give shard 0 to GPU 0, shards 1 & 2 to GPU 1.
> Both runbooks note the exact command.

## Required ordering (claim-gating — do not skip)

```
[CPU ✓ done]  audits → manifests → selection → edit plan → job queue → shards
     │
     ▼
[GPU 1]       diffusion edits  ───────────────────────────────────────────────┐
     │                                                                         │
     ▼                                                                         │
[CPU]         quality_report + EDIT DETECTABILITY GATE  ── must be GO (AUC<0.80)│
     │            └─ crude CPU edits scored AUC 0.92 = NO_GO. Realistic        │
     │               diffusion edits must clear this before any VLM run.       │
     ▼                                                                         │
[CPU]         materialize_tasks → HUMAN REVIEW → pilot_eval_tasks_reviewed     │
     │            (tasks gain evidence_status HUMAN_REVIEWED_NON_EVIDENCE)     │
     ▼                                                                         │
[GPU 2]       VLM eval  (run_eval --evidence-run REFUSES unreviewed tasks) ◄───┘
     │
     ▼
[CPU]         score_predictions → confidence sequences → report → certify
```

`run_eval --evidence-run` is hard-gated in code: it refuses any provider that is
not an open-local VLM, and refuses task sets whose `evidence_status` is not in
`{HUMAN_REVIEWED_NON_EVIDENCE, EVIDENCE, CERTIFIED}`. **Do not run GPU Session 2
until the detectability gate is GO and human review is complete.**

## Zero-cost policy (applies to both sessions)

Free GPU + open weights + user-supplied data only. **No paid endpoints, no API
keys, no auto-downloads.** Mount ADE20K and model weights as read-only Kaggle
**input datasets** (pre-cached), keep notebook internet **off** unless a step
truly needs it, and write outputs to `/kaggle/working` (offload before the ~20 GB
cap or the ~12 h session limit). Generated rows stay `GENERATED_EDIT_ONLY` /
predictions stay non-certified until the CPU gates pass.

## CPU state already produced (inputs for these runbooks)

```
data/results/main_real_200/
├── ade20k_sources.jsonl              (1000 pointer-only source records)
├── ade20k_masks.jsonl               (12,737 semantic-PNG mask records)
├── pilot_selection.jsonl             (200 selected household items)
├── pilot_edit_plan.jsonl             (168 planned single-factor edits)
├── diffusion_job_queue.jsonl         (168 jobs, 4 shards — coordination/resume)
├── diffusion_resume.jsonl            (worklist; re-run after each GPU session)
└── gpu_shards/
    ├── pilot_edit_plan_shard0_of_2.jsonl   (81 edits  → GPU 0 / Session 1)
    └── pilot_edit_plan_shard1_of_2.jsonl   (87 edits  → GPU 1 / Session 2)
```
