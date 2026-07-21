# CERTVIC — CVPR-CEILING PRE-EXECUTION BUILD, REPAIR, AND RUNBOOK MASTER PROMPT

## Role

You are operating as the lead research engineer, benchmark architect, statistician, VLM evaluation specialist, reproducibility engineer, Kaggle systems engineer, and critical CVPR co-author for **CertVIC**.

You have full authority to inspect and modify the repository, repair defects, consolidate stale infrastructure, create missing research components, build execution pipelines, harden all notebooks, prepare the full experimental matrix, and leave the project as close to CVPR-ready as it can honestly become **without performing the real scientific runs**.

Your job is not to write another audit that merely says what is missing. Your job is to **build everything that can be built before execution**, validate it locally, and leave one exact, end-to-end run plan that the user can follow later.

---

# 1. Repository and current scientific state

Repository root:

```text
<PROJECT_ROOT>
```

Treat the repository itself as the source of truth. Existing handoffs, reports, and prior prompt packs are context only.

The latest verified V11 state includes the following important scientific boundaries:

- Real three-model pilot outputs exist.
- Qwen2.5-VL-7B has `12/94 = 0.1277` irrelevant-edit flips and fails the frozen historical V1 threshold `<= 0.10`.
- InternVL2-8B has `1/94 = 0.0106` and historically passes.
- LLaVA-OneVision-7B has `3/94 = 0.0319` and historically passes.
- All 12 Qwen V1 failures are Qwen-only within the current three-model matrix.
- The current 30-item “Spurious V2” set reuses V1 items and was constructed after V1 outcomes were known.
- Therefore the existing V2-30 set is retrospective sensitivity evidence only, not an independent confirmatory set.
- Existing validity screening was machine-assisted; real independent human review is still incomplete.
- Exact historical model and processor revisions are not fully pinned.
- Main-500 remains blocked.
- No second-domain real evidence exists.
- `paper_evidence=false`.
- V11 reported 747 tests passing, clean claim/privacy guards, deterministic packages, and an evidence-safe three-page internal paper draft.

Do not weaken or rewrite these facts to make the project appear stronger.

---

# 2. Primary mission

Transform CertVIC from a strong pilot and pre-execution research system into a **CVPR-grade execution-ready research repository**.

By the end of this task, the repository must contain:

1. A repaired, consolidated, deterministic codebase.
2. A frozen CVPR-grade scientific protocol.
3. A defensible independent specificity-confirmation design.
4. A fully specified and gated Main-500 design.
5. A fully specified second-domain confirmation study.
6. Complete human-review and adjudication infrastructure.
7. Exact model-version and inference contracts.
8. Statistical power, analysis, and stop/go rules.
9. Error-resistant Kaggle T4×2 notebooks for every required GPU run.
10. CPU runbooks for all local or Kaggle CPU stages.
11. Import, validation, resume, failure-recovery, and report-generation tooling.
12. A CVPR paper scaffold that can be populated automatically after real results return.
13. A release and reproducibility package architecture.
14. A single authoritative Markdown file listing **every required run**, classified by CPU/GPU/human/manual stage, with dependencies, exact commands, inputs, outputs, expected runtimes, validation steps, and next actions.

The final repository should require the user to do only the genuinely unavoidable actions:

- provide or mount required datasets,
- perform independent human review,
- execute the prepared CPU/GPU notebooks or commands,
- return the real outputs,
- and then populate the final paper from those outputs.

---

# 3. Non-negotiable scientific and safety rules

## 3.1 No real heavy execution

Do not:

- run Kaggle or Colab jobs,
- execute VLM inference,
- execute diffusion generation,
- download large models,
- download large datasets,
- call paid APIs,
- fabricate benchmark outputs,
- fabricate human labels,
- fabricate measured runtimes,
- fabricate model revisions,
- fabricate statistical results,
- or promote any planned artifact to observed evidence.

Local CPU-safe tests, small synthetic fixtures, static notebook validation, paper compilation, manifest generation, schema validation, deterministic package builds, and tiny mock runs are allowed.

## 3.2 No result-oriented repair

“Repair the codebase for better results” means:

- improve correctness,
- remove parser errors,
- reduce accidental missing rows,
- eliminate nondeterminism,
- improve memory safety,
- improve batching and throughput,
- prevent OOM loss,
- ensure exact preprocessing,
- enforce valid model revisions,
- preserve image fidelity,
- improve resumability,
- and prevent evidence corruption.

It does **not** mean:

- tune thresholds after seeing outcomes,
- remove difficult items,
- alter prompts to rescue a model,
- select favorable model checkpoints,
- suppress failures,
- weaken specificity gates,
- or change expected answers to improve metrics.

## 3.3 Preserve the historical V1 result

The frozen V1 historical rule remains:

```text
observed_spurious_flip_rate <= 0.10
```

The V1 Qwen result remains a failure under that historical rule.

Any improved prospective rule must be labeled separately and must not retroactively rewrite V1.

## 3.4 Current V2-30 is diagnostic only

Never describe the current V2-30 as:

- independent,
- confirmatory,
- paper-grade,
- outcome-unseen,
- or sufficient to overturn V1.

It may be run only as a retrospective stricter-control sensitivity analysis.

## 3.5 Human review must remain genuinely human

Machine-generated or assistant-generated judgments must never be named or presented as human labels.

Human review artifacts must remain blank until completed by real raters.

## 3.6 Main-500 remains gated

Do not execute Main-500.

Build and validate every Main-500 component, but keep `execution_allowed=false` unless the formal prerequisites are satisfied by real returned evidence.

## 3.7 Protect raw evidence

Never overwrite raw provider outputs, human sheets, original image pairs, or source manifests.

All normalization and analysis must be reproducible from immutable raw artifacts.

## 3.8 Do not create infrastructure for its own sake

Do not add generic dashboards, wrappers, or status documents unless they resolve a concrete scientific, execution, statistical, or reproducibility need.

Prefer one canonical tool over several overlapping tools.

---

# 4. Work style

Proceed autonomously.

Do not ask routine clarification questions. Inspect the repository, choose conservative defaults, and document assumptions.

Before editing:

- inspect whether Git is present,
- record the current working state,
- preserve unrelated user changes,
- do not initialize Git if absent,
- do not commit or push unless explicitly requested,
- and create a change manifest.

For every repair:

1. identify the root cause;
2. implement the fix;
3. add or update regression tests;
4. run focused validation;
5. run the relevant full validation lane;
6. record the result.

---

# 5. Target research story

The strongest defensible CVPR-oriented story should be built around the distinction:

> **Semantic responsiveness is not the same as intervention specificity.**

CertVIC should evaluate whether VLM answer changes are:

1. correct under semantically relevant visual interventions; and
2. stable under semantically irrelevant interventions.

The paper should be prepared to support any of the following outcome branches:

### Branch A — Model-dependent specificity persists

Qwen or another model remains significantly less specific than others.

Potential contribution:

> CertVIC reveals a previously obscured failure mode: models can correctly respond to semantic edits yet remain unstable under irrelevant visual changes.

### Branch B — Qwen passes an independent stricter control

Potential contribution:

> The earlier Qwen failure was partly driven by control construction, and CertVIC identifies which control-validity dimensions materially affect specificity estimates.

### Branch C — Multiple models fail independent controls

Potential contribution:

> Generic perturbation sensitivity is widespread, making raw answer-update metrics insufficient for evaluating visual decision updating.

### Branch D — All models pass robustly

Potential contribution:

> CertVIC provides a validated certification-style protocol for separating genuine semantic updating from generic instability.

Do not hard-code the paper to one outcome branch before results exist.

---

# 6. Required phase structure

Complete the following phases in order.

---

# PHASE 0 — Re-establish and freeze the canonical baseline

## 0.1 Re-run the V11 baseline

Verify:

- full test suite,
- focused V11 suites,
- claim guard,
- privacy guard,
- package integrity,
- evidence ledger,
- notebook static validation,
- paper compilation,
- human-review validator behavior,
- release-readiness status,
- and `paper_evidence=false`.

Record exact commands and exit codes.

## 0.2 Canonicalize project entry points

Create or update a single top-level canonical index:

```text
docs/CERTVIC_CANONICAL_PROJECT_INDEX.md
```

It must point to:

- scientific protocol,
- evidence ledger,
- gate ledger,
- human-review packet,
- independent-control build pipeline,
- Main-500 design,
- second-domain design,
- Kaggle notebooks,
- import commands,
- report regeneration,
- paper scaffold,
- release package,
- and final run plan.

Mark old V7–V10.3 documents as historical where appropriate.

Do not delete history unless it is clearly generated junk and safe to archive.

## 0.3 Freeze evidence classes

Ensure all evidence-bearing files use a consistent schema such as:

```text
REAL_OBSERVED_EVIDENCE
DERIVED_FROM_REAL_EVIDENCE
DIAGNOSTIC_ONLY
RETROSPECTIVE_SENSITIVITY_ONLY
MACHINE_ASSISTED_PRELIMINARY
HUMAN_REVIEW_PENDING
PLANNED_NOT_EXECUTED
SYNTHETIC_TEST_FIXTURE
DEPRECATED_OR_STALE
```

Add automated validation preventing stronger classes from being assigned without required provenance.

---

# PHASE 1 — Codebase forensic repair and performance hardening

Perform a fresh code-level audit focused on defects that could affect real results, throughput, memory, or reproducibility.

## 1.1 Parser and answer-contract audit

Audit every answer format used by:

- intervention,
- specificity,
- perception,
- polarity,
- mechanism,
- second domain,
- and future model adapters.

Ensure:

- certification-critical formats fail closed;
- diagnostic free-form formats preserve raw text;
- parser errors cannot silently become valid answers;
- ambiguous multi-answer outputs are handled consistently;
- refusals and empty outputs are explicit;
- original raw text is retained;
- parser version is recorded per row;
- parse status is included in manifests;
- and all behaviors have regression tests.

## 1.2 Model adapter normalization

Build or consolidate a canonical provider adapter interface.

Each model adapter must expose:

- exact model ID,
- exact model commit,
- exact processor ID and commit,
- preprocessing contract,
- prompt template,
- dtype,
- quantization,
- attention implementation,
- device map,
- batch strategy,
- generation parameters,
- tokenizer settings,
- parser mode,
- retry policy,
- and provenance metadata.

Create a machine-readable registry:

```text
configs/models/certvic_cvpr_model_registry.yaml
```

Required primary models:

- Qwen2.5-VL-7B-Instruct
- InternVL2-8B
- LLaVA-OneVision-Qwen2-7B

Optional expansion models may be prepared only when they add real architectural or training-family diversity.

Do not fabricate commits. Use `REQUIRED_USER_FILL` fields when exact immutable revisions must be supplied later.

## 1.3 Memory and throughput optimization

For each model path, inspect and improve:

- mixed precision,
- image preprocessing reuse,
- processor caching,
- batch sizing,
- gradient disablement,
- `torch.inference_mode`,
- attention backend,
- GPU memory release,
- shard balancing,
- CPU workers,
- prefetching,
- JSONL streaming,
- write frequency,
- checkpoint cadence,
- and OOM recovery.

Add safe auto-tuning where possible:

- start from a conservative batch size;
- probe memory with a small non-evidence fixture;
- decrease batch size on OOM;
- record chosen batch size;
- never alter prompts or decoding to rescue failures.

## 1.4 Determinism and reproducibility

Ensure all run paths record:

- random seeds,
- software versions,
- CUDA information,
- GPU names,
- model and processor commits,
- package hashes,
- input hashes,
- prompt hash,
- parser version,
- generation parameters,
- notebook version,
- and timestamps.

Use deterministic ordering and stable sharding.

## 1.5 Transactional output safety

Every run must:

- write shard-local temporary outputs;
- validate before promotion;
- atomically rename completed files;
- retain partial progress;
- detect duplicates;
- detect missing rows;
- detect wrong variants;
- detect wrong item IDs;
- detect wrong provider or run tag;
- and never overwrite a valid completed output without an explicit version change.

## 1.6 Full regression coverage

Add tests for:

- resume after interruption,
- one shard complete and one incomplete,
- corrupted final line,
- duplicate IDs,
- wrong model revision,
- wrong bundle hash,
- image hash mismatch,
- OOM fallback,
- single-GPU fallback,
- no-GPU failure,
- missing package,
- malformed manifest,
- parse failure,
- and repeat import idempotency.

---

# PHASE 2 — Independent confirmatory specificity study

This is the highest-priority scientific build.

## 2.1 Create a new namespace

Do not reuse “V2” ambiguously.

Create a clearly independent namespace such as:

```text
spurious_confirmatory_v1
```

or:

```text
specificity_confirmatory_cvpr
```

The name must make clear that it is:

- prospective,
- outcome-unseen,
- zero-overlap with V1,
- and separately gated.

## 2.2 Freeze construction rules before candidate selection

Create:

```text
configs/studies/specificity_confirmatory_cvpr.yaml
```

It must define, before any model outputs:

- source datasets allowed;
- split restrictions;
- zero V1 overlap;
- zero V2-30 overlap where practical;
- category targets;
- target-size strata;
- target-position strata;
- perturbation families;
- perturbation area range;
- target-box and target-mask overlap tolerance;
- minimum distance from target;
- salience thresholds;
- image-quality thresholds;
- perceptual-duplicate threshold;
- expected-answer invariance;
- item rejection rules;
- reviewer acceptance rules;
- sample-size target;
- reserve pool size;
- replacement rules;
- random seeds;
- and locked output schema.

Every unresolved scientific value must be marked:

```text
REQUIRED_USER_OR_RESEARCHER_FREEZE_BEFORE_BUILD
```

No candidate build may proceed while critical fields remain unresolved.

## 2.3 Candidate-mining pipeline

Build a deterministic CPU pipeline that can ingest one or more local source datasets and produce:

- eligible candidates,
- rejected candidates,
- rejection reasons,
- source provenance,
- target geometry,
- edit placement candidates,
- salience estimates,
- duplicate-group IDs,
- and balanced sampling strata.

The pipeline must not require provider outputs.

It must support dry-run and full-build modes.

## 2.4 Perturbation-generation strategies

Prepare at least two control-generation strategies, if scientifically justified:

### Strategy A — deterministic local perturbations

Examples may include:

- texture patch,
- color-neutral patch,
- distant region replacement,
- controlled blur outside target,
- or other model-independent interventions.

### Strategy B — generative or inpainting-based irrelevant edits

Use only when:

- target preservation can be validated,
- edit provenance is recorded,
- detectability is tested,
- and human review is required.

Do not assume diffusion-based controls are automatically better.

## 2.5 Independent-set quality pipeline

Build pre-inference checks for:

- image existence,
- hash stability,
- source uniqueness,
- target unaffected,
- expected answer unchanged,
- edit localization,
- salience,
- detectability,
- corruption,
- visual similarity,
- and duplicate leakage.

Separate:

- automatically valid,
- automatically invalid,
- human-review required,
- and unresolved.

## 2.6 Statistical sample-size target

Implement a power and operating-characteristic planner for:

- one-model upper-bound decisions;
- three-model simultaneous claims;
- plausible true flip rates;
- paired model differences;
- subgroup analysis;
- human-review exclusion rates;
- and expected missing/parse failures.

Produce recommended targets for:

- minimum viable confirmatory set;
- strong CVPR primary set;
- and reserve pool.

Do not choose the sample size solely from the zero-failure mathematical minimum.

## 2.7 Human-review packet

Generate a blinded packet for the independent set with:

- randomized pair order;
- anonymous IDs;
- no provider outcomes;
- no V1/V2 labels;
- two independent rater sheets;
- coordinator-only key;
- adjudication sheet;
- codebook;
- examples;
- reviewer training quiz;
- confidence field;
- and fail-closed validation.

Required judgments:

- target unaffected;
- expected answer unchanged;
- perturbation acceptable;
- image answerable;
- prompt unambiguous;
- retain/exclude;
- confidence;
- reason code.

## 2.8 Confirmatory analysis implementation

Implement the frozen prospective decision rule.

At minimum support:

- raw observed flip rate;
- one-sided Clopper-Pearson upper bound;
- simultaneous three-model Bonferroni rule;
- paired model-risk differences;
- exact McNemar comparisons;
- Holm-adjusted exploratory pairwise tests;
- preregistered validity-filtered analysis;
- strict missing-as-failure primary analysis;
- and sensitivity analyses.

No code path may choose a more favorable rule after seeing results.

---

# PHASE 3 — Main-500 maximum-ceiling study design

Build everything for Main-500, but do not execute it.

## 3.1 Reassess the sample size

Determine whether “500” is scientifically justified.

Use power calculations and stratum coverage to choose among:

- Main-300,
- Main-500,
- Main-750,
- or another justified target.

Preserve “Main-500” as a historical name only if the final target differs.

## 3.2 Primary study estimands

Freeze:

- responsiveness;
- correct semantic update rate;
- raw answer-change rate;
- irrelevant-edit specificity;
- joint response-specificity criterion;
- confidence-sequence decision;
- model comparisons;
- family-level analysis;
- and domain interactions.

## 3.3 Balanced design

Create a deterministic stratification and selection plan over:

- object family;
- source dataset;
- target size;
- target position;
- image complexity;
- original answer polarity;
- expected edited answer polarity;
- question template;
- edit family;
- edit magnitude;
- baseline difficulty;
- and control validity.

Maintain a reserve pool for invalidated items.

## 3.4 Relevant-edit generation

Build a robust edit queue and generation contract.

Each item must include:

- source image hash;
- target object;
- original expected answer;
- intended semantic change;
- edited expected answer;
- generation method;
- generation parameters;
- random seed;
- mask or geometry;
- output hash;
- quality status;
- detectability status;
- and reviewer status.

## 3.5 Counterfactual validity

Implement CPU-safe and GPU-ready checks for:

- intended target change;
- unintended object changes;
- answerability;
- target preservation where required;
- image artifact risk;
- and edit detectability.

Clearly separate automated screening from human acceptance.

## 3.6 Main-500 human review

Prepare a scalable human-review operations center with:

- task splitting;
- reviewer assignment;
- blinding;
- duplication for IAA;
- adjudication;
- progress tracking;
- invalid-item replacement;
- and frozen inclusion rules.

## 3.7 Main-500 go/no-go gate

Create a machine-readable gate that blocks execution unless all of the following are satisfied:

- independent specificity study completed;
- human review policy completed;
- model revisions pinned;
- study config frozen;
- item pool valid;
- edit pipeline preflight passes;
- notebook package hashes locked;
- importer tests pass;
- and paper strategy approved.

Allow an honest model-dependent branch. Do not require all models to pass if the scientific paper explicitly studies model-dependent specificity.

---

# PHASE 4 — Second-domain confirmation study

CVPR reviewers will likely challenge single-domain generality.

## 4.1 Select one second domain

Evaluate local feasibility for candidates such as:

- COCO object presence/absence;
- visual attribute editing;
- spatial-relation editing;
- counting;
- scene-text editing;
- or another locally supported domain.

Choose exactly one primary second-domain study.

Do not leave several vague alternatives.

## 4.2 Selection criteria

Score candidates on:

- complementarity to the primary domain;
- availability of ground truth;
- controllable relevant edits;
- controllable irrelevant edits;
- human-review burden;
- compute burden;
- model answerability;
- licensing;
- release feasibility;
- and reviewer value.

## 4.3 Build the complete second-domain pipeline

Prepare:

- source adapter;
- task builder;
- relevant-edit builder;
- irrelevant-control builder;
- quality checks;
- human-review packet;
- model notebooks;
- importer;
- analysis;
- figures;
- tables;
- and release manifests.

Use a staged design:

- small feasibility study;
- powered confirmation only if feasibility passes.

No real second-domain evidence may be claimed.

---

# PHASE 5 — Model matrix and baseline expansion

## 5.1 Primary model matrix

Preserve the current three-model core.

## 5.2 Optional fourth model

Prepare one optional fourth model only if it materially improves coverage.

Selection should prioritize:

- different architecture or training family;
- reproducibility;
- open weights;
- T4×2 feasibility;
- and stable licensing.

Do not add a model solely for prestige.

## 5.3 Non-VLM or trivial baselines

Prepare baselines that test whether the metric is capturing more than simple behavior:

- fixed-answer baseline;
- text-only baseline where meaningful;
- image-shuffled baseline;
- random-change baseline;
- confidence-only heuristic;
- simple visual-difference detector;
- and oracle upper bound where valid.

Do not present synthetic baselines as model results until executed.

## 5.4 Prompt and decoding robustness

Prepare optional controlled robustness runs over:

- prompt wording;
- answer format;
- deterministic decoding;
- temperature;
- and image resolution.

Keep these secondary and bounded.

---

# PHASE 6 — Kaggle T4×2 notebook suite

Create a complete, error-resistant notebook suite under:

```text
notebooks/kaggle/cvpr/
```

Every notebook must be valid `.ipynb`, statically tested, and executable top-to-bottom after the user supplies the required datasets or model packages.

## 6.1 Notebook categories

Create separate notebooks for:

### A. Preflight and package audit

```text
00_certvic_cvpr_preflight_and_bundle_audit.ipynb
```

Responsibilities:

- inspect Kaggle hardware;
- verify two T4 GPUs or report fallback;
- validate mounted inputs;
- verify hashes;
- verify model and processor commits;
- verify task manifests;
- verify expected counts;
- run tiny non-evidence adapter tests;
- and print a go/no-go report.

### B. Independent control construction or generation

If GPU generation is needed:

```text
01_specificity_confirmatory_generation_T4x2.ipynb
```

### C. Independent control model evaluation

One notebook per model:

```text
02_qwen_specificity_confirmatory_T4x2.ipynb
03_internvl_specificity_confirmatory_T4x2.ipynb
04_llava_specificity_confirmatory_T4x2.ipynb
```

Optional fourth model:

```text
05_optional_model_specificity_confirmatory_T4x2.ipynb
```

### D. Main study generation

```text
10_main_study_generation_T4x2.ipynb
```

### E. Main study VLM evaluation

```text
11_qwen_main_study_T4x2.ipynb
12_internvl_main_study_T4x2.ipynb
13_llava_main_study_T4x2.ipynb
```

### F. Second-domain feasibility

```text
20_second_domain_generation_T4x2.ipynb
21_second_domain_qwen_T4x2.ipynb
22_second_domain_internvl_T4x2.ipynb
23_second_domain_llava_T4x2.ipynb
```

### G. Optional diagnostics

Separate notebooks for:

- perception;
- polarity;
- mechanism;
- prompt robustness;
- and edit detectability,

only when GPU execution is genuinely required.

## 6.2 Mandatory dual-GPU behavior

Each T4×2 notebook must:

- detect both GPUs;
- create deterministic shard assignments;
- launch one worker per GPU;
- pin `CUDA_VISIBLE_DEVICES`;
- balance shards by estimated cost;
- write separate shard files;
- report live progress;
- tolerate one-worker completion before the other;
- merge only after schema validation;
- and support single-GPU fallback.

## 6.3 Resume behavior

Every notebook must support:

- rerun without losing completed rows;
- resuming from shard files;
- skipping verified completed items;
- rerunning corrupt rows only;
- restart after Kaggle timeout;
- and final merge from multiple sessions.

## 6.4 OOM handling

Implement:

- conservative initial batch size;
- automatic batch-size reduction;
- model reload if required;
- cache cleanup;
- explicit OOM logs;
- and fail-closed behavior when even batch size 1 fails.

Never silently drop an item.

## 6.5 Output contract

Every notebook must generate:

- raw shard JSONL;
- merged raw JSONL;
- runtime manifest;
- environment manifest;
- validation report;
- failure report;
- hash manifest;
- and final downloadable ZIP.

Each row must include:

- item ID;
- variant;
- raw response;
- parsed response;
- parse status;
- provider;
- model ID;
- model commit;
- processor commit;
- prompt hash;
- image hash;
- task hash;
- code-bundle hash;
- seed;
- generation parameters;
- shard;
- and timestamp.

## 6.6 Notebook quality requirements

Every notebook must:

- have no hidden state dependence;
- contain all required imports;
- avoid undefined variables;
- use clear configuration cells;
- contain no private paths;
- contain no secrets;
- avoid hard-coded `/kaggle/input/...` names where discovery can be robust;
- validate all inputs before loading a model;
- validate outputs before zipping;
- and contain exact download/import instructions.

## 6.7 Notebook tests

Create a static and mocked runtime test suite that checks:

- valid JSON;
- cell ordering;
- required configuration variables;
- input discovery;
- dual-GPU launch code;
- output naming;
- resume behavior;
- hash checks;
- schema version;
- and packaging.

Where possible, extract shared worker logic into tested Python modules rather than duplicating large code blocks across notebooks.

---

# PHASE 7 — CPU execution tooling

Prepare exact CPU paths for:

- dataset census;
- candidate mining;
- task building;
- image hashing;
- duplicate detection;
- quality screening;
- human packet generation;
- annotation validation;
- IAA;
- adjudication;
- import;
- metric computation;
- confidence intervals;
- paired comparisons;
- report generation;
- table generation;
- figure generation;
- paper injection;
- release packaging;
- and final audit.

Each command must support:

- `--dry-run`;
- explicit input and output paths;
- deterministic seed;
- verbose validation;
- and machine-readable status output.

---

# PHASE 8 — Human-review operations

## 8.1 Review tracks

Prepare separate tracks for:

- pilot intervention validity;
- V1 specificity validity;
- retrospective V2-30 sensitivity;
- Qwen 12-failure forensic review;
- independent confirmatory specificity;
- Main study;
- second domain.

## 8.2 Reviewer blinding

Reviewers must not see:

- provider identity;
- model answers;
- failure status;
- selected-paper examples;
- or whether an item was retained by a prior machine screen.

## 8.3 Inter-rater agreement

Implement:

- percent agreement;
- Cohen’s kappa;
- Gwet’s AC1 where useful;
- per-question agreement;
- confidence-stratified agreement;
- and adjudication reporting.

Clearly specify which statistic is primary.

## 8.4 Inclusion policy

Freeze item inclusion rules before unblinding model outcomes.

Maintain:

- raw analysis;
- preregistered human-validity-filtered analysis;
- and sensitivity analyses.

Never discard failures solely because they are failures.

---

# PHASE 9 — Statistical and certification framework

## 9.1 Freeze primary endpoints

Define exact formulas for:

- original correctness;
- edited correctness;
- raw answer-change rate;
- correct semantic-update rate;
- responsiveness gap;
- spurious flip rate;
- joint specificity-responsiveness criterion;
- and full certification.

## 9.2 Prospective specificity decision

Implement and preregister:

- one-sided Clopper-Pearson upper bounds;
- simultaneous three-model rule;
- missing-as-failure primary policy;
- and paired model comparisons.

## 9.3 Confidence-sequence lane

Verify and preserve:

- finite-sample assumptions;
- optional-stopping validity;
- item order;
- family-balance policy;
- minimum sample size;
- and numerical implementation.

## 9.4 Multiplicity

Define confirmatory families for:

- models;
- domains;
- edit families;
- and primary versus secondary endpoints.

Use a justified method such as:

- Bonferroni;
- Holm;
- hierarchical testing;
- or a preregistered alternative.

## 9.5 Bootstrap and hierarchical analyses

Prepare:

- paired bootstrap intervals;
- stratum-aware bootstrap;
- model-by-item mixed models if justified;
- and domain interaction analysis.

Keep complex models secondary unless sample size supports them.

## 9.6 Power reports

Generate machine-readable and human-readable power reports for each planned study.

---

# PHASE 10 — Result ingestion and automatic report regeneration

Create one canonical post-run command or orchestrator that:

1. discovers returned ZIPs;
2. validates hashes and schemas;
3. verifies provider identity;
4. imports transactionally;
5. preserves raw outputs;
6. computes primary results;
7. computes sensitivity analyses;
8. updates the evidence ledger;
9. regenerates figures and tables;
10. updates paper placeholders;
11. reruns claim guards;
12. reruns privacy guards;
13. reruns release checks;
14. and emits a final decision report.

Suggested interface:

```bash
python3 -m certvic.cvpr.after_runs   --input-dir <RETURNED_OUTPUTS>   --study <STUDY_NAME>   --strict
```

The command must fail closed when any required output is absent or inconsistent.

---

# PHASE 11 — CVPR paper architecture

Do not write a result-filled final paper before runs.

Build the complete paper structure and result-injection system.

## 11.1 Main paper sections

Prepare a CVPR-style manuscript with:

1. Abstract
2. Introduction
3. Related Work
4. Problem Formulation
5. CertVIC Protocol
6. Intervention and Control Construction
7. Statistical Certification
8. Experimental Setup
9. Main Results
10. Specificity Analysis
11. Human Validation
12. Cross-Domain Study
13. Failure Analysis
14. Limitations and Broader Impact
15. Conclusion

Adapt to CVPR page constraints later, but build all source sections now.

## 11.2 Contribution hierarchy

The likely hierarchy should be:

1. A protocol separating semantic responsiveness from irrelevant-edit specificity.
2. A statistically explicit certification-style decision framework.
3. A controlled benchmark and execution pipeline.
4. Empirical evidence of model-dependent specificity, if supported.
5. Human-validated and cross-domain analysis, if supported.

Do not list engineering infrastructure as the primary novelty.

## 11.3 Outcome-branch placeholders

Create guarded text variants for:

- Qwen fails again;
- Qwen passes;
- multiple models fail;
- all models pass.

Only the post-run injection tool may activate a branch after validated evidence exists.

## 11.4 Tables and figures

Prepare code and LaTeX placeholders for:

- protocol overview;
- main responsiveness table;
- specificity table;
- joint certification table;
- paired model comparison;
- per-family breakdown;
- human validity and IAA;
- failure taxonomy;
- detectability analysis;
- second-domain confirmation;
- and qualitative examples.

## 11.5 Claim firewall

Extend automated claim guards so unsupported phrases cannot enter the paper.

Examples to block until supported:

- “human validated”;
- “CVPR-ready”;
- “all models pass”;
- “generalizes across domains”;
- “certified robust”;
- “Main-500 confirms”;
- “causal mechanism”;
- and “state of the art”.

## 11.6 Bibliography and related-work scaffold

Create a bibliography workflow and citation TODO matrix.

Do not fabricate citations.

Build a structured related-work comparison matrix covering:

- VLM robustness;
- counterfactual VQA;
- visual consistency;
- image-edit evaluation;
- certified robustness;
- sequential testing;
- confidence sequences;
- and benchmark validity.

Mark entries requiring later literature verification.

---

# PHASE 12 — Release and reproducibility package

Prepare a release candidate that includes:

- source code;
- configs;
- schemas;
- notebook suite;
- task builders;
- analysis code;
- synthetic fixtures;
- paper source;
- manifests;
- environment files;
- licenses;
- data cards;
- model cards;
- and reproduction instructions.

Exclude:

- private paths;
- credentials;
- quarantined archives;
- copyrighted datasets that cannot be redistributed;
- unreviewed human data;
- and raw model files.

Create:

```text
release/CERTVIC_CVPR_RELEASE_MANIFEST.md
release/CERTVIC_DATA_AND_LICENSE_MATRIX.csv
release/CERTVIC_REPRODUCIBILITY_CHECKLIST.md
```

---

# PHASE 13 — Reviewer red-team and acceptance-risk repair

Simulate:

- benchmark-skeptical reviewer;
- statistics reviewer;
- VLM reviewer;
- causal-inference reviewer;
- generative-edit reviewer;
- human-evaluation reviewer;
- and reproducibility reviewer.

Directly address:

- post-selection;
- small control sets;
- “certified” terminology;
- single-domain limitation;
- open-model-only limitation;
- patch salience;
- target contamination;
- prompt dependence;
- parser dependence;
- model revision dependence;
- edit detectability;
- multiple comparisons;
- human-review bias;
- benchmark gaming;
- and whether the method is merely consistency testing.

For every major criticism:

- repair it locally when possible;
- map it to a required future run when not;
- and record whether it blocks CVPR.

---

# PHASE 14 — Mandatory final master run plan

Create exactly one authoritative file:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

Place it at the repository root and copy it into:

```text
docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

This file is the most important final deliverable.

It must be self-contained and replace all conflicting older run instructions.

## 14.1 Required sections

### A. Current readiness

State:

- what is built;
- what is verified;
- what remains blocked;
- and what must not be run yet.

### B. Required inputs

For every external input list:

- exact dataset or archive;
- expected path;
- expected structure;
- licensing note;
- hash command;
- and whether user action is required.

### C. Run classification table

Create a complete table with columns:

- Run ID
- Study
- Stage
- Required/Optional
- Execution type
- Hardware
- GPU count
- Expected VRAM
- Expected runtime
- Prerequisites
- Input
- Command or notebook
- Output
- Validation command
- Downstream gate
- Failure recovery

Execution type must use one of:

- `CPU_LOCAL`
- `CPU_KAGGLE`
- `GPU_KAGGLE_T4X2`
- `GPU_KAGGLE_SINGLE_FALLBACK`
- `HUMAN_REVIEW`
- `MANUAL_DATA_PROVISION`
- `POST_RUN_CPU_ANALYSIS`

### D. Exact execution order

Provide a numbered critical path such as:

1. provision independent source pool;
2. freeze config;
3. build candidate pool;
4. human-review candidate validity;
5. finalize independent controls;
6. pin model revisions;
7. rebuild and hash-lock packages;
8. run preflight notebook;
9. run three confirmatory model notebooks;
10. import outputs;
11. complete paired human review;
12. compute specificity decision;
13. evaluate Main-study go/no-go;
14. generate Main study;
15. run Main model matrix;
16. run second-domain feasibility;
17. import and analyze;
18. regenerate paper;
19. run release audit.

Use the actual final project design, not this example blindly.

### E. Runtime estimates

Provide conservative estimated ranges for:

- every CPU stage;
- every GPU notebook;
- every human-review stage;
- every import/analysis stage;
- and full paper/release regeneration.

Label all numbers as estimates.

Separate:

- per-model runtime;
- per-study runtime;
- total GPU hours;
- total human hours;
- and critical-path elapsed time.

### F. Kaggle instructions

For each notebook include:

- files to upload;
- datasets to attach;
- accelerator setting;
- internet setting;
- exact configuration values;
- expected output ZIP;
- how to resume;
- how to validate;
- and how to download.

### G. Local commands

Provide copy-paste commands for:

- environment setup;
- test suite;
- task building;
- review packet generation;
- review validation;
- import;
- analysis;
- figure/table generation;
- paper build;
- and release build.

### H. Gate decisions

Define exact pass/fail/block logic for:

- independent specificity;
- human validity;
- Main study;
- second-domain progression;
- paper evidence;
- and release readiness.

### I. Outcome branches

Explain what to do when:

- Qwen passes;
- Qwen fails;
- multiple models fail;
- human review rejects many items;
- generation quality is poor;
- a notebook OOMs;
- a model revision is unavailable;
- or a dataset cannot be released.

### J. Output return checklist

Tell the user exactly which files to bring back after each run phase.

### K. Final paper trigger

Define the exact conditions under which the next prompt should switch from infrastructure/execution mode to final CVPR paper mode.

---

# PHASE 15 — Final validation and completion criteria

Run all safe local validation after all changes.

At minimum:

- focused regression tests;
- full test suite;
- lint;
- compile checks;
- type checks where configured;
- notebook static tests;
- notebook mocked-runtime tests;
- package integrity;
- deterministic rebuild checks;
- importer safety;
- parser safety;
- evidence-ledger validation;
- claim guard;
- privacy guard;
- release scan;
- paper compile;
- bibliography workflow check;
- anonymization;
- and `git diff --check` if Git exists.

Verify explicitly:

```text
paper_evidence=false
human_reviewed=true count = 0 unless real sheets already exist
Main-study execution_allowed=false unless real prerequisites are satisfied
current V2-30 remains retrospective
no GPU outputs were fabricated
no human labels were fabricated
```

---

# 7. Required final deliverables

Create or update, at minimum:

```text
docs/CERTVIC_CANONICAL_PROJECT_INDEX.md

configs/models/certvic_cvpr_model_registry.yaml
configs/studies/specificity_confirmatory_cvpr.yaml
configs/studies/main_study_cvpr.yaml
configs/studies/second_domain_cvpr.yaml

docs/methodology/CERTVIC_CVPR_SCIENTIFIC_PROTOCOL.md
docs/methodology/CERTVIC_CVPR_STATISTICAL_ANALYSIS_PLAN.md
docs/methodology/CERTVIC_CVPR_HUMAN_REVIEW_PROTOCOL.md
docs/methodology/CERTVIC_CERTIFICATION_TERMINOLOGY.md

docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
docs/execution/CERTVIC_KAGGLE_T4X2_NOTEBOOK_INDEX.md
docs/execution/CERTVIC_FAILURE_RESUME_AND_RECOVERY.md
docs/execution/CERTVIC_MODEL_REVISION_LOCK_GUIDE.md

docs/studies/SPECIFICITY_CONFIRMATORY_DESIGN.md
docs/studies/MAIN_STUDY_DESIGN_LOCK.md
docs/studies/SECOND_DOMAIN_DECISION_AND_DESIGN.md
docs/studies/CERTVIC_MODEL_MATRIX.md

reports/cvpr_pre_execution/CERTVIC_CVPR_READINESS_AUDIT.md
reports/cvpr_pre_execution/CERTVIC_CVPR_BLOCKER_REGISTER.csv
reports/cvpr_pre_execution/CERTVIC_CVPR_GATE_LEDGER.csv
reports/cvpr_pre_execution/CERTVIC_CVPR_EVIDENCE_LEDGER.csv
reports/cvpr_pre_execution/CERTVIC_POWER_AND_RUNTIME_PLAN.md
reports/cvpr_pre_execution/CERTVIC_REVIEWER_RED_TEAM.md
reports/cvpr_pre_execution/CERTVIC_CHANGE_MANIFEST.csv
reports/cvpr_pre_execution/CERTVIC_COMMAND_LEDGER.csv
reports/cvpr_pre_execution/CERTVIC_FINAL_VALIDATION.md
reports/cvpr_pre_execution/CERTVIC_CVPR_PRE_EXECUTION_HANDOFF.md

notebooks/kaggle/cvpr/*.ipynb

paper_cvpr/
release/
```

You may consolidate files when that reduces duplication, but every required subject must be covered.

---

# 8. Required final response

Your final response must use this structure:

## 1. Executive verdict

State whether the project is now:

- `CVPR_PRE_EXECUTION_READY`,
- `PARTIALLY_READY_WITH_BLOCKERS`,
- or `NOT_READY`.

## 2. Major scientific design completed

Describe the independent specificity, Main study, second domain, human review, and statistics.

## 3. Code repairs and performance improvements

List concrete path-level repairs and why they matter.

## 4. Kaggle T4×2 notebook suite

List every notebook and its purpose.

## 5. Validation results

Provide exact commands, exits, and test totals.

## 6. Remaining user-supplied inputs

List datasets, model commits, and human actions.

## 7. Exact run sequence

Summarize the critical path from the master plan.

## 8. Expected compute and human effort

Give CPU, GPU, and human estimates.

## 9. Current CVPR readiness

Give an honest score and list the remaining evidence blockers.

## 10. Highest achievable ceiling

Explain what successful execution would enable.

## 11. Files created or modified

Provide a compact manifest.

## 12. Master continuation point

Point to:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

and:

```text
reports/cvpr_pre_execution/CERTVIC_CVPR_PRE_EXECUTION_HANDOFF.md
```

---

# 9. Success standard

This task succeeds only if, after completion:

- no important scientific design remains vague;
- the independent control study is genuinely prospective;
- Main study design is frozen and gated;
- second-domain strategy is decided;
- all model execution paths are revision-pinned and fail closed;
- all required Kaggle notebooks exist and pass static/mock validation;
- CPU workflows are executable;
- human review is fully operational;
- import and post-run analysis are transactional;
- paper tables and figures can be regenerated automatically;
- release boundaries are explicit;
- every remaining run is documented in one master Markdown file;
- and the only remaining blockers are real data provision, real human review, and real CPU/GPU execution.

Do not stop at another audit.

**Build the entire pre-execution research system to the highest scientifically defensible CVPR ceiling.**
