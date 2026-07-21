# ADE20K-First Pilot Plan

Objective: prepare approximately 200 real-image intervention pairs using local
user-provided ADE20K files.

Why ADE20K first: dense labels can make mask extraction and single-factor edit
selection cleaner than weakly annotated sources.

No downloads are automatic. The user must provide a local ADE20K root. V1.5 can
generate a tiny number of local simple edits from an accepted edit plan and run
quality gates. It still does not run models, scale to a full pilot, or enable
evidence claims.

Expected local layouts include:

```text
/path/to/ADE20K/
  images/
    training/
    validation/
  annotations/
    training/
    validation/

/path/to/ADE20K/ADEChallengeData2016/
  images/
    training/
    validation/
  annotations/
    training/
    validation/
```

Unsupported or uncertain layouts are reported as `unsupported_layout` or
`parser_required` with next-step instructions.

## Dry-Run Inspection

Run this first:

```bash
python3 -m certvic.data.pilot_readiness \
  --config configs/real_pilot_ade20k.yaml \
  --ade20k-root /path/to/ADE20K \
  --out-dir data/results/pilot_readiness_ade20k \
  --dry-run
```

Expected outputs:

- `dataset_inspection.json`
- `candidate_summary.json`
- `license_summary.json`
- `readiness_report.md`

The inspection reports candidate image folders, candidate annotation folders,
train/validation-like counts, matched image/annotation pairs, missing annotation
stems, candidate label-mask counts, mask-area statistics, top label IDs, and
whether the layout is `supported_layout`, `parser_required`, or
`unsupported_layout`.

## Later Manifest Commands

```bash
python3 -m certvic.data.ade20k_adapter \
  --ade20k-root /path/to/ADE20K \
  --out-sources data/manifests/ade20k_sources.jsonl \
  --out-masks data/manifests/ade20k_masks.jsonl \
  --inspection-out data/results/pilot_readiness_ade20k/dataset_inspection.json \
  --max-items 500

python3 -m certvic.data.select_pilot_items \
  --sources data/manifests/ade20k_sources.jsonl \
  --masks data/manifests/ade20k_masks.jsonl \
  --out data/manifests/pilot_selection.jsonl \
  --summary-out data/manifests/pilot_selection_summary.json \
  --target 200 \
  --seed 0 \
  --max-masks-per-source 1 \
  --domains household \
  --splits train val \
  --allowed-task-families support_stability occlusion_safety affordance_reachability control_irrelevant \
  --min-mask-area-fraction 0.01 \
  --max-mask-area-fraction 0.40
```

By default, the adapter writes mask manifest rows that point back to the
annotation PNG and include label ID, bbox, area fraction, and regeneration
metadata. It does not save full binary masks unless explicitly requested:

```bash
python3 -m certvic.data.ade20k_adapter \
  --ade20k-root /path/to/ADE20K \
  --out-sources data/manifests/ade20k_sources.jsonl \
  --out-masks data/manifests/ade20k_masks.jsonl \
  --export-binary-masks \
  --mask-out-dir data/masks/ade20k_pilot \
  --max-items 500
```

Use binary mask export only for local inspection artifacts. It is not required
for recipe-first manifests and should not be treated as redistributable data.

## V1.4 Candidate And Edit-Plan Review

After real source and mask manifests exist, select pilot candidates for
human/code review:

```bash
python3 -m certvic.data.select_pilot_items \
  --sources data/manifests/ade20k_sources.jsonl \
  --masks data/manifests/ade20k_masks.jsonl \
  --out data/manifests/pilot_selection.jsonl \
  --summary-out data/manifests/pilot_selection_summary.json \
  --target 200 \
  --seed 0 \
  --max-masks-per-source 1 \
  --domains household \
  --splits train val \
  --allowed-task-families support_stability occlusion_safety affordance_reachability control_irrelevant \
  --min-mask-area-fraction 0.01 \
  --max-mask-area-fraction 0.40
```

The selection manifest records `CANDIDATE_ONLY` rows with source pointers, mask
IDs, label IDs/names, bbox, area fraction, proposed task family, proposed edit
type, proposed required change, selection reason, and release/license posture.
If the target cannot be met, the summary includes warnings and rejection counts.

Build the deterministic edit plan without generating images:

```bash
python3 -m certvic.edit.plan_edits \
  --selection data/manifests/pilot_selection.jsonl \
  --out data/manifests/pilot_edit_plan.jsonl \
  --summary-out data/manifests/pilot_edit_plan_summary.json \
  --seed 0
```

The planner writes feasible `PLANNED_ONLY` edits and writes infeasible rows to:

```text
data/manifests/pilot_edit_plan_rejected.jsonl
```

Preview non-runnable tasks:

```bash
python3 -m certvic.data.preview_tasks \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --out data/manifests/pilot_task_preview.jsonl \
  --summary-out data/manifests/pilot_task_preview_summary.json
```

Build the review report:

```bash
python3 -m certvic.reporting.pilot_plan_report \
  --selection data/manifests/pilot_selection.jsonl \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --task-preview data/manifests/pilot_task_preview.jsonl \
  --out-dir data/results/pilot_plan_review
```

Manual inspection before generation:

- source paths exist locally and remain pointer-first
- label IDs/names are plausible for the proposed task family
- bbox and mask-area fractions are plausible
- max one mask per source is acceptable for the pilot
- rejected candidates are understood
- task previews have no prompt or filename leakage
- release mode and license posture are recorded

Why this is still not evidence:

- no edited images exist
- no edit quality gates have passed
- no human validity checks exist
- no VLM inference has run
- no model predictions or scores exist
- artifacts are `CANDIDATE_ONLY`, `PLANNED_ONLY`, or `PREVIEW_ONLY`

## V1.5 Tiny Edit Generation And Quality Gates

After `pilot_edit_plan.jsonl` has been reviewed, generate at most a tiny pilot
batch with the simple local generator:

```bash
python3 -m certvic.edit.generate_edits \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --out-dir data/edits/ade20k_tiny_pilot \
  --out-manifest data/manifests/pilot_generated_edits.jsonl \
  --rejected-out data/manifests/pilot_generated_edits_rejected.jsonl \
  --summary-out data/results/tiny_edit_generation_summary.json \
  --max-items 20 \
  --mode simple \
  --seed 0
```

Simple mode is deterministic, local, CPU-friendly, and zero-cost. It uses simple
fill, occlusion patch, cut/paste displacement, and mild irrelevant control
edits. It is only for pipeline validation and quality-gate review, not for
paper evidence.

The optional `diffusers_inpaint` mode is disabled by default. It must not import
heavy dependencies at module import time, must use user-prepared local/cache
weights, and must not download models automatically.

Build the quality report:

```bash
python3 -m certvic.edit.quality_report \
  --generated-manifest data/manifests/pilot_generated_edits.jsonl \
  --rejected data/manifests/pilot_generated_edits_rejected.jsonl \
  --out-dir data/results/tiny_edit_quality_report
```

Quality gates check mask area, bbox validity, inside-mask changes, outside-mask
changes, edit-specific allowed regions, image-size match, edited file/hash
presence, changed-region non-emptiness, and simple artifact warnings. Passing
quality gates means the local edit file is structurally reviewable; it does not
mean the item is semantically valid or model-evaluation evidence.

Materialize tiny non-evidence task rows from preview and generated edits:

```bash
python3 -m certvic.data.materialize_tasks \
  --task-preview data/manifests/pilot_task_preview.jsonl \
  --generated-edits data/manifests/pilot_generated_edits.jsonl \
  --out data/manifests/pilot_eval_tasks_tiny.jsonl \
  --summary-out data/manifests/pilot_eval_tasks_tiny_summary.json
```

Only generated edits that passed quality gates and leakage checks are included.
Materialized rows are marked `EDIT_READY_NON_EVIDENCE`.

Manual inspection before any VLM inference:

- inspect every original/edited pair in the review gallery manifest
- inspect rejected generation rows and quality warnings
- confirm simple edits are semantically valid for the task family
- confirm control edits are not destructive
- confirm displace destination changes match the plan
- confirm no prompt or filename leakage
- run human validity checks

Why generated edits are still not evidence:

- simple mode is pipeline validation only
- generated rows are `GENERATED_EDIT_ONLY`
- materialized task rows are `EDIT_READY_NON_EVIDENCE`
- no VLM inference has run
- no human validity labels exist
- no model predictions, scores, or certification outputs exist

Go/no-go gates:

- local root exists and has image folders
- annotation/mask folders are present
- semantic PNG mask manifest has enough valid label-region candidates
- enough valid source/mask candidates exist
- pilot candidate and edit-plan review report has been inspected
- tiny generated edit quality report has been inspected
- human validity checks are prepared
- edits photorealistic enough
- no prompt or filename leakage
- model gap nonzero or null result honestly reported
- confidence-sequence behavior understood

V1.5 to V1.6 gate: only after tiny generated edits pass quality review and human
validity preparation should CertVIC consider any local zero-cost VLM inference.
Claims remain blocked until model outputs, scoring, and certification artifacts
exist.

## V2 label policy gate

Before pilot selection, build the label-policy diagnostics and confirm the
label map:

```bash
python3 -m certvic.data.label_policy_report --masks data/manifests/ade20k_masks.jsonl \
  --policy configs/ade20k_label_policy.yaml --out-dir data/results/label_policy_report
```

Then run selection and edit planning with `--label-policy
configs/ade20k_label_policy.yaml`. The shipped policy is UNVERIFIED; resolving
the ADE20K label names (so questions are well-posed) and verifying the map are
prerequisites for any evidence run. Unresolved labels are restricted to control
edits until named.

## Diffusion job queue (V3)

For diffusion edit generation on free GPU, shard and resume via the job queue so
sessions that die mid-run can be picked up cleanly:

```bash
python3 -m certvic.edit.job_queue build --edit-plan data/manifests/pilot_edit_plan.jsonl --out data/manifests/diffusion_job_queue.jsonl --shards 4
python3 -m certvic.edit.job_queue next-shard --queue data/manifests/diffusion_job_queue.jsonl --shard-index 0 --num-shards 4 --out data/manifests/diffusion_job_shard_0.jsonl
python3 -m certvic.edit.job_queue status --queue data/manifests/diffusion_job_queue.jsonl --generated data/manifests/pilot_generated_edits.jsonl --out data/results/diffusion_job_status.json
python3 -m certvic.edit.diffusion_resume --queue data/manifests/diffusion_job_queue.jsonl --generated data/manifests/pilot_generated_edits.jsonl --out data/manifests/diffusion_resume.jsonl
```

Sharding is deterministic (complete + non-overlapping); statuses cover pending /
generated / rejected / failed / duplicate / missing_output / hash_mismatch. See
`docs/DIFFUSION_JOB_QUEUE.md`.
