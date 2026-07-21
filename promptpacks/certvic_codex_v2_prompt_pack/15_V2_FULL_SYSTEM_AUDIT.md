# CertVIC Codex V2 Prompt 15 — Full V2 System Audit

Do not use paid services. Do not fabricate results. Do not make claims from ineligible artifacts.

## Goal

Build the final V2 audit that verifies the project is ready to run real tiny/main pilots and produce paper outputs without breaking safety, cost, or claim discipline.

## Tasks

1. Add command:

   `python3 -m certvic.v2.full_audit --out docs/V2_FULL_SYSTEM_AUDIT_REPORT.md`

2. Checks:
   - V1–V1.5 handoffs exist
   - V2 handoffs exist
   - tests pass
   - zero-cost policy
   - no paid provider enabled
   - no fake paper results
   - no forbidden claims
   - configs exist
   - runbooks exist
   - release audit available
   - claim policy exists
   - gate checks available
   - important commands import

3. Add test:
   - `tests/test_v2_full_system_audit.py`

4. Add docs:
   - `docs/V2_COMMAND_INDEX.md`
   - `docs/V2_NEXT_ACTIONS.md`

5. `docs/V2_NEXT_ACTIONS.md` should list exact sequences for:
   - real ADE20K root
   - tiny pilot
   - 200 pilot
   - open-local VLM eval
   - certification
   - paper update
   - artifact release

6. Run:
   - `python3 -m pytest -q`
   - `python3 -m certvic.v2.full_audit --out docs/V2_FULL_SYSTEM_AUDIT_REPORT.md`

## Final response

Report files changed, tests run, V2 full audit status, command index location, and exact next action for the user.
