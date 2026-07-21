# CertVIC Codex V2 Prompt 12 — End-to-End Tiny Real Pilot Orchestrator

Do not download data. Do not use paid services. Do not run full-scale jobs. Do not run VLM inference here. Do not make paper claims. Tests must use fake fixtures.

## Goal

Build an orchestrator that can run the full tiny pilot sequence once the user supplies a real ADE20K root.

## Tasks

1. Add package/module:
   - `certvic/pipeline/__init__.py`
   - `certvic/pipeline/run_tiny_pilot.py`

2. Add command:

   `python3 -m certvic.pipeline.run_tiny_pilot --config configs/real_pilot_ade20k.yaml --ade20k-root /absolute/path/to/ADE20K --out-dir data/results/tiny_real_pilot --max-items 20 --dry-run`

3. Stages:
   - pilot readiness
   - source/mask manifests
   - label policy report
   - pilot selection
   - edit planning
   - task preview
   - pilot plan report
   - tiny edit generation
   - quality report
   - task materialization
   - visual review sheet export

4. Do not include VLM inference in this orchestrator.

5. Add stage resume:
   - skip completed stage unless `--force`
   - write stage_status.json
   - write command log
   - write zero_cost_audit.json

6. Add dry-run mode:
   - inspect only
   - no edit generation
   - clear next commands

7. Add tests:
   - `tests/test_v2_tiny_pilot_orchestrator.py`

8. Add docs:
   - `docs/TINY_REAL_PILOT_RUNBOOK.md`
   - update `docs/REPRO.md`

9. Create:
   - `docs/V2_TINY_REAL_PILOT_ORCHESTRATOR_REPORT.md`

10. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, command added, whether orchestrator passed, and next prompt: `13_V2_OPEN_MODEL_TINY_EVAL_AND_SCORING.md`.
