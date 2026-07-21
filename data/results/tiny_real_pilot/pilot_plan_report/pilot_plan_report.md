# CertVIC Pilot Candidate + Edit-Plan Review

Status: candidate/edit-plan only. No edits generated. No VLM inference. No evidence claims.

This report reviews manifest artifacts before generation. It is not a benchmark result, not a model evaluation, and not paper evidence.

## Inputs

- selection: `data/results/tiny_real_pilot/pilot_selection.jsonl`
- edit plan: `data/results/tiny_real_pilot/pilot_edit_plan.jsonl`
- task preview: `data/results/tiny_real_pilot/pilot_task_preview.jsonl`
- rejected candidates sidecar: `data/results/tiny_real_pilot/pilot_edit_plan_rejected.jsonl`

## Counts

- selected candidates: 20
- planned edits: 13
- task previews: 13
- rejected candidates: 7
- leakage warnings: 0

## Feasibility

- planned statuses: `['PLANNED_ONLY']`
- generation statuses: `['not_generated']`
- rejection reasons: `{'edit type incompatible with task family': 7}`

## Review Requirements Before Generation

- inspect selected source and mask rows
- inspect label IDs and unresolved label names
- confirm mask areas and bounding boxes are plausible
- confirm task-family and edit-type mapping
- confirm release mode remains recipe-first or otherwise verified
- confirm leakage summary is clean

## Next Gate

The next gate is actual edit generation plus quality gates. Evidence claims remain blocked until real edited images, human validity checks, model outputs, scoring, and certification artifacts exist.

