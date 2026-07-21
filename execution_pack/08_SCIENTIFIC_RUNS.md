# Scientific provider runs

After genuine review, exact selection, detectability, and task freeze pass, issue one matrix:

```bash
python3 -m certvic.cvpr.reconcile_provider_permissions issue-matrix \
  --inputs-json PRIVATE_EXACT_INPUTS.json \
  --out data/studies/specificity_confirmatory_cvpr/execution_permission.json
```

Derive one child per provider with `derive-provider --matrix ... --provider-config ... --smoke-gate
... --out ...`. Run notebooks 02, 03, and 04 in separate Kaggle T4x2 sessions. Inputs bind exact task,
review, detectability, code, environment, model, prompt, parser, and run-contract bytes. Budget 1–4
hours per provider; use the runtime planner for current estimates.

Each output ZIP must include the provider permission, immutable event chain, authorization proof,
runtime manifest, predictions, and member hashes. Validate final state `OUTPUT_PACKAGED`, expected row
universe, no extras/duplicates, and nonce uniqueness.

Retry only transient failures under the documented state machine. Never change frozen inputs or reuse
a consumed nonce. Main notebooks 11–13 and COCO notebooks 21–23 remain blocked until their separate
signed decisions and permissions exist.

