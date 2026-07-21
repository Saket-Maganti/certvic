# CertVIC V6 Prompt — No More Generic Infrastructure Enforcer

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

Add a guardrail doc/check that prevents future V7-like generic building unless real-run evidence exposes a missing gate.

Create:
- `docs/V6_STOP_BUILDING_BEGIN_RUNS.md`
- `certvic/v6/stop_condition_audit.py`

CLI:
`python3 -m certvic.v6.stop_condition_audit --out docs/V6_STOP_CONDITION_AUDIT.md --json-out data/results/v6_stop_condition_audit.json`

It should report:
- all V6 directional corrections complete
- next action is ADE20K dry-run
- generic infrastructure work is disallowed
- allowed future coding only if:
  - run crashes
  - gate missing
  - artifact contract mismatch
  - edit generation fails
  - detectability pipeline missing field
  - VLM output parser fails on real outputs

Tests:
- audit passes if docs exist
- audit fails if next action recommends more generic infra

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
