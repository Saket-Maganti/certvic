# CertVIC V1.3 ADE20K Mask Manifest Report

Date: 2026-06-21

Verdict: PASS for ADE20K annotation/mask manifest readiness.

This is not a real pilot run. V1.3 adds conservative ADE20K-style semantic PNG
annotation parsing and mask manifest creation from a user-provided local root.
It does not generate edited images, run VLM inference, use GPU, download large
datasets, use paid services, or enable evidence claims.

## What Changed

- Added conservative ADE20K layout detection for common local roots:
  - `images/training`
  - `images/validation`
  - `annotations/training`
  - `annotations/validation`
  - the same folders under `ADEChallengeData2016/`
- Added image/annotation pairing by split and stem.
- Added semantic PNG annotation reading for indexed/grayscale labels.
- Added mask candidate extraction:
  - non-background label IDs
  - `ade20k_label_<id>` fallback labels when names are unresolved
  - `bbox_xyxy`
  - `mask_area_fraction`
  - source links
  - annotation pointer and regeneration metadata
- Added manifest-only mask JSONL writing by default.
- Added opt-in binary mask export:
  - `--export-binary-masks`
  - `--mask-out-dir data/masks/ade20k_pilot`
- Updated pilot readiness to report:
  - image count
  - annotation count
  - matched image/annotation pairs
  - candidate label/mask count
  - mask-area statistics
  - top label IDs by frequency
  - unsupported/missing pairs
  - readiness for source manifest, mask manifest, and pilot selection
- Updated pilot selection to consume generated ADE20K mask manifests and filter
  by valid source link, valid bbox, duplicate source avoidance, and mask-area
  thresholds.

## Tests Run

```bash
python3 -m pytest -q
```

Result: 98 passed.

## Commands Added Or Updated

Dry-run readiness:

```bash
python3 -m certvic.data.pilot_readiness \
  --config configs/real_pilot_ade20k.yaml \
  --ade20k-root /absolute/path/to/ADE20K \
  --out-dir data/results/pilot_readiness_ade20k \
  --dry-run
```

Adapter dry run:

```bash
python3 -m certvic.data.ade20k_adapter \
  --ade20k-root /absolute/path/to/ADE20K \
  --out-sources data/manifests/ade20k_sources.jsonl \
  --out-masks data/manifests/ade20k_masks.jsonl \
  --inspection-out data/results/pilot_readiness_ade20k/dataset_inspection.json \
  --max-items 500 \
  --dry-run
```

Manifest generation:

```bash
python3 -m certvic.data.ade20k_adapter \
  --ade20k-root /absolute/path/to/ADE20K \
  --out-sources data/manifests/ade20k_sources.jsonl \
  --out-masks data/manifests/ade20k_masks.jsonl \
  --inspection-out data/results/pilot_readiness_ade20k/dataset_inspection.json \
  --max-items 500
```

Optional local binary mask export:

```bash
python3 -m certvic.data.ade20k_adapter \
  --ade20k-root /absolute/path/to/ADE20K \
  --out-sources data/manifests/ade20k_sources.jsonl \
  --out-masks data/manifests/ade20k_masks.jsonl \
  --export-binary-masks \
  --mask-out-dir data/masks/ade20k_pilot \
  --max-items 500
```

Pilot candidate selection:

```bash
python3 -m certvic.data.select_pilot_items \
  --sources data/manifests/ade20k_sources.jsonl \
  --masks data/manifests/ade20k_masks.jsonl \
  --out data/manifests/pilot_selection.jsonl \
  --target 200 \
  --seed 0 \
  --min-mask-area-fraction 0.01 \
  --max-mask-area-fraction 0.40
```

## Fake Fixture Validation

A tiny local ADE20K-like fixture was generated under:

```text
data/results/v1_3_ade20k_mask_fixture/ADEChallengeData2016
```

It used `images/{training,validation}` and `annotations/{training,validation}`
with tiny semantic PNG annotations.

Observed validation results:

- layout status: `supported_layout`
- matched image/annotation pairs: 4
- candidate label masks: 10
- mask area min: 0.125
- mask area mean: 0.225
- mask area max: 0.3125
- source manifest rows: 4
- mask manifest rows: 10
- pilot selector target 3: passed with 3 selected candidates
- binary masks exported by default: false

The readiness report for this tiny fixture still blocks full pilot selection at
the default target of 200 because the fixture is intentionally small. That is
expected.

## Current Non-Evidence Status

V1.3 is still non-evidence:

- no real edits generated
- no model inference run
- no GPU jobs
- no paid APIs or paid cloud
- no dataset downloads
- no human validation
- no confidence-sequence claim
- no paper result claims

ADE20K source records remain pointer-aware and recipe-first:

- `license_category=pointer_only`
- `redistribution_allowed=false`
- release mode `recipe_only`

## Known Limitations

- Only semantic PNG-style annotations are supported.
- Non-PNG or uncertain annotation formats remain `parser_required`.
- ADE20K label names are unresolved unless a verified label map is supplied, so
  mask labels use `ade20k_label_<id>`.
- Mask manifests are structural candidates, not validated edit targets.
- Binary mask export is local and opt-in only.
- Pilot selection still needs review before edit generation.

## Exact Commands For A Real ADE20K Root

First inspect:

```bash
python3 -m certvic.data.pilot_readiness \
  --config configs/real_pilot_ade20k.yaml \
  --ade20k-root /absolute/path/to/ADE20K \
  --out-dir data/results/pilot_readiness_ade20k \
  --dry-run
```

If the report shows `supported_layout` and adequate candidates, build manifests:

```bash
python3 -m certvic.data.ade20k_adapter \
  --ade20k-root /absolute/path/to/ADE20K \
  --out-sources data/manifests/ade20k_sources.jsonl \
  --out-masks data/manifests/ade20k_masks.jsonl \
  --inspection-out data/results/pilot_readiness_ade20k/dataset_inspection.json \
  --max-items 500
```

Then select pilot candidates:

```bash
python3 -m certvic.data.select_pilot_items \
  --sources data/manifests/ade20k_sources.jsonl \
  --masks data/manifests/ade20k_masks.jsonl \
  --out data/manifests/pilot_selection.jsonl \
  --target 200 \
  --seed 0 \
  --min-mask-area-fraction 0.01 \
  --max-mask-area-fraction 0.40
```

## Remaining Blockers Before Real Edits

- Run the commands above on the real local ADE20K root.
- Review candidate label IDs and unresolved semantic names.
- Confirm source/mask manifest counts and area distributions.
- Choose task-family mapping rules for label IDs.
- Run leakage and manifest checks on selected pilot items.
- Generate edits only after manifest review.
- Run edit quality gates.
- Run human validity checks.
- Only then consider open local VLM runs on free compute.

Evidence claims remain blocked until real edits, real model outputs, validity
checks, and certification gates exist.
