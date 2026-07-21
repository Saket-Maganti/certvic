
# CertVIC Model Snapshot Manifest Guide

The 40-character revision is a label until the mounted files are proven. Create a manifest only from
the exact local directory that will be attached to Kaggle:

```bash
python3 -m certvic.cvpr.model_snapshot_manifest create   --snapshot <SNAPSHOT> --model-id <MODEL_ID>   --model-commit <40_HEX> --processor-commit <40_HEX>   --architecture <EXPECTED_CLASS>
sha256sum <SNAPSHOT>/certvic_model_snapshot_manifest.json
```

The manifest records every regular file, size and SHA-256; config architecture/model type;
tokenizer/processor files; weight files; model and processor commits; and an offline-only rule. Run
`verify` with all expected fields before any adapter load. Verification rejects missing or extra files,
modified bytes, architecture drift, processor omissions, fake revisions, and manifests that permit
network access. Copy the manifest-file SHA-256 into the frozen runtime config and registry. A changed
snapshot requires a new manifest and run version; never relabel old outputs.
