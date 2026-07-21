# V2 Failure Taxonomy and Gallery Report

Date: 2026-06-22
Prompt: `09_V2_FAILURE_TAXONOMY_AND_GALLERY.md`

## What was added

- `certvic/reporting/failure_taxonomy.py` — 10-type taxonomy + deterministic
  rule-based `classify_failure` (no LLM), with manual-override support.
- `certvic/reporting/failure_gallery_v2.py` — gallery builder: failure_gallery.jsonl,
  failure_taxonomy_summary.csv, failure_gallery.md, local_gallery.html,
  paper_candidate_failures.jsonl, summary json.

## Safety

No pixel copy by default; local links; license/release mode + claim eligibility
recorded; prompts/raw outputs/parsed answers included; safe paper captions
(single-factor descriptive, no deployment/causal claims).

## Tests

- `tests/test_v2_failure_taxonomy_gallery.py` — 7 tests (taxonomy size,
  missed-change+inertia, spurious-flip, parse-failure, manual override,
  non-failure excluded, gallery outputs + safe caption). Full suite: **189
  passed** (was 182).

## Status: PASS. Next: `10_V2_ARTIFACT_RELEASE_RECIPE_FIRST.md`.
