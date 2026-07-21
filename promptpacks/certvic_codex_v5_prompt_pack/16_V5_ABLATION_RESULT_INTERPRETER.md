# CertVIC V5 Prompt — Ablation Result Interpreter

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build an interpreter that turns future ablation outputs into cautious text snippets.

Create:
- `certvic/reporting/ablation_interpreter.py`

CLI:
`python3 -m certvic.reporting.ablation_interpreter --ablation-report data/results/ablation_report --out docs/ABLATION_INTERPRETATION_DRAFT.md`

Rules:
- no fake results
- if text-only high, warn construct threat
- if parser sensitivity high, warn claim threat
- if controls flip high, block claims
- generate cautious language only

Tests:
- high text-only triggers warning
- high control flips blocks
- clean ablation produces cautious positive draft
- no unsupported claims

Docs:
- `docs/V5_ABLATION_INTERPRETER_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
