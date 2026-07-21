# Codex Prompt 01 — Bootstrap the CertVIC Repository

Build the initial repository skeleton for the CertVIC project.

## Goal

Create a clean Python research repo called `certvic` for a zero-cost CVPR 2027 project on certified visual consistency.

## Requirements

Create the full directory structure:

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
      __init__.py
    edit/
      __init__.py
    data/
      __init__.py
    providers/
      __init__.py
    eval/
      __init__.py
    metrics/
      __init__.py
    reporting/
      __init__.py
    validation/
      __init__.py
  notebooks/
    kaggle/
      README.md
  tests/
    conftest.py
    test_imports.py
  paper/
    main.tex
    sections/
      01_intro.tex
      02_related.tex
      03_method.tex
      04_experiments.tex
      05_results.tex
      06_limitations.tex
      07_conclusion.tex
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

## pyproject.toml

Use a minimal modern Python setup:
- package name: `certvic`
- Python >=3.10
- dependencies:
  - numpy
  - pandas
  - pillow
  - pydantic
  - pyyaml
  - tqdm
  - scikit-learn
  - matplotlib
- optional dependencies:
  - dev: pytest, ruff
  - stats: confseq
  - vision: torch, torchvision, transformers, accelerate, bitsandbytes, diffusers, opencv-python
  - kaggle: ipykernel

Do not make heavy GPU packages mandatory for tests.

## README.md

Write a serious project README with:
- project title
- thesis
- zero-cost rule
- quickstart
- smoke-mode workflow
- what is implemented vs planned
- no paid API policy
- claim safety language

## ZERO_COST_POLICY.md

Document:
- no paid APIs
- no paid cloud
- no paid datasets
- no paid annotation
- free Kaggle/Colab/local only
- optional free-tier references must be disabled by default and version-labeled

## Config files

Add usable YAML configs.

`smoke.yaml`:
- tiny fixture mode
- no GPU required
- no external downloads
- mock provider
- 10 items max
- alpha 0.05
- gap threshold 0.05

`real_pilot.yaml`:
- 200 item target
- ADE20K-first
- open models disabled by default until explicitly run
- quality gates enabled

`real_main.yaml`:
- 2500–3000 pairs target
- three task families
- two domains
- strict leakage checks

`kaggle_open_vlm.yaml`:
- batch size fields
- resume enabled
- 4-bit option
- output jsonl path
- max runtime/session notes

## Tests

Add:
- `tests/test_imports.py` to verify package imports.
- `tests/conftest.py` with basic temp path fixtures.

## Docs

Populate initial docs with concise but useful content:
- THESIS.md: method-first thesis.
- DATA_CARD.md: recipe-first data release plan.
- METRICS_SPEC.md: definitions of `C_i`, `a_i`, `p`, `Delta`.
- CLAIM_LEDGER.md: safe and forbidden claims.
- REPRO.md: smoke, pilot, main workflow.
- RISK_REGISTER.md: edit quality, no gap, licensing, compute limits.

## Finish

Run:
```bash
python -m pytest -q
```

Report:
- files changed
- tests run
- next prompt: `02_SCHEMA_AND_VALIDATORS.md`
