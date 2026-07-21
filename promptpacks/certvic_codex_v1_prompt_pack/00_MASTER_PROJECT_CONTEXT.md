# Codex Prompt 00 — MASTER PROJECT CONTEXT / NON-NEGOTIABLES

You are working inside a new research-code repository for a zero-cost CVPR 2027 project.

Project name:
`certvic`

Working paper title:
“Certifying When Vision-Language Models See the Change: Anytime-Valid Consistency Under Controlled Real-Image Interventions”

Short name:
Certified Visual Consistency / CertVIC

## Core thesis

Build a method-first evaluation pipeline for vision-language models. The paper is not “just another benchmark.” The contribution is:

1. A zero-cost generator of controlled single-factor counterfactual image pairs from licensed/public real-image sources.
2. A consistency evaluation protocol where the expected answer-change is determined by the controlled edit itself.
3. Anytime-valid certification of intervention-consistency rates and intervention-consistency gaps under limited compute and optional stopping.

## Strict zero-cost rule

This project must use:
- Free Kaggle GPU only.
- Free Colab only as fallback.
- Local Mac/CPU.
- Open-source models.
- Public/free datasets.
- Optional free-tier reference APIs only if genuinely free and explicitly marked as non-core/reference-only.

Never add:
- Paid APIs.
- Paid cloud GPU assumptions.
- Paid annotation workflows.
- Paid datasets.
- Paid storage.
- Paid experiment tracking.
- Paid model endpoints.
- Hidden paid dependencies.

If an optional feature may cost money, implement it as disabled by default, guarded by explicit config flags, and document it as non-core.

## Project posture

Avoid unsafe or overbroad claims.

Allowed language:
- controlled single-factor visual intervention
- decision consistency
- intervention-consistency gap
- anytime-valid certification
- budget-certified evaluation
- real-image edit-generated counterfactual pairs
- recipe-first artifact

Avoid:
- “VLMs cannot reason causally”
- “This proves models do not understand vision”
- “Autonomous driving systems are unsafe”
- “Clinical/autonomous deployment claims”
- “Frontier models fail”
- Any untested generalization beyond the actual edit families/domains.

## Core task families

Implement the project around three initial families:

1. Support / physical stability
   - Remove support object.
   - Required behavior: model should change decision when support is removed.

2. Occlusion / safety decision
   - Occlude hazard/object.
   - Required behavior: model should remain cautious or avoid unsafe flip depending on task spec.

3. Affordance / reachability
   - Move/displace tool/object.
   - Required behavior: model should change action feasibility decision.

## Core domains

Initial domains:
- Household/object scenes.
- Driving/road scenes, only as evaluation stimuli and never as deployment claims.

## Data strategy

Recipe-first artifact:
- Store source pointers, hashes, masks, edit parameters, regeneration scripts.
- Do not re-host non-redistributable pixels.
- Re-host only public-domain/CC0 pixels when safe.
- Track license metadata per item.

Initial sources may include:
- ADE20K, because dense masks help clean single-factor edits.
- COCO, documented carefully.
- Public-domain/CC0 examples from Wikimedia/Openverse for figures.
- BDD100K/nuScenes only if redistribution terms are handled recipe-first.

## Statistical core

For each pair i:
- `C_i = 1` iff the model’s original/edited answer pair respects required_change.
- `a_i = 1` iff original-image answer is correct.
- consistency rate `p = E[C_i]`.
- intervention-consistency gap `Delta = a - p`.

Need:
- point estimates
- paired bootstrap intervals
- anytime-valid confidence sequences for `p`
- anytime-valid confidence sequences for `Delta`
- claim gate: only certify gap if lower CS bound exceeds configured threshold.

Prefer using the `confseq` package if available. Provide a safe fallback wrapper that fails clearly if unavailable, not silently.

## Engineering principles

Every component must be:
- deterministic where possible
- config-driven
- resumable
- cache-aware
- tested
- leakage-guarded
- claim-ledger-aware
- usable on Kaggle free notebooks
- runnable in smoke mode without GPU

Implement small smoke fixtures first. Do not require downloading huge datasets just to run tests.

## Required repo structure

Create or maintain this structure:

```text
certvic/
  README.md
  pyproject.toml
  configs/
    smoke.yaml
    real_pilot.yaml
    real_main.yaml
    kaggle_open_vlm.yaml
  data/
    README.md
    sources/
    masks/
    edits/
    manifests/
    annotations/
    predictions/
    results/
  certvic/
    __init__.py
    config.py
    io.py
    hashing.py
    logging_utils.py
    schema/
    edit/
    data/
    providers/
    eval/
    metrics/
    reporting/
    validation/
  notebooks/
    kaggle/
  tests/
  paper/
    main.tex
    sections/
    figures/
    tables/
    supp/
  docs/
    THESIS.md
    DATA_CARD.md
    METRICS_SPEC.md
    CLAIM_LEDGER.md
    REPRO.md
    ZERO_COST_POLICY.md
    RISK_REGISTER.md
```

## First implementation priority

Always prefer:
1. working skeleton
2. schema + validators
3. tests
4. smoke data
5. metrics
6. runner
7. edit stubs
8. real model integrations

Do not jump straight into heavyweight VLM code before schemas and smoke tests exist.

## Output expectation for every Codex task

For every task:
- Modify files directly.
- Add or update tests.
- Run relevant tests if possible.
- At the end, print:
  - files changed
  - tests run
  - known limitations
  - next recommended prompt number
