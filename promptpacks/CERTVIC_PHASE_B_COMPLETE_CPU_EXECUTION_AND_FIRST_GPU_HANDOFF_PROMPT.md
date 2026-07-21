# PHASE B COORDINATION OVERRIDE

This is Phase B of the final coordinated CertVIC execution workflow.

Before doing anything, read:

```text
reports/kaggle_execution_pack/CERTVIC_KAGGLE_READY_FOR_PHASE_B_HANDOFF.md
kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md
```

Execute the complete CPU contract below, but stop at the **first authorized real Kaggle wave**.

The first real GPU wave must contain only:

```text
00A environment validation
00B Qwen snapshot validation
00B InternVL snapshot validation
00B LLaVA snapshot validation
```

Do not authorize or run 00C2 during this Phase B pass unless valid 00A and all three valid 00B returns already exist in the canonical incoming-artifact locations.

Create a completely self-contained handoff:

```text
reports/cpu_execution/CERTVIC_FIRST_GPU_WAVE_HANDOFF.md
```

For 00A and each 00B run it must list exact upload ZIPs, Kaggle dataset names, mount paths, notebook, configuration, T4×2 setting, estimated runtime, return ZIP filename, download destination, validation checklist, and the exact resume command.

After the first GPU returns, the required continuation is:

```bash
python3 scripts/run_all_cpu_workflows.py --resume
```

Required terminal status:

```text
PHASE_B_ALL_AVAILABLE_CPU_RUNS_COMPLETE
PRE_GPU_CPU_CLOSURE_COMPLETE
FIRST_KAGGLE_WAVE_READY
```

Future CPU stages that depend on GPU returns or genuine review must be recorded as resumable blockers, not treated as failed local execution.

---

# CERTVIC — COMPLETE CPU RUN EXECUTION AND PRE-GPU CLOSURE MASTER PROMPT

## Role

You are operating as the lead CPU execution engineer, local workflow orchestrator, artifact-packaging engineer, data-validation engineer, statistics engineer, reproducibility engineer, release engineer, and critical CVPR co-author for **CertVIC**.

This is an execution task—not another audit-only pass.

Your job is to execute and finish every CPU-based run that can be completed from the current repository and currently available local inputs. Actually run the workflows, repair safe local failures, regenerate stale artifacts, validate outputs, and leave one final handoff for the GPU phase.

Target status:

```text
ALL_AVAILABLE_CPU_RUNS_COMPLETE
PRE_GPU_CPU_CLOSURE_COMPLETE
READY_FOR_KAGGLE_GPU_EXECUTION
```

Use that status only when every locally runnable CPU workflow has completed or is truthfully blocked by missing external bytes, GPU outputs, upstream scientific gates, or genuine human review.

If a task cannot run because an input is missing, do not fabricate it. Mark it:

```text
CPU_RUN_BLOCKED_BY_MISSING_EXTERNAL_INPUT
```

and provide the exact missing path, producer stage, builder command, and next action.

---

## Repository

```text
/Users/saketmaganti/Projects/certVIC
```

Treat the live checkout as authoritative.

The `kaggleoutputs/` folder was intentionally removed to save space. Do not recreate historical outputs. Use the current canonical return-ZIP, artifact-registry, transactional-import, and execution-plan workflows.

Do not initialize Git when absent. Do not commit or push unless explicitly requested.

---

## Hardware policy

The local machine is a MacBook Air M4 with limited sustained cooling.

Use conservative execution:

```text
maximum CPU workers: 4
maximum heavy Python processes: 1
maximum notebook executions: 1
maximum archive builders: 1
```

Run long image-processing, testing, analysis, and archive jobs sequentially. Use checkpoints and resume support. Avoid uncontrolled multiprocessing and repeated hashing of already-verified content-addressed files.

Do not execute real GPU work, VLM inference, diffusion generation, or large model loading.

Synthetic mock-adapter notebook tests are allowed only when CPU-safe and explicitly non-evidence.

---

## Frozen evidence boundary

Preserve:

- Qwen2.5-VL-7B V1: `12/94 = 0.1277`.
- InternVL2-8B V1: `1/94 = 0.0106`.
- LLaVA-OneVision-7B V1: `3/94 = 0.0319`.
- Frozen V1 threshold: `observed_spurious_flip_rate <= 0.10`.
- Qwen fails V1.
- V2-30 remains retrospective.
- Confirmatory remains prospective and zero-overlap with V1.
- Main remains blocked until confirmatory and real review gates pass.
- COCO remains feasibility-only.
- `paper_evidence=false`.
- Genuine `human_reviewed=true` count remains zero until actual review.

Do not fabricate source images, model weights, predictions, labels, review decisions, runtimes, metrics, licenses, revisions, or claims.

---

# Mission

Execute all available CPU work in these categories:

1. repository validation;
2. local Kaggle bundle construction;
3. dependency and wheelhouse preflight;
4. snapshot manifest preflight;
5. data and license inventory;
6. source exclusion and overlap checks;
7. candidate mining and task construction;
8. deterministic CPU QA;
9. review-packet preparation;
10. exact selection where genuine inputs permit;
11. detectability where genuine inputs permit;
12. task freeze and permissions where gates permit;
13. processing of available Kaggle returns;
14. transactional import and recovery;
15. statistical analysis where canonical outputs exist;
16. Main and COCO CPU preparation;
17. runtime and upload-map generation;
18. paper evidence compilation;
19. deterministic release construction;
20. final CPU closure validation.

---

# Phase 0 — CPU orchestration layer

Create or update:

```text
certvic/cvpr/cpu_execution.py
scripts/run_all_cpu_workflows.py
configs/execution/certvic_cpu_run_plan.yaml
```

Provide:

```bash
python3 scripts/run_all_cpu_workflows.py --status
python3 scripts/run_all_cpu_workflows.py --execute
python3 scripts/run_all_cpu_workflows.py --resume
python3 scripts/run_all_cpu_workflows.py --only <STAGE>
```

The orchestrator must:

- read the canonical run graph;
- execute only CPU-safe nodes;
- respect prerequisites;
- skip valid content-addressed artifacts;
- checkpoint progress;
- record commands, timing, memory, inputs, outputs, hashes, and exit codes;
- stop on scientific-integrity failures;
- continue past independent external-input blockers;
- never launch GPU jobs.

Each run-plan node must define:

- run ID;
- command;
- prerequisites;
- inputs;
- outputs;
- expected runtime;
- memory class;
- retry policy;
- evidence class;
- blocker policy.

---

# Phase 1 — Baseline validation

Run sequentially:

```bash
python3 -m pytest -q
python3 -m ruff check certvic scripts tests
python3 -m compileall -q certvic scripts tests
python3 -m certvic.cvpr.notebook_validation --root notebooks/kaggle/cvpr
python3 scripts/validate_t4x2_notebooks.py
python3 -m certvic.cvpr.doctor --json
python3 -m certvic.cvpr.run_graph status
python3 -m certvic.cvpr.artifact_registry verify
```

Also run:

- claim guard;
- privacy guard;
- path audit;
- ZIP security tests;
- paper compilation twice;
- release audit;
- clean-extraction tests;
- deterministic rebuild tests.

Repair safe local failures. Do not weaken guards.

Estimated runtime:

```text
30–90 minutes
```

---

# Phase 2 — Build all repository-only Kaggle upload ZIPs

Run:

```bash
python3 -m certvic.cvpr.build_all_kaggle_inputs --local-only
```

Build and validate all possible repository-only bundles, including:

```text
kaggle_uploads/00_code/certvic_code_bundle.zip
kaggle_uploads/00_code/certvic_notebooks_bundle.zip
kaggle_uploads/00_code/certvic_configs_bundle.zip
kaggle_uploads/00_code/certvic_execution_tools_bundle.zip
kaggle_uploads/00_code/certvic_synthetic_validation_bundle.zip
```

For each ZIP:

- build twice;
- require byte identity;
- verify hashes;
- reject private paths, unsafe members, and duplicate members;
- register in artifact registry;
- update upload manifest with size and SHA-256.

Estimated runtime:

```text
15–60 minutes
```

---

# Phase 3 — Dependency and wheelhouse CPU work

Generate or verify:

```text
requirements/kaggle_base.lock
requirements/kaggle_qwen.lock
requirements/kaggle_internvl.lock
requirements/kaggle_llava.lock
requirements/kaggle_generation.lock
requirements/kaggle_analysis.lock
```

Check:

- version conflicts;
- missing dependencies;
- platform-specific packages;
- unpinned remote-code dependencies;
- Torch/CUDA compatibility assumptions.

Run:

```bash
python3 -m certvic.cvpr.wheelhouse_builder --mode LOCAL_VERIFY_ONLY
```

Do not package macOS wheels as Kaggle Linux wheels.

When Linux-compatible wheel bytes are missing, complete the lock files, expected-wheel inventory, installation script, import-smoke script, compatibility report, and builder command; report:

```text
BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES
```

Estimated runtime:

```text
15–45 minutes
```

---

# Phase 4 — Snapshot preflight

For:

```text
qwen2_5_vl_7b
internvl2_8b
llava_onevision_7b
```

Search configured local roots.

When a snapshot exists:

- validate required files;
- reject partial downloads;
- hash all files;
- verify tokenizer and processor;
- run local-files-only configuration smoke;
- create canonical snapshot manifest;
- create snapshot upload ZIP when valid;
- register artifact.

When absent:

- create required-file checklist;
- expected directory structure;
- size range;
- exact builder command;
- validation command;
- blocked status.

Do not download large models unless explicitly authorized.

Estimated hashing time:

```text
15–60 minutes per available model
```

---

# Phase 5 — Data, licensing, and overlap inventory

Run the source/license registry.

Inventory:

- ADE20K;
- COCO;
- exclusion sets;
- insertion assets;
- smoke candidates;
- historical V1/V2 IDs;
- redistributable and non-redistributable assets.

Create:

```text
reports/cpu_execution/CERTVIC_DATA_AVAILABILITY.csv
reports/cpu_execution/CERTVIC_LICENSE_STATUS.csv
reports/cpu_execution/CERTVIC_SOURCE_OVERLAP_AUDIT.csv
```

Fail closed on unresolved licensing.

Estimated runtime:

```text
15–90 minutes
```

---

# Phase 6 — Real smoke CPU preparation

When two real licensed smoke examples exist:

- create exactly two portable tasks;
- verify zero V1/V2 overlap;
- verify image and task hashes;
- build task-bundle manifest;
- build smoke contract;
- bind prompt/parser/run-contract identities;
- validate portability;
- create:

```text
kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip
```

When missing, create the candidate checklist, directory layout, exact builder command, and blocked report.

Do not use synthetic images in real mode.

Estimated runtime:

```text
10–30 minutes
```

---

# Phase 7 — Confirmatory source and candidate preparation

When licensed unseen data exists, execute:

1. source manifest;
2. exclusion filter;
3. historical overlap audit;
4. candidate mining;
5. task-schema validation;
6. source-diversity audit;
7. family/stratum coverage;
8. generation plan;
9. deterministic seed/shard plan;
10. portable generation input pack.

Create:

```text
kaggle_uploads/05_confirmatory/certvic_confirmatory_generation_input.zip
```

Do not run diffusion generation.

Estimated runtime:

```text
1–4 hours
```

---

# Phase 8 — CPU QA for existing generated edits

When canonical generated edits exist, run:

- completeness;
- readability;
- dimensions;
- source/edit pairing;
- hashes;
- masks and geometry;
- outside-mask leakage;
- task schema;
- control family;
- duplicates;
- corruption checks;
- licensing;
- candidate enrichment.

Do not invent missing edits.

Estimated runtime:

```text
30 minutes–3 hours
```

---

# Phase 9 — Review preparation

Execute:

- reviewer qualification packet;
- blinded packet generation;
- packet inventory and hashes;
- reviewer instructions;
- adjudication templates;
- progress tooling;
- missing-row detection;
- packet diff;
- blind-ID validation;
- exclusion-report shell.

Do not create reviewer identities or complete decisions.

When genuine completed sheets exist, validate and process them.

Estimated runtime:

```text
20–90 minutes
```

excluding human work.

---

# Phase 10 — Exact selection

Run real exact selection only when genuine finalized inclusion inputs exist.

Validate:

- eligibility;
- review state;
- source caps;
- family quotas;
- stratum targets;
- primary/reserve assignment;
- deterministic solution;
- solver fallback;
- freeze hash.

Otherwise run only synthetic solver regression and report:

```text
CPU_RUN_BLOCKED_BY_GENUINE_HUMAN_REVIEW
```

Estimated runtime:

```text
5–60 minutes
```

---

# Phase 11 — Detectability CPU gate

Run the real grouped detectability gate only on the genuine selected set.

Compute:

- symmetric AUC;
- grouped folds;
- bootstrap interval;
- family breakdown;
- exact-byte binding;
- gate hash.

When blocked, run synthetic validation only.

Estimated runtime:

```text
15–90 minutes
```

---

# Phase 12 — Freeze and permissions

When all required gates exist:

- freeze final tasks;
- build reproducibility capsule;
- issue matrix authorization;
- derive provider permissions;
- create scientific provider input ZIPs;
- register all artifacts.

For pre-smoke permissions require:

- 00A;
- three 00B artifacts;
- real smoke bundle;
- code, prompt, parser, and run-contract identities.

If GPU-generated inputs are missing, record exact blockers.

Estimated runtime:

```text
5–30 minutes
```

---

# Phase 13 — Process existing Kaggle return ZIPs

Search canonical artifact locations and registry for:

- 00A;
- 00B;
- 00C2;
- confirmatory;
- Main;
- COCO returns.

Do not depend on deleted `kaggleoutputs/`.

For available groups:

- verify ZIPs;
- validate manifests;
- verify permissions;
- reconcile provider states;
- run smoke handoff;
- stage transactional import;
- recover interrupted transactions;
- register outputs.

Estimated runtime:

```text
5–45 minutes per group
```

---

# Phase 14 — CPU analysis

When canonical provider outputs exist, run:

- raw/filtered denominators;
- provider completion;
- missingness;
- flip rates;
- confidence sequences;
- Bonferroni decision;
- McNemar/Holm matrix;
- family/category/stratum breakdowns;
- exclusion sensitivity;
- decision trace;
- claim eligibility.

Do not promote synthetic outputs.

Estimated runtime:

```text
10–60 minutes per study
```

---

# Phase 15 — Main CPU preparation

Run all allowed Main CPU work:

- candidate-pool planning;
- source inventory;
- oversampling sufficiency;
- quota validation;
- task construction;
- generation plan;
- seed/shard plan;
- upload builder;
- review templates;
- exact-solver regressions;
- runtime planner.

Do not authorize Main without confirmatory go/no-go.

Estimated runtime:

```text
1–5 hours
```

---

# Phase 16 — COCO CPU preparation

Run:

- COCO adapter validation;
- licensing;
- source manifest;
- 60-item feasibility candidate construction;
- generation and seed plan;
- review templates;
- provider-input builders;
- feasibility-analysis dry run.

Do not claim real COCO evidence.

Estimated runtime:

```text
1–3 hours
```

---

# Phase 17 — Runtime estimates and upload map

Regenerate:

```text
reports/kaggle_execution_pack/CERTVIC_KAGGLE_RUNTIME_ESTIMATES.csv
reports/kaggle_execution_pack/CERTVIC_KAGGLE_RUNTIME_ESTIMATES.md
kaggle_uploads/CERTVIC_KAGGLE_UPLOAD_MANIFEST.csv
kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md
```

Separate CPU hours, dual-T4 notebook-hours, individual GPU-hours, human person-hours, and storage.

Mark unmeasured values as estimates.

Estimated runtime:

```text
5–15 minutes
```

---

# Phase 18 — Paper evidence compiler

Run the canonical evidence compiler.

It must:

- verify registry lineage;
- refuse synthetic/planned artifacts as real;
- generate eligible tables only;
- update injection manifest;
- run guards;
- compile twice;
- record PDF hash.

Expected result may be:

```text
PAPER_EVIDENCE_BLOCKED
```

when genuine evidence is incomplete. That is correct.

Estimated runtime:

```text
10–30 minutes
```

---

# Phase 19 — Deterministic releases

Build:

```text
release/certvic_cvpr_pre_run_maximum.zip
```

and the current Kaggle execution-pack release.

Require:

- deterministic timestamps;
- stable member order;
- byte-identical rebuild;
- clean extraction;
- critical CLI probes;
- no incoming project ZIPs;
- no weights;
- no private datasets;
- no caches;
- no `kaggleoutputs/`;
- no secrets or host paths.

Estimated runtime:

```text
15–60 minutes
```

---

# Phase 20 — Final validation

Run:

- full pytest;
- CPU orchestration tests;
- bundle tests;
- solver tests;
- detectability fixture tests;
- transaction recovery;
- notebook synthetic tests;
- Ruff;
- compileall;
- notebook validation;
- T4×2 static validation;
- claim guard;
- privacy guard;
- path audit;
- paper compile;
- release audit;
- clean extraction;
- deterministic rebuild.

Verify:

```text
paper_evidence=false unless genuine canonical evidence permits otherwise
genuine human_reviewed=true count = 0 unless real sheets exist
Main execution_allowed=false unless all real gates pass
COCO execution_allowed=false unless all real gates pass
V2-30 remains retrospective
no GPU inference executed
no predictions fabricated
no reviews fabricated
no external bytes fabricated
```

---

# Required reports

Create:

```text
reports/cpu_execution/CERTVIC_CPU_EXECUTION_SESSION.md
reports/cpu_execution/CERTVIC_CPU_RUN_PLAN.csv
reports/cpu_execution/CERTVIC_CPU_RUN_RESULTS.csv
reports/cpu_execution/CERTVIC_CPU_RUN_COMMANDS.csv
reports/cpu_execution/CERTVIC_CPU_RUN_BLOCKERS.csv
reports/cpu_execution/CERTVIC_CPU_RUNTIME_ACTUALS.csv
reports/cpu_execution/CERTVIC_CPU_CLOSURE_VALIDATION.md
reports/cpu_execution/CERTVIC_CPU_READY_FOR_GPU_HANDOFF.md
```

For each run record:

- ID;
- category;
- command;
- start/end;
- wall time;
- CPU/I/O class;
- peak memory when possible;
- input/output hashes;
- exit code;
- status;
- blocker;
- retry/recovery.

Statuses:

```text
COMPLETED
ALREADY_VALID
BLOCKED_BY_EXTERNAL_BYTES
BLOCKED_BY_GPU_OUTPUT
BLOCKED_BY_GENUINE_HUMAN_REVIEW
BLOCKED_BY_UPSTREAM_GATE
FAILED_LOCAL_REPAIR_REQUIRED
```

---

# Final status rule

Report:

```text
ALL_AVAILABLE_CPU_RUNS_COMPLETE
PRE_GPU_CPU_CLOSURE_COMPLETE
READY_FOR_KAGGLE_GPU_EXECUTION
```

only when every available CPU node is complete or truthfully blocked by an external/GPU/human prerequisite.

Missing GPU outputs are not local CPU failures.

Do not claim confirmatory, Main, or COCO completion without real inputs.

---

# Required final response

Use:

## 1. Executive verdict

## 2. CPU runs completed

Group by validation, packaging, dependency preparation, data preparation, QA, review operations, selection/detectability, import, analysis, paper, and release.

## 3. CPU runs already valid

## 4. CPU runs blocked

For each include exact missing input, producer stage, next action, and blocker class.

## 5. Artifacts created

Include paths, sizes, and hashes.

## 6. Actual CPU runtimes

## 7. Kaggle upload readiness

## 8. Remaining GPU runs

## 9. Remaining human work

## 10. Validation totals

## 11. Exact next sequence

Usually:

```text
wheelhouse and snapshots
→ 00A
→ 00B
→ smoke bundle and permissions
→ 00C2
```

## 12. Master continuation point

Point to:

```text
reports/cpu_execution/CERTVIC_CPU_READY_FOR_GPU_HANDOFF.md
kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

---

# Success standard

This succeeds when:

1. every available CPU run is actually executed;
2. no runnable CPU work remains as a recommendation;
3. blockers are precisely classified;
4. all locally buildable upload bundles exist;
5. manifests and reports are current;
6. tests and guards pass;
7. deterministic releases are sealed;
8. the next work is genuinely GPU execution or external provisioning;
9. no evidence is fabricated;
10. the repository can resume from the first remaining non-CPU stage.

**Execute every available CPU workflow, finish all local packaging and validation, preserve the evidence boundary, and hand CertVIC cleanly to the Kaggle GPU phase.**
