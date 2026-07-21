# CertVIC V1.2 Real-Pilot Readiness Report

Date: 2026-06-21

Verdict: PASS for V1.2 dry-run readiness tooling.

This is not a real ADE20K pilot run. V1.2 prepares CertVIC to accept a
user-provided local ADE20K root and inspect it safely. No edits were generated,
no model inference was run, no large dataset was downloaded, no GPU was
required, no paid service was used, and no evidence claims are enabled.

## What Changed

- Replaced the placeholder ADE20K adapter with a conservative local-root
  inspector.
- Added dry-run layout detection for ADE20K-like roots:
  - candidate image folders
  - candidate annotation/mask folders
  - train/validation-like split folders
  - image and annotation counts
  - unmatched image stems
  - `parser_required` or `unsupported_layout` status
- Added clear `ADE20KLayoutError` failures for missing roots and missing image
  files.
- Kept ADE20K source records pointer-aware by default:
  - `license_category=pointer_only`
  - `redistribution_allowed=false`
  - release mode `recipe_only`
- Added `python3 -m certvic.data.pilot_readiness`.
- Hardened pilot selection:
  - target count
  - seed
  - duplicate source-ID avoidance
  - mask-area thresholds when available
  - task-family balancing where possible
  - `selection_summary.json`
  - clear failure when candidates are insufficient
- Documented that ADE20K annotation parsing is still `parser_required`; V1.2
  does not guess mask manifests.

## Tests Run

```bash
python3 -m pytest -q
```

Result: 92 passed.

## Commands Added

Dry-run readiness command:

```bash
python3 -m certvic.data.pilot_readiness \
  --config configs/real_pilot_ade20k.yaml \
  --ade20k-root /path/to/ADE20K \
  --out-dir data/results/pilot_readiness_ade20k \
  --dry-run
```

ADE20K adapter dry run:

```bash
python3 -m certvic.data.ade20k_adapter \
  --ade20k-root /path/to/ADE20K \
  --dry-run \
  --inspection-out data/results/pilot_readiness_ade20k/dataset_inspection.json
```

Pointer-aware source manifest command:

```bash
python3 -m certvic.data.ade20k_adapter \
  --ade20k-root /path/to/ADE20K \
  --out-sources data/manifests/ade20k_sources.jsonl \
  --out-masks data/manifests/ade20k_masks.jsonl \
  --max-items 500
```

Pilot selector command, still blocked until a valid mask manifest exists:

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

## Dry-Run Behavior

The readiness command writes:

- `dataset_inspection.json`
- `candidate_summary.json`
- `license_summary.json`
- `readiness_report.md`

The report states:

- no edits generated yet
- no model inference run yet
- no evidence claims
- zero paid services
- local dataset root only
- next commands after the root is confirmed

A tiny fake ADE20K-like fixture was used to verify the command outside pytest:

```bash
python3 -m certvic.data.pilot_readiness \
  --config configs/real_pilot_ade20k.yaml \
  --ade20k-root data/results/v1_2_pilot_readiness_fixture/ADEChallengeData2016 \
  --out-dir data/results/v1_2_pilot_readiness_dry_run \
  --dry-run
```

The fixture dry run found 3 candidate images and 3 candidate annotations,
reported `layout_status=parser_required`, and correctly blocked pilot selection
because the fixture is below target and V1.2 has no ADE20K mask parser.

## Known Limitations

- V1.2 does not parse ADE20K dense annotations into `MaskRecord` manifests.
- V1.2 does not generate edits.
- V1.2 does not run VLM inference.
- V1.2 does not validate edit photorealism or single-factor validity.
- V1.2 does not enable paper claims or evidence claims.
- Real pilot selection remains blocked until masks are parsed and quality gates
  are available.

## Exact Command To Run With A Real Local Root

Once you have a local ADE20K root, run:

```bash
python3 -m certvic.data.pilot_readiness \
  --config configs/real_pilot_ade20k.yaml \
  --ade20k-root /absolute/path/to/ADE20K \
  --out-dir data/results/pilot_readiness_ade20k \
  --dry-run
```

Review `data/results/pilot_readiness_ade20k/readiness_report.md` before running
any manifest or pilot-selection commands.

## Remaining Blockers Before Real Evidence Claims

- Confirm local ADE20K layout and source counts.
- Implement or enable ADE20K annotation parsing into mask manifests.
- Verify license and release-mode policy for all pilot sources.
- Build source and mask manifests.
- Select pilot candidates with mask-area and duplicate checks.
- Generate edits and run quality gates.
- Run human validity checks.
- Run open local VLMs on free compute only.
- Install/use optional anytime-valid CS tooling only when eligible real,
  non-smoke evidence exists.
- Keep paper result sections at `[RESULT REQUIRED]` until evidence gates pass.
