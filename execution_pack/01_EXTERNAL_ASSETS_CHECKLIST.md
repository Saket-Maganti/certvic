# External assets checklist

## Inputs

- Offline wheelhouse matching `configs/runtime/kaggle_t4x2_environment.lock.json`; every wheel must
  appear in a completed `wheelhouse_manifest.json` with filename, package, version, tags, size, and
  SHA-256.
- Unified offline model and processor snapshots for `qwen2_5_vl_7b`, `internvl_8b`, and
  `llava_onevision_7b`; fill immutable commits and all-file root hashes only from downloaded bytes.
- Licensed ADE20K validation assets and a source manifest for confirmatory construction. Do not put
  source image bytes in a release.
- COCO assets are not required for the immediate smoke route and must remain absent/blocked unless
  separately licensed, provisioned, and authorized.

## Commands and hardware

Build the manifests on a networked provisioning machine, then attach the resulting private Kaggle
datasets. Generate paste-ready settings with:

```bash
python3 -m certvic.cvpr.kaggle_config --notebook 00A --out generated_configs
python3 -m certvic.cvpr.kaggle_config --notebook 00B --provider qwen2_5_vl_7b --out generated_configs
python3 -m certvic.cvpr.kaggle_config --notebook 00C2 --provider qwen2_5_vl_7b --out generated_configs
```

Repeat provider commands for InternVL and LLaVA. Expected provisioning time is 2–6 hours and disk
need is at least 40 GB plus snapshots. Validation is all-file hashing with no extras and internet
disabled at execution time.

## Retry and recovery

Resume incomplete downloads by provider. After any resumed download, hash the entire snapshot again;
never reuse an earlier root hash. A missing license record blocks task building, not just release.

