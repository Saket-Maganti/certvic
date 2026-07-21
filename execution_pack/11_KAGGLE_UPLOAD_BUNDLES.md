# Kaggle Upload Bundles

Start with `python3 -m certvic.cvpr.build_all_kaggle_inputs --local-only`. It creates five byte-reproducible ZIPs in `kaggle_uploads/00_code/`; each contains `README.md`, `bundle_manifest.json`, and `hash_manifest.json`. Verify a ZIP with `python3 -m certvic.cvpr.kaggle_bundle verify <ZIP>` and inspect its private-dataset slug and exact mount with `... inspect <ZIP>`.

Publish every ZIP as a private Kaggle dataset using the exact slug in its manifest. Do not rename files, rewrite paths, edit hashes, merge datasets, or extract/re-ZIP them. Attach the code, configs, tools, and wheelhouse to 00A. Attach only the provider snapshot required by 00B/00C2/scientific notebooks. The complete notebook-to-dataset mapping is `kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md`.

Externally dependent inputs are never placeholders. `--status` reports `BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES`, `BLOCKED_BY_UPSTREAM_GATE`, or `CONDITIONAL_ON_CONFIRMATORY` with an exact builder command. Once external roots exist, describe them in YAML/JSON and run `python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots <CONFIG>`.

If a dataset does not mount, compare the attached dataset slug and filename with the bundle manifest. If discovery finds zero or multiple matches, remove the wrong attachment; never patch notebook search paths. A corrupt download must be downloaded again and reverified locally before import.

