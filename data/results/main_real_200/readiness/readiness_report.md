# CertVIC ADE20K Pilot Readiness Dry Run

Status: dry-run only. No edits generated yet. No model inference run yet. No evidence claims.

Zero paid services were used. The command inspected a local dataset root only and did not download data.

## Dataset Inspection

- root: `/Users/saketmaganti/Projects/ade20k_root/ADEChallengeData2016`
- layout status: `supported_layout`
- candidate images: 22210
- candidate annotations: 22210
- matched image/annotation pairs: 22210
- candidate label masks: 5714
- train images: 20210
- val images: 2000
- missing annotation pairs: 0
- mask area stats: `{'n': 5714, 'min': 2.3847680097680098e-06, 'max': 0.7246150942532943, 'mean': 0.08495468592565057}`
- top label IDs: `[{'label_id': 1, 'count': 497}, {'label_id': 4, 'count': 443}, {'label_id': 6, 'count': 313}, {'label_id': 8, 'count': 300}, {'label_id': 9, 'count': 259}, {'label_id': 16, 'count': 255}, {'label_id': 37, 'count': 244}, {'label_id': 19, 'count': 225}, {'label_id': 23, 'count': 201}, {'label_id': 11, 'count': 196}, {'label_id': 28, 'count': 189}, {'label_id': 58, 'count': 178}, {'label_id': 15, 'count': 168}, {'label_id': 48, 'count': 151}, {'label_id': 40, 'count': 150}, {'label_id': 38, 'count': 120}, {'label_id': 82, 'count': 115}, {'label_id': 66, 'count': 101}, {'label_id': 71, 'count': 93}, {'label_id': 135, 'count': 87}]`

## Candidate Readiness

- ready for source manifest: True
- ready for mask manifest: True
- ready for pilot selection: True

Blockers:
- None

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
