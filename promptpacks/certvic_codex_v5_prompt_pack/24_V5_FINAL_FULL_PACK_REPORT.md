# CertVIC V5 Prompt — Final Full V5 Pack Report

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Create final V5 full-pack report and command index.

Create:
- `docs/V5_FULL_PACK_REPORT.md`
- `docs/V5_COMMAND_INDEX.md`
- `docs/V5_STOP_INFRASTRUCTURE_BEGIN_EMPIRICAL_RUNS.md`

Include:
- all V5 modules
- all commands
- tests added
- docs added
- exact next real-run commands
- strict stop condition
- remaining empirical blockers

Run:
`python3 -m pytest -q`
`python3 -m certvic.v5.cvpr_ready_except_results_audit --out docs/V5_CVPR_READY_EXCEPT_RESULTS_AUDIT.md --json-out data/results/v5_cvpr_ready_except_results_audit.json`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
