# CertVIC V6 Prompt — Tiny Pilot Decision Dashboard

Read `00_V6_MASTER_CONTEXT.md` first.

You are correcting project direction, not building generic infrastructure.

Hard constraints:
- Do not initialize git.
- Do not commit or tag.
- Do not use paid APIs.
- Do not use paid cloud.
- Do not download data or weights.
- Do not run GPU jobs.
- Do not run VLM inference.
- Do not fabricate results.
- Do not fabricate citations.
- Do not insert fake paper numbers.
- Do not make evidence claims from mock/smoke/simulated/planned/unreviewed/simple-edit-only artifacts.
- Keep tests local and CPU-only.
- Heavy dependencies must be optional/import-safe.

Create a tiny-pilot dashboard/report template that makes the next go/no-go obvious.

Create:
- `certvic/dashboard/tiny_pilot_decision.py`
- `docs/TINY_PILOT_DECISION_TEMPLATE.md`

CLI:
`python3 -m certvic.dashboard.tiny_pilot_decision --pilot-dir data/results/tiny_real_pilot --out docs/TINY_PILOT_DECISION.md --json-out data/results/tiny_pilot_decision.json`

It should summarize:
- dry-run status
- edit generation status
- quality pass rate
- detectability AUC
- visual review count
- answerability review count
- item certificate pass rate
- whether VLM eval may begin
- top blockers

Tests:
- missing artifacts handled gracefully
- AUC high blocks
- reviewed/valid items insufficient blocks
- output deterministic

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
