# V8 NewRuns Discovery and Inventory

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
Build a complete inventory of `kaggleoutputs/newruns` before any canonical ingestion.

Do not move files into canonical locations yet. This prompt only inventories and stages safely.

Create:

```text
data/results/main_real_200/v8_upgrade/newruns_file_inventory.json
data/results/main_real_200/v8_upgrade/NEWRUNS_FILE_INVENTORY.md
```

For every file under `kaggleoutputs/newruns`, record:
- relative_path, size_bytes, sha256, extension
- inferred_provider: qwen2_5_vl_7b / internvl_8b / llava_onevision_7b / unknown
- inferred_run_tag: spurious / perception_scaled / polarity / mechanism / unknown
- artifact_type: merged_pred / shard_pred / log / summary_json / runtime_manifest / zip / notebook / unknown
- jsonl_row_count and valid_jsonl if JSONL
- json_keys_sample for first 3 rows if JSONL
- zip_members if archive
- expected_output_match
- notes

Expected final files:

```text
pred_qwen2_5_vl_7b_spurious_merged.jsonl
pred_internvl_8b_spurious_merged.jsonl
pred_llava_onevision_7b_spurious_merged.jsonl
pred_qwen2_5_vl_7b_perception_scaled_merged.jsonl
pred_internvl_8b_perception_scaled_merged.jsonl
pred_llava_onevision_7b_perception_scaled_merged.jsonl
pred_qwen2_5_vl_7b_polarity.jsonl
pred_internvl_8b_polarity.jsonl
pred_llava_onevision_7b_polarity.jsonl
pred_qwen2_5_vl_7b_mechanism.jsonl
pred_internvl_8b_mechanism.jsonl
pred_llava_onevision_7b_mechanism.jsonl
```

Inspect any `*_run_preds.zip` contents, but extract only into:

```text
data/results/main_real_200/v8_upgrade/staging/newruns_extracted/
```

Never extract archives destructively into canonical folders.

Update `v8_task_ledger.json` entry `V8_00_newruns_discovery`.

Final answer required: file counts, JSONL counts, expected found/missing, staged extraction status, inventory paths.
