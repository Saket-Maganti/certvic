# V3 Prompt 11 — Static Local Run Dashboard Report

## Goal

Generate a local static HTML dashboard for runs, metrics, quality gates, review
progress, artifact status, and claim eligibility.

## What was built

- `certvic/dashboard/build_dashboard.py` — defensive collectors for runs (prediction run manifests), metrics (score summaries), quality (edit detectability + generation), review (progress/IAA), claims (claim ledger), and artifacts (provenance graph + run ledger); missing-gate and non-evidence-flag scanners; static HTML renderer (inline CSS, no JS framework) writing `index.html` + 6 section pages + `dashboard_data.json`.

## Tests

`tests/test_v3_dashboard.py` — 7 tests: empty project builds with missing gates + all pages; runs+metrics collected; paid-services flagged; certified-claim recognized; artifacts section reads the run ledger; HTML is self-contained (inline CSS, no external http(s), no `<script src>`); no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (363 passed; was 356).
- CLI smoke on real `data/results`: 8 files written; correctly flagged missing gates (no certified claim, no human-review progress, no provenance ledger); no non-evidence flags.

## Evidence / cost discipline

Static files only — no external services, no JS framework, no pixel copying, no
inference. `evidence_claims_made=false`, `external_services_used=false`,
`pixels_copied=false`. Non-evidence statuses and paid-services runs are surfaced
prominently. No heavy imports.

## Status

**PASSED.**

## Remaining blockers

None. Pages fill in automatically as real runs, reviews, claims, and provenance
artifacts are produced.
