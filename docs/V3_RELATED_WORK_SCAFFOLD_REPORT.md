# V3 Prompt 13 — Related Work and Citation Scaffold Report

## Goal

Create a non-fabricating related-work matrix and citation audit. No invented
citations or unsupported novelty claims.

## What was built

- `paper/related_work_matrix.yaml` — 8 categories (VLM eval, counterfactual/minimal-pair VQA, causal visual reasoning, editing for evaluation, robustness/consistency, anytime-valid inference, licensing/artifacts, budgeted evaluation) each with description, relation-to-CertVIC, differentiator, keywords, and an **empty** `representative_works` (citation TODO). Explicit `fabrication_policy`.
- `docs/RELATED_WORK_PLAN.md` — positioning narrative + rules (no invented refs; qualified novelty).
- `docs/CITATION_TODO.md` — per-category citation slots + the verify→bib→matrix→cite→re-audit process.
- `certvic/paper/related_work_audit.py` — category coverage check against the section, citation-fabrication check (`\cite` keys without a verified bib), and novelty-claim flagging ("first to", "novel", …). Emits `docs/RELATED_WORK_AUDIT.md`.

## Tests

`tests/test_v3_related_work_audit.py` — 7 tests: matrix has all 8 categories with empty works; audit on the real section (8 categories, all need citations, no fabrication risk); coverage detection; unverified-cite-key flag + bib clears it; novelty-claim flagging; report renders; no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (379 passed; was 372).
- CLI smoke: audited the real `02_related.tex` — 8 categories, all needing citations, no fabrication risk. The audit also flagged 3 categories (causal reasoning, robustness/consistency, budgeted evaluation) as not yet keyword-covered in the section — a concrete TODO to address before submission.

## Evidence / cost discipline

No browsing, no fabricated citations (`fabricated_citations=false`), no evidence
claims. Novelty phrases are flagged for human review, not asserted. No heavy imports.

## Status

**PASSED.**

## Remaining blockers

Citations themselves: `representative_works` are empty by design and must be filled
by a human with verified references (`docs/CITATION_TODO.md`).
