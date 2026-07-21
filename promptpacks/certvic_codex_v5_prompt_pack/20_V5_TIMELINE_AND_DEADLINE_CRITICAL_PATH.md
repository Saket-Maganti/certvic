# CertVIC V5 Prompt — Timeline and Deadline Critical Path

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build deadline and critical-path planner.

Create:
- `certvic/planning/deadline_plan.py`
- `docs/CVPR_2027_CRITICAL_PATH.md`

CLI:
`python3 -m certvic.planning.deadline_plan --target-date 2026-11-15 --out docs/CVPR_2027_CRITICAL_PATH.md`

Include:
- real data deadline
- tiny pilot deadline
- 200 pilot deadline
- 1k/2k scale deadline
- paper draft deadline
- artifact freeze deadline
- submission package deadline
- risk buffers

Tests:
- dates ordered
- impossible schedule flagged
- buffer computed

Docs:
- `docs/V5_DEADLINE_PLAN_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
