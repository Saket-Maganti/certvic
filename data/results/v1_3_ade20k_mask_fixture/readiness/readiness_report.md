# CertVIC ADE20K Pilot Readiness Dry Run

Status: dry-run only. No edits generated yet. No model inference run yet. No evidence claims.

Zero paid services were used. The command inspected a local dataset root only and did not download data.

## Dataset Inspection

- root: `data/results/v1_3_ade20k_mask_fixture/ADEChallengeData2016`
- layout status: `supported_layout`
- candidate images: 4
- candidate annotations: 4
- matched image/annotation pairs: 4
- candidate label masks: 10
- train images: 2
- val images: 2
- missing annotation pairs: 0
- mask area stats: `{'n': 10, 'min': 0.125, 'max': 0.3125, 'mean': 0.225}`
- top label IDs: `[{'label_id': 1, 'count': 1}, {'label_id': 2, 'count': 1}, {'label_id': 3, 'count': 1}, {'label_id': 4, 'count': 1}, {'label_id': 5, 'count': 1}, {'label_id': 6, 'count': 1}, {'label_id': 7, 'count': 1}, {'label_id': 8, 'count': 1}, {'label_id': 9, 'count': 1}, {'label_id': 10, 'count': 1}]`

## Candidate Readiness

- ready for source manifest: True
- ready for mask manifest: True
- ready for pilot selection: False

Blockers:
- candidate image count 4 is below target 200
- candidate mask count 10 is below target 200

## License Policy

- default license category: `pointer_only`
- default release mode: `recipe_only`
- pixels are not rehostable by default

## Next Commands Once Root Is Confirmed

```bash
python3 -m certvic.data.pilot_readiness --config configs/real_pilot_ade20k.yaml --ade20k-root /path/to/ADE20K --out-dir data/results/pilot_readiness_ade20k --dry-run
python3 -m certvic.data.ade20k_adapter --ade20k-root /path/to/ADE20K --out-sources data/manifests/ade20k_sources.jsonl --out-masks data/manifests/ade20k_masks.jsonl --inspection-out data/results/pilot_readiness_ade20k/dataset_inspection.json --max-items 500
python3 -m certvic.data.select_pilot_items --sources data/manifests/ade20k_sources.jsonl --masks data/manifests/ade20k_masks.jsonl --out data/manifests/pilot_selection.jsonl --target 200 --seed 0 --min-mask-area-fraction 0.01 --max-mask-area-fraction 0.40
```

Binary mask PNG export is disabled by default; use --export-binary-masks only when a local inspection artifact is explicitly needed.
