# CERTVIC — ABSOLUTE FINAL CVPR PRE-RUN CLOSURE, END-TO-END INTEGRATION, AND EXECUTION AUTHORIZATION MASTER PROMPT

## Role

You are operating as the lead research engineer, benchmark architect, VLM deployment engineer, counterfactual-editing specialist, human-evaluation systems designer, statistician, Kaggle runtime engineer, reproducibility engineer, release engineer, and critical CVPR co-author for **CertVIC**.

This is the **absolute final repair and pre-run closure pass**.

Do not perform another broad audit.

Do not create another optimistic scaffold.

Do not stop after documenting defects.

Do not mark the project ready merely because isolated modules or tests pass.

Your job is to close every remaining integration break between:

- task construction;
- generation;
- QA;
- blinded review;
- adjudication;
- exact selection;
- task freezing;
- smoke validation;
- execution authorization;
- scientific notebooks;
- atomic import;
- human-aware analysis;
- paper branch activation;
- and release state.

The target status is:

```text
CVPR_PRE_EXECUTION_READY
```

You may use that status only if the complete pre-run path is executable end to end with synthetic fixtures and all scientific notebooks are blocked solely by real external inputs and real execution.

If any local integration defect remains, report:

```text
PARTIALLY_READY_WITH_BLOCKERS
```

and name the exact blocker.

---

# 1. Repository

```text
<CERTVIC_REPOSITORY_ROOT>
```

Treat the live repository as the source of truth.

Preserve:

- historical provider outputs;
- original image pairs;
- canonical manifests;
- review originals;
- evidence and gate ledgers;
- user-owned files;
- and all scientifically relevant provenance.

Do not initialize Git when absent.

Do not commit or push unless explicitly requested.

---

# 2. Frozen scientific boundaries

The following facts must remain unchanged unless direct repository evidence proves otherwise:

- Real three-model pilot outputs exist.
- Qwen2.5-VL-7B has `12/94 = 0.1277` irrelevant-edit flips.
- InternVL2-8B has `1/94 = 0.0106`.
- LLaVA-OneVision-7B has `3/94 = 0.0319`.
- The frozen historical V1 rule is:

```text
observed_spurious_flip_rate <= 0.10
```

- Qwen fails the frozen historical V1 rule.
- All 12 Qwen V1 flips are Qwen-only within the present model matrix.
- Existing pilot item-validity review was machine-assisted, not completed independent human review.
- The current V2-30 set is retrospective sensitivity evidence only.
- The future confirmatory specificity set must be prospective, outcome-unseen, and zero-overlap with V1.
- Main-study execution remains blocked until confirmatory and human gates pass.
- No real second-domain evidence exists.
- `paper_evidence=false`.
- Structured `human_reviewed=true` count remains zero until genuine completed review exists.
- No planned artifact may be represented as real evidence.
- No threshold, prompt, expected answer, inclusion rule, item filter, or model revision may be changed after seeing outcomes to improve a preferred conclusion.

---

# 3. Confirmed remaining defects

Verify each lead in the live repository, then repair every confirmed defect.

## 3.1 Main task builder and semantic generator use incompatible schemas

The Main task builder emits fields such as:

```text
original_question
original_gold_answer
edited_gold_answer
edit_family
mask_path
```

while semantic generation expects fields such as:

```text
question
original_expected_answer
edited_expected_answer
semantic_edit_family
target_mask_path
required_change
```

The task builder, semantic generator, evaluation notebooks, importer, and analysis must use one canonical Main task schema.

## 3.2 Main analysis expects different gold-answer fields

The analysis path may read:

```text
answer_original
expected_original
answer_edited
expected_edited
```

while the builder emits other names.

One canonical field set must be enforced across all Main-study components.

## 3.3 Generation notebooks bypass strict generation packaging

The strict global generation packager exists, but generation notebooks may still create ZIPs manually and write self-declared validation reports.

Notebooks 01, 10, and 20 must invoke the strict packager.

## 3.4 Human review is not joined to final exact selection

The exact selector must consume the validated final review ledger and may select only adjudicated retained items.

## 3.5 Negative-item policy exists in config but not in executable code

The absent-category protected-scene policy must be implemented, including protected-scene geometry and verified background-only edit regions.

## 3.6 Prospective engine selection exists but is not used

The engine-selection policy must drive real semantic generation.

Complex edits must route to the approved inpainting branch or fail closed.

## 3.7 Real smoke gate is too permissive

The smoke gate must verify the exact two-item fixture, provider, model, revision, snapshot, environment, prompt, parser, task, image hashes, run contract, ZIP member hashes, and output rows.

## 3.8 No signed transition exists from blocked study to execution permission

The user must not manually edit `execution_allowed=true`.

Create a signed or hash-bound authorization artifact generated only when all prerequisites pass.

## 3.9 Confirmatory selection does not enforce review provenance

The selection CLI must reject rows not present as retained in the final reviewed inclusion ledger.

## 3.10 Main task construction stops at candidates

The Main builder must support candidate construction, automated QA, review linkage, balanced selection, reserve assignment, and final frozen task export.

## 3.11 Attribute tasks may silently use incorrect transforms

Attribute transitions must be explicit, verified, schema-bound, and consumed exactly by the generator.

## 3.12 Exact solver may have scalability risks

The exact selector needs pruning, memoization, timeout control, and a deterministic fallback.

---

# 4. Primary mission

By the end of this task:

1. One canonical task schema must govern confirmatory, Main, and COCO studies.
2. Main task builder output must run directly through semantic generation.
3. Main analysis must consume the same gold-answer fields.
4. Generation notebooks must use strict global packaging.
5. Final review state must control exact selection.
6. Negative-item construction must be executable.
7. Prospective engine selection must control generation.
8. Real smoke validation must be importer-grade.
9. Execution permission must be signed and machine-gated.
10. Main study must progress from candidates to frozen final tasks.
11. Attribute transformations must be explicit and verified.
12. Exact selection must be scalable and deterministic.
13. A complete synthetic end-to-end study must exercise all joins.
14. The release must contain and validate every new path.
15. The execution master plan must be the sole accurate continuation point.

---

# 5. Non-negotiable restrictions

## 5.1 No real scientific execution

Do not run:

- real confirmatory inference;
- real Main inference;
- real COCO inference;
- full diffusion generation;
- real human review;
- large model downloads;
- large dataset downloads;
- paid APIs.

Synthetic and non-evidence fixtures are allowed.

## 5.2 No fabricated evidence

Do not fabricate:

- model outputs;
- human labels;
- scientific metrics;
- measured runtimes;
- model commits;
- paper results;
- or evidence eligibility.

## 5.3 No result-oriented tuning

Do not alter:

- thresholds;
- prompts;
- expected answers;
- item inclusion;
- category quotas;
- model revisions;
- or statistical rules

after observing outcomes.

## 5.4 No duplicate infrastructure

Use one canonical CLI and one canonical schema wherever possible.

---

# PHASE 0 — Baseline and defect reproduction

## 0.1 Reproduce baseline

Run and record:

- full test suite;
- latest final-integration tests;
- execution-closure tests;
- runtime-hardening tests;
- notebook tests;
- review tests;
- generation tests;
- task-builder tests;
- importer tests;
- analysis tests;
- claim guard;
- privacy guard;
- paper compile;
- clean release extraction;
- deterministic release rebuild.

## 0.2 Create final closure records

Create:

```text
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_SESSION.md
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_DEFECTS.csv
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_CHANGELOG.csv
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_COMMANDS.csv
```

---

# PHASE 1 — Canonical task schema unification

Create:

```text
certvic/cvpr/task_schema.py
```

## 1.1 Define one versioned schema

Use a version such as:

```text
certvic.cvpr.task.v1
```

Required fields:

```text
task_schema_version
study
task_id
source_dataset
source_split
source_image_id
source_image_path
source_image_hash
license_status

question
original_expected_answer
edited_expected_answer
required_change

semantic_edit_family
control_edit_family
target_category
queried_category
queried_category_absent

target_bbox
target_mask_path
target_mask_hash
protected_scene_mask_path
protected_scene_mask_hash

attribute_name
original_attribute
edited_attribute
attribute_transform
original_attribute_verified

edit_engine_policy
selected_engine
engine_fallbacks
engine_parameters
seed

primary_or_reserve
strata
review_status
qa_status
task_hash
```

Allow fields to be null only when the study contract permits it.

## 1.2 Canonical converters

Provide explicit converters from legacy candidate formats.

No hidden alias lookup in analysis.

## 1.3 Enforce across all paths

Use the canonical task schema in:

- confirmatory candidate builder;
- confirmatory QA;
- exact selection;
- Main task builder;
- semantic generator;
- COCO builder;
- notebooks;
- worker;
- importer;
- analysis;
- paper injection;
- release fixtures.

## 1.4 End-to-end schema test

Add:

```text
build task
→ validate schema
→ generate edit
→ package generation
→ run mock model
→ import
→ analyze
```

---

# PHASE 2 — Fix Main task builder to generator compatibility

## 2.1 Builder output

`main_task_builder.py` must emit canonical semantic tasks directly or through one explicit compilation command.

## 2.2 Required families

Support:

- object removal;
- object insertion;
- verified attribute modification.

Optional count or relation tasks may remain disabled unless fully implemented.

## 2.3 Required fields

For every Main task include:

- question;
- original expected answer;
- edited expected answer;
- required change;
- semantic edit family;
- target mask;
- engine policy;
- selected candidate asset;
- attribute transition when applicable;
- source and asset license;
- strata;
- difficulty;
- provenance;
- reserve group.

## 2.4 Integration test

Prove:

```text
main_task_builder
→ semantic_edits
→ package_generation
```

works with:

- one removal;
- one insertion;
- one attribute task.

---

# PHASE 3 — Unify Main analysis

## 3.1 Gold answers

Read only canonical fields:

```text
original_expected_answer
edited_expected_answer
```

Remove ambiguous fallback chains from certification-critical analysis.

## 3.2 Validate task-result join

Every prediction row must join exactly one canonical task.

Reject:

- missing tasks;
- duplicate tasks;
- wrong variants;
- wrong schema;
- wrong task hash.

## 3.3 Main metrics

Implement from canonical fields:

- original correctness;
- edited correctness;
- raw answer change;
- correct semantic update;
- responsiveness gap;
- confidence sequence;
- family balance;
- and certification policy.

---

# PHASE 4 — Make strict generation packaging mandatory

## 4.1 Notebook integration

Repair notebooks:

```text
01_specificity_confirmatory_generation_T4x2.ipynb
10_main_study_generation_T4x2.ipynb
20_second_domain_generation_T4x2.ipynb
```

They must invoke:

```bash
python3 -m certvic.cvpr.package_generation ...
```

## 4.2 Remove manual success reports

No notebook may write:

```json
{"passed": true}
```

without recomputed validation.

## 4.3 Global validation

The packager must verify:

- exact expected task universe;
- exact shard membership;
- all generated images;
- all record files;
- all QA rows;
- all task hashes;
- all image hashes;
- all run-contract hashes;
- all engine families;
- no duplicates;
- no extras;
- no missing items;
- and deterministic ZIP output.

## 4.4 Failure behavior

Any global mismatch must prevent ZIP promotion.

---

# PHASE 5 — Join review to selection

Update the exact selector CLI:

```bash
python3 -m certvic.cvpr.candidate_selection \
  --qa-enriched-manifest <QA_ROWS> \
  --final-inclusion-ledger <FINAL_REVIEW_LEDGER> \
  --config <CONFIG> \
  --out-dir <OUT>
```

## 5.1 Required review validation

Before selection verify:

- final review status;
- complete item universe;
- packet hash;
- qualification artifacts;
- rater-sheet hashes;
- agreement artifact;
- adjudication artifact;
- and final ledger hash.

## 5.2 Selection universe

Only:

```text
final_inclusion=true
```

items may enter the solver.

## 5.3 Preserve exclusions

Write a complete excluded-item audit.

## 5.4 Freeze output

The final selected task manifest must include:

- canonical task schema;
- review provenance;
- QA provenance;
- solver proof;
- task hash;
- freeze hash.

---

# PHASE 6 — Implement negative-item construction

Create:

```text
certvic/cvpr/negative_item_builder.py
```

## 6.1 Required policy

Implement the frozen absent-category protected-scene policy.

For every negative item record:

```text
queried_category
queried_category_absent=true
absence_verification
protected_annotation_ids
protected_scene_mask_path
protected_scene_mask_hash
background_edit_region
background_region_validation
expected_answer=no
```

## 6.2 Text protection

When text annotations or OCR-free text masks are unavailable, mark the item unresolved or reject it.

Do not pretend text is protected when it is not.

## 6.3 Background-only placement

The edit region must avoid:

- all annotated objects;
- protected text;
- target-relevant regions;
- image boundaries;
- and invalid low-information zones.

## 6.4 Positive/negative balance

Only enforce 50/50 polarity when both positive and negative item rules are actually satisfiable.

Otherwise revise the prospective config before final task freeze.

---

# PHASE 7 — Wire prospective engine selection

## 7.1 Production use

`prospective_engine_selection()` or its successor must be called by the real semantic generation path.

## 7.2 Rules

Example policy:

- simple verified removal → deterministic preliminary or inpainting;
- complex removal → inpainting required;
- insertion → inpainting or validated asset composite;
- attribute → explicit verified transform only;
- unresolved engine → fail closed.

## 7.3 Record decisions

Every task and output must record:

- engine policy;
- selected engine;
- reason;
- fallback sequence;
- QA result;
- and final engine used.

## 7.4 Attribute safety

No default transform may be silently used.

Require:

```text
original_attribute_verified=true
attribute_transform=<EXPLICIT_TRANSFORM>
```

The transform must match:

```text
original_attribute → edited_attribute
```

---

# PHASE 8 — Harden the real smoke gate

The smoke gate unlocks scientific runs and must be importer-grade.

## 8.1 Expected inputs

Require:

- trusted smoke fixture manifest;
- expected provider;
- expected model ID;
- expected model revision;
- expected snapshot manifest;
- expected environment lock;
- expected code hash;
- expected prompt hash;
- expected parser version;
- expected task hashes;
- expected image hashes;
- expected run-contract hash.

## 8.2 ZIP verification

Verify:

- ZIP path safety;
- duplicate members;
- `hash_manifest.json`;
- every member hash;
- raw prediction file hash;
- runtime manifest;
- environment manifest;
- snapshot artifact;
- validation report;
- exact two fixture rows;
- parse status;
- no OOM;
- peak VRAM;
- cleanup status.

## 8.3 Row verification

Every row must match the trusted fixture and expected model contract.

## 8.4 Gate output

Write:

```text
PASS
FAIL
BLOCKED_HARDWARE
PENDING
```

with exact reasons.

## 8.5 Negative tests

Reject:

- hand-written pass reports;
- sparse rows;
- wrong model ID;
- wrong revision;
- wrong snapshot;
- wrong task hash;
- wrong image hash;
- wrong parser;
- missing member hashes;
- duplicate rows;
- extra rows.

---

# PHASE 9 — Signed execution authorization

Create:

```text
certvic/cvpr/execution_gate.py
```

## 9.1 Authorization command

Example:

```bash
python3 -m certvic.cvpr.execution_gate authorize \
  --study specificity_confirmatory_cvpr \
  --smoke-gate <SMOKE_GATE> \
  --final-task-manifest <TASKS> \
  --final-review-ledger <REVIEW> \
  --freeze-manifest <FREEZE> \
  --code-hash <HASH> \
  --environment-lock <LOCK> \
  --model-registry <REGISTRY> \
  --out <SIGNED_PERMISSION>
```

## 9.2 Required checks

Verify:

- all required smoke rows PASS;
- final tasks frozen;
- review finalized;
- QA passed;
- solver passed;
- schema consistent;
- code hash locked;
- environment locked;
- model snapshots locked;
- no unresolved blocker;
- study config unchanged.

## 9.3 Permission artifact

Record:

- study;
- permission ID;
- all input hashes;
- issue timestamp;
- authorization status;
- expiry or one-run policy;
- and signature/hash.

## 9.4 Notebook behavior

Scientific notebooks must refuse to run without the valid permission artifact.

## 9.5 Import behavior

`after_runs` must verify the same permission artifact.

Remove reliance on manually editing:

```text
execution_allowed=true
```

---

# PHASE 10 — Complete Main final-task construction

Extend `main_task_builder.py` or create a finalization module.

## 10.1 Stages

Implement:

1. candidate build;
2. automated semantic QA;
3. visual review packet;
4. qualification and review;
5. adjudication;
6. final inclusion;
7. exact balanced selection;
8. primary/reserve assignment;
9. final task freeze.

## 10.2 Main constraints

Balance:

- edit family;
- category;
- answer transition;
- target size;
- target position;
- image complexity;
- difficulty;
- source diversity;
- engine family.

## 10.3 Final output

Produce:

```text
main_primary_tasks.jsonl
main_reserve_tasks.jsonl
main_exclusions.jsonl
main_balance_report.json
main_solver_report.json
main_freeze_manifest.json
```

## 10.4 Main execution gate

Main permission must require:

- confirmatory outcome;
- Main review completion;
- Main task freeze;
- model smoke pass;
- code/environment lock;
- and signed Main go/no-go.

---

# PHASE 11 — Attribute task closure

## 11.1 Explicit transitions

Support only registered transforms.

Example registry:

```text
red_to_blue
blue_to_red
saturated_to_desaturated
desaturated_to_saturated
```

Only include transforms that are visually and semantically valid.

## 11.2 Verification

Require:

- original attribute evidence;
- target mask;
- transformed attribute evidence;
- question template;
- original answer;
- edited answer.

## 11.3 No silent fallback

Missing transform or verification must fail the task.

---

# PHASE 12 — Scale the exact solver safely

## 12.1 Add pruning

Use:

- remaining-quota feasibility;
- duplicate-group bounds;
- category bounds;
- memoized states;
- deterministic candidate ordering.

## 12.2 Add limits

Support:

- maximum states;
- timeout;
- progress reporting;
- and deterministic cancellation.

## 12.3 Deterministic fallback

When the in-repo solver exceeds limits, use an optional ILP or min-cost-flow backend if installed.

If no backend exists, report:

```text
SOLVER_RESOURCE_LIMIT
```

not:

```text
NO_FEASIBLE_SELECTION_EXISTS
```

## 12.4 Stress tests

Test on synthetic candidate pools at:

- 100;
- 300;
- 600;
- and 1,000 rows.

---

# PHASE 13 — End-to-end synthetic closure tests

Create one authoritative synthetic test suite.

## 13.1 Confirmatory route

Exercise:

```text
candidate build
→ negative/positive construction
→ generation
→ QA enrichment
→ visual review packet
→ synthetic qualified independent raters
→ agreement
→ adjudication
→ final inclusion
→ exact selection
→ task freeze
→ mock smoke gate
→ signed execution permission
→ three mock model runs
→ strict package validation
→ atomic import
→ human-aware analysis
→ evidence/gate update
→ paper branch
```

## 13.2 Main route

Exercise:

```text
Main candidate builder
→ semantic generation
→ QA
→ review
→ exact selection
→ task freeze
→ signed Main permission
→ mock model matrix
→ Main analysis
```

## 13.3 COCO route

Exercise the 60-item feasibility schema using synthetic fixtures.

## 13.4 Labels

All outputs must be marked:

```text
SYNTHETIC_END_TO_END_FIXTURE
paper_evidence=false
```

---

# PHASE 14 — Update post-run closure

`after_runs` must:

- verify signed permission;
- verify smoke gate;
- verify final task freeze;
- verify review finalization;
- verify schema;
- atomically import;
- compute raw and filtered results;
- update evidence and gate ledgers;
- activate the guarded paper branch;
- update release state;
- emit Main permission or blocker;
- retain `paper_evidence=false` until all required evidence gates pass.

Add exact negative tests for every missing artifact.

---

# PHASE 15 — Update notebooks

Repair all 16 CVPR notebooks.

At minimum:

- use canonical task schema;
- use strict generation package validator;
- require smoke permission;
- require signed execution permission;
- enforce schema v2 outputs;
- install or verify offline environment;
- verify unified snapshot;
- validate all outputs;
- print exact local import command.

Do not store outputs in notebook cells.

---

# PHASE 16 — Update the master execution plan

Update:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

Remove stale commands.

The exact route must now include:

1. provision data;
2. provision wheelhouse;
3. create snapshot manifests;
4. run 00A;
5. run 00B;
6. run 00C2 for each model;
7. validate smoke gate;
8. build confirmatory candidates;
9. generate controls;
10. QA enrichment;
11. build visual review packet;
12. qualify reviewers;
13. complete review;
14. agreement;
15. adjudication;
16. finalize inclusion;
17. exact balanced selection;
18. freeze final tasks;
19. authorize confirmatory execution;
20. run three confirmatory models;
21. strict package validation;
22. atomic import;
23. human-aware analysis;
24. Main go/no-go;
25. build Main candidates;
26. semantic generation;
27. Main QA/review/freeze;
28. authorize Main execution;
29. run Main matrix;
30. run COCO feasibility;
31. regenerate paper;
32. rebuild release.

For every run list:

- input;
- command;
- hardware;
- estimated runtime;
- output;
- validation;
- resume;
- failure recovery;
- downstream gate.

---

# PHASE 17 — Potential final upgrades

Implement only when they improve rigor without expanding scope.

## 17.1 Artifact lineage visualization

Generate a deterministic DAG of:

```text
source → task → generation → review → selection → run → import → analysis → paper
```

## 17.2 Study freeze diff

Provide a tool that compares any proposed task/config change against the frozen study and explains whether reauthorization is required.

## 17.3 Reproducibility capsule

Generate a compact machine-readable capsule containing:

- code hash;
- task hash;
- environment hash;
- snapshot hashes;
- review hash;
- analysis-plan hash;
- permission hash.

## 17.4 Failure replay

Provide a command that reconstructs the exact context of any failed row without rerunning the full study.

## 17.5 Runtime calibration

Consume real smoke outputs later and update per-model runtime/VRAM estimates automatically.

---

# PHASE 18 — Required deliverables

Create or update:

```text
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_SESSION.md
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_DEFECTS.csv
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_CHANGELOG.csv
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_COMMANDS.csv
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_VALIDATION.md
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_SCORECARD.md
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_HANDOFF.md

certvic/cvpr/task_schema.py
certvic/cvpr/negative_item_builder.py
certvic/cvpr/execution_gate.py

docs/execution/CERTVIC_CANONICAL_TASK_SCHEMA_GUIDE.md
docs/execution/CERTVIC_SIGNED_EXECUTION_AUTHORIZATION_GUIDE.md
docs/execution/CERTVIC_MAIN_FINAL_TASK_CONSTRUCTION_GUIDE.md
docs/execution/CERTVIC_STRICT_SMOKE_VALIDATION_GUIDE.md
docs/execution/CERTVIC_END_TO_END_SYNTHETIC_PROOF.md

CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

---

# PHASE 19 — Final validation

Run:

- focused absolute-final tests;
- full test suite;
- Ruff;
- compileall;
- type checks where configured;
- canonical schema tests;
- Main builder-to-generator tests;
- Main analysis tests;
- strict generation packaging tests;
- review-to-selection tests;
- negative-item tests;
- engine-selection tests;
- strict smoke-gate tests;
- execution-authorization tests;
- Main final-task tests;
- attribute-transition tests;
- solver scalability tests;
- end-to-end synthetic confirmatory tests;
- end-to-end synthetic Main tests;
- COCO synthetic tests;
- post-run closure tests;
- notebook static tests;
- notebook synthetic-runtime tests;
- claim guard;
- privacy guard;
- paper compile;
- release clean extraction;
- deterministic release rebuild;
- `git diff --check` when applicable.

Verify explicitly:

```text
paper_evidence=false
human_reviewed=true count = 0 unless genuine review exists
Main execution_allowed=false
COCO execution_allowed=false
V2-30 remains retrospective
no real GPU evidence created
no human labels fabricated
Main builder output is accepted by semantic generator
Main analysis reads canonical gold-answer fields
generation notebooks use strict global packaging
selection cannot ignore final human review
negative items use protected-scene policy
engine selection controls generation
smoke gate rejects sparse or tampered ZIPs
scientific notebooks require signed execution permission
mixed task or output schemas fail closed
release works from clean extraction
```

---

# 6. Final status rule

Report:

```text
CVPR_PRE_EXECUTION_READY
```

only when:

- all local integration defects are closed;
- the complete synthetic confirmatory route passes;
- the complete synthetic Main route passes;
- COCO synthetic feasibility passes;
- the release contains all new modules;
- all notebooks are smoke-ready;
- and the only remaining blockers are real data, real snapshots, real wheelhouse bytes, real human review, and real execution.

Otherwise report:

```text
PARTIALLY_READY_WITH_BLOCKERS
```

and list the exact remaining defect.

---

# 7. Required final response

Use this structure:

## 1. Executive verdict

## 2. Final defects repaired

For each:

- path;
- original defect;
- repair;
- regression test;
- result.

## 3. Canonical task schema

## 4. Confirmatory end-to-end path

## 5. Main end-to-end path

## 6. COCO feasibility path

## 7. Human review and exact selection

## 8. Smoke validation and execution authorization

## 9. Generation packaging and notebooks

## 10. Atomic import and post-run closure

## 11. Release self-containment

## 12. Synthetic proof results

## 13. Validation results

Give exact commands, exits, and test totals.

## 14. Remaining external blockers

## 15. Exact next sequence

The next action must be the real Kaggle smoke sequence, not another implementation prompt.

## 16. Runtime estimates

## 17. CVPR readiness scores

Separate:

- scientific design;
- engineering;
- runtime;
- evidence;
- paper;
- release.

## 18. Files created or modified

## 19. Master continuation point

Point to:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_HANDOFF.md
```

---

# 8. Success standard

This is the final repair prompt.

After this pass, the next step must be:

1. provision wheelhouse bytes;
2. provision verified model snapshots;
3. run 00A;
4. run 00B;
5. run 00C2 for Qwen, InternVL, and LLaVA;
6. return the real smoke ZIPs;
7. authorize and execute the independent confirmatory study.

There must be no remaining local implementation prompt between this pass and real smoke execution.

Do not declare readiness from isolated tests.

**Prove the full end-to-end synthetic path, close every remaining join, and leave CertVIC ready for real Kaggle smoke and real evidence acquisition.**
