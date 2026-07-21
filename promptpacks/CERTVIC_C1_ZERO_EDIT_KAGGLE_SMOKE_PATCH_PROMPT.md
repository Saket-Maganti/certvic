# CERTVIC — C.1 ZERO-EDIT KAGGLE SMOKE PATCH AND FIRST-RUN HANDOFF

## Scope

This is a narrow execution-defect repair. Do not begin another broad audit, rebuild, or scientific redesign.

Phase A, Phase B, and Phase C are complete. Preserve the corrected scientific protocol, frozen endpoints, immutable model identities, evidence boundaries, wheelhouse, reports, release lineage, and all valid tests.

The current canonical 00A, 00B, and 00C2 notebooks still expose a large `REQUIRED_USER_FILL` configuration block. The first-wave handoff identifies datasets and hashes but does not provide a genuinely zero-edit, directly runnable notebook configuration. Fix that execution defect now.

## Repository

```text
/Users/saketmaganti/Projects/certVIC
```

Read first:

```text
reports/cpu_execution/CERTVIC_FIRST_GPU_WAVE_HANDOFF.md
reports/non_human_closure/CERTVIC_NON_HUMAN_EXECUTION_FINAL_HANDOFF.md
reports/non_human_closure/CERTVIC_NON_HUMAN_CLOSURE_VALIDATION.md
kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md
kaggle_uploads/CERTVIC_KAGGLE_UPLOAD_MANIFEST.csv
```

## Frozen boundary

Do not alter:

- scientific protocol or primary endpoints;
- statistical thresholds;
- task definitions;
- prompt/parser contracts;
- historical evidence;
- model commits;
- `paper_evidence=false`;
- human-review state;
- Main/COCO authorization;
- any completed wheelhouse or bundle bytes unless regeneration is required by this patch.

Do not claim that 00A, 00B, or 00C2 has been executed.

## Required correction

### 1. Make 00A genuinely zero-edit

Regenerate:

```text
notebooks/kaggle/cvpr/00A_certvic_code_and_environment_smoke.ipynb
```

It must run without the user editing paths, hashes, or unrelated placeholders.

It must automatically:

1. discover these attached private Kaggle datasets by exact slug and filename:
   - `certvic/certvic-code` / `certvic_code_bundle.zip`
   - `certvic/certvic-configs` / `certvic_configs_bundle.zip`
   - `certvic/certvic-execution-tools` / `certvic_execution_tools_bundle.zip`
   - `certvic/certvic-offline-wheelhouse` / `certvic_offline_wheelhouse.zip`
2. verify each bundle before extraction;
3. safely extract the code and wheelhouse ZIPs into `/kaggle/working`;
4. discover exactly one project root;
5. derive the environment-lock path from the extracted authoritative project/config bundle;
6. compute the canonical environment-lock hash in code rather than asking the user to type it;
7. locate and verify `wheelhouse_manifest.json`;
8. install or accept the exact environment according to the frozen policy;
9. run CPU/environment checks with accelerator off and Internet off;
10. emit exactly:
   ```text
   /kaggle/working/00A_environment_bundle.zip
   ```
11. print the exact download filename and local destination:
   ```text
   data/runtime/00A_environment_bundle.zip
   ```
12. require no manual configuration cell edits.

The known code-bundle hash currently recorded by the handoff is:

```text
bc038cc970c3a32e31f9452fc5af656399723177e2158485b67cf9f958c07853
```

The known wheelhouse archive hash is:

```text
d62fe562ee7d012062c03fad3537f0a4da71e0e860b04b9dc7b6f942f4d15bda
```

Do not hard-code these blindly if the live bundle manifests provide the authoritative values. Verify live bytes and update handoffs consistently if hashes have legitimately changed.

### 2. Make 00B provider-specific and zero-edit

Create three ready-to-run notebooks or three generated parameter variants:

```text
00B_qwen2_5_vl_7b_snapshot_smoke.ipynb
00B_internvl_8b_snapshot_smoke.ipynb
00B_llava_onevision_7b_snapshot_smoke.ipynb
```

Each notebook must automatically discover:

- the common code/config/tools/wheelhouse datasets;
- exactly one matching provider snapshot dataset;
- the unified snapshot root;
- the snapshot manifest;
- the immutable model and processor commits;
- expected architecture;
- snapshot root hash;
- all required file hashes.

No user should type model IDs, commits, paths, architecture names, manifest hashes, or output names.

Each notebook must remain CPU-only, must not load the model, and must emit exactly:

```text
00B_qwen2_5_vl_7b_snapshot_bundle.zip
00B_internvl_8b_snapshot_bundle.zip
00B_llava_onevision_7b_snapshot_bundle.zip
```

If a snapshot is absent, fail immediately with one stable error that names the exact missing Kaggle dataset slug.

### 3. Prepare provider-specific 00C2 notebooks

Create three provider-specific 00C2 notebooks:

```text
00C2_qwen2_5_vl_7b_real_model_two_item_smoke.ipynb
00C2_internvl_8b_real_model_two_item_smoke.ipynb
00C2_llava_onevision_7b_real_model_two_item_smoke.ipynb
```

They must auto-discover all required datasets and permission artifacts.

The only remaining operator action should be:

- attach the listed datasets;
- select T4×2 or the allowed single-T4 fallback;
- keep Internet off;
- click Run All.

No prompt, path, hash, permission ID, model ID, commit, task path, or output filename should require manual editing.

Do not authorize or execute 00C2. These notebooks must remain fail-closed until the real smoke bundle and pre-smoke permissions exist.

### 4. Safe ZIP extraction

The attached Kaggle datasets contain canonical ZIP archives. Add a shared helper that:

- locates an exact dataset slug and exact filename;
- verifies the outer bundle;
- rejects traversal, duplicates, corruption, unsafe links, and ambiguous files;
- extracts to a deterministic `/kaggle/working` path;
- discovers the unique manifest/root;
- verifies all inner files;
- returns resolved paths and hashes.

Do not assume Kaggle automatically extracts ZIP members.

### 5. Update execution documentation

Create:

```text
reports/non_human_closure/CERTVIC_KAGGLE_ZERO_EDIT_SMOKE_HANDOFF.md
```

It must contain separate cards for:

- 00A;
- 00B Qwen;
- 00B InternVL;
- 00B LLaVA;
- 00C2 Qwen;
- 00C2 InternVL;
- 00C2 LLaVA.

Each card must list:

- notebook filename;
- Kaggle accelerator;
- Internet setting;
- exact private dataset slugs;
- exact attached filenames;
- expected mounts;
- expected return ZIP;
- local destination;
- exact resume command;
- estimated runtime;
- stable failure codes;
- no manual edits required.

Update:

```text
reports/cpu_execution/CERTVIC_FIRST_GPU_WAVE_HANDOFF.md
kaggle_uploads/CERTVIC_KAGGLE_UPLOAD_MANIFEST.csv
kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

Remove language telling the user to fill a large configuration cell.

### 6. Notebook validation

For all new notebooks:

- clear outputs and execution counts;
- validate JSON;
- run Ruff-compatible source extraction;
- run static notebook validation;
- run synthetic execution with mounted fixture datasets that preserve the real discovery/extraction flow;
- verify exact canonical return filenames;
- verify zero `REQUIRED_USER_FILL` values on active execution paths;
- verify 00A and 00B require zero GPUs;
- verify 00C2 requires GPU and fails before model load if permissions or real task bytes are missing;
- verify no Internet dependency in scientific mode.

Add regression tests that scan active notebook cells for unresolved runtime placeholders.

### 7. Final validation

Run:

```bash
python3 -m pytest -q
python3 -m ruff check --no-cache certvic scripts tests
python3 -m compileall -q certvic scripts tests
python3 -m certvic.cvpr.notebook_validation --root notebooks/kaggle/cvpr
python3 scripts/validate_t4x2_notebooks.py
python3 -m certvic.cvpr.artifact_registry verify
python3 -m certvic.cvpr.doctor --json
```

Also run claim, privacy, path, deterministic release, and clean-extraction checks.

Preserve:

```text
paper_evidence=false
genuine human_reviewed=true count = 0
Main execution_allowed=false
COCO execution_allowed=false
```

## Required terminal status

Use only after all checks pass:

```text
CERTVIC_ZERO_EDIT_KAGGLE_SMOKE_PATCH_COMPLETE
00A_READY_TO_RUN_WITH_NO_MANUAL_CONFIGURATION
00B_PROVIDER_NOTEBOOKS_READY_WITH_NO_MANUAL_CONFIGURATION
00C2_PROVIDER_NOTEBOOKS_READY_AND_FAIL_CLOSED
FIRST_EXTERNAL_ACTION_RUN_00A
```

## Required final response

Report:

1. exact files changed;
2. exact notebook names;
3. proof that no active placeholder remains;
4. exact 00A dataset attachments;
5. exact 00A expected output;
6. all validation totals;
7. final release hash;
8. the single next action:
   ```text
   RUN 00A ON KAGGLE CPU WITH INTERNET OFF
   ```
