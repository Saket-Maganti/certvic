# Zero-Cost Policy

The core CertVIC workflow permits:

- local CPU/Mac execution
- free Kaggle GPU
- free Colab fallback
- open-source/local models
- public/free datasets with license checks

The core workflow forbids:

- paid APIs
- paid cloud GPU
- paid datasets
- paid annotation
- paid storage
- paid experiment tracking
- hidden paid model endpoints

Optional free-tier references are disabled by default, version-labeled,
reference-only, and never required for reproducibility.

## Recipe-first release (V2)

The release artifact (`certvic.release.build_artifact`) contains pointers, hashes,
and metadata only. No non-redistributable pixels are rehosted; users regenerate
images/edits from source pointers. The release audit emits a zero-cost statement
asserting all steps run on local CPU/Mac or free Kaggle/Colab GPU.

## Storage discipline (V3)

Free-tier disk is finite: Kaggle `/kaggle/working` is ~20 GB and Colab ~70 GB.
`certvic.storage.plan_storage` estimates the working set per study and warns
before a run would overflow the quota. Diffusion weight caches are loaded from a
Kaggle **input** dataset (not the working dir), and rejected-edit pixels are
deleted after their hashes are recorded. No paid storage is ever used.

## Security / privacy audit (V3)

Before any artifact release, scan for leaked private paths, secrets/credentials,
committed `.env` files, paid endpoints, and accidental pixels:

```bash
python3 -m certvic.security.release_privacy_audit --root . --out docs/SECURITY_PRIVACY_AUDIT.md
```

The audit exits non-zero on any finding and confirms no paid endpoints are wired
in. See `docs/SECURITY_PRIVACY_POLICY.md`.
