# CertVIC Real-Smoke Artifact Contract

Schema: `certvic.cvpr.smoke_artifact.v1`. Smoke is non-evidence and keeps
`paper_evidence=false`.

00A returns exactly `00A_environment.json`, `00A_environment_validation.json`, and
`00A_environment_bundle.zip`. 00B returns exactly `00B_<provider>_snapshot.json`, its validation
JSON, and its bundle ZIP. 00C2 returns `00C2_<provider>_real_model_smoke.zip` containing exactly:

- `predictions.jsonl`
- `runtime_manifest.json`
- `environment_manifest.json`
- `snapshot_manifest.json`
- `task_bundle_manifest.json`
- `validation_report.json`
- `hash_manifest.json`
- `authorization_proof.json`

The proof binds provider, model and processor revisions, snapshot manifest/root, environment, code,
parser, prompt, task bundle, and two-item fixture hashes. `hash_manifest.json` binds every other ZIP
member. 00C2 intentionally uses one logical shard on both T4x2 and the allowed single-GPU fallback;
the worker assignment, runtime manifest, validation, and packager must all say one.

Run the return gate without copying or renaming files:

```bash
python3 -m certvic.cvpr.smoke_handoff \
  --artifacts-dir <RETURNED_ARTIFACTS> \
  --smoke-contract <TRUSTED_SMOKE_CONTRACT.json> \
  --model-registry configs/models/certvic_cvpr_model_registry.yaml \
  --environment-lock configs/runtime/kaggle_t4x2_environment.lock.json \
  --out-dir <SMOKE_GATE_DIR>
```
