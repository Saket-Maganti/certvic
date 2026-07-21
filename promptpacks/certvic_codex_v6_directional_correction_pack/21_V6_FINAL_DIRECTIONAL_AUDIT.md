# CertVIC V6 Prompt — Final Directional Audit

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

Create final V6 directional audit.

Create:
- `certvic/v6/final_directional_audit.py`

CLI:
`python3 -m certvic.v6.final_directional_audit --out docs/V6_FINAL_DIRECTIONAL_AUDIT.md --json-out data/results/v6_final_directional_audit.json`

Checks:
- identity audit passes
- detectability gate exists
- staged command safety passes
- main figure/table v6 manifests exist
- mechanism probe infrastructure exists
- open-only defense exists
- validity-gated scoring path exists
- naive-vs-validity-gated report exists
- CVPR bar checker exists
- no-more-infra stop condition exists
- directional language guard passes
- run-after-v6 checklist exists
- no evidence claims
- no fake numbers

Tests:
- audit passes current expected repo
- missing required module fails clearly

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
