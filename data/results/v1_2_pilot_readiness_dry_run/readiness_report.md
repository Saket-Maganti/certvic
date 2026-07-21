# CertVIC ADE20K Pilot Readiness Dry Run

Status: dry-run only. No edits generated yet. No model inference run yet. No evidence claims.

Zero paid services were used. The command inspected a local dataset root only and did not download data.

## Dataset Inspection

- root: `data/results/v1_2_pilot_readiness_fixture/ADEChallengeData2016`
- layout status: `parser_required`
- candidate images: 3
- candidate annotations: 3
- train images: 2
- val images: 1

## Candidate Readiness

- ready for source manifest: True
- ready for mask manifest: False
- ready for pilot selection: False

Blockers:
- candidate image count 3 is below target 200
- ADE20K mask parser is not implemented in V1.2; parser_required before selection

## License Policy

- default license category: `pointer_only`
- default release mode: `recipe_only`
- pixels are not rehostable by default

## Next Commands Once Root Is Confirmed

```bash
python3 -m certvic.data.pilot_readiness --config configs/real_pilot_ade20k.yaml --ade20k-root /path/to/ADE20K --out-dir data/results/pilot_readiness_ade20k --dry-run
python3 -m certvic.data.ade20k_adapter --ade20k-root /path/to/ADE20K --out-sources data/manifests/ade20k_sources.jsonl --out-masks data/manifests/ade20k_masks.jsonl --max-items 500
python3 -m certvic.data.select_pilot_items --sources data/manifests/ade20k_sources.jsonl --masks data/manifests/ade20k_masks.jsonl --out data/manifests/pilot_selection.jsonl --target 200 --seed 0
```

The second and third commands remain blocked until an ADE20K annotation parser and valid mask manifests are available.
