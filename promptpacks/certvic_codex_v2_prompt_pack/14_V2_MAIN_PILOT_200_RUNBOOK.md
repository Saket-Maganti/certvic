# CertVIC Codex V2 Prompt 14 — Main 200-Item Pilot Runbook and Gates

Do not run full pilot automatically. Do not use paid services. Do not make claims before gates pass.

## Goal

Prepare the main 200-item pilot runbook and gate system.

## Tasks

1. Add:
   - `docs/MAIN_PILOT_200_RUNBOOK.md`
   - `docs/PILOT_GATE_CHECKS.md`

2. Runbook stages:
   - real ADE20K inspection
   - manifests
   - label policy
   - selection
   - edit plan
   - preview
   - plan report
   - edit generation
   - quality report
   - visual review
   - reviewed tasks
   - open-local VLM preflight
   - VLM inference
   - scoring
   - certification
   - paper report

3. Add gate command:

   `python3 -m certvic.pipeline.pilot_gate_check --stage before_vlm --config configs/real_pilot_ade20k.yaml --out data/results/pilot_gate_before_vlm.json`

4. Gate stages:
   - before_edit_generation
   - before_visual_review
   - before_vlm
   - before_claims
   - before_release

5. Add tests:
   - `tests/test_v2_pilot_gate_check.py`

6. Update:
   - `docs/REPRO.md`

7. Create:
   - `docs/V2_MAIN_PILOT_200_RUNBOOK_REPORT.md`

8. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, commands added, whether main pilot runbook passed, and next prompt: `15_V2_FULL_SYSTEM_AUDIT.md`.
