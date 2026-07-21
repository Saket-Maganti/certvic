# CertVIC 00C2 Canonical Package Guide

00C2 runs one intentional logical shard and calls `certvic.cvpr.package_run`. For
`REAL_MODEL_SMOKE`, the packager requires the verified snapshot manifest and creates
`00C2_<provider>_real_model_smoke.zip` directly. Do not call a second packager, rename files, edit
JSON, copy hashes, reset permission events, or modify the ZIP.

The exact ten members are:

- `predictions.jsonl`
- `runtime_manifest.json`
- `environment_manifest.json`
- `snapshot_manifest.json`
- `task_bundle_manifest.json`
- `validation_report.json`
- `hash_manifest.json`
- `authorization_proof.json`
- `provider_permission.json`
- `permission_events.jsonl`

`hash_manifest.json` binds every other member. Runtime, rows, validation, proof, and provider
permission carry the same run-contract and prompt-template hashes. The portable event chain ends at
`PACKAGE_WRITTEN`; the live provider state advances to `OUTPUT_PACKAGED` only after the validated
temporary ZIP is atomically promoted.

The only local handoff is the exact command printed by the notebook:

```text
python3 -m certvic.cvpr.smoke_handoff --artifacts-dir <RETURNED_ARTIFACTS> --smoke-contract <TRUSTED_SMOKE_CONTRACT> --model-registry configs/models/certvic_cvpr_model_registry.yaml --environment-lock configs/runtime/kaggle_t4x2_environment.lock.json --out-dir <SMOKE_GATE_DIR>
```

