# Security / Privacy / Path Policy (V3)

Prevents accidental release of private paths, keys/tokens, `.env` files, paid
endpoints, local dataset roots, or non-rehostable pixels. Static text inspection
only — no network, no heavy imports, no evidence claims. Run it before any
artifact release.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.security.path_audit` | Private absolute paths (`/Users/`, `/home/`, home dir) and local dataset roots. |
| `certvic.security.secrets_audit` | API/AWS/GitHub/Slack keys, bearer tokens, private-key headers, committed `.env`, paid endpoints. |
| `certvic.security.release_privacy_audit` | Orchestrates the above + accidental pixels in a release dir; writes the report. |

## What is flagged

- **Private paths**: anything under `/Users/`, `/home/`, `/root/`, `/mnt/`,
  `/media/`, or the current home dir; `ade20k_root`/`dataset_root` set to an
  absolute path.
- **Secrets**: `AKIA…`, `ghp_…`, `sk-…`, `xox[baprs]-…`, `Authorization: Bearer …`,
  `-----BEGIN … PRIVATE KEY-----`, and `api_key/secret_key=…` assignments.
- **`.env`**: committed `.env` / `.env.local` / `.env.prod` (templates are fine).
- **Paid endpoints**: `api.openai.com`, `api.anthropic.com`, `api.cohere.ai`, …
- **Release pixels**: image files inside a release directory (recipe-first means
  pixels are pointers, never rehosted).

## Allowlist

Generated output trees (`data/results`, `data/predictions`, `compute_bundles`,
`release`, …) are skipped, and an allowlist exempts files that legitimately show
examples: the audit's own pattern definitions, `certvic/storage/path_policy.py`,
`certvic/compute/job_bundle.py`, `certvic/release/reproduction_audit.py`, the
Codex prompt packs (`*_prompt_pack`), the test suite, and example-bearing docs.

## Command

```bash
python3 -m certvic.security.release_privacy_audit --root . --out docs/SECURITY_PRIVACY_AUDIT.md
# before shipping a release bundle:
python3 -m certvic.security.release_privacy_audit --root . --release-dir release/certvic_recipe_artifact --out docs/SECURITY_PRIVACY_AUDIT.md
```

The audit exits non-zero on any finding. The current repo passes with zero
findings.
