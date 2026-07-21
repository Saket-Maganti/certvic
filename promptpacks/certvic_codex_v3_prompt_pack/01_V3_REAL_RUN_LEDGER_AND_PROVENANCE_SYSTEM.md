# CertVIC Codex V3 Prompt 01 — Real Run Ledger and Provenance System


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

Build a central ledger so every future data/edit/VLM/scoring/report/paper artifact can be traced to commands, configs, inputs, outputs, hashes, evidence status, and zero-cost policy.

## Inspect first

`certvic/hashing.py`, `certvic/io.py`, schema manifest/prediction modules, existing run sidecars, claim ledger validation.

## Build / modify

Create `certvic/provenance/run_ledger.py`, `artifact_graph.py`, `trace_claim.py`, and package init. Add stable entry schema, artifact hashing, graph generation, missing-artifact detection, and claim-to-run tracing.

## CLI commands to add or verify

`python3 -m certvic.provenance.run_ledger init --out data/provenance/run_ledger.jsonl`

`python3 -m certvic.provenance.run_ledger add --stage edit_generation --run-id <ID> --inputs <paths...> --outputs <paths...> --config <path> --command "<cmd>"`

`python3 -m certvic.provenance.artifact_graph --ledger data/provenance/run_ledger.jsonl --out-dir data/provenance/artifact_graph`

`python3 -m certvic.provenance.trace_claim --claim-ledger data/results/claim_ledger.json --run-ledger data/provenance/run_ledger.jsonl --out data/provenance/claim_trace_report.md`

## Outputs / behavior

Ledger fields: run_id, stage, timestamp_utc, command, config/input/output hashes, evidence_status, zero_cost, paid_services_used=false, environment summary, user_notes. Trace status: trace_complete, missing_artifact, hash_mismatch, ineligible_evidence, unknown.

## Tests

Create or update:

`tests/test_v3_run_ledger_provenance.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/RUN_LEDGER.md`, `docs/V3_RUN_LEDGER_PROVENANCE_REPORT.md`; update `docs/CLAIM_LEDGER.md` and `docs/REPRO.md`.

## Extra notes

This is high priority because it makes every future paper number traceable.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
