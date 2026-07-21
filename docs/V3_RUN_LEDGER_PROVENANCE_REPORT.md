# V3 Prompt 01 — Run Ledger and Provenance System Report

## Goal

Build a central ledger so every future data/edit/VLM/scoring/report/paper
artifact can be traced to commands, configs, inputs, outputs, hashes, evidence
status, and zero-cost policy.

## What was built

- `certvic/provenance/__init__.py` — package docstring (no eager submodule import, so `python -m` stays clean).
- `certvic/provenance/run_ledger.py` — `LedgerEntry` schema, file/dir hashing, `init`/`add` CLI, append-only JSONL ledger, import-safe environment summary.
- `certvic/provenance/artifact_graph.py` — bipartite `input -> run -> output` graph; re-hashes artifacts to detect missing files and hash drift; emits JSON + markdown + Graphviz DOT.
- `certvic/provenance/trace_claim.py` — traces each claim-ledger entry to producing runs; statuses `trace_complete / missing_artifact / hash_mismatch / ineligible_evidence / unknown`; flags integrity violations for certified-but-untraceable claims (CLI exits non-zero).

## Tests

`tests/test_v3_run_ledger_provenance.py` — 14 tests covering: positive init/add path, missing/remote artifacts hashing to null, stable content-sensitive directory hashing, paid-services flag, import-safe environment summary (asserts `torch` not imported), malformed-ledger rejection, healthy graph, missing+mismatch detection, orphan inputs, and all five trace statuses plus report renderers.

## Verification

- `python3 -m pytest -q` — full suite green (260 passed; was 246).
- CLI smoke test: `init` → `add` (real smoke artifacts) → `artifact_graph` produced a healthy graph (1 run, 3 artifacts, 0 missing/mismatch). `python -m` runs without the runpy double-import warning.

## Evidence / cost discipline

No downloads, no GPU, no paid services, no evidence claims. All result dicts
carry `evidence_claims_made=false`; entries carry `paid_services_used` and
`zero_cost`. Heavy modules (`torch`, `diffusers`) are only probed via
`importlib.util.find_spec`, never imported.

## Status

**PASSED.**

## Remaining blockers

None for this prompt. Downstream V3 stages should call
`certvic.provenance.run_ledger add` after each real run so the artifact graph and
claim tracer have data to work on; until a real pilot runs, the ledger is empty
by design.
