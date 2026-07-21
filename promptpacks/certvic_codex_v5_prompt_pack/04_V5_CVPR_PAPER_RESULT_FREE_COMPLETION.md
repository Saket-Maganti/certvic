# CertVIC V5 Prompt — CVPR Paper Result-Free Completion

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Make the paper read like a complete CVPR submission except results placeholders.

Create/upgrade:
- intro, method, experiment, limitations, conclusion glue
- section transition comments
- result placeholders with exact artifact names
- contribution statement
- ethics/reproducibility statement
- checklist comments

Add:
- `certvic/paper/result_free_completeness_audit.py`

CLI:
`python3 -m certvic.paper.result_free_completeness_audit --paper-dir paper --out docs/RESULT_FREE_COMPLETENESS_AUDIT.md`

Tests:
- all required sections exist
- no TODO except approved RESULT REQUIRED tokens
- no fake numbers
- limitations present
- contributions not overclaiming
- placeholders map to expected future artifacts

Docs:
- `docs/V5_RESULT_FREE_PAPER_COMPLETION_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
