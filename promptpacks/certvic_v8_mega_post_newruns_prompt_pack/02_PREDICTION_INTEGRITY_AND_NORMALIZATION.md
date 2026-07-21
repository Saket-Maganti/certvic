# V8 Prediction Integrity Audit and Canonical Normalization

You are Codex operating inside the CertVIC repository as a careful ML systems engineer, reproducibility lead, statistical audit lead, and CVPR paper-hardening agent.

Repo:

/Users/saketmaganti/Projects/certVIC

New external outputs:

kaggleoutputs/newruns

Critical context:
- The V7/T4×2 runbook-prep stage created Kaggle notebooks and bundles, but did not create model results.
- The user now says all four phase GPU runs were completed using the main200 bundle.
- Expected run families: spurious, perception_scaled, polarity, mechanism.
- Expected providers: qwen2_5_vl_7b, internvl_8b, llava_onevision_7b.
- Old external audit said the project was infrastructure-complete with a real 91-item pilot but not CVPR-main ready because scaled evidence, human validation, spurious/edit-realism controls, and paper compilation were missing.
- V8 must ingest and verify the new Kaggle outputs, not fabricate them.

Hard constraints:
- No fake predictions, no fake results, no fake human review, no fake citations.
- Do not weaken gates or thresholds.
- Do not mark paper_evidence=true unless existing repo policy explicitly permits it after real gates pass.
- Preserve old/canonical V7 artifacts; never overwrite without provenance.
- If a required artifact is missing, mark the step BLOCKED with exact missing files and next commands.
- All tests must remain CPU/local.
- No git commit unless explicitly asked.
- Keep result language pilot-only unless evidence gates explicitly promote a claim.


Task:
Validate all prediction JSONL files and normalize/copy them into canonical V8 result folders.

Input:

```text
data/results/main_real_200/v8_upgrade/newruns_file_inventory.json
kaggleoutputs/newruns
```

Create:

```text
data/results/main_real_200/v8_upgrade/prediction_integrity_audit.json
data/results/main_real_200/v8_upgrade/PREDICTION_INTEGRITY_AUDIT.md
data/results/main_real_200/v8_upgrade/canonical_prediction_manifest.json
data/results/main_real_200/v8_upgrade/CANONICAL_PREDICTION_MANIFEST.md
```

Canonical folders/files:

```text
data/results/main_real_200/kaggle_spurious/pred_qwen2_5_vl_7b_spurious_merged.jsonl
data/results/main_real_200/kaggle_spurious/pred_internvl_8b_spurious_merged.jsonl
data/results/main_real_200/kaggle_spurious/pred_llava_onevision_7b_spurious_merged.jsonl
data/results/main_real_200/kaggle_perception_scaled/pred_qwen2_5_vl_7b_perception_scaled_merged.jsonl
data/results/main_real_200/kaggle_perception_scaled/pred_internvl_8b_perception_scaled_merged.jsonl
data/results/main_real_200/kaggle_perception_scaled/pred_llava_onevision_7b_perception_scaled_merged.jsonl
data/results/main_real_200/kaggle_polarity/pred_qwen2_5_vl_7b_polarity.jsonl
data/results/main_real_200/kaggle_polarity/pred_internvl_8b_polarity.jsonl
data/results/main_real_200/kaggle_polarity/pred_llava_onevision_7b_polarity.jsonl
data/results/main_real_200/kaggle_mechanism/pred_qwen2_5_vl_7b_mechanism.jsonl
data/results/main_real_200/kaggle_mechanism/pred_internvl_8b_mechanism.jsonl
data/results/main_real_200/kaggle_mechanism/pred_llava_onevision_7b_mechanism.jsonl
```

Integrity checks:
- Valid JSONL and nonzero rows.
- Expected row counts: spurious 188/provider; perception_scaled 738/provider; polarity 728/provider; mechanism 364/provider.
- Provider and run tag match if fields exist.
- No duplicate stable IDs. If row schema lacks explicit ID, derive from task_id/item_id + image_variant + prompt/probe_family.
- Never use shard-only files as canonical merged files unless merged file is missing and you explicitly merge shards deterministically with a manifest.

Update task ledger entries `V8_01_prediction_integrity_audit` and `V8_02_prediction_normalization`.

Final answer required: normalized files, row counts, malformed/missing outputs, whether all 12 are ready.
