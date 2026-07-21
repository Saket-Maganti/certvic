# V8.1 Go/No-Go

`paper_evidence=false`

Decision: `GO_HUMAN_AUDIT_FIRST`

Exact answer: do not start Main-500 until Qwen spurious failure is resolved or the paper is reframed to exclude clean Qwen specificity.

Current state:

- Qwen raw gate: FAIL, 12/94 = 0.1277.
- InternVL and LLaVA-OneVision: PASS.
- Claim-valid recompute scenarios passing: False.
- Qwen failed items that only Qwen flips: 12/12.

Recommended next action: real human audit of the 12-item gallery, followed by either preregistered Spurious V2 or an honest paper reframe.
