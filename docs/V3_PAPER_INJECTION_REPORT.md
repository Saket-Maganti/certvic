# V3 Prompt 12 — Paper Result Injection and Traceability Report

## Goal

Build a claim-gated paper update system that refuses fake/simulated/ineligible
numbers and only injects approved table/figure references.

## What was built

- `certvic/paper/result_manifest.py` — scans a report dir for tables/figures/data, hashes each (`sha256`), conservatively derives evidence status + provider type (defaults to non-evidence), and marks eligibility via the guard's `_eligible_entry`. Manifest is compatible with `paper_numbers_guard`.
- `certvic/paper/inject_results.py` — replaces `[RESULT REQUIRED]` with `\input`/`\includegraphics` for eligible+hashed artifacts only; dry-run by default; `--allow-write` to write; runs the number guard after any write; records refusals.
- `certvic/paper/paper_trace_report.py` — traces each injected `\input` to its manifest entry (traced / missing_in_manifest / missing_hash / ineligible_evidence), counts remaining placeholders and untraced numbers.

## Tests

`tests/test_v3_paper_injection.py` — 9 tests: manifest marks non-evidence ineligible + requires hashes; eligible for real open-local; dry-run does not write; ineligible artifacts preserve placeholders + refusal flagged; allow-write injects eligible + guard passes; missing-hash refused; trace report placeholders-only; trace report after injection (all inputs traced, ok); no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (372 passed; was 363).
- CLI smoke against the real paper: manifest over `data/results/smoke_report` → 7 entries, 0 eligible (UNKNOWN status); dry-run injection → 0 injected, 6 placeholders preserved, paper untouched; trace report ok. The safe default holds — no non-evidence number can reach the paper.

## Evidence / cost discipline

No inference, no downloads, no paid services. Dry-run by default; non-evidence and
unhashed artifacts are refused; the number guard runs after every write.
`evidence_claims_made=false`. No heavy imports.

## Status

**PASSED.**

## Remaining blockers

None. Injection writes real numbers only once an eligible open-local run produces
a `REAL_EVIDENCE` report and the manifest marks artifacts eligible.
