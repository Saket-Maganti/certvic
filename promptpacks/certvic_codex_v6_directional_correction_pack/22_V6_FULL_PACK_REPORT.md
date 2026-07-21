# CertVIC V6 Prompt — Full V6 Pack Report

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

Create final V6 full-pack report.

Create:
- `docs/V6_FULL_PACK_REPORT.md`
- `docs/V6_COMMAND_INDEX.md`
- `docs/V6_FINAL_GO_NO_GO.md`

Include:
- what changed strategically
- why V6 exists after V5
- all modules added
- all CLIs added
- all docs added
- tests added
- final status
- exact next command
- explicit statement: after V6, run; do not build V7

Run:
`python3 -m pytest -q`
`python3 -m certvic.v6.final_directional_audit --out docs/V6_FINAL_DIRECTIONAL_AUDIT.md --json-out data/results/v6_final_directional_audit.json`

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
