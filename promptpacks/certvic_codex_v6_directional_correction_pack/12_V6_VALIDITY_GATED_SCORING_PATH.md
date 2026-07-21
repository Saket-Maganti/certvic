# CertVIC V6 Prompt — Validity-Gated Scoring Path

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

Ensure scoring and reporting can restrict to certificate-eligible items.

Create/update:
- `certvic/metrics/score_predictions.py`
- `certvic/reporting/build_report.py`
- `certvic/validity/filter_scores.py`

CLI:
`python3 -m certvic.validity.filter_scores --scores <pair_scores.jsonl> --certificates <item_certificates.jsonl> --out <valid_scores.jsonl> --rejected-out <rejected_scores.jsonl>`

Rules:
- only evidence_eligible_candidate true items pass
- missing certificate rejects
- rejected scores keep reasons
- filtering preserves provenance
- filtered outputs are required for main paper claims

Tests:
- eligible item passes
- rejected item removed
- missing cert removed
- rejection reasons preserved
- mock/non-evidence still cannot claim

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
