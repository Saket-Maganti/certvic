# Smoke handoff

Place exact 00A, 00B, and 00C2 returns in one private input directory, then run:

```bash
python3 -m certvic.cvpr.smoke_handoff \
  --artifacts-dir local_inputs/smoke_returns \
  --smoke-contract local_inputs/smoke_returns/smoke_contract.json \
  --model-registry configs/models/certvic_cvpr_model_registry.yaml \
  --environment-lock configs/runtime/kaggle_t4x2_environment.lock.json \
  --out-dir data/runtime/smoke_handoff
```

Inputs remain private and unchanged. Expected outputs are a three-provider reconciliation report,
machine diagnostics, and a `REAL_MODEL_SMOKE_PASSED` gate with strict importer-grade validation.
Hardware is local CPU; expected duration is under five minutes.

Validation requires all providers `PASS`, exact real-model identities, no synthetic fixture marker,
zero OOMs, complete model/CUDA teardown, and matching prompt/run-contract hashes. If any row fails,
use its stable error code and remediation. Do not edit artifacts; rerun only the failed external smoke
with newly issued permission where required.

