# CertVIC V5 Prompt — All Commands Dry-Run Smoke Harness

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build harness that smoke-tests all safe CLIs without real data/GPU.

Create:
- `certvic/v5/all_commands_smoke.py`

CLI:
`python3 -m certvic.v5.all_commands_smoke --out data/results/v5_all_commands_smoke.json`

It should:
- list safe commands
- run only commands with fake fixtures or --help/dry-run
- skip real data/GPU/VLM commands
- record pass/fail/skip
- never execute paid/download/GPU work

Tests:
- smoke harness skips unsafe commands
- safe fake commands pass
- report written

Docs:
- `docs/V5_ALL_COMMANDS_SMOKE_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
