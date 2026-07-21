# CertVIC Codex V2 Prompt 01 — Baseline Audit and Backward Compatibility

Do not initialize git. Do not use paid services. Do not download data. Do not run GPU jobs. Do not run VLM inference. Do not make evidence claims.

## Goal

Establish a V2 baseline audit that proves V1–V1.5 guarantees still hold before heavy V2 upgrades.

## Tasks

1. Inspect handoff docs:
   - `docs/V1_SMOKE_AUDIT_REPORT.md`
   - `docs/V1_1_SCAFFOLD_HARDENING_REPORT.md`
   - `docs/V1_2_REAL_PILOT_READINESS_REPORT.md`
   - `docs/V1_3_ADE20K_MASK_MANIFEST_REPORT.md`
   - `docs/V1_4_PILOT_CANDIDATE_EDIT_PLAN_REPORT.md`
   - `docs/V1_5_TINY_EDIT_GENERATION_QUALITY_REPORT.md`

2. Add package:
   - `certvic/v2/__init__.py`
   - `certvic/v2/baseline_audit.py`

3. Add command:

   `python3 -m certvic.v2.baseline_audit --out docs/V2_BASELINE_AUDIT_REPORT.md`

4. Audit checks:
   - handoff docs exist
   - core commands import
   - core configs exist
   - schema modules import
   - no paid providers enabled by default
   - V1.5 non-evidence statuses recognized
   - paper files contain no fake results
   - zero-cost policy exists
   - no forbidden claim phrases in paper/results docs

5. Add tests:
   - `tests/test_v2_baseline_audit.py`

6. Create:
   - `docs/V2_BASELINE_AUDIT_REPORT.md`

7. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, whether audit passed, and next prompt: `02_V2_VISUAL_REVIEW_AND_APPROVAL_WORKFLOW.md`.
