# CertVIC Codex V3 Prompt 16 — Security Privacy and Path Audit


## Global constraints

- Work in `/Users/saketmaganti/Projects/certVIC`.
- Do not initialize git, commit, or tag.
- Do not use paid APIs, paid cloud, paid datasets, paid annotation, paid credits, or paid tracking.
- Do not download large datasets or model weights.
- Do not run GPU jobs or VLM inference in tests.
- Do not fabricate results or insert fake paper numbers.
- Keep heavy dependencies optional and import-safe.
- Normal tests must run locally without GPU.
- Simulated/pre-run artifacts must be marked non-evidence and blocked from claims.
- Preserve backward compatibility and run `python3 -m pytest -q`.

## Goal

Prevent accidental release of private paths, keys, tokens, paid endpoints, or non-rehostable pixels.

## Inspect first

Zero-cost policy, release builder, data card, path policies.

## Build / modify

Create `certvic/security/path_audit.py`, `secrets_audit.py`, `release_privacy_audit.py`.

## CLI commands to add or verify

`python3 -m certvic.security.release_privacy_audit --root . --out docs/SECURITY_PRIVACY_AUDIT.md`

## Outputs / behavior

Detect `/Users/...` paths, token-like strings, `.env`, paid endpoints, local dataset roots, accidental pixels in release dirs. Allowlist docs that mention examples.

## Tests

Create or update:

`tests/test_v3_security_privacy_audit.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/SECURITY_PRIVACY_POLICY.md`, `docs/V3_SECURITY_PRIVACY_AUDIT_REPORT.md`; update zero-cost and data card docs.

## Extra notes

Critical before artifact release.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
