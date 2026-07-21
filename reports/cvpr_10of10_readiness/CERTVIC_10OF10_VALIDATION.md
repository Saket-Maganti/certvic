# CertVIC 10-of-10 Validation

All required local checks pass.

| Validation | Result |
| --- | --- |
| Baseline before patch | 814 passed |
| Focused 10-of-10 tests | 7 passed |
| Selected CVPR closure regression | 74 passed |
| Full final suite | 821 passed |
| CVPR notebook static validation | 16/16 passed |
| Historical T4x2 notebook validation | 6/6 passed |
| Ruff and compileall | passed |
| Three isolated Kaggle-session simulator | reconciliation, commit, recovery, idempotency, and replay rejection passed |
| Claim and privacy guards | 0 findings each |
| Guarded paper | two passes, three pages |
| Clean release extraction | passed |
| Release manifest/hash audit | passed |
| Deterministic release rebuild | byte-identical |

Explicit boundary checks pass: no structured `paper_evidence=true`; no genuine structured
`human_reviewed=true`; Main and COCO stay blocked; V2-30 stays retrospective; no real GPU evidence,
human labels, model outputs, model commits, or runtimes were fabricated.

Runtime-path assertions pass: the 00C2 worker receives the bundle root, manifest, and hash; smoke
runtime and packaging both expect one produced shard; canonical notebook outputs enter the gate
directly; active variables are the only permission map; separate sessions share no writable state;
provider ZIPs carry verifiable proofs; synthetic smoke is barred from scientific authorization;
smoke/current snapshot and environment identities must be equal; detectability binds exact tasks and
image bytes; import plus nonce consumption recovers and is idempotent; Main has frozen oversampling;
and the release imports and runs from clean extraction.

Exact commands, exits, and totals are recorded in `CERTVIC_10OF10_COMMANDS.csv`.
