# CertVIC Codex V3 Prompt 12 — Paper Result Injection and Traceability


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

Build a claim-gated paper update system that refuses fake/simulated/ineligible numbers and only injects approved table/figure references.

## Inspect first

Paper number guard, paper sections, claim ledger, provenance if present.

## Build / modify

Create `certvic/paper/result_manifest.py`, `inject_results.py`, `paper_trace_report.py`. Dry-run default; `--allow-write` required for writes; run paper guard after injection.

## CLI commands to add or verify

`python3 -m certvic.paper.result_manifest --report-dir data/results/v2_report --claim-ledger data/results/claim_ledger.json --out paper/result_manifest.json`

`python3 -m certvic.paper.inject_results --manifest paper/result_manifest.json --paper-dir paper --dry-run`

`python3 -m certvic.paper.paper_trace_report --paper-dir paper --manifest paper/result_manifest.json --out docs/PAPER_TRACE_REPORT.md`

## Outputs / behavior

Rules: refuse non-evidence artifacts, require hashes, preserve placeholders if ineligible, no overwrite by default.

## Tests

Create or update:

`tests/test_v3_paper_injection.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/PAPER_RESULT_TRACEABILITY.md`, `docs/V3_PAPER_INJECTION_REPORT.md`; update paper plan and claim ledger.

## Extra notes

Important for final paper integrity.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
