# CertVIC V5 Prompt — Result Contracts and Schema Freeze

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Create result contracts so future outputs cannot silently drift.

Create:
- `certvic/contracts/result_contracts.py`
- `configs/result_contracts.yaml`

CLI:
`python3 -m certvic.contracts.result_contracts validate --contracts configs/result_contracts.yaml --root data/results`

Contracts for:
- pair scores
- certification report
- visual review summary
- model comparison
- failure gallery
- paper table
- claim ledger

Tests:
- missing required field fails
- extra fields warn not fail
- version mismatch flagged
- fake result contract cannot be evidence

Docs:
- `docs/V5_RESULT_CONTRACTS_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
