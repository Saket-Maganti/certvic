# CertVIC V5 Prompt — CVPR-Ready Except Results Audit

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Create audit that says whether the repo is CVPR-ready except empirical artifacts.

Create:
- `certvic/v5/cvpr_ready_except_results_audit.py`

CLI:
`python3 -m certvic.v5.cvpr_ready_except_results_audit --out docs/V5_CVPR_READY_EXCEPT_RESULTS_AUDIT.md --json-out data/results/v5_cvpr_ready_except_results_audit.json`

Checks:
- V4 final audit exists/passes
- item certificate module imports
- analysis plan lock exists
- theory audit exists
- result-free paper audit passes
- rater training exists
- model/eval cards exist
- experiment registry exists
- result contracts exist
- claim language guard passes
- figure/table manifests exist
- submission package plan exists
- no fake paper numbers
- no evidence claims from planned artifacts

Tests:
- audit passes current expected repo
- missing module clearly fails
- stop guidance included

Docs:
- `docs/V5_CVPR_READY_EXCEPT_RESULTS_AUDIT_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
