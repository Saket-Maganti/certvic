# CertVIC V5 Prompt — Certification Interpreter and Claim Drafter

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build a claim drafter that uses certification outputs but refuses ineligible artifacts.

Create:
- `certvic/reporting/certification_interpreter.py`

CLI:
`python3 -m certvic.reporting.certification_interpreter --cert-report data/results/certification.json --claim-ledger data/results/claim_ledger.json --out docs/CERTIFICATION_CLAIM_DRAFT.md`

Output:
- certified claim draft if eligible
- descriptive-only draft if not certified
- rejection reasons
- required missing artifacts

Tests:
- certified eligible produces cautious claim
- unavailable CS blocks certification
- bootstrap-only blocked
- mock/simulated blocked

Docs:
- `docs/V5_CERTIFICATION_INTERPRETER_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
