# CertVIC Codex V2 Prompt 00 — Master Context and Non-Negotiables

You are working inside the existing CertVIC repository:

`/Users/saketmaganti/Projects/certVIC`

Project: **Certified Visual Consistency / CertVIC**

Working title: **“Certifying When Vision-Language Models See the Change: Anytime-Valid Consistency Under Controlled Real-Image Interventions”**

## Current state

The project has passed V1 through V1.5:

- V1 smoke audit.
- V1.1 scaffold hardening.
- V1.2 real-pilot readiness.
- V1.3 ADE20K mask manifest readiness.
- V1.4 pilot candidate + edit-plan readiness.
- V1.5 tiny edit generation + quality gates.

Current tests before V2: `python3 -m pytest -q -> 110 passed`.

Main handoffs:

- `docs/V1_SMOKE_AUDIT_REPORT.md`
- `docs/V1_1_SCAFFOLD_HARDENING_REPORT.md`
- `docs/V1_2_REAL_PILOT_READINESS_REPORT.md`
- `docs/V1_3_ADE20K_MASK_MANIFEST_REPORT.md`
- `docs/V1_4_PILOT_CANDIDATE_EDIT_PLAN_REPORT.md`
- `docs/V1_5_TINY_EDIT_GENERATION_QUALITY_REPORT.md`

## V2 goal

Upgrade CertVIC from a working scaffold into a **paper-producing research system**.

V2 must build:

1. Baseline and full-system audits.
2. Human/visual review and approval.
3. ADE20K label-policy and task-family eligibility.
4. Modular edit engine and stronger quality gates.
5. Open-local VLM inference readiness on free compute.
6. Baselines and ablations.
7. Certification, power planning, and optional-stopping diagnostics.
8. Paper-ready tables, figures, and failure galleries.
9. Recipe-first artifact packaging.
10. Tiny real pilot and 200-pilot runbooks.

## Absolute zero-cost rule

Forbidden:

- paid APIs
- paid cloud GPUs
- paid datasets
- paid annotation
- paid storage
- paid experiment tracking
- required proprietary endpoints
- “just use credits” shortcuts

Allowed:

- local Mac/CPU
- Kaggle free GPU
- Colab free fallback
- open-source packages
- user-supplied local datasets
- optional free-tier reference only if disabled by default, explicitly free, version-labeled, non-core, and never required

## No-git rule

Do not initialize git. Do not create commits. Do not create tags. The user will decide when to use git.

## Evidence discipline

Do not make paper/evidence claims until claim gates allow them.

Evidence claims require all of:

- real split
- real image source
- generated edits passing quality gates
- visual/human validity approval
- non-mock provider
- open-local/free allowed inference
- prediction scoring
- CS available when claiming certification
- claim wording approved
- paper gate passed

Smoke/fake/simple/edit-only/human-reviewed artifacts are not paper evidence by themselves.

## Safety language

Allowed:

- controlled single-factor visual interventions
- decision consistency under intervention
- intervention-consistency gap
- anytime-valid certification
- recipe-first artifact
- budget-certified evaluation

Forbidden:

- VLMs cannot reason causally
- proves lack of understanding
- unsafe for autonomous driving
- safe for autonomous driving
- frontier models fail
- all VLMs fail
- deployment claims
- generalization beyond tested edit families/domains

## For every V2 prompt

1. Read this master context first.
2. Inspect referenced files before modifying.
3. Preserve V1–V1.5 behavior.
4. Add tests.
5. Add/update docs.
6. Run `python3 -m pytest -q`.
7. Create the requested handoff doc.
8. Report files changed, tests run, commands added, and blockers.

Do not skip tests. Do not fabricate results. Do not modify paper result sections with fake numbers.
