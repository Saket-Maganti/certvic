# PHASE A COORDINATION OVERRIDE

This is Phase A of the final coordinated CertVIC execution workflow.

Complete the full Kaggle input-bundle and T4×2 runbook contract below, but **do not launch any real GPU/Kaggle scientific runs** during this phase.

At completion, create:

```text
reports/kaggle_execution_pack/CERTVIC_KAGGLE_READY_FOR_PHASE_B_HANDOFF.md
```

That handoff must state exactly what was built, what external bytes remain missing, which CPU workflows Phase B must execute, and the exact command to begin Phase B.

Required terminal status:

```text
PHASE_A_KAGGLE_PACKAGING_COMPLETE
ALL_BUILDABLE_UPLOAD_ZIPS_CREATED
ALL_EXTERNAL_BUNDLE_BUILDERS_READY
ALL_16_RUNBOOKS_VALIDATED
READY_FOR_PHASE_B_CPU_EXECUTION
```

Do not call the project globally blocked merely because model weights, Linux wheels, licensed datasets, or human review are external. Use `BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES` for those items when the builder and validation path are complete.

---

# CERTVIC — COMPLETE KAGGLE INPUT-BUNDLE FACTORY, T4×2 PARALLEL RUNBOOKS, AND ZERO-ERROR EXECUTION PACK MASTER PROMPT

## Role

You are operating as the lead Kaggle execution engineer, offline dependency engineer, VLM deployment engineer, dual-GPU orchestration engineer, artifact-packaging engineer, benchmark architect, provenance engineer, reproducibility engineer, release engineer, and critical CVPR co-author for **CertVIC**.

This task is not another audit.

Your job is to build the complete execution layer required to take CertVIC from the current maximum-ceiling pre-run repository to a **fully packaged Kaggle execution system**.

The repository already contains the scientific framework, authorization split, notebook suite, doctor, next-action tool, run graph, artifact registry, recovery layer, and maximum-ceiling release.

Now finish the missing execution assets:

1. Create every Kaggle input ZIP that can be created from current repository bytes.
2. Create deterministic builders for every ZIP that depends on external assets.
3. Generate or regenerate all ready-to-run `.ipynb` runbooks.
4. Make the heavy notebooks truly compatible with Kaggle T4×2 parallel execution.
5. Add deterministic seed handling across both GPUs and all shards.
6. Ensure all dependencies are installed or loaded correctly without internet assumptions.
7. Execute synthetic notebook proofs for every runbook.
8. Produce exact runtime and resource estimates.
9. Produce one complete upload/execute/download/import handbook.
10. Leave no hidden manual packaging steps.

The desired status is:

```text
KAGGLE_EXECUTION_PACK_COMPLETE
ALL_BUILDABLE_INPUT_ZIPS_CREATED
ALL_EXTERNAL_INPUT_BUILDERS_READY
ALL_T4X2_RUNBOOKS_VALIDATED
LOCAL_PRE_RUN_READINESS_10_OF_10
```

Use this status only when all locally buildable ZIPs exist, all external-dependent bundles have validated builders and schemas, every notebook passes execution proof, and the only missing bytes are genuinely external model/data assets.

If a bundle cannot be physically created because the source files are unavailable, do not fabricate it. Report:

```text
BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES
```

and provide the exact builder command, required directory layout, expected size, validation procedure, and output ZIP name.

---

# 1. Repository

```text
/Users/saketmaganti/Projects/certVIC
```

Treat the live checkout as authoritative.

The `kaggleoutputs/` directory was intentionally removed to save space. Do not recreate historical outputs merely to satisfy old paths.

New Kaggle outputs must use the current canonical return-ZIP and transactional-import pipeline.

Preserve frozen evidence, provider outputs still present elsewhere, evidence and gate ledgers, review originals, scientific configs, current authorization split, and user-owned files.

Do not initialize Git when absent. Do not commit or push unless explicitly requested.

---

# 2. Frozen evidence boundary

Do not change:

- Qwen2.5-VL-7B V1: `12/94 = 0.1277`.
- InternVL2-8B V1: `1/94 = 0.0106`.
- LLaVA-OneVision-7B V1: `3/94 = 0.0319`.
- Frozen V1 rule: `observed_spurious_flip_rate <= 0.10`.
- Qwen fails the frozen V1 rule.
- V2-30 remains retrospective sensitivity evidence.
- Confirmatory remains prospective and zero-overlap with V1.
- Main remains blocked until confirmatory and human-review gates pass.
- COCO remains feasibility-only until real execution.
- `paper_evidence=false`.
- Genuine `human_reviewed=true` count remains zero until actual review.
- No model output, human label, model commit, metric, or runtime may be fabricated.
- No thresholds, prompts, expected answers, revisions, item filters, or analysis rules may be tuned after observing real outcomes.

Synthetic fixtures must remain:

```text
paper_evidence=false
synthetic_fixture=true
```

---

# 3. Primary mission

By the end of this task, the repository must contain:

## 3.1 Upload bundles already buildable from repository bytes

Create all possible ZIPs now, including:

```text
kaggle_uploads/00_code/certvic_code_bundle.zip
kaggle_uploads/00_code/certvic_notebooks_bundle.zip
kaggle_uploads/00_code/certvic_configs_bundle.zip
kaggle_uploads/00_code/certvic_execution_tools_bundle.zip
kaggle_uploads/00_code/certvic_synthetic_validation_bundle.zip
```

Create any additional code/config bundles that reduce Kaggle setup friction.

## 3.2 External-dependent bundle builders

Create deterministic builders for:

```text
kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip
kaggle_uploads/02_snapshots/qwen2_5_vl_7b_snapshot.zip
kaggle_uploads/02_snapshots/internvl2_8b_snapshot.zip
kaggle_uploads/02_snapshots/llava_onevision_7b_snapshot.zip
kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip
kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip
kaggle_uploads/05_confirmatory/certvic_confirmatory_generation_input.zip
kaggle_uploads/06_confirmatory_runs/certvic_confirmatory_qwen_input.zip
kaggle_uploads/06_confirmatory_runs/certvic_confirmatory_internvl_input.zip
kaggle_uploads/06_confirmatory_runs/certvic_confirmatory_llava_input.zip
kaggle_uploads/07_main/certvic_main_generation_input.zip
kaggle_uploads/08_main_runs/certvic_main_qwen_input.zip
kaggle_uploads/08_main_runs/certvic_main_internvl_input.zip
kaggle_uploads/08_main_runs/certvic_main_llava_input.zip
kaggle_uploads/09_coco/certvic_coco_generation_input.zip
kaggle_uploads/10_coco_runs/certvic_coco_qwen_input.zip
kaggle_uploads/10_coco_runs/certvic_coco_internvl_input.zip
kaggle_uploads/10_coco_runs/certvic_coco_llava_input.zip
```

Some of these will be blocked until real external files or upstream gates exist. Their builders must still be complete and tested with synthetic fixtures.

## 3.3 Ready-to-run notebooks

Regenerate and validate all 16 canonical notebooks:

```text
00A_certvic_code_and_environment_smoke.ipynb
00B_certvic_model_snapshot_smoke.ipynb
00C2_certvic_real_model_two_item_smoke.ipynb

01_specificity_confirmatory_generation_T4x2.ipynb
02_qwen_specificity_confirmatory_T4x2.ipynb
03_internvl_specificity_confirmatory_T4x2.ipynb
04_llava_specificity_confirmatory_T4x2.ipynb

10_main_study_generation_T4x2.ipynb
11_qwen_main_study_T4x2.ipynb
12_internvl_main_study_T4x2.ipynb
13_llava_main_study_T4x2.ipynb

20_second_domain_generation_T4x2.ipynb
21_second_domain_qwen_T4x2.ipynb
22_second_domain_internvl_T4x2.ipynb
23_second_domain_llava_T4x2.ipynb
```

Every notebook must be upload-ready, output-free in the repository, dependency-safe, and synthetically executable.

---

# 4. Hard restrictions

## 4.1 No external-byte fabrication

Do not create fake wheel files, model weights, processors, tokenizers, source images, licenses, human reviews, real permissions, or provider predictions.

## 4.2 No network dependence during scientific notebooks

The scientific notebooks must run with:

```text
internet disabled
local_files_only=true
```

after required Kaggle datasets are attached.

If an optional network-enabled provisioning notebook is created, label it clearly as a separate provisioning-only path and never use it for scientific evidence.

## 4.3 No hidden manual steps

The user must not need to rename files, edit manifests, change hashes, manually merge shards, manually rewrite paths, guess dataset mount names, or reconstruct permissions.

---

# PHASE 0 — Baseline and inventory

Run full pytest, notebook validation, T4×2 validation, doctor, next-action, run graph, artifact-registry verification, release audit, claim guard, privacy guard, and paper build.

Inventory current ZIPs, notebooks, configs, wheel requirements, snapshot manifests, source-data requirements, permission inputs, and expected Kaggle outputs.

Create:

```text
reports/kaggle_execution_pack/CERTVIC_KAGGLE_PACK_SESSION.md
reports/kaggle_execution_pack/CERTVIC_KAGGLE_PACK_INVENTORY.csv
reports/kaggle_execution_pack/CERTVIC_KAGGLE_PACK_CHANGELOG.csv
reports/kaggle_execution_pack/CERTVIC_KAGGLE_PACK_COMMANDS.csv
```

---

# PHASE 1 — Canonical Kaggle bundle schema

Create:

```text
certvic/cvpr/kaggle_bundle.py
```

Every upload bundle must contain:

```text
bundle_manifest.json
hash_manifest.json
README.md
```

The manifest must record schema version, bundle type, study, stage, provider, created time, file list, sizes, SHA-256 values, required notebook, expected Kaggle dataset slug, mount path, external dependency status, evidence class, builder command, and validation command.

Use:

```text
certvic.kaggle.bundle.v1
```

Provide:

```bash
python3 -m certvic.cvpr.kaggle_bundle verify <ZIP>
python3 -m certvic.cvpr.kaggle_bundle inspect <ZIP>
python3 -m certvic.cvpr.kaggle_bundle diff <ZIP_A> <ZIP_B>
```

Reject traversal, duplicates, unsafe symlinks, unexpected files, missing hashes, and host-specific absolute paths.

---

# PHASE 2 — Code and notebook upload bundles

Build now:

```text
kaggle_uploads/00_code/certvic_code_bundle.zip
kaggle_uploads/00_code/certvic_notebooks_bundle.zip
kaggle_uploads/00_code/certvic_configs_bundle.zip
kaggle_uploads/00_code/certvic_execution_tools_bundle.zip
kaggle_uploads/00_code/certvic_synthetic_validation_bundle.zip
```

The code bundle includes `certvic/`, required scripts, `pyproject.toml`, runtime configs, licenses, and release metadata.

Exclude datasets, snapshots, weights, historical outputs, caches, incoming archives, private review sheets, and host paths.

Build each twice and require byte identity.

---

# PHASE 3 — Offline Linux wheelhouse builder

Create:

```text
certvic/cvpr/wheelhouse_builder.py
scripts/build_kaggle_wheelhouse.py
```

Target the real Kaggle Linux/Python/CUDA environment.

Create locks:

```text
requirements/kaggle_base.lock
requirements/kaggle_qwen.lock
requirements/kaggle_internvl.lock
requirements/kaggle_llava.lock
requirements/kaggle_generation.lock
requirements/kaggle_analysis.lock
```

Expected output:

```text
kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip
```

Include wheel files, lock files, package hash manifest, installation script, compatibility report, smoke-import script, and README.

Notebooks must install with:

```bash
pip install --no-index --find-links <wheelhouse> -r <lock>
```

Use `--require-hashes` where feasible.

Support:

```text
LOCAL_VERIFY_ONLY
LINUX_CONTAINER_BUILD
KAGGLE_PROVISIONING_BUILD
```

Never package macOS wheels as Kaggle Linux wheels.

If Linux-compatible bytes are unavailable, report `BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES`.

Validate imports for torch, torchvision, transformers, accelerate, tokenizers, safetensors, sentencepiece, PIL, numpy, scipy, pandas, sklearn, OpenCV when required, model-specific packages, generation dependencies, and project modules.

---

# PHASE 4 — Model snapshot bundle factory

Create:

```text
certvic/cvpr/snapshot_bundle_builder.py
scripts/build_model_snapshot_bundle.py
```

Support Qwen2.5-VL-7B, InternVL2-8B, and LLaVA-OneVision-7B.

For each provider:

- validate required files;
- reject partial downloads;
- reject external symlinks;
- record real revision/commit when available;
- hash every file;
- validate tokenizer and processor;
- perform local-files-only import smoke;
- create canonical snapshot manifest;
- create ZIP or Kaggle-dataset-ready directory.

Outputs:

```text
kaggle_uploads/02_snapshots/qwen2_5_vl_7b_snapshot.zip
kaggle_uploads/02_snapshots/internvl2_8b_snapshot.zip
kaggle_uploads/02_snapshots/llava_onevision_7b_snapshot.zip
```

If bytes are missing, create required-file checklists, directory trees, size estimators, configs, validation commands, and blocked reports. Do not create placeholder weights.

---

# PHASE 5 — Real two-item smoke input bundle

Create:

```text
certvic/cvpr/smoke_input_builder.py
```

Output:

```text
kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip
```

Bundle must contain exactly two trusted smoke tasks, portable source/edited images, required masks/assets, task manifest, task-bundle manifest, smoke contract, prompt/parser/run-contract hashes, licensing metadata, validation report, and README.

The builder must accept real licensed files, refuse synthetic fixtures in real mode, verify bytes, verify zero historical overlap, verify portability, enforce cardinality, and produce stable hashes.

---

# PHASE 6 — Pre-smoke permission bundle

Create:

```text
certvic/cvpr/pre_smoke_packager.py
```

Output:

```text
kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip
```

Include pre-smoke matrix authorization, three child permissions, environment identity, snapshot identities, code hash, prompt hash, parser version, run-contract hashes, task-bundle hash, and README.

Create only after valid 00A, all three 00B artifacts, the real smoke bundle, and the code bundle exist. Before that, provide a tested builder and explicit blocked report.

---

# PHASE 7 — Confirmatory generation input pack

Create:

```text
certvic/cvpr/confirmatory_input_builder.py
```

Output:

```text
kaggle_uploads/05_confirmatory/certvic_confirmatory_generation_input.zip
```

Include unseen source manifest, exclusion inventory, generation config, source image references or redistributable bytes, insertion assets, masks, licenses, engine policy, seed plan, shard plan, resume ledger, and README.

Fail closed when licenses or bytes are missing.

---

# PHASE 8 — Scientific provider input packs

Create one builder supporting confirmatory, Main, and COCO.

Expected outputs include confirmatory, Main, and COCO provider-specific ZIPs for Qwen, InternVL, and LLaVA.

Each bundle binds final task bundle, task freeze, review ledger, detectability gate, environment lock, model registry, snapshot manifest, code hash, prompt hash, run contract, parent authorization, child permission, schema, run tag, and README.

Do not create real scientific bundles before upstream gates exist. Provide synthetic proof for every builder.

---

# PHASE 9 — T4×2 dual-GPU orchestration

Create or upgrade:

```text
certvic/cvpr/t4x2.py
```

Detect zero, one, or two GPUs and unexpected accelerator types.

For heavy notebooks:

```text
two T4s → dual-shard parallel mode
one T4 → validated sequential fallback
zero GPUs → fail before model load
```

00A and 00B may inspect both GPUs. 00C2 may intentionally use one logical shard but must document this consistently.

## Deterministic seed hierarchy

Create:

```text
global_seed
study_seed
provider_seed
gpu_seed
shard_seed
task_seed
generation_attempt_seed
```

Use stable hash-derived seeds and write `seed_manifest.json` into every generation and scientific output.

Seeds must not collide across providers, GPUs, shards, tasks, retries, or engines.

## Parallel execution

- launch one worker per GPU;
- pin `CUDA_VISIBLE_DEVICES`;
- separate outputs and logs;
- deterministic shard assignment;
- merge only after validation;
- resume per shard;
- prefer independent sharding over unnecessary DDP.

## OOM recovery

Use a prospective fallback ladder:

1. reduce batch size;
2. switch approved attention implementation;
3. use conservative dtype/config;
4. single-GPU sequential fallback;
5. stop and report.

Do not alter prompts, items, or scientific rules to hide failures.

---

# PHASE 10 — Notebook dependency bootstrap

Create:

```text
certvic/cvpr/notebook_bootstrap.py
```

Every notebook must:

1. declare run identity;
2. locate Kaggle datasets;
3. validate code bundle;
4. locate wheelhouse;
5. install offline;
6. print package versions;
7. run import smoke;
8. detect GPUs;
9. verify snapshot/source bundle;
10. verify permission;
11. derive prompt/run-contract hashes;
12. create workspace;
13. execute workload.

Fail with stable error codes. Do not duplicate fragile bootstrap logic.

---

# PHASE 11 — Regenerate all runbooks

Regenerate all 16 notebooks using the canonical builder.

Every notebook must include:

- title and evidence warning;
- required upload datasets;
- configuration cell;
- offline dependency installation;
- import smoke;
- T4×2 detection;
- deterministic seed plan;
- input verification;
- permission checks;
- resumable execution;
- progress reporting;
- peak VRAM tracking;
- shard validation;
- strict packaging;
- exact output ZIP name;
- exact local handoff command;
- runtime estimate;
- troubleshooting.

Repository notebooks must have null execution counts and empty outputs.

---

# PHASE 12 — Actual notebook execution proof

Use the notebook runner to execute synthetic versions of every notebook.

At minimum prove 00A, 00B, all three 00C2 providers, confirmatory generation and all three providers, Main generation and all three providers, COCO generation and all three providers, and post-run import/handoff.

Preserve actual control flow with mock adapters and tiny fixtures.

Verify dependency bootstrap, input discovery, GPU branching, seed manifest, output packaging, expected ZIP filename, and output clearing.

---

# PHASE 13 — Runtime estimation and calibration

Create:

```text
reports/kaggle_execution_pack/CERTVIC_KAGGLE_RUNTIME_ESTIMATES.csv
reports/kaggle_execution_pack/CERTVIC_KAGGLE_RUNTIME_ESTIMATES.md
```

For every notebook record CPU/GPU class, accelerator, dual-GPU behavior, task count, batch size, wall time, individual GPU-hours, VRAM, output size, checkpoints, Kaggle risk, single-T4 time, evidence basis, and confidence.

Use planning ranges before real smoke, then recalibrate from observed 00C2 manifests.

Initial ranges to review:

```text
00A: 10–20 min
00B: 15–30 min per provider
00C2: 15–45 min per provider

Confirmatory generation: 2–5 h
Confirmatory Qwen: 2–5 h
Confirmatory InternVL: 3–7 h
Confirmatory LLaVA: 2–5 h

Main generation: 4–10 h, with 8–18 h conservative reserve
Main Qwen: 5–10 h
Main InternVL: 8–16 h
Main LLaVA: 5–10 h

COCO generation: 2–5 h
COCO Qwen: 1–2 h
COCO InternVL: 1.5–3 h
COCO LLaVA: 1–2 h
```

Distinguish dual-GPU notebook-hours, individual T4 GPU-hours, CPU hours, and human-review person-hours.

---

# PHASE 14 — Upload manifest and dataset map

Create:

```text
kaggle_uploads/CERTVIC_KAGGLE_UPLOAD_MANIFEST.csv
kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md
```

For each notebook list filename, required ZIPs, Kaggle dataset slug, mount path, size, status, builder, hash, user action, expected output ZIP, and next local command.

Statuses:

```text
CREATED_AND_VALIDATED
BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES
BLOCKED_BY_UPSTREAM_GATE
CONDITIONAL_ON_CONFIRMATORY
```

---

# PHASE 15 — One-command bundle factory

Create:

```text
certvic/cvpr/build_all_kaggle_inputs.py
```

Commands:

```bash
python3 -m certvic.cvpr.build_all_kaggle_inputs --local-only
python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots config.yaml
python3 -m certvic.cvpr.build_all_kaggle_inputs --status
```

`--local-only` builds all possible repository-only ZIPs.

`--with-external-roots` accepts wheelhouse, snapshots, smoke source, ADE20K, COCO, and insertion asset roots.

Build available bundles and report precise blockers for unavailable ones.

---

# PHASE 16 — Output ZIP contracts

Every notebook must create one canonical return ZIP.

Examples:

```text
00A_environment_bundle.zip
00B_qwen2_5_vl_7b_snapshot_bundle.zip
00B_internvl2_8b_snapshot_bundle.zip
00B_llava_onevision_7b_snapshot_bundle.zip

00C2_qwen2_5_vl_7b_real_model_smoke.zip
00C2_internvl2_8b_real_model_smoke.zip
00C2_llava_onevision_7b_real_model_smoke.zip

confirmatory_qwen_return.zip
confirmatory_internvl_return.zip
confirmatory_llava_return.zip

main_qwen_return.zip
main_internvl_return.zip
main_llava_return.zip

coco_qwen_return.zip
coco_internvl_return.zip
coco_llava_return.zip
```

Return ZIPs must include predictions/generated artifacts, runtime manifest, environment manifest, snapshot manifest when applicable, task-bundle manifest, seed manifest, validation report, hash manifest, authorization proof, provider permission/events when applicable, logs, and resume state.

---

# PHASE 17 — Failure playbooks

Create:

```text
execution_pack/11_KAGGLE_UPLOAD_BUNDLES.md
execution_pack/12_T4X2_PARALLEL_EXECUTION.md
execution_pack/13_DEPENDENCY_FAILURES.md
execution_pack/14_MODEL_SNAPSHOT_FAILURES.md
execution_pack/15_OOM_AND_RESUME.md
execution_pack/16_RETURN_ZIP_HANDOFF.md
```

Cover mount errors, missing wheels, dependency conflicts, Torch/CUDA mismatch, tokenizer errors, unsupported kernels, one-GPU fallback, OOM, restart, partial shards, disk full, ZIP failure, corrupted downloads, permission mismatch, stale prompt/run contract, and transaction recovery.

---

# PHASE 18 — Potential upgrades

Implement only if useful:

- private Kaggle dataset metadata/publisher helper;
- duplicate-file and bundle-size optimizer;
- multi-part snapshot archive support;
- run-cost ledger for notebook hours, GPU-hours, retries, storage, and human time;
- static execution dashboard;
- dry-run config linter.

---

# PHASE 19 — Release integration

Update the maximum release to include all builders, repository-only upload ZIPs, notebooks, manifests, estimates, maps, guides, synthetic fixtures, and tests.

Exclude real weights, private datasets, unavailable bytes, human reviews, secrets, caches, old `kaggleoutputs/`, and non-release historical returns.

Build twice and require byte identity.

---

# PHASE 20 — Required deliverables

Create or update:

```text
kaggle_uploads/
kaggle_uploads/CERTVIC_KAGGLE_UPLOAD_MANIFEST.csv
kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md

reports/kaggle_execution_pack/CERTVIC_KAGGLE_PACK_SESSION.md
reports/kaggle_execution_pack/CERTVIC_KAGGLE_PACK_INVENTORY.csv
reports/kaggle_execution_pack/CERTVIC_KAGGLE_PACK_CHANGELOG.csv
reports/kaggle_execution_pack/CERTVIC_KAGGLE_PACK_COMMANDS.csv
reports/kaggle_execution_pack/CERTVIC_KAGGLE_PACK_VALIDATION.md
reports/kaggle_execution_pack/CERTVIC_KAGGLE_RUNTIME_ESTIMATES.csv
reports/kaggle_execution_pack/CERTVIC_KAGGLE_RUNTIME_ESTIMATES.md
reports/kaggle_execution_pack/CERTVIC_KAGGLE_PACK_SCORECARD.md
reports/kaggle_execution_pack/CERTVIC_KAGGLE_READY_TO_UPLOAD_HANDOFF.md

certvic/cvpr/kaggle_bundle.py
certvic/cvpr/wheelhouse_builder.py
certvic/cvpr/snapshot_bundle_builder.py
certvic/cvpr/smoke_input_builder.py
certvic/cvpr/pre_smoke_packager.py
certvic/cvpr/confirmatory_input_builder.py
certvic/cvpr/scientific_input_builder.py
certvic/cvpr/t4x2.py
certvic/cvpr/notebook_bootstrap.py
certvic/cvpr/build_all_kaggle_inputs.py

scripts/build_kaggle_wheelhouse.py
scripts/build_model_snapshot_bundle.py

execution_pack/11_KAGGLE_UPLOAD_BUNDLES.md
execution_pack/12_T4X2_PARALLEL_EXECUTION.md
execution_pack/13_DEPENDENCY_FAILURES.md
execution_pack/14_MODEL_SNAPSHOT_FAILURES.md
execution_pack/15_OOM_AND_RESUME.md
execution_pack/16_RETURN_ZIP_HANDOFF.md
```

---

# PHASE 21 — Final validation

Run:

- full pytest;
- bundle-builder tests;
- ZIP security tests;
- wheelhouse-builder tests;
- dependency-lock tests;
- snapshot-builder synthetic tests;
- smoke-input synthetic tests;
- permission-packager tests;
- scientific-input-builder tests;
- T4×2 sharding tests;
- seed collision tests;
- single-T4 fallback tests;
- notebook-bootstrap tests;
- actual synthetic execution of all 16 notebooks;
- return-ZIP validation;
- upload-manifest consistency;
- runtime-estimate coverage;
- doctor;
- next-action;
- run graph;
- artifact registry;
- claim guard;
- privacy guard;
- Ruff;
- compileall;
- configured type checks;
- paper compile;
- maximum release clean extraction;
- deterministic rebuild.

Verify explicitly:

```text
paper_evidence=false
genuine human_reviewed=true count = 0
Main execution_allowed=false
COCO execution_allowed=false
V2-30 remains retrospective
no real model bytes fabricated
no real source images fabricated
no wheel files fabricated
no real provider outputs fabricated

all repository-only Kaggle ZIPs exist
every external-dependent ZIP has a tested builder
all notebooks have offline dependency bootstrap
all heavy notebooks support T4×2 sharding
all heavy notebooks support single-T4 fallback
seed manifests are deterministic and collision-free
all notebooks emit canonical return ZIPs
all 16 notebooks execute synthetically
no notebook contains host-specific paths
no notebook requires internet for scientific execution
upload manifest covers every notebook
runtime estimates cover every notebook
release works from clean extraction
```

---

# Final status rule

Report:

```text
KAGGLE_EXECUTION_PACK_COMPLETE
ALL_BUILDABLE_INPUT_ZIPS_CREATED
ALL_EXTERNAL_INPUT_BUILDERS_READY
ALL_T4X2_RUNBOOKS_VALIDATED
LOCAL_PRE_RUN_READINESS_10_OF_10
```

only when every local requirement passes.

For unavailable external bytes, use:

```text
BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES
```

Do not call the whole project blocked merely because model weights or licensed datasets are not locally present, provided their builders, schemas, and validation paths are complete.

---

# Required final response

Use:

## 1. Executive verdict

## 2. Kaggle input ZIPs created

For each list path, size, SHA-256, notebooks, and validation status.

## 3. External-dependent bundle builders

For each list source root, exact command, expected output, expected size, and blocker.

## 4. Wheelhouse and dependency readiness

## 5. Model snapshot readiness

## 6. Smoke bundle and permissions

## 7. Confirmatory upload packs

## 8. Main upload packs

## 9. COCO upload packs

## 10. T4×2 parallel implementation

Explain shard assignment, process model, seed hierarchy, fallback, and resume behavior.

## 11. Notebook execution proof

Give results for all 16 notebooks.

## 12. Runtime estimates

Separate CPU hours, dual-GPU notebook-hours, individual T4 GPU-hours, and human-review person-hours.

## 13. Upload manifest

## 14. Remaining external bytes

Only list genuinely absent assets.

## 15. Exact next sequence

1. build/provide wheelhouse;
2. build/provide snapshots;
3. create real two-item smoke bundle;
4. run 00A;
5. run 00B;
6. create pre-smoke permission bundle;
7. run 00C2.

## 16. Validation results

Give exact commands, exits, and test totals.

## 17. Files created or modified

## 18. Master continuation point

Point to:

```text
kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md
reports/kaggle_execution_pack/CERTVIC_KAGGLE_READY_TO_UPLOAD_HANDOFF.md
execution_pack/11_KAGGLE_UPLOAD_BUNDLES.md
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

---

# Success standard

This task succeeds when:

1. every upload ZIP that can be built now exists;
2. every unavailable external bundle has a complete tested builder;
3. all 16 notebooks are ready to run;
4. heavy workloads truly shard across T4×2;
5. single-T4 fallback is validated;
6. dependencies install offline without errors;
7. seeds are deterministic and non-colliding;
8. every notebook produces one canonical return ZIP;
9. runtimes and resources are documented;
10. no hidden manual step remains.

**Build the complete Kaggle input-bundle factory, validate every T4×2 runbook, eliminate dependency and packaging ambiguity, and leave CertVIC ready for real upload and execution.**
