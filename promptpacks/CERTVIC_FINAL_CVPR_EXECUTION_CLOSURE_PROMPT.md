# CERTVIC — FINAL CVPR EXECUTION-CLOSURE, SCIENTIFIC PIPELINE COMPLETION, AND PRE-RUN CERTIFICATION MASTER PROMPT

## Role

You are operating as the lead research engineer, VLM deployment engineer, benchmark architect, counterfactual-editing specialist, statistician, human-evaluation designer, Kaggle systems engineer, reproducibility engineer, release engineer, and critical CVPR co-author for **CertVIC**.

You have full authority to inspect and modify the repository, repair all remaining execution defects, replace incomplete or misleading implementations, complete the Main-study and second-domain pipelines, harden the Kaggle runtime, close the human-review and post-run analysis loop, and produce a self-contained execution and release package.

This is the **final pre-run execution-closure pass**.

Do not perform another broad forensic audit.

Do not stop after documenting remaining gaps.

You must implement and validate every remaining local or synthetic-runtime component that can be completed before the real study.

The target state is:

```text
CVPR_PRE_EXECUTION_READY
```

This status may be used only when:

- the confirmatory specificity lane is actually runnable;
- the Main-study relevant-edit lane is actually implemented;
- the second-domain feasibility lane is actually implemented;
- Kaggle notebooks are genuinely parallel, installable, resumable, and dependency-locked;
- model snapshots and runtime environments are verifiably bound;
- human review is executable end to end;
- import and evidence promotion are atomic and provenance-correct;
- post-run analysis consumes real adjudicated inclusion;
- the release package is self-contained;
- and the only remaining blockers are real data, model snapshots, human review, and real CPU/GPU execution.

---

# 1. Repository

```text
<CERTVIC_REPOSITORY_ROOT>
```

Treat the live repository as the source of truth.

Existing handoffs, reports, prompt packs, and prior completion claims are orientation only.

Preserve:

- raw provider outputs;
- original image pairs;
- historical evidence;
- human-review originals;
- canonical manifests;
- and user-owned files.

Do not initialize Git when absent.

Do not commit or push unless explicitly requested.

---

# 2. Frozen scientific facts

The following boundaries must remain unchanged unless direct repository evidence proves otherwise:

- Real three-model pilot outputs exist.
- Qwen2.5-VL-7B has `12/94 = 0.1277` irrelevant-edit flips and fails the frozen historical V1 rule.
- InternVL2-8B has `1/94 = 0.0106`.
- LLaVA-OneVision-7B has `3/94 = 0.0319`.
- The frozen historical V1 rule is:

```text
observed_spurious_flip_rate <= 0.10
```

- All 12 Qwen V1 flips are Qwen-only within the current three-model matrix.
- Existing pilot validity review was machine-assisted, not completed independent human validation.
- The 30-item V2 set reuses V1 items and is retrospective sensitivity evidence only.
- The independent confirmatory specificity set must be prospective, outcome-unseen, and zero-overlap with V1.
- Main-study execution is blocked.
- No real second-domain evidence exists.
- Exact immutable model and processor revisions remain external prerequisites unless verifiably resolved.
- `paper_evidence=false`.
- `human_reviewed=true` count must remain zero until genuine completed review exists.
- No planned output may be represented as observed evidence.
- No threshold, prompt, item, or expected answer may be altered to improve a preferred model.

---

# 3. Confirmed remaining implementation defects

Verify each defect in the live repository, then repair every confirmed defect.

## 3.1 Main-study generation is not a semantic intervention pipeline

The current Main-study generation path reuses irrelevant-control engines such as:

- structured texture patch;
- neutral patch;
- distant blur.

Those edits do not change the correct answer.

The Main study requires **semantically relevant interventions** such as:

- target-object removal;
- target-object insertion;
- attribute modification;
- count modification;
- or another explicitly specified semantic change.

A generic irrelevant perturbation must never be presented as a Main-study relevant edit.

## 3.2 Second-domain COCO support remains incomplete

The second-domain path currently lacks a complete:

- COCO source adapter;
- task builder;
- target selection policy;
- relevant edit pipeline;
- irrelevant-control pipeline;
- question/answer builder;
- human-review packet;
- importer;
- analysis;
- and feasibility gate.

No `NotImplementedError` may remain on a required path.

## 3.3 Generation notebooks are not truly T4×2 parallel

The generation notebook currently launches shard processes sequentially.

A dual-GPU notebook must launch both workers concurrently.

Global smoke limits must apply to the total study, not independently per shard.

## 3.4 Optional inpainting is not notebook-ready

The optional inpainting implementation exists but is not fully wired to:

- model snapshot path;
- snapshot manifest;
- mask schema;
- model hash;
- offline dependency setup;
- precision;
- two-GPU execution;
- and caching.

It may also reload the pipeline per item, which is unacceptable.

## 3.5 Candidate selection does not enforce the complete protocol

The candidate pipeline must enforce:

- minimum image resolution;
- RGB requirements;
- allowed dataset split;
- license eligibility;
- exact category targets;
- yes/no polarity balance;
- target-size balance;
- target-position balance;
- image-complexity balance;
- salience limits;
- detectability limits;
- generated-edit quality;
- exact and perceptual overlap with historical pools;
- and final primary/reserve manifest integrity.

## 3.6 Resume validation omits snapshot provenance

A completed or partial shard must not be reused when any of the following changed:

- model snapshot manifest hash;
- processor snapshot manifest hash;
- model ID;
- processor ID;
- schema version;
- parser version;
- generation parameters;
- environment manifest;
- code-bundle hash;
- prompt hash;
- task hash;
- or image hashes.

## 3.7 Evidence-ledger hashes are provenance-incomplete

When canonical output is normalized or sorted during promotion, the evidence ledger must record separately:

- returned raw archive hash;
- returned merged-file hash;
- staged canonical normalized hash;
- promoted canonical file hash;
- and analysis artifact hash.

Never record the raw hash as though it were the canonical hash.

## 3.8 Human review is not fully connected to one CLI workflow

The repository contains review components, but the canonical user path must cover:

- visual packet generation;
- reviewer qualification;
- packet hash verification;
- rater-sheet validation;
- agreement computation;
- disagreement extraction;
- adjudication;
- final inclusion manifest;
- and evidence-ledger update.

## 3.9 Post-run analysis does not fully consume adjudicated inclusion

The post-run route must ingest the real final inclusion manifest and produce:

- raw analysis;
- preregistered validity-filtered analysis;
- exclusion reasons;
- IAA;
- adjudication summary;
- sensitivity analyses;
- and paper-eligible state only when all gates pass.

## 3.10 Kaggle dependencies are not locked for offline execution

The notebooks must not assume compatible preinstalled versions.

Build an offline-compatible dependency strategy for:

- PyTorch;
- torchvision;
- Transformers;
- Accelerate;
- bitsandbytes;
- safetensors;
- tokenizers;
- Pillow;
- NumPy;
- SciPy;
- pandas;
- Diffusers;
- model-specific remote code;
- and any other required dependency.

## 3.11 Mock smoke and real smoke are too easy to confuse

A mock smoke must never be mistaken for real adapter validation.

Separate:

```text
SYNTHETIC_MOCK_RUNTIME
```

from:

```text
NON_EVIDENCE_REAL_MODEL_SMOKE
```

The real-model smoke must fail closed until real snapshots and `USE_REAL_MODEL=true` are supplied.

## 3.12 InternVL deployment is likely unsafe on a single T4

The current FP16 8B loading strategy may exceed one 16 GB T4.

A real T4 deployment strategy must be selected and validated through the smoke contract.

Candidates include:

- 8-bit quantization;
- 4-bit quantization;
- tensor/model sharding across two GPUs;
- reduced dynamic-tile cap;
- or another faithful reproducible path.

Do not silently change the model architecture or use a different checkpoint.

## 3.13 Snapshot manifests prove local bytes, not authentic remote commits

The repository must distinguish:

```text
LOCAL_SNAPSHOT_BYTES_VERIFIED
```

from:

```text
REMOTE_COMMIT_AUTHENTICATED
```

A user-entered commit string does not cryptographically prove remote authenticity.

## 3.14 Release package is not self-contained

The release candidate currently omits transitive modules required by:

- `certvic.cvpr.after_runs`;
- `certvic.cvpr.analysis`;
- metrics;
- validation;
- security;
- and report generation.

A clean extraction must support the advertised commands without relying on the original repository.

---

# 4. Primary mission

Close every remaining execution gap.

By the end of the task:

1. The independent confirmatory specificity study must be genuinely runnable.
2. The Main study must have a true semantically relevant edit pipeline.
3. The COCO feasibility study must be executable.
4. Generation must use real dual-GPU concurrency.
5. Global smoke limits must be exact.
6. Optional inpainting must be production-wired or explicitly optional and non-blocking.
7. Candidate selection must enforce every frozen rule.
8. Resume must reject any provenance drift.
9. Evidence hashes must distinguish raw and canonical artifacts.
10. Human review must run through one canonical CLI.
11. Post-run analysis must consume adjudicated inclusion.
12. Dependencies must be locked for offline Kaggle.
13. Real and mock smoke must be impossible to confuse.
14. InternVL must have a realistic T4 deployment plan.
15. The release ZIP must be self-contained.
16. The execution plan must list all remaining runs and expected runtimes.
17. The final status must remain partial unless every local implementation criterion passes.

---

# 5. Restrictions

## 5.1 No real scientific execution

Do not run:

- real confirmatory inference;
- real Main-study inference;
- real COCO inference;
- full diffusion generation;
- real human review;
- paid APIs;
- large model downloads;
- or large dataset downloads.

Tiny synthetic and non-evidence smoke fixtures are allowed.

## 5.2 No fabricated evidence

Do not fabricate:

- predictions;
- human labels;
- metrics;
- runtimes;
- model commits;
- paper results;
- or release readiness.

## 5.3 No result-oriented tuning

Do not alter:

- thresholds;
- prompts;
- candidate rules;
- expected answers;
- inclusion rules;
- or model revisions

after observing outcomes in order to improve conclusions.

## 5.4 No decorative interfaces

Remove or implement any CLI option that has no real effect.

No required notebook may contain placeholder cells that imply completion.

---

# 6. Required phases

---

# PHASE 0 — Baseline and regression reproduction

## 0.1 Reproduce the live state

Run and record:

- full test suite;
- focused runtime-hardening suite;
- CVPR tests;
- parser tests;
- candidate tests;
- generation tests;
- notebook tests;
- importer tests;
- analysis tests;
- claim guard;
- privacy guard;
- paper compile;
- release audit;
- and package integrity.

## 0.2 Create final-closure session records

Create:

```text
reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_SESSION.md
reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_DEFECTS.csv
reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_CHANGELOG.csv
reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_COMMANDS.csv
```

## 0.3 Verify builder ownership

No builder may delete or package artifacts owned by another builder.

Add tests for shared output directories.

---

# PHASE 1 — Implement real Main-study semantic interventions

The Main study must measure correct semantic updating, not generic perturbation sensitivity.

## 1.1 Define supported semantic edit families

Implement a frozen set of semantically relevant edit families.

At minimum consider:

### A. Target-object removal

Original answer:

```text
yes
```

Edited answer:

```text
no
```

### B. Target-object insertion

Original answer:

```text
no
```

Edited answer:

```text
yes
```

### C. Attribute modification

Examples:

- color;
- state;
- presence of a visible property;

only when the expected answer can be objectively defined.

### D. Optional counting or relation modification

Use only when source annotations and review validity are sufficient.

Do not include edit types merely to increase variety.

## 1.2 Main-study task schema

Every task must contain:

- task ID;
- source dataset;
- source image ID;
- source image hash;
- target category;
- target geometry;
- original question;
- original expected answer;
- intended intervention;
- edited expected answer;
- edit family;
- generation engine;
- seed;
- mask hash;
- generation parameters;
- quality status;
- human-review status;
- and provenance.

## 1.3 Deterministic and generative paths

Provide:

- a deterministic path where scientifically valid;
- and an optional inpainting path for object removal/insertion.

Do not use irrelevant patches as relevant edits.

## 1.4 Semantic validity QA

Implement automated checks for:

- intended target-region change;
- unintended target remnants;
- unintended non-target changes;
- edited answer plausibility;
- source/edited image integrity;
- dimensions;
- image hash;
- target-mask consistency;
- artifact score;
- and answerability.

Automated checks are preliminary only.

## 1.5 Human-review packet

Main-study human review must assess:

- intended semantic change succeeded;
- edited expected answer is correct;
- image is answerable;
- non-target content is acceptably preserved;
- artifacts are acceptable;
- and item is retainable.

## 1.6 Main-study generation notebook

Repair:

```text
10_main_study_generation_T4x2.ipynb
```

It must use the new semantic-edit pipeline.

It must never invoke the irrelevant-control generator as the primary Main-study path.

---

# PHASE 2 — Complete COCO second-domain feasibility

## 2.1 Build COCO source adapter

Implement:

- COCO 2017 image discovery;
- annotation loading;
- category mapping;
- segmentation and box extraction;
- split restrictions;
- source licensing metadata;
- and deterministic task IDs.

## 2.2 Feasibility design

Start with:

```text
60 feasibility items
```

or another justified target.

Balance:

- object categories;
- target sizes;
- image complexity;
- original answer polarity;
- insertion/removal;
- and question templates.

## 2.3 Relevant edits

Support:

- object removal for present objects;
- object insertion for absent objects;

only when the edit can be human validated.

## 2.4 Irrelevant controls

Create matched irrelevant controls under the same domain.

## 2.5 COCO question and answer contract

Use an explicit object-presence contract.

No ambiguous synonyms or category mappings may remain unresolved.

## 2.6 Full second-domain path

Implement:

- task builder;
- generation;
- review packet;
- model notebooks;
- importer;
- analysis;
- feasibility gate;
- and conditional expansion rule.

No required `NotImplementedError` may remain.

---

# PHASE 3 — True T4×2 generation concurrency

## 3.1 Concurrent workers

Replace sequential shard launching with concurrent processes.

Use one process per GPU.

Capture:

- stdout;
- stderr;
- exit code;
- runtime;
- progress;
- and failure reason.

## 3.2 Global smoke-limit semantics

`MAX_ITEMS=N` must apply globally.

The assignment manifest must contain exactly N total items across all shards.

## 3.3 Shard validation

Before merge, verify:

- expected global count;
- expected shard membership;
- no duplicates;
- no missing items;
- task hashes;
- output hashes;
- and runtime manifests.

## 3.4 Generation resume across sessions

Support downloading partial shard packages and resuming in a new Kaggle session.

---

# PHASE 4 — Production-wire optional inpainting

## 4.1 Pipeline lifecycle

Load the inpainting pipeline once per worker, not once per item.

Implement:

- `prepare()`;
- `generate_batch()` or efficient item loop;
- `release()`.

## 4.2 Offline snapshot verification

Require:

- local model directory;
- snapshot manifest;
- model hash;
- revision;
- compatible Diffusers version;
- and offline mode.

## 4.3 Mask contract

Define exact mask semantics:

- white region changed;
- black region preserved;
- dimensions;
- antialiasing;
- dilation;
- and target safety.

## 4.4 Precision and OOM

Implement:

- FP16;
- attention slicing;
- optional xFormers when available;
- VAE slicing/tiling where appropriate;
- CPU offload only when explicitly supported;
- batch reduction;
- and OOM retry.

## 4.5 Optional branch policy

When inpainting weights are absent:

- deterministic confirmatory controls remain executable;
- Main semantic edits that require inpainting remain blocked;
- and the notebook prints the exact missing input.

---

# PHASE 5 — Complete confirmatory candidate enforcement

## 5.1 Source eligibility

Enforce:

- allowed split;
- minimum dimensions;
- RGB or controlled conversion;
- valid annotation;
- license eligibility;
- zero historical overlap;
- and source hash.

## 5.2 Exact category list

Freeze and enumerate the 12 categories.

For every category define:

- 20 primary;
- 5 reserve;
- 10 expected-yes;
- 10 expected-no;
- target-size distribution;
- and target-position distribution.

When data cannot satisfy this, produce a shortage certificate.

## 5.3 Generated-edit quality before final freeze

Do not freeze 240+60 before generation and QA.

The correct sequence is:

1. mine candidate pool;
2. generate edit candidates;
3. automated QA;
4. blinded human review;
5. adjudication;
6. final balanced selection;
7. reserve assignment;
8. task hash lock.

## 5.4 Salience and detectability

Enforce the declared salience range.

Implement a set-level detectability report.

Do not use detectability alone to exclude failures after model outputs.

## 5.5 Polarity balance

Build or verify questions so the final set balances expected yes/no answers.

## 5.6 Full manifest hash

Hash the canonical serialized contents of:

- study config;
- item fields;
- source hashes;
- edited hashes;
- question text;
- expected answers;
- placements;
- engine versions;
- review outcomes;
- and reserve status.

A hash over IDs alone is insufficient.

---

# PHASE 6 — Close resume provenance

## 6.1 Run contract hash

Create one canonical `run_contract_hash` covering:

- study manifest;
- code bundle;
- environment lock;
- model snapshot manifest;
- processor snapshot manifest;
- model ID;
- processor ID;
- revisions;
- prompt template;
- parser version;
- generation parameters;
- schema version;
- and sharding seed.

Every row and shard manifest must record it.

## 6.2 Resume validation

A row may be skipped only when its `run_contract_hash` matches exactly.

## 6.3 Quarantine

Any mismatch must move the stale file into:

```text
quarantine/<reason>/<timestamp>/
```

with a machine-readable report.

## 6.4 Completed-shard verification

A completed shard must be fully revalidated before returning `SHARD_ALREADY_COMPLETE`.

---

# PHASE 7 — Correct evidence-ledger provenance

## 7.1 Separate hashes

Record:

- source ZIP hash;
- raw merged JSONL hash;
- canonical normalized JSONL hash;
- promoted canonical hash;
- analysis table hashes;
- figure hashes;
- and paper-injection manifest hash.

## 7.2 Immutable provenance chain

Create an artifact lineage graph:

```text
returned ZIP
  -> raw extracted artifact
  -> staged validated artifact
  -> canonical normalized artifact
  -> derived analysis
  -> table/figure
  -> paper branch
```

## 7.3 Validation

Add tests proving that normalizing/sorting changes the canonical hash and that both hashes are retained correctly.

---

# PHASE 8 — One canonical human-review CLI

Create a single CLI namespace such as:

```bash
python3 -m certvic.cvpr.review build
python3 -m certvic.cvpr.review qualify
python3 -m certvic.cvpr.review validate
python3 -m certvic.cvpr.review agreement
python3 -m certvic.cvpr.review adjudication-packet
python3 -m certvic.cvpr.review finalize
```

## 8.1 Build

Generate:

- visual HTML/PDF;
- rater sheets;
- coordinator key;
- packet hashes;
- codebook;
- quiz;
- and answer key.

## 8.2 Qualify

Record reviewer quiz completion and enforce the configured threshold.

Do not auto-fill reviewer identity or answers.

## 8.3 Validate

Verify:

- distinct reviewers;
- complete sheets;
- packet hashes;
- valid choices;
- and no post-hoc row edits.

## 8.4 Agreement

Generate:

- percent agreement;
- Cohen’s kappa;
- Gwet’s AC1;
- per-question agreement;
- and confidence-based summaries.

## 8.5 Adjudication

Build only disagreement packets.

Preserve raw rater sheets.

## 8.6 Finalize

Create the final inclusion manifest with:

- inclusion decision;
- reason;
- rater provenance;
- adjudication provenance;
- and hash.

---

# PHASE 9 — Human-aware post-run analysis

## 9.1 Required inputs

The post-run route must require:

- complete provider matrix;
- final inclusion manifest;
- review packet hash;
- agreement report;
- adjudication report;
- frozen study config;
- and expected run contract.

## 9.2 Raw versus filtered analysis

Always produce both:

- raw all-item results;
- preregistered valid-item results.

## 9.3 Exclusion audit

Report every excluded item and reason without hiding model outcomes.

## 9.4 Evidence promotion

Only after all gates pass may derived artifacts become paper-eligible.

Raw model outputs remain real evidence even when human validity is pending.

## 9.5 Main-study go/no-go

After confirmatory specificity, automatically evaluate:

- Qwen pass/fail branch;
- all-model branch;
- model-dependent branch;
- human invalidation rate;
- interval conclusiveness;
- and whether Main execution is allowed.

---

# PHASE 10 — Offline Kaggle environment lock

## 10.1 Environment manifest

Create:

```text
configs/runtime/kaggle_t4x2_environment.lock.json
```

Include:

- Python version;
- CUDA version;
- PyTorch;
- torchvision;
- Transformers;
- Accelerate;
- bitsandbytes;
- tokenizers;
- safetensors;
- Diffusers;
- Pillow;
- NumPy;
- SciPy;
- pandas;
- and model-specific dependencies.

## 10.2 Wheelhouse strategy

Prepare:

- a wheelhouse build script;
- a wheelhouse manifest;
- package hashes;
- offline install command;
- and dependency validation.

Do not download packages during this task.

## 10.3 Preinstalled-environment branch

When Kaggle already has compatible packages:

- verify exact allowed versions;
- skip reinstall only when compatible;
- record the environment hash.

## 10.4 Incompatible environment

Fail before model loading and print the exact remediation.

---

# PHASE 11 — Separate mock and real smoke

## 11.1 Mock smoke notebook

Create:

```text
00C1_certvic_mock_adapter_smoke.ipynb
```

Clearly mark:

```text
SYNTHETIC_MOCK_RUNTIME
```

It may validate worker plumbing only.

## 11.2 Real-model smoke notebook

Create:

```text
00C2_certvic_real_model_two_item_smoke.ipynb
```

It must require:

```text
USE_REAL_MODEL = True
```

and fail closed otherwise.

## 11.3 Real smoke outputs

Generate:

- two fixture predictions;
- runtime manifest;
- environment manifest;
- snapshot manifest hash;
- peak VRAM;
- throughput;
- parser status;
- and smoke ZIP.

Store outside scientific evidence directories.

## 11.4 Per-model smoke

Run separately for:

- Qwen;
- InternVL;
- LLaVA.

The project must not permit scientific runs until all three real smoke outputs validate.

---

# PHASE 12 — InternVL T4 deployment closure

## 12.1 Evaluate supported deployment strategies

Prepare and test configuration construction for:

- 8-bit quantization;
- 4-bit quantization;
- two-GPU model sharding;
- and tile-cap control.

## 12.2 Faithfulness

The chosen path must preserve:

- selected checkpoint;
- official preprocessing;
- model class;
- prompt contract;
- and deterministic decoding.

## 12.3 Smoke gate

The real InternVL 00C2 smoke must demonstrate:

- successful model load;
- two-item inference;
- no OOM;
- peak VRAM;
- output parsing;
- and cleanup.

If it fails on T4×2, mark the provider blocked and document the required alternative hardware.

Do not fake compatibility.

---

# PHASE 13 — Snapshot authenticity language

## 13.1 Status classes

Use separate states:

```text
LOCAL_SNAPSHOT_BYTES_VERIFIED
REMOTE_COMMIT_DECLARED
REMOTE_COMMIT_AUTHENTICATED
```

## 13.2 Authentication

When internet or trusted metadata is unavailable, do not claim remote authentication.

## 13.3 Paper and release language

State exactly what provenance is proven.

---

# PHASE 14 — Self-contained release package

## 14.1 Transitive dependency closure

Build a module dependency audit starting from:

- worker;
- generation;
- candidate selection;
- review;
- whole-study import;
- analysis;
- after-runs;
- claim guard;
- privacy guard;
- report generation;
- and paper injection.

Include all required local modules in the release ZIP.

## 14.2 Clean extraction test

In a temporary empty directory:

1. extract the release ZIP;
2. create a clean Python environment or isolated import path;
3. run imports;
4. run synthetic tests;
5. run CLI help;
6. run mock generation;
7. run mock worker;
8. run mock import;
9. run mock analysis;
10. build the paper scaffold.

## 14.3 Release contents

Include:

- source;
- configs;
- schemas;
- notebooks;
- synthetic fixtures;
- guides;
- environment lock;
- wheelhouse manifest;
- paper source;
- release manifest;
- licenses;
- and data/model cards.

Exclude:

- weights;
- private paths;
- historical quarantined ZIPs;
- real human data;
- and non-redistributable datasets.

## 14.4 Deterministic release

Rebuild twice and require byte-identical output.

---

# PHASE 15 — Additional high-value upgrades

Implement only where they improve the final study.

## 15.1 End-to-end synthetic study simulation

Create a complete synthetic run that exercises:

- task build;
- generation;
- review packet;
- mock rater completion fixture;
- adjudication fixture;
- model mock outputs;
- whole-study import;
- analysis;
- table generation;
- paper injection;
- and release update.

Clearly label all artifacts:

```text
SYNTHETIC_END_TO_END_FIXTURE
```

## 15.2 Throughput and VRAM calibration

Create a tool that consumes real smoke manifests later and updates runtime estimates.

## 15.3 Failure-injection tests

Test:

- one provider missing;
- one ZIP corrupted;
- wrong snapshot;
- wrong environment;
- stale shard;
- human sheet hash mismatch;
- adjudication incomplete;
- Main relevant edit invalid;
- COCO annotation missing;
- and release dependency missing.

## 15.4 Study freeze signatures

Create signed or hash-locked freeze manifests for:

- confirmatory study;
- Main study;
- COCO feasibility;
- model matrix;
- analysis plan;
- and human-review rules.

## 15.5 Paper branch safety

The paper branch selector must reject activation when:

- study incomplete;
- human inclusion missing;
- evidence hashes mismatch;
- intervals inconclusive;
- or claim guard fails.

---

# PHASE 16 — Notebook repairs

Repair and validate all CVPR notebooks.

At minimum:

```text
00A_certvic_code_and_environment_smoke.ipynb
00B_certvic_model_snapshot_smoke.ipynb
00C1_certvic_mock_adapter_smoke.ipynb
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

Every notebook must:

- install or verify the code package;
- install or verify dependencies;
- verify input hashes;
- verify snapshot manifests;
- inspect T4 hardware;
- enforce offline mode;
- use real concurrent T4×2 execution where applicable;
- support single-GPU fallback;
- support resume;
- capture logs;
- validate outputs;
- create deterministic ZIPs;
- and print exact local import commands.

---

# PHASE 17 — Master execution plan

Update:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

It must be the sole execution authority.

## 17.1 Run classifications

Use:

- `MANUAL_DATA_PROVISION`;
- `CPU_LOCAL`;
- `CPU_KAGGLE`;
- `KAGGLE_RUNTIME_SMOKE`;
- `GPU_KAGGLE_T4X2`;
- `GPU_KAGGLE_SINGLE_FALLBACK`;
- `HUMAN_REVIEW`;
- `POST_RUN_CPU_ANALYSIS`;
- and `OPTIONAL_SECONDARY`.

## 17.2 Required table

For every run list:

- Run ID;
- Study;
- Stage;
- Required/Optional;
- Hardware;
- GPU count;
- VRAM;
- estimated runtime;
- prerequisites;
- input;
- command/notebook;
- output;
- validation;
- resume;
- failure recovery;
- and downstream gate.

## 17.3 Exact order

Provide the true final order:

1. source provision;
2. environment preparation;
3. snapshot manifest creation;
4. 00A;
5. 00B;
6. real 00C2 per model;
7. candidate mining;
8. confirmatory generation;
9. human review;
10. final task freeze;
11. three-model confirmatory execution;
12. atomic import;
13. human-aware analysis;
14. Main go/no-go;
15. Main semantic generation;
16. Main model matrix;
17. COCO feasibility;
18. paper regeneration;
19. release audit.

Adjust only when the final implementation requires a different dependency order.

## 17.4 Runtime estimates

Separate:

- smoke runtime;
- confirmatory CPU;
- confirmatory GPU;
- confirmatory human hours;
- Main generation;
- Main model runs;
- COCO feasibility;
- post-run analysis;
- and paper/release regeneration.

Label all values as estimates until real smoke data exists.

---

# PHASE 18 — Final deliverables

Create or update:

```text
reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_SESSION.md
reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_DEFECTS.csv
reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_CHANGELOG.csv
reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_COMMANDS.csv
reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_VALIDATION.md
reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_SCORECARD.md
reports/cvpr_execution_closure/CERTVIC_FINAL_PRE_RUN_HANDOFF.md

docs/execution/CERTVIC_MAIN_SEMANTIC_EDIT_GUIDE.md
docs/execution/CERTVIC_COCO_FEASIBILITY_GUIDE.md
docs/execution/CERTVIC_OFFLINE_KAGGLE_ENVIRONMENT_GUIDE.md
docs/execution/CERTVIC_REAL_MODEL_SMOKE_GUIDE.md
docs/execution/CERTVIC_HUMAN_REVIEW_CLI_GUIDE.md
docs/execution/CERTVIC_EVIDENCE_LINEAGE_GUIDE.md
docs/execution/CERTVIC_RELEASE_REPRODUCTION_GUIDE.md

configs/runtime/kaggle_t4x2_environment.lock.json
configs/studies/main_study_cvpr.yaml
configs/studies/second_domain_cvpr.yaml
configs/studies/specificity_confirmatory_cvpr.yaml
configs/models/certvic_cvpr_model_registry.yaml

CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

---

# PHASE 19 — Final validation

Run:

- focused repaired-path tests;
- full test suite;
- Ruff;
- compileall;
- type checks where configured;
- semantic-edit tests;
- COCO adapter tests;
- concurrent generation tests;
- global limit tests;
- inpainting lifecycle tests;
- candidate enforcement tests;
- resume provenance tests;
- ledger-hash tests;
- review CLI tests;
- agreement/adjudication tests;
- human-aware analysis tests;
- environment-lock tests;
- real/mock smoke separation tests;
- InternVL deployment-config tests;
- clean release extraction tests;
- deterministic release rebuild;
- notebook static tests;
- notebook synthetic-runtime tests;
- claim guard;
- privacy guard;
- paper compile;
- release audit;
- and `git diff --check` when applicable.

Verify explicitly:

```text
paper_evidence=false
human_reviewed=true count = 0 unless genuine review exists
Main-study execution_allowed=false
second-domain execution_allowed=false
V2-30 remains retrospective
no real GPU evidence created
no human labels fabricated
no required path contains NotImplementedError
no required notebook launches workers sequentially
no stale shard can pass with changed snapshot provenance
raw and canonical hashes are both recorded
release imports succeed in a clean extraction
```

---

# 7. Final status rule

Report:

```text
CVPR_PRE_EXECUTION_READY
```

only when all local criteria pass.

Otherwise report:

```text
PARTIALLY_READY_WITH_BLOCKERS
```

and list the exact remaining implementation defects.

External blockers such as:

- dataset bytes;
- model snapshots;
- real Kaggle smoke;
- real human review;
- and real scientific runs

do not prevent `CVPR_PRE_EXECUTION_READY` when every pre-run implementation is complete and fail-closed.

---

# 8. Required final response

Use this structure:

## 1. Executive verdict

## 2. Confirmed defects repaired

For each include:

- path;
- original defect;
- repair;
- regression test;
- validation.

## 3. Confirmatory specificity pipeline

## 4. Main semantic-edit pipeline

## 5. COCO second-domain pipeline

## 6. Kaggle concurrency, dependencies, and smoke readiness

## 7. Model adapters and InternVL deployment

## 8. Human-review CLI and adjudication

## 9. Atomic import, evidence lineage, and analysis

## 10. Release self-containment

## 11. Notebook readiness levels

Classify each notebook as:

- static passed;
- synthetic runtime passed;
- real Kaggle smoke pending;
- scientific run blocked.

## 12. Validation results

Give exact commands, exits, and test totals.

## 13. Remaining external blockers

## 14. Exact next run sequence

## 15. Runtime estimates

## 16. CVPR readiness scores

Separate:

- scientific design;
- engineering;
- runtime;
- evidence;
- paper;
- release.

## 17. Files created or modified

## 18. Master continuation point

Point to:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
reports/cvpr_execution_closure/CERTVIC_FINAL_PRE_RUN_HANDOFF.md
```

---

# 9. Success standard

This pass succeeds only when:

- the confirmatory lane is implemented end to end;
- Main uses real semantic interventions;
- COCO feasibility is implemented;
- T4×2 generation is concurrent;
- smoke bounds are global;
- inpainting is production-wired or explicitly blocked;
- candidate rules are all enforced;
- resume uses a complete run-contract hash;
- raw and canonical provenance are both preserved;
- human review has one complete CLI;
- post-run analysis consumes adjudicated inclusion;
- Kaggle dependencies are offline-locked;
- mock and real smoke are impossible to confuse;
- InternVL has a realistic T4 strategy;
- release extraction is self-contained;
- and the only remaining work is real external execution.

Do not produce another optimistic scaffold.

**Close the execution system completely, prove it locally, and leave CertVIC at the strongest honest CVPR pre-run ceiling.**
