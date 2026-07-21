# CertVIC V1.4 Pilot Candidate + Edit-Plan Report

Date: 2026-06-21

Verdict: PASS for real ADE20K pilot candidate and edit-plan readiness.

This is not a real pilot run. V1.4 prepares reviewable candidate, edit-plan,
task-preview, and plan-review artifacts from source/mask manifests. It does not
generate edited images, run VLM inference, use GPU, download datasets, use paid
services, or enable evidence claims.

## What Changed

- Expanded ADE20K pilot selection into a flat review manifest with:
  - source pointer/path
  - mask ID
  - label ID/name
  - bbox
  - mask-area fraction
  - proposed task family
  - proposed edit type
  - proposed required change
  - selection reason
  - release mode and license posture
  - `evidence_status=CANDIDATE_ONLY`
- Added deterministic selection filters:
  - target count
  - seed
  - min/max mask-area fraction
  - max masks per source
  - source de-duplication
  - task-family balancing where possible
  - domain and split filters
  - label allowlist/blocklist
  - target shortfall warnings
- Added edit-plan generation:
  - `python3 -m certvic.edit.plan_edits`
  - `PLANNED_ONLY`
  - `generation_status=not_generated`
  - `zero_cost=true`
  - rejected infeasible candidates sidecar
- Added conservative feasibility checks for area, bbox, local image existence,
  task/edit compatibility, required-change compatibility, release posture,
  leakage terms, and duplicate edit IDs.
- Added task-preview generation:
  - `python3 -m certvic.data.preview_tasks`
  - neutral prompts
  - planned/unavailable edited image paths
  - `PREVIEW_ONLY`
  - non-runnable eval task flag
- Added pilot-plan review reporting:
  - `pilot_plan_report.md`
  - selection/edit-plan CSV summaries
  - leakage and feasibility JSON summaries
- Updated claim gates so `CANDIDATE_ONLY`, `PLANNED_ONLY`, and `PREVIEW_ONLY`
  cannot support certified claims.

## Tests Run

```bash
python3 -m pytest -q
```

Result: 104 passed.

Focused V1.4 fake-fixture coverage is in:

```text
tests/test_v1_4_pilot_candidate_edit_plan.py
```

## Commands Added Or Updated

Pilot selection:

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

Edit plan:

```bash
python3 -m certvic.edit.plan_edits \
  --selection data/manifests/pilot_selection.jsonl \
  --out data/manifests/pilot_edit_plan.jsonl \
  --summary-out data/manifests/pilot_edit_plan_summary.json \
  --seed 0
```

Task preview:

```bash
python3 -m certvic.data.preview_tasks \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --out data/manifests/pilot_task_preview.jsonl \
  --summary-out data/manifests/pilot_task_preview_summary.json
```

Pilot-plan report:

```bash
python3 -m certvic.reporting.pilot_plan_report \
  --selection data/manifests/pilot_selection.jsonl \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --task-preview data/manifests/pilot_task_preview.jsonl \
  --out-dir data/results/pilot_plan_review
```

## Fake Fixture Validation

The V1.4 tests use tiny local fake fixtures only. They verify deterministic
selection, source de-duplication, max masks per source, mask-area thresholds,
label allow/block filters, edit-plan type creation, infeasible rejection
reasons, duplicate edit ID rejection, non-runnable previews, leakage-clean
prompts, report outputs, and claim blocking for non-evidence statuses.

No real ADE20K root was processed during V1.4 validation.

## Current Non-Evidence Status

- selected candidates are `CANDIDATE_ONLY`
- planned edits are `PLANNED_ONLY`
- task previews are `PREVIEW_ONLY`
- edited images are not generated
- VLM inference is not run
- GPU is not required
- paid services are disabled
- evidence claims remain blocked

## Exact Command Sequence After Real ADE20K Manifests Exist

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

python3 -m certvic.edit.plan_edits \
  --selection data/manifests/pilot_selection.jsonl \
  --out data/manifests/pilot_edit_plan.jsonl \
  --summary-out data/manifests/pilot_edit_plan_summary.json \
  --seed 0

python3 -m certvic.data.preview_tasks \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --out data/manifests/pilot_task_preview.jsonl \
  --summary-out data/manifests/pilot_task_preview_summary.json

python3 -m certvic.reporting.pilot_plan_report \
  --selection data/manifests/pilot_selection.jsonl \
  --edit-plan data/manifests/pilot_edit_plan.jsonl \
  --task-preview data/manifests/pilot_task_preview.jsonl \
  --out-dir data/results/pilot_plan_review
```

If the target cannot be met, inspect
`data/manifests/pilot_selection_summary.json` before changing thresholds or
using `--allow-partial` for review-only shortfall inspection.

## Manual Review Before Generation

- inspect `pilot_selection.jsonl`
- inspect `pilot_selection_summary.json`
- inspect `pilot_edit_plan.jsonl`
- inspect `pilot_edit_plan_rejected.jsonl`
- inspect `pilot_task_preview.jsonl`
- inspect `data/results/pilot_plan_review/pilot_plan_report.md`
- confirm leakage summary is clean
- confirm release posture is recorded and acceptable
- confirm task-family and edit-type mapping is plausible
- confirm rejected candidates are expected

## Remaining Blockers Before Edit Generation

- run V1.4 commands against real local ADE20K source/mask manifests
- manually review candidate labels, bboxes, mask areas, and source pointers
- decide whether unresolved ADE20K label names need a verified label map
- choose and document the V1.5 local edit generator
- generate actual edited images only after review
- run edit quality gates
- run human validity checks

## Remaining Blockers Before Evidence Claims

- real edited images must exist
- edit quality gates must pass
- human validity checks must pass
- open local or otherwise zero-cost model outputs must exist
- scoring artifacts must exist
- confidence-sequence/certification artifacts must exist
- claim ledger and paper scanner must pass

Until then, paper result sections must keep `[RESULT REQUIRED]` placeholders.
