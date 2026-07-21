# V3 Prompt 16 — Security / Privacy / Path Audit Report

## Goal

Prevent accidental release of private paths, keys, tokens, paid endpoints, or
non-rehostable pixels.

## What was built

- `certvic/security/path_audit.py` — scans text files for private absolute paths and local dataset roots; skips generated output trees; allowlists example-bearing files (incl. the Codex prompt packs).
- `certvic/security/secrets_audit.py` — token patterns (AWS/GitHub/OpenAI/Slack keys, bearer tokens, private-key headers, generic key assignments), committed `.env` detection, and paid-endpoint detection.
- `certvic/security/release_privacy_audit.py` — orchestrates path + secrets + (optional) release-pixel scan; markdown report; exits non-zero on any finding.

## Tests

`tests/test_v3_security_privacy_audit.py` — 11 tests: private-path + dataset-root detection; clean tree passes; allowlist skips example docs; generated dirs skipped; OpenAI/AWS key detection; committed `.env` + paid endpoint; clean secrets; release-pixel detection; combined fail + report; **real repo passes with zero findings**; no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (407 passed; was 396).
- CLI smoke on the real repo (`--root .`): `passed: true`, 0 findings. The allowlist correctly exempts `certvic/storage/path_policy.py`, the audit sources, and the prompt packs (which intentionally name the working directory).

## Evidence / cost discipline

Static text inspection only — no network, no downloads, no paid services, no
evidence claims (`evidence_claims_made=false`). No heavy imports.

## Status

**PASSED.**

## Remaining blockers

None. Before shipping a release bundle, run with `--release-dir <bundle>` to also
catch accidental pixels.
