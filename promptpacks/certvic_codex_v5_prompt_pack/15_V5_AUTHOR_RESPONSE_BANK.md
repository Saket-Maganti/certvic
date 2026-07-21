# CertVIC V5 Prompt — Author Response Bank

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build a response bank for likely CVPR reviews.

Create:
- `docs/response_bank/`
- `certvic/review/response_bank.py`

CLI:
`python3 -m certvic.review.response_bank --out docs/response_bank/index.md`

Topics:
- edit realism
- not causal
- small scale
- open-only models
- optional stopping
- label ambiguity
- artifact release
- human review
- no frontier models
- zero-cost constraint
- statistical conservatism

Tests:
- all topics exist
- responses contain no fake results
- responses map to required artifacts

Docs:
- `docs/V5_AUTHOR_RESPONSE_BANK_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
