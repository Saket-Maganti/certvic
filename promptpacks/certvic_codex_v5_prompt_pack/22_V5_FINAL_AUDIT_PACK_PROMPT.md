# CertVIC V5 Prompt — Final Audit Pack Prompt

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Create an audit prompt pack for the next model pass.

Create:
- `docs/audit_prompts/01_BREAK_CLAIM_GATES.md`
- `docs/audit_prompts/02_BREAK_PROVENANCE.md`
- `docs/audit_prompts/03_BREAK_PAPER_NUMBERS.md`
- `docs/audit_prompts/04_BREAK_RUN_COMMANDS.md`
- `docs/audit_prompts/05_BREAK_RELEASE_PACKAGE.md`
- `docs/audit_prompts/06_BREAK_STATISTICS.md`
- `docs/audit_prompts/07_BREAK_HUMAN_REVIEW.md`
- `docs/audit_prompts/08_BREAK_DIFFUSION_VALIDITY.md`
- `docs/audit_prompts/09_BREAK_VLM_OUTPUTS.md`
- `docs/audit_prompts/10_FINAL_RED_TEAM_REPORT.md`

Each prompt should instruct an auditor to actively try to break that subsystem and report exact fixes.

Tests:
- all audit prompts exist
- each contains refusal to fabricate evidence
- each has expected output format

Docs:
- `docs/V5_FINAL_AUDIT_PACK_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
