
# CertVIC Strict Smoke Validation Guide

The real smoke gate is importer-grade and non-evidence. First build a trusted contract from exactly
two canonical tasks (four paired rows), exact snapshot/run-contract artifacts, the environment lock,
the code ZIP, and the frozen prompt hash:

```bash
python3 -m certvic.cvpr.smoke_contract --task-manifest <TWO_TASKS.jsonl>   --provider-contracts <PROVIDERS.json> --environment-lock <LOCK> --code-bundle <CODE.zip>   --prompt-template-hash <SHA256> --out <TRUSTED_CONTRACT.json>
python3 -m certvic.cvpr.smoke_gate --smoke-root <RETURNED_ROOT>   --model-registry configs/models/certvic_cvpr_model_registry.yaml   --smoke-contract <TRUSTED_CONTRACT.json> --out <REAL_MODEL_SMOKE_GATE.csv>
```

For every provider the gate verifies 00A, 00B, safe ZIP paths, duplicate/corrupt members, an exact
member hash manifest, raw prediction hash, runtime/environment/snapshot/run contracts, provider,
model and processor revisions, task/image/prompt/parser/code hashes, exact paired row universe,
schema v2, PARSE_OK, recomputed validation, zero failures/OOM, positive peak VRAM, and model cleanup.
Sparse, extra, duplicated, hand-written, or tampered returns fail. PASS never creates paper evidence;
it is only one input to signed study authorization.
