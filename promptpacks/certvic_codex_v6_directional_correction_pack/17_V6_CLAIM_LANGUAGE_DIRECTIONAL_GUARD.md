# CertVIC V6 Prompt — Directional Claim Language Guard

Read `00_V6_MASTER_CONTEXT.md` first.

You are correcting project direction, not building generic infrastructure.

Hard constraints:
- Do not initialize git.
- Do not commit or tag.
- Do not use paid APIs.
- Do not use paid cloud.
- Do not download data or weights.
- Do not run GPU jobs.
- Do not run VLM inference.
- Do not fabricate results.
- Do not fabricate citations.
- Do not insert fake paper numbers.
- Do not make evidence claims from mock/smoke/simulated/planned/unreviewed/simple-edit-only artifacts.
- Keep tests local and CPU-only.
- Heavy dependencies must be optional/import-safe.

Extend claim-language guard to catch benchmark-only/common framing.

Create/update:
- `certvic/validation/claim_language_guard.py`
- `certvic/validation/directional_language_guard.py`

Catch overuse of:
- "benchmark" as lead identity
- "dataset" as lead contribution
- "VLMs are inconsistent" without decision-update/validity framing
- "robustness benchmark" as main paper identity
- "we prove VLMs reason/fail to reason"

CLI:
`python3 -m certvic.validation.directional_language_guard --root paper docs --out docs/V6_DIRECTIONAL_LANGUAGE_GUARD_REPORT.md`

Tests:
- benchmark-only abstract fails
- decision-update/confound-controlled abstract passes
- forbidden universal claims fail
- placeholders allowed

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
