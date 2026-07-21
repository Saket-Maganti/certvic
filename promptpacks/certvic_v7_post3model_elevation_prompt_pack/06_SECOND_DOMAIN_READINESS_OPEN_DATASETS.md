# 06 — Second-Domain Readiness With Free/Open Data

You are Claude Opus acting as a senior CVPR research advisor, ML systems engineer, statistician, VLM evaluation scientist, reproducibility lead, and adversarial reviewer.

Repo:
/Users/saketmaganti/Projects/certVIC

Project:
CertVIC — Certified, Confound-Controlled Measurement of Visual Decision Updates in Vision-Language Models.

Hard constraints:
- No paid APIs.
- No paid cloud GPUs.
- No paid datasets.
- No paid annotation.
- No paid credits.
- Use local Mac/M4 CPU, Kaggle free GPU, Colab free fallback, public/free datasets, and open-source models only.
- No fake results, fake citations, or paper numbers not backed by real artifacts.
- No evidence claims from mock/smoke/synthetic/planned/unreviewed/simple-edit-only artifacts.
- Keep tests CPU/local.
- Heavy dependencies must be optional/import-safe.
- Do not weaken quality, detectability, evidence, leakage, claim, or paper-number gates.
- Do not initialize, commit, or tag unless explicitly asked.
- Keep all current results explicitly pilot-only unless the repo's evidence gates say otherwise.

Current real pilot facts to preserve:
- Same 91 reviewed presence/intervention items.
- Same 120 absent-object control items.
- Same protocol across Qwen2.5-VL-7B, InternVL2-8B, and LLaVA-OneVision-7B.
- Qwen2.5-VL-7B: a=0.923, p=0.176, Delta=0.747, CS lower bound=0.364, certified=true, absent control 60/60, present control 50/60.
- InternVL2-8B: a=0.923, p=0.099, Delta=0.824, CS lower bound=0.441, certified=true, absent control 58/60, present control 58/60.
- LLaVA-OneVision-7B: a=0.890, p=0.176, Delta=0.714, CS lower bound=0.331, certified=true, absent control 60/60, present control 58/60.
- The scientific core: open VLMs can detect natural absence, but often fail to revise after controlled low-detectability removals/edits.
- Current status: strong pilot, not paper-grade yet.
- Claude is already working separately on the spurious-flip/control_irrelevant arm. Do not duplicate that work; integrate its outputs only after they exist.

Before coding:
- Inspect existing files and commands.
- Reuse existing infrastructure.
- Do not invent paths.
- Explain briefly what you will do, then execute.

After coding:
- Run relevant CPU tests.
- Run security/privacy/claim guards if docs/results/reporting changed.
- Give exact commands and artifact paths.

## Motivation
A single ADE20K domain is a paper weakness. A second domain can improve external validity, but only if licensing/provenance and masks support the CertVIC protocol.

## Task
Create a second-domain readiness analysis for free/public datasets. Do not download large datasets unless explicitly asked.

## Candidate datasets to evaluate
Evaluate only using metadata/docs already in repo or public knowledge if already available locally. If current information is needed, say what must be manually verified.

Potential candidates:
- COCO panoptic/instances if available/free
- OpenImages subsets if masks/boxes sufficient
- LVIS if license and masks usable
- SA-1B is huge; likely not zero-cost practical; evaluate cautiously
- Cityscapes has license constraints; likely not ideal
- any already-local user dataset if present

## Create/update
- `docs/SECOND_DOMAIN_READINESS.md`
- `registry/datasets/second_domain_candidates.json`
- optional adapter stubs only if clearly useful and testable without data

## Scoring criteria
- mask availability
- object classes overlapping table/sofa/chair/car or new classes
- license compatibility
- data size/free feasibility
- annotation format complexity
- edit suitability
- review burden
- expected reviewer objections

## Deliverable
Rank top 2 candidates and recommend one next dataset.

## Hard rules
- Do not claim a dataset is usable without provenance/license evidence.
- Do not download paid/restricted data.
- Do not build a full adapter unless the candidate is selected.

## Validation
Run:
```bash
python3 -m pytest -q
```

## Final response
Give ranked candidates, blocked candidates, and the exact next local check.
