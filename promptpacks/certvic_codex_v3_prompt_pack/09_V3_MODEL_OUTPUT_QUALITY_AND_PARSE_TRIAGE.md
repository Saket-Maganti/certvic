# CertVIC Codex V3 Prompt 09 — Model Output Quality and Parse Triage


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

Build post-run triage for VLM raw outputs: parse failures, repeated outputs, answer priors, refusals, long rationales, invalid formats.

## Inspect first

Parser, scoring, ablations.

## Build / modify

Create `certvic/eval/output_triage.py` and `certvic/reporting/parse_triage_report.py`.

## CLI commands to add or verify

`python3 -m certvic.eval.output_triage --preds data/predictions/run.jsonl --tasks data/manifests/tasks.jsonl --out-dir data/results/output_triage`

## Outputs / behavior

Outputs: parse_failure_examples.jsonl, answer_distribution.csv, provider_output_stats.csv, suspicious_outputs.csv, parse_triage_report.md.

## Tests

Create or update:

`tests/test_v3_output_triage.py`

Tests must cover positive path, failure path, non-evidence behavior, and no-paid/no-heavy-import behavior where relevant.

## Docs

Create `docs/MODEL_OUTPUT_TRIAGE.md`, `docs/V3_OUTPUT_TRIAGE_REPORT.md`; update metrics spec.

## Extra notes

Useful immediately after first tiny VLM run.

## Required verification

Run:

`python3 -m pytest -q`

If a CLI is added, smoke-test it on fixtures or dry-run inputs.

## Final response

Report files changed, tests run, commands added, whether this V3 prompt passed, and remaining blockers.
