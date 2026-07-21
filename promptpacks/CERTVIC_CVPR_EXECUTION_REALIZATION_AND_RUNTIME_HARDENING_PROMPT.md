# CERTVIC — CVPR EXECUTION-REALIZATION, RUNTIME-PROOFING, AND FINAL PRE-RUN HARDENING MASTER PROMPT

## Role

You are operating as the lead research engineer, VLM systems engineer, benchmark architect, statistician, Kaggle runtime engineer, human-evaluation designer, reproducibility engineer, and critical CVPR co-author for **CertVIC**.

You have full authority to inspect and modify the repository, repair runtime defects, replace placeholder implementations, consolidate incomplete execution paths, complete missing scientific tooling, harden every notebook and importer, and bring the project to the strongest **genuinely runnable pre-execution state** achievable without performing the real scientific study.

This is **not another broad audit**.

This task begins from a repository that already has a strong V11 scientific boundary and a substantial CVPR pre-execution scaffold. Your job is to close the gap between:

```text
contract exists
```

and:

```text
pipeline is actually executable
```

as well as the gap between:

```text
notebook is statically valid
```

and:

```text
notebook is realistically runtime-ready
```

You must implement, validate, and prove every critical path that can be proven without carrying out the real benchmark runs.

---

# 1. Repository

```text
<PROJECT_ROOT>
```

Treat the live repository as the source of truth.

Do not trust prior status reports without reproducing the relevant behavior.

Preserve all raw evidence and user-owned work.

Do not initialize Git when absent.

Do not commit or push unless explicitly requested.

---

# 2. Verified current scientific boundaries

The following facts must remain unchanged unless direct repository evidence proves otherwise:

- Real three-model pilot outputs exist.
- Qwen2.5-VL-7B has `12/94 = 0.1277` irrelevant-edit flips and fails the frozen V1 historical rule.
- InternVL2-8B has `1/94 = 0.0106`.
- LLaVA-OneVision-7B has `3/94 = 0.0319`.
- The V1 historical rule remains:

```text
observed_spurious_flip_rate <= 0.10
```

- All 12 Qwen V1 failures are Qwen-only within the current three-model matrix.
- Existing pilot item-validity screening was machine-assisted, not completed independent human review.
- The 30-item V2 set reuses V1 items and is retrospective sensitivity evidence only.
- The future independent specificity study must be prospective, outcome-unseen, and zero-overlap with V1.
- Main-study execution remains blocked.
- No real second-domain evidence exists.
- Exact immutable model and processor revisions remain user-supplied prerequisites unless they are independently and verifiably resolvable.
- `paper_evidence=false`.
- Human-review templates must remain blank until real reviewers complete them.
- No missing Kaggle output folder may be treated as scientific evidence loss when canonical normalized outputs remain elsewhere; however, future returned outputs must use the new locked contracts.

---

# 3. Current execution-critical defects that must be treated as confirmed leads

Do not merely repeat these findings. Verify them in the live repository and repair every confirmed defect.

## 3.1 Generation notebooks currently fail before generation

The CVPR generation notebooks invoke the edit engine without satisfying its full-run safety contract.

The affected notebooks include:

```text
notebooks/kaggle/cvpr/01_specificity_confirmatory_generation_T4x2.ipynb
notebooks/kaggle/cvpr/10_main_study_generation_T4x2.ipynb
notebooks/kaggle/cvpr/20_second_domain_generation_T4x2.ipynb
```

The engine currently requires one of:

```text
--max-items
--allow-full-run
```

The notebooks must be repaired to use an explicit and safe run-size contract.

## 3.2 The selected optional diffusion engine is nonfunctional

The current `diffusers_inpaint_optional` path is disabled by design and does not perform real inpainting.

You must either:

1. implement a real, local/cached, GPU-safe diffusion or inpainting engine with complete provenance and resume support; or
2. remove it from the required path and provide a scientifically valid deterministic control-generation path as the primary executable implementation.

Do not leave required notebooks pointing at a deliberately disabled engine.

## 3.3 Worker flags advertise behavior that is not implemented

The worker exposes options such as:

```text
--batch-size
--oom-reduce-to-one
--fail-closed
--resume
```

but the underlying runtime must be verified to actually use them.

Implement real:

- batching;
- adaptive batch reduction;
- OOM catch and retry;
- model reload when necessary;
- cache cleanup;
- item-level fail-closed behavior;
- deterministic resume;
- and explicit run manifests.

Do not retain unused CLI flags.

## 3.4 Completed and partial shards are trusted too easily

Existing completed or partial shards must never be accepted solely because files exist.

Every resume path must revalidate:

- study name;
- provider;
- task IDs;
- expected variants;
- task manifest hash;
- code-bundle hash;
- model ID;
- model revision;
- processor revision;
- prompt hash;
- image hashes;
- parser version;
- schema version;
- generation parameters;
- and row count.

Stale or mismatched shards must be quarantined rather than silently reused.

## 3.5 Notebooks verify the code bundle but may not install it

Every Kaggle notebook must:

- discover the attached code bundle;
- verify its SHA-256;
- extract it to a deterministic working directory;
- install it in editable or wheel form, or set a verified `PYTHONPATH`;
- verify `import certvic`;
- print the resolved package path;
- verify package version or source hash;
- and fail before model loading if installation is inconsistent.

## 3.6 Model revision locks are declarative rather than proven

A typed 40-character commit string is not sufficient provenance.

Implement snapshot-manifest verification for model and processor packages.

The manifest should include:

- provider;
- model ID;
- model revision;
- processor ID;
- processor revision;
- resolved repository commit;
- relative filenames;
- file sizes;
- SHA-256 hashes;
- config hash;
- tokenizer hash;
- processor-config hash;
- generation-config hash;
- expected architecture class;
- expected dtype policy;
- and compatible library versions.

Every notebook must verify the mounted snapshot against the manifest before loading it.

## 3.7 InternVL preprocessing and T4 dtype need correction

The InternVL adapter must use the intended native dynamic-image preprocessing contract rather than a generic full-image `448 × 448` resize when the official model path requires dynamic tiles.

The T4 path must not assume unsupported or unreliable BF16 behavior.

Implement and validate an explicit T4-safe precision policy.

## 3.8 Current candidate mining is only a census

The prospective confirmatory pipeline must be completed beyond:

- source overlap checks;
- exact-hash duplicate checks;
- image existence;
- category presence;
- and target geometry presence.

It must implement actual:

- perceptual deduplication;
- category balancing;
- target-size strata;
- target-position strata;
- image-complexity strata;
- perturbation placement;
- perturbation generation;
- target-distance rules;
- target-box and target-mask overlap checks;
- salience metrics;
- detectability metrics;
- balanced primary/reserve selection;
- deterministic seeded sampling;
- and frozen rejection reasons.

## 3.9 Human-review infrastructure lacks complete visual operations

Blank CSV templates are insufficient.

Build reviewer-ready visual packets containing:

- side-by-side or randomized A/B images;
- anonymized pair IDs;
- question and expected-answer context;
- no provider outcomes;
- no failure status;
- no prior machine labels;
- reviewer instructions;
- reviewer training examples;
- a reviewer qualification quiz;
- rater sheets;
- immutable packet hashes;
- adjudication tooling;
- IAA tooling;
- and final inclusion-manifest generation.

## 3.10 Importer verification is incomplete

The importer must verify:

- returned ZIP member hashes;
- `hash_manifest.json`;
- expected prompt hash;
- expected image hash;
- expected task hash;
- expected code-bundle hash;
- expected model/processor manifest hash;
- study schema version;
- output completeness;
- and provider matrix completeness.

The entire multi-provider study import must be atomic.

No provider may be promoted to canonical evidence if the complete required matrix fails validation.

## 3.11 Post-run analysis is incomplete

The post-run pipeline must implement:

- adjudicated human-validity filtering;
- raw and validity-filtered analyses;
- IAA;
- exact specificity decisions;
- paired model comparisons;
- multiplicity correction;
- confidence-sequence decisions for the main study;
- branch-safe result summaries;
- evidence-ledger updates;
- figure generation;
- table generation;
- paper injection;
- claim guard;
- privacy guard;
- and release-state update.

## 3.12 Notebook tests are mostly static

Add realistic mock-runtime and smoke validation that exercises:

- code-bundle installation;
- input discovery;
- task loading;
- model snapshot verification;
- adapter initialization with a tiny fake or lightweight model fixture;
- dual-worker launch;
- single-GPU fallback;
- resume;
- OOM fallback;
- atomic merge;
- deterministic ZIP packaging;
- and importer ingestion.

---

# 4. Primary mission

Bring CertVIC to the status:

```text
CVPR_PRE_EXECUTION_READY
```

only when every required CPU, human, generation, model, import, analysis, paper, and release path is genuinely implemented and validated as far as possible without performing the real study.

By the end of this task:

- no required notebook may point at a disabled engine;
- no critical CLI flag may be decorative;
- no resume path may trust stale outputs;
- no model revision may be accepted without snapshot verification;
- no candidate-selection rule may remain vague;
- no human-review track may lack visual packets and agreement tooling;
- no importer may accept well-formed but incorrect hashes;
- no study import may be partially promoted;
- no post-run analysis may stop at provider summaries;
- and no status report may call static validation equivalent to runtime proof.

---

# 5. Non-negotiable restrictions

## 5.1 No real scientific runs

Do not execute:

- real VLM benchmark inference;
- real confirmatory model runs;
- real Main-study runs;
- real second-domain runs;
- real diffusion generation over the study;
- paid APIs;
- large model downloads;
- large dataset downloads;
- or human review.

Tiny synthetic or non-evidence smoke fixtures are allowed.

A tiny runtime smoke may use:

- mock adapters;
- generated fixture images;
- a tiny local test model;
- or dependency-only loading;

provided it is explicitly marked:

```text
SYNTHETIC_RUNTIME_FIXTURE
```

and never enters evidence directories.

## 5.2 No outcome-aware tuning

Do not:

- alter prompts to improve a preferred model;
- remove difficult items after seeing outputs;
- weaken gates;
- change expected answers;
- select favorable revisions;
- change analysis rules after outcomes;
- or relabel the retrospective V2-30.

## 5.3 Preserve raw evidence

Never overwrite:

- historical provider outputs;
- raw human sheets;
- original image pairs;
- canonical manifests;
- or signed hashes.

## 5.4 Build, do not merely document

Every major finding must result in one of:

- a code repair;
- a complete implementation;
- a test;
- a validated notebook;
- a frozen config;
- a runbook;
- or an explicit external blocker.

Avoid adding reports that duplicate existing reports.

---

# 6. Phase structure

Complete all phases in order.

---

# PHASE 0 — Baseline and ownership audit

## 0.1 Reproduce baseline

Run and record:

- full test suite;
- focused CVPR tests;
- V11 tests;
- parser tests;
- notebook tests;
- claim guard;
- privacy guard;
- package audit;
- paper compile;
- release audit;
- and evidence-ledger validation.

## 0.2 Create execution-realization manifest

Create:

```text
reports/cvpr_runtime_hardening/CERTVIC_RUNTIME_HARDENING_SESSION.md
```

Record:

- repository state;
- commands;
- environment;
- files changed;
- initial failures;
- package hashes;
- and known external blockers.

## 0.3 Protect builder ownership

Audit every builder that writes to:

- `dist/`;
- `notebooks/`;
- `reports/`;
- `data/results/`;
- `release/`;
- and human-review directories.

Each builder must delete and package only files it owns.

Add regression tests for cross-builder deletion or accidental ZIP inclusion.

---

# PHASE 1 — Complete deterministic control generation

The independent confirmatory study must have a fully executable non-placeholder generation path.

## 1.1 Primary deterministic perturbation engines

Implement at least three scientifically distinct deterministic irrelevant-edit families, subject to the frozen protocol:

1. texture or structured patch outside the target;
2. luminance- and color-controlled neutral patch outside the target;
3. controlled distant-region blur or local transformation outside the target.

Each engine must:

- accept the same canonical task schema;
- obey target-distance rules;
- obey target-box and target-mask overlap limits;
- use deterministic seeds;
- preserve image dimensions;
- preserve color mode;
- record placement geometry;
- record engine version;
- record parameters;
- record source and output hashes;
- and support resume.

Do not introduce a control family that changes the expected semantic answer.

## 1.2 Optional inpainting engine

When optional local/cached weights are present, implement a real inpainting engine using an appropriate open model.

The implementation must support:

- explicit local model path;
- no hidden downloads by default;
- offline mode;
- exact model snapshot manifest;
- deterministic seeds;
- mask handling;
- two-GPU sharding;
- precision policy;
- OOM fallback;
- resume;
- output hashes;
- and provenance.

When weights are absent, the notebook must:

- mark the inpainting branch unavailable;
- continue with deterministic engines if the protocol permits;
- or fail with an explicit external-input blocker.

It must never call a deliberately disabled stub.

## 1.3 Fix full-run safety

Generation CLI and notebooks must use an explicit safety contract:

- dry-run;
- bounded smoke run;
- exact item count;
- or explicit `--allow-full-run`.

The selected mode must be printed and recorded in the runtime manifest.

## 1.4 Generation QA

Implement automated checks for:

- file readability;
- dimensions;
- mode;
- source/output difference;
- target-box overlap;
- target-mask overlap;
- distance from target;
- perturbation area;
- perturbation salience;
- perceptual similarity;
- and duplicate outputs.

Invalid outputs must not be promoted.

## 1.5 Generation regression suite

Test:

- deterministic repeatability;
- different seed behavior;
- target overlap rejection;
- invalid mask;
- missing source image;
- corrupt image;
- existing valid output;
- existing conflicting output;
- resume;
- and package determinism.

---

# PHASE 2 — Complete candidate mining and balanced selection

## 2.1 Freeze explicit category targets

The study config must enumerate the actual categories rather than saying only:

```text
12_categories_20_primary_items_each
```

For each category define:

- primary target;
- reserve target;
- source availability;
- expected answer polarity balance;
- target-size balance;
- and target-position balance.

## 2.2 Implement perceptual deduplication

Use a deterministic method such as:

- pHash;
- dHash;
- CLIP-free local perceptual descriptors;
- or another CPU-safe method.

Record:

- duplicate group;
- distance;
- threshold;
- retained representative;
- and rejection reason.

Exact hashes remain mandatory, but are not sufficient.

## 2.3 Implement image-complexity and geometry strata

Calculate and record:

- target-area fraction;
- target-center distance;
- target-edge distance;
- object count or complexity proxy;
- image entropy or texture proxy;
- source resolution;
- and category.

## 2.4 Implement placement planning

For each candidate, generate valid placement proposals satisfying:

- target distance;
- target overlap tolerance;
- image boundary constraints;
- area-fraction constraints;
- perturbation-family compatibility;
- and deterministic selection.

## 2.5 Implement salience and detectability screening

Use CPU-safe metrics where possible.

At minimum calculate:

- pixel-difference area;
- mean absolute difference;
- SSIM or equivalent;
- local contrast change;
- edge-energy change;
- and location-relative salience.

Prepare optional learned detectability only as a diagnostic, not as the sole validity criterion.

## 2.6 Deterministic balanced selection

Use the frozen seed and strata to select:

```text
240 primary
60 reserve
```

or a statistically justified revised target.

Produce:

- selected primary manifest;
- reserve manifest;
- rejected manifest;
- shortage report;
- balance report;
- and selection hash.

The selection must fail closed when category or stratum requirements cannot be met.

## 2.7 Zero-overlap proof

Verify zero overlap with:

- V1 item IDs;
- V1 source-image IDs;
- V1 image hashes;
- V2-30 IDs;
- V2-30 source IDs;
- and perceptual duplicate groups.

Create a machine-readable overlap certificate.

---

# PHASE 3 — Production model adapters and snapshot verification

## 3.1 Canonical snapshot manifest

Implement:

```text
certvic/cvpr/model_snapshot_manifest.py
```

Support:

- manifest creation from a locally mounted snapshot;
- manifest verification;
- strict offline mode;
- architecture assertion;
- config verification;
- tokenizer/processor verification;
- and SHA-256 file validation.

## 3.2 Qwen adapter

Validate:

- chat template;
- image token handling;
- processor revision;
- input placement;
- 4-bit configuration;
- output slicing;
- max token behavior;
- deterministic decoding;
- and T4 memory policy.

## 3.3 InternVL adapter

Replace generic resizing with the correct dynamic-image preprocessing contract required by the selected revision.

Implement:

- dynamic tiling;
- thumbnail policy;
- pixel-value normalization;
- patch-count bounds;
- prompt/image token contract;
- and T4-safe float16 behavior.

Do not use BF16 on T4 unless a runtime capability check proves it safe.

## 3.4 LLaVA-OneVision adapter

Validate:

- processor contract;
- model class;
- chat template;
- image token behavior;
- 4-bit or float16 policy;
- decoding;
- and output slicing.

## 3.5 Shared adapter contract

Every adapter must provide:

- `prepare()`;
- `generate_one()`;
- optional `generate_batch()`;
- `release()`;
- runtime capability report;
- provenance manifest;
- and deterministic configuration hash.

## 3.6 Adapter smoke suite

Create a tiny smoke notebook or local fixture that verifies:

- import;
- snapshot-manifest rejection;
- fake revision rejection;
- processor mismatch rejection;
- architecture mismatch rejection;
- batch contract;
- and output schema.

When actual model snapshots are absent, use mock adapters plus package-level compatibility tests.

Create optional user-run model smoke notebooks that process exactly two fixture items and clearly label outputs as:

```text
NON_EVIDENCE_RUNTIME_SMOKE
```

---

# PHASE 4 — Real batch, OOM, and resume behavior

## 4.1 Implement true batching

The worker must actually honor `--batch-size`.

Record:

- requested batch size;
- effective batch size;
- batch changes;
- per-batch duration;
- and OOM events.

## 4.2 Adaptive OOM fallback

On CUDA OOM:

1. record the event;
2. clear tensors and cache;
3. halve batch size;
4. retry the same items;
5. fall back to batch size 1;
6. reload the model if required;
7. fail closed if batch size 1 still fails.

Never drop or skip an item silently.

## 4.3 Resume validation

Before skipping any prior row, verify it against the current run contract.

Completed shard files must undergo full validation before returning:

```text
SHARD_ALREADY_COMPLETE
```

Invalid prior rows must be quarantined and regenerated.

## 4.4 Atomic shard promotion

Use:

```text
*.partial.jsonl
*.validated.jsonl.tmp
*.complete.jsonl
```

or an equally explicit transactional state machine.

Promotion must happen only after:

- row schema validation;
- expected ID validation;
- revision validation;
- hash validation;
- duplicate validation;
- and count validation.

## 4.5 Deterministic shard balancing

Balance by estimated item cost when relevant.

Record the assignment manifest so resumed runs preserve the same sharding.

## 4.6 Multi-session resume

Support combining valid shard outputs from multiple Kaggle sessions while proving:

- same study;
- same code;
- same model revision;
- same processor revision;
- same task manifest;
- and no duplicate conflicts.

---

# PHASE 5 — Kaggle code installation and notebook realism

## 5.1 Canonical setup module

Extract shared notebook setup into a tested module or generated setup cell that:

- discovers ZIPs;
- verifies hashes;
- extracts code;
- installs dependencies;
- sets offline environment variables;
- adds project path;
- verifies imports;
- verifies package source hash;
- verifies model snapshots;
- and verifies input manifests.

## 5.2 Notebook input discovery

Avoid brittle hard-coded Kaggle dataset folder names.

Print discovered candidates and require an unambiguous match.

## 5.3 Accelerator checks

Each GPU notebook must verify:

- CUDA availability;
- GPU count;
- GPU models;
- VRAM;
- compute capability;
- float16/BF16 support;
- and disk space.

## 5.4 Dual-GPU launch

Use one worker per GPU with explicit:

```text
CUDA_VISIBLE_DEVICES=0
CUDA_VISIBLE_DEVICES=1
```

Capture worker stdout and stderr separately.

## 5.5 Single-GPU fallback

When only one GPU exists:

- use one deterministic shard sequence;
- preserve output compatibility;
- record fallback status;
- and update runtime estimate.

## 5.6 Kaggle timeout recovery

Write progress frequently enough to survive session termination.

Provide a continuation notebook path that can consume previously downloaded shard ZIPs when the original Kaggle working directory is lost.

## 5.7 Notebook runtime tests

Beyond token checks, execute notebook-derived commands against synthetic fixtures.

Validate:

- package extraction;
- import;
- preflight;
- two-worker mock execution;
- one-worker fallback;
- partial resume;
- stale-shard rejection;
- merge;
- and ZIP creation.

## 5.8 Notebook set

Repair and validate all existing CVPR notebooks.

Add smoke notebooks when needed:

```text
00A_certvic_code_and_environment_smoke.ipynb
00B_certvic_model_snapshot_smoke.ipynb
00C_certvic_adapter_two_item_smoke.ipynb
```

These smoke notebooks must never write into scientific evidence directories.

---

# PHASE 6 — Complete human-review operations

## 6.1 Visual packet builder

Build actual reviewer-facing HTML and/or PDF packets.

Each pair must show:

- anonymous pair ID;
- randomized image A;
- randomized image B;
- task question;
- candidate expected answer;
- review questions;
- and no model outcomes.

The packet must not reveal which image is original or edited unless the specific judgment requires that information.

## 6.2 Separate review tracks

Support:

- pilot intervention validity;
- V1 specificity validity;
- retrospective V2-30;
- Qwen 12-failure forensics;
- independent confirmatory specificity;
- Main study;
- and second domain.

## 6.3 Reviewer training and qualification

Create:

- codebook;
- example decisions;
- ambiguous examples;
- invalid-control examples;
- target-contamination examples;
- short qualification quiz;
- answer key stored separately;
- and minimum qualification threshold.

No fabricated completion may be created.

## 6.4 Immutable review packet hashes

Record hashes for:

- images;
- packet HTML/PDF;
- CSV templates;
- coordinator key;
- and codebook.

## 6.5 Agreement analysis

Implement:

- percent agreement;
- Cohen’s kappa;
- Gwet’s AC1;
- per-question agreement;
- confidence-stratified agreement;
- and bootstrap intervals where appropriate.

Freeze the primary agreement statistic in the protocol.

## 6.6 Adjudication

Implement:

- disagreement extraction;
- adjudicator packet;
- final adjudicated sheet;
- immutable raw-rater preservation;
- adjudication provenance;
- and final valid-item manifest.

## 6.7 Fail-closed inclusion

No result may become paper-eligible until:

- required sheets are complete;
- packet hashes match;
- rater identities are distinct;
- adjudication is complete where required;
- inclusion rules are satisfied;
- and the final inclusion manifest validates.

---

# PHASE 7 — Whole-study transactional importer

## 7.1 Returned ZIP verification

Verify:

- ZIP integrity;
- path safety;
- duplicate members;
- member hashes;
- `hash_manifest.json`;
- runtime manifest;
- environment manifest;
- provider;
- study;
- schema;
- expected row count;
- and output hash.

## 7.2 Expected-value verification

Compare every row against the frozen expected task manifest:

- item ID;
- variant;
- prompt hash;
- image hash;
- task hash;
- expected provider;
- expected model ID;
- model revision;
- processor revision;
- parser version;
- code-bundle hash;
- and model-snapshot manifest hash.

Well-formed but incorrect hashes must fail.

## 7.3 Whole-study atomicity

For a required three-model matrix:

1. validate all provider ZIPs into a staging directory;
2. validate matrix completeness;
3. validate cross-provider task identity;
4. validate study-wide provenance;
5. compute a staged audit report;
6. promote all providers atomically;
7. or promote none.

## 7.4 Idempotency and conflict refusal

Reimporting identical outputs should succeed as a no-op.

Any conflicting output must fail and be quarantined.

## 7.5 Evidence-class update

Only successful atomic promotion may update the evidence ledger.

The update must preserve:

```text
REAL_OBSERVED_EVIDENCE
```

for raw predictions while retaining:

```text
HUMAN_REVIEW_PENDING
```

until human review is complete.

---

# PHASE 8 — Complete post-run scientific analysis

## 8.1 Independent specificity analysis

Implement:

- raw observed rates;
- missing-as-failure rates;
- one-sided Clopper–Pearson bounds;
- Bonferroni simultaneous decisions;
- paired risk differences;
- exact McNemar tests;
- Holm-adjusted exploratory tests;
- per-family and per-stratum results;
- and sensitivity analyses.

## 8.2 Human-validity integration

Produce:

- raw analysis;
- preregistered human-validity-filtered analysis;
- adjudication report;
- exclusion table;
- and robustness analysis.

## 8.3 Main-study analysis

Implement:

- original correctness;
- raw answer changes;
- correct semantic updates;
- responsiveness gap;
- confidence-sequence lower bound;
- full certification policy;
- family balance;
- model comparisons;
- edit-family interactions;
- and specificity-responsiveness joint conclusions.

## 8.4 Second-domain analysis

Implement:

- feasibility gate;
- primary domain comparison;
- domain interaction;
- and conditional expansion decision.

## 8.5 Outcome-branch engine

Create guarded branches for:

- Qwen fails again;
- Qwen passes;
- multiple models fail;
- all models pass;
- high human invalidation;
- and inconclusive intervals.

Only validated results may activate a branch.

## 8.6 Automatic artifacts

Generate:

- CSV tables;
- LaTeX tables;
- figures;
- reviewer-ready summary;
- evidence-ledger update;
- gate-ledger update;
- paper placeholders;
- release status;
- and final post-run handoff.

---

# PHASE 9 — Paper and release upgrades

## 9.1 Expand the paper scaffold

The paper scaffold must contain complete non-result sections, not one-line placeholders.

Build substantive drafts for:

- introduction;
- problem formulation;
- protocol;
- intervention construction;
- specificity controls;
- statistical analysis;
- human evaluation;
- experimental setup;
- limitations;
- ethics;
- and reproducibility.

Do not fabricate citations or results.

## 9.2 Related-work matrix

Create a structured TODO matrix for source-verified literature covering:

- VLM robustness;
- counterfactual VQA;
- image-edit evaluation;
- consistency testing;
- certified robustness;
- confidence sequences;
- sequential testing;
- benchmark validity;
- and human evaluation.

## 9.3 Figure and table generators

Implement generators for:

- protocol overview;
- study flow;
- specificity decision;
- model comparison;
- family breakdown;
- human agreement;
- qualitative examples;
- and second-domain summary.

## 9.4 Claim firewall

Ensure unsupported language remains blocked until evidence exists.

## 9.5 Release candidate

Build a real release candidate package with:

- code;
- configs;
- schemas;
- notebook suite;
- synthetic fixtures;
- documentation;
- paper source;
- licenses;
- data cards;
- model cards;
- and reproduction instructions.

Quarantine non-release archives.

---

# PHASE 10 — Additional high-value upgrades

Implement these only when they increase scientific value without delaying the required path.

## 10.1 Baseline suite

Prepare executable baselines for:

- fixed-answer;
- text-only;
- image-shuffled;
- random-change;
- simple pixel-difference heuristic;
- and oracle upper bound where valid.

## 10.2 Prompt robustness

Prepare a small preregistered secondary prompt-robustness matrix.

## 10.3 Resolution sensitivity

Prepare optional image-resolution sensitivity for models whose processors support it.

## 10.4 Fourth-model feasibility

Prepare one optional fourth model only if:

- architecture/training diversity is meaningful;
- licensing is clear;
- T4×2 execution is realistic;
- and it does not delay the core three-model study.

## 10.5 Cost and runtime calibration

Build a runtime-estimation tool that uses:

- item counts;
- image complexity;
- measured smoke throughput when later available;
- model family;
- GPU count;
- batch size;
- and retry overhead.

Estimates must be labeled as estimates until measured.

## 10.6 Dataset shortage branch

If ADE20K cannot supply enough zero-overlap controls:

- produce a shortage certificate;
- identify the exact deficit by category/stratum;
- prepare a source-compatible expansion path;
- and preserve prospective rules.

Do not weaken the rules merely to reach 240.

---

# PHASE 11 — Required smoke-proof ladder

No notebook may be called runtime-ready until it passes the applicable ladder.

## Level 0 — Static

- valid JSON;
- no hidden outputs;
- required cells;
- no private paths;
- no secrets.

## Level 1 — Synthetic local runtime

- install package;
- load fixture task;
- run mock adapter;
- create shards;
- resume;
- merge;
- package;
- import.

## Level 2 — Dependency smoke

- import actual libraries;
- verify CUDA-dependent branches are guarded;
- verify snapshot manifest behavior;
- verify quantization configuration construction.

## Level 3 — Kaggle environment smoke

Prepare exact user-run notebooks that perform:

- environment audit;
- code installation;
- snapshot verification;
- two-item non-evidence adapter run;
- two-GPU launch;
- and downloadable smoke ZIP.

Do not claim this level passed until the user returns real Kaggle smoke outputs.

## Level 4 — Scientific execution

Blocked until all prior levels and human/data gates pass.

---

# PHASE 12 — Final execution master plan update

Update:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

and its canonical copy.

The plan must classify every remaining action as:

- `CPU_LOCAL`;
- `CPU_KAGGLE`;
- `GPU_KAGGLE_T4X2`;
- `GPU_KAGGLE_SINGLE_FALLBACK`;
- `KAGGLE_RUNTIME_SMOKE`;
- `HUMAN_REVIEW`;
- `MANUAL_DATA_PROVISION`;
- `POST_RUN_CPU_ANALYSIS`;
- or `OPTIONAL_SECONDARY`.

For every run include:

- run ID;
- study;
- exact dependency;
- exact input;
- exact command or notebook;
- hardware;
- GPU count;
- expected VRAM;
- estimated runtime;
- expected output;
- validation command;
- resume procedure;
- failure procedure;
- and downstream gate.

Add a separate table for:

```text
SMOKE RUNS REQUIRED BEFORE SCIENTIFIC RUNS
```

---

# PHASE 13 — Final deliverables

Create or update at minimum:

```text
reports/cvpr_runtime_hardening/CERTVIC_RUNTIME_HARDENING_SESSION.md
reports/cvpr_runtime_hardening/CERTVIC_RUNTIME_DEFECT_REGISTER.csv
reports/cvpr_runtime_hardening/CERTVIC_RUNTIME_REPAIR_CHANGELOG.csv
reports/cvpr_runtime_hardening/CERTVIC_RUNTIME_VALIDATION.md
reports/cvpr_runtime_hardening/CERTVIC_RUNTIME_READINESS_SCORECARD.md
reports/cvpr_runtime_hardening/CERTVIC_EXECUTION_REALIZATION_HANDOFF.md

certvic/cvpr/model_snapshot_manifest.py
certvic/cvpr/runtime_preflight.py
certvic/cvpr/generation.py
certvic/cvpr/candidate_selection.py
certvic/cvpr/review_packets.py
certvic/cvpr/agreement.py
certvic/cvpr/adjudication.py

configs/studies/specificity_confirmatory_cvpr.yaml
configs/models/certvic_cvpr_model_registry.yaml

docs/execution/CERTVIC_KAGGLE_RUNTIME_SMOKE_GUIDE.md
docs/execution/CERTVIC_MODEL_SNAPSHOT_MANIFEST_GUIDE.md
docs/execution/CERTVIC_HUMAN_REVIEW_OPERATIONS_GUIDE.md
docs/execution/CERTVIC_POST_RUN_ATOMIC_IMPORT_GUIDE.md

notebooks/kaggle/cvpr/00A_certvic_code_and_environment_smoke.ipynb
notebooks/kaggle/cvpr/00B_certvic_model_snapshot_smoke.ipynb
notebooks/kaggle/cvpr/00C_certvic_adapter_two_item_smoke.ipynb
```

Repair all existing CVPR notebooks and worker modules.

Update the paper and release surfaces only where implementations now justify it.

---

# PHASE 14 — Final validation

Run:

- focused repaired-path tests;
- full test suite;
- lint;
- compileall;
- type checks when configured;
- notebook static tests;
- notebook synthetic-runtime tests;
- generation tests;
- candidate-selection tests;
- snapshot-manifest tests;
- adapter tests;
- batching/OOM tests;
- resume tests;
- human-review packet tests;
- agreement/adjudication tests;
- importer tests;
- whole-study atomicity tests;
- post-run analysis tests;
- claim guard;
- privacy guard;
- package determinism;
- paper compile;
- release audit;
- and `git diff --check` when applicable.

Verify explicitly:

```text
paper_evidence=false
human_reviewed=true count = 0 unless genuine completed sheets exist
Main-study execution_allowed=false
V2-30 remains retrospective
no real GPU evidence created
no human labels fabricated
no disabled engine remains on a required execution path
no CLI flag is decorative
no stale shard can be accepted without validation
```

---

# 7. Final status rules

You may report:

```text
CVPR_PRE_EXECUTION_READY
```

only when all of the following are true:

- deterministic generation path works on synthetic fixtures;
- candidate mining and balanced selection are implemented;
- visual human-review packets are buildable;
- IAA and adjudication are implemented;
- model snapshot manifests are enforced;
- code installation works in notebook runtime tests;
- batch and OOM behavior are implemented;
- resume revalidates old rows;
- all three primary adapters satisfy their contracts;
- import verifies expected hashes;
- whole-study promotion is atomic;
- post-run analysis is complete;
- all required notebooks pass static and synthetic runtime validation;
- and only real external inputs and real execution remain.

If any of these fail, report:

```text
PARTIALLY_READY_WITH_BLOCKERS
```

and list the exact remaining implementation blockers.

---

# 8. Required final response

Use this exact structure:

## 1. Executive verdict

Use one of:

```text
CVPR_PRE_EXECUTION_READY
PARTIALLY_READY_WITH_BLOCKERS
NOT_READY
```

## 2. Confirmed defects repaired

For each:

- path;
- original defect;
- implementation;
- regression test;
- validation result.

## 3. Generation and candidate pipeline

Explain what is now genuinely executable.

## 4. Model adapters and Kaggle runtime

Explain installation, snapshot verification, T4 precision, batching, OOM, sharding, and resume.

## 5. Human-review operations

Explain visual packets, blinding, qualification, IAA, adjudication, and final inclusion.

## 6. Import and analysis

Explain expected-hash checks, whole-study atomicity, human integration, statistics, and paper regeneration.

## 7. Notebook suite

List every notebook and its validated readiness level.

## 8. Validation results

Give exact commands, exits, and test totals.

## 9. Remaining external blockers

List only genuine external inputs or actions:

- source data;
- model snapshots;
- Kaggle smoke runs;
- real human review;
- real scientific runs;
- and licensing decisions.

## 10. Exact next sequence

Use the updated execution master plan.

## 11. Runtime estimates

Separate:

- smoke;
- confirmatory;
- Main study;
- second domain;
- CPU;
- GPU;
- and human review.

## 12. CVPR readiness assessment

Give separate scores for:

- engineering readiness;
- execution readiness;
- evidence readiness;
- paper readiness;
- and release readiness.

## 13. Files created or modified

Provide a compact manifest.

## 14. Master continuation point

Point to:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
reports/cvpr_runtime_hardening/CERTVIC_EXECUTION_REALIZATION_HANDOFF.md
```

---

# 9. Success standard

This task is complete only when the repository no longer confuses scaffolding with executable infrastructure.

The goal is not more documentation.

The goal is:

> **Every required pre-run path is implemented, fail-closed, provenance-locked, realistically tested, and ready for the user to execute with real datasets, real model snapshots, real human reviewers, and real Kaggle GPUs.**

Do not stop after identifying the gaps.

Repair them, test them, and leave the project at the strongest honest CVPR pre-execution ceiling.
