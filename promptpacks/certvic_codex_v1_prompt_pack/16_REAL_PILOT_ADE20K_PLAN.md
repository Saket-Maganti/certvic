# Codex Prompt 16 — Real Pilot Plan: ADE20K-First, 200 Items

Prepare the repo for the first real pilot, without downloading large data automatically.

## Goal

Create a controlled pilot plan targeting ~200 real-image pairs, ADE20K-first because dense labels make cleaner single-factor edits.

This prompt should not run expensive downloads by default. It should prepare scripts, configs, checklists, and TODOs.

## Files to create/update

```text
configs/real_pilot_ade20k.yaml
certvic/data/ade20k_adapter.py
certvic/data/select_pilot_items.py
certvic/edit/ade20k_masks.py
docs/PILOT_ADE20K.md
docs/RISK_REGISTER.md
tests/test_ade20k_adapter_import.py
tests/test_pilot_selection.py
```

## ADE20K adapter

Implement import-safe adapter:
- no download by default
- user provides local ADE20K root path
- scan images and annotations if present
- create SourceImageRecords
- create MaskRecords from dense labels if annotation format is available
- if format uncertain, implement clean TODO and fail clearly

CLI:
```bash
python -m certvic.data.ade20k_adapter \
  --ade20k-root /path/to/ADE20K \
  --out-sources data/manifests/ade20k_sources.jsonl \
  --out-masks data/manifests/ade20k_masks.jsonl \
  --max-items 500
```

## Pilot selection

Implement:
```bash
python -m certvic.data.select_pilot_items \
  --sources data/manifests/ade20k_sources.jsonl \
  --masks data/manifests/ade20k_masks.jsonl \
  --out data/manifests/pilot_selection.jsonl \
  --target 200 \
  --seed 0
```

Selection should balance:
- task family
- object labels where possible
- domain
- license/release mode
- mask area thresholds
- image sizes

## Pilot config

Create `real_pilot_ade20k.yaml`:
- target_items: 200
- families:
  - support_stability
  - affordance_reachability
  - control_irrelevant
- quality gates strict
- no paid services
- open model provider initially mock unless changed
- confseq alpha 0.05
- gap threshold 0.05

## Pilot doc

Create `docs/PILOT_ADE20K.md`:
- objective
- why ADE20K first
- commands
- expected artifacts
- quality gate
- human validation sample
- go/no-go gate:
  - edits photorealistic enough?
  - no prompt leakage?
  - model gap nonzero?
  - CS behaves?
- fallback if no gap:
  - change edit types
  - improve question templates
  - add occlusion/control variants
  - do not fake claims

## Tests

Test:
- adapter imports without ADE20K installed
- missing root fails clearly
- selection deterministic
- selection respects target count on fake records

## Finish

Run:
```bash
python -m pytest -q
```

Report:
- files changed
- tests run
- next prompt: `17_V1_END_TO_END_SMOKE_AUDIT.md`
