# Codex Prompt 14 — Paper Scaffold, Figures, Tables, and Writing Plan

Build the CVPR-style paper scaffold around the method-first thesis.

## Goal

Create a serious paper scaffold that can later be filled with real results. The paper should be honest, CVPR-safe, and aligned with the code.

## Files to create/update

```text
paper/main.tex
paper/sections/01_intro.tex
paper/sections/02_related.tex
paper/sections/03_method.tex
paper/sections/04_experiments.tex
paper/sections/05_results.tex
paper/sections/06_limitations.tex
paper/sections/07_conclusion.tex
paper/supp/supplement.tex
paper/tables/README.md
paper/figures/README.md
docs/PAPER_PLAN.md
docs/CLAIM_LEDGER.md
```

## Paper posture

Method-first:
- Do not frame as a large dataset contribution.
- The artifact is a reproducible recipe + certified evaluation pipeline.
- Data is important but not the headline.

## Intro

Include:
- VLMs may answer correctly but not update decisions when controlled visual factors change.
- Existing benchmark crowding problem.
- Need for controlled real-image interventions and statistically valid claims under limited compute.
- Contributions:
  1. recipe-first controlled intervention pipeline
  2. edit-derived consistency tasks
  3. anytime-valid certification of consistency gaps
  4. zero-cost reproducible open-model evaluation

## Related work placeholders

Sections:
- VLM evaluation and visual reasoning benchmarks.
- Counterfactual/minimal-pair vision-language evaluation.
- Image editing/inpainting for evaluation.
- Selective/anytime-valid/statistical evaluation.
- Dataset licensing and reproducibility.

Use TODO citations, not fabricated citations.

## Method

Must define:
- source records
- masks
- edit specs
- task items
- consistency indicator
- gap
- bootstrap
- anytime-valid CS
- claim gate

## Experiments

Describe:
- task families
- domains
- models
- baselines
- human validity check
- zero-cost compute setup

No fake results. Use placeholders like:
`[RESULT REQUIRED]`

## Results

Create subsections:
- main consistency results
- gap certification
- edit-type breakdown
- control edits/spurious flips
- text-only/caption-only ablations
- failure gallery
- frontier reference if available

Everything should say `[RESULT REQUIRED]` until real outputs exist.

## Limitations

Include:
- generated edits may contain artifacts
- labels depend on edit validity
- limited domains/edit families
- free-tier reference instability
- no deployment/safety claims
- recipe-first release may require users to regenerate data

## Docs

Create `docs/PAPER_PLAN.md` with:
- target venue CVPR 2027
- abstract/full timeline
- kill gates
- required result tables
- required figures
- claim certification rules

## Build script optional

If there is no LaTeX environment, do not require compile in tests.
Add a simple sanity test that required section files exist and contain no fake numeric result claims.

## Tests

Create:
```text
tests/test_paper_scaffold.py
```

Test:
- all section files exist
- contains RESULT REQUIRED placeholders
- forbidden overclaims absent
- no fake numeric CVPR result claims in paper

## Finish

Run:
```bash
python -m pytest -q
```

Report:
- files changed
- tests run
- next prompt: `15_CI_TESTS_AND_AUDIT_GATES.md`
