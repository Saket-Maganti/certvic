# CertVIC V5 Prompt — Experiment Registry and Run Naming

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Create a strict experiment registry and naming scheme.

Create:
- `certvic/experiments/registry.py`
- `configs/experiments.yaml`

CLI:
`python3 -m certvic.experiments.registry validate --config configs/experiments.yaml`
`python3 -m certvic.experiments.registry render --config configs/experiments.yaml --out docs/EXPERIMENT_REGISTRY.md`

Include:
- tiny_pilot
- main_200
- main_1000
- main_2000
- each model run
- ablations
- controls
- paper figures

Tests:
- duplicate run IDs rejected
- invalid names rejected
- required stages present
- registry renders docs

Docs:
- `docs/V5_EXPERIMENT_REGISTRY_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
