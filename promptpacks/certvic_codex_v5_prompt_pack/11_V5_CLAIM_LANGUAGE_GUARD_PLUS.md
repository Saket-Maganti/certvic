# CertVIC V5 Prompt — Claim Language Guard Plus

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Upgrade claim-language guard for paper/docs/reports.

Create:
- `certvic/validation/claim_language_guard.py`

CLI:
`python3 -m certvic.validation.claim_language_guard --root paper docs --out docs/CLAIM_LANGUAGE_GUARD_REPORT.md`

Detect:
- causal overclaims
- deployment safety claims
- universal VLM claims
- frontier-model claims
- benchmark-first framing
- bootstrap certification misuse
- fake novelty/first claims
- hidden result claims in prose

Tests:
- forbidden phrases caught
- allowed cautious phrasing passes
- RESULT REQUIRED placeholders allowed
- docs examples can be allowlisted

Docs:
- `docs/V5_CLAIM_LANGUAGE_GUARD_PLUS_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
