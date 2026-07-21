# CertVIC Final Runtime Patch Session

Scope: final local repair of 00C2 canonical packaging, strict runtime integrity, run-contract and
prompt identity, parent/child notebook preflight, and retry-safe packaging. No real VLM inference,
dataset execution, human review, or paper evidence was created.

Baseline full pytest: `815 passed, 6 failed`. The six failures shared one cause: the privacy scanner
treated a development-only prompt contract under `promptpacks/` as a release artifact because its
allowlist recognized older prompt-pack names only. Runtime-focused baseline defects matched the
patch contract: `REAL_MODEL_SMOKE` snapshot omission, incomplete canonical teardown checks, missing
cross-artifact hash enforcement, missing parent preflight, manually supplied prompt hash, and a
pre-promotion `OUTPUT_PACKAGED` transition.

Implementation reuses the existing worker, package runner, smoke artifact, smoke gate, provider
permission, notebook builder, and release builder paths. Synthetic proof artifacts remain
`paper_evidence=false` and cannot authorize scientific execution.

