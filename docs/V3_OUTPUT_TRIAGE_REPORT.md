# V3 Prompt 09 — Model Output Quality and Parse Triage Report

## Goal

Build post-run triage for VLM raw outputs: parse failures, repeated outputs,
answer priors, refusals, long rationales, invalid formats.

## What was built

- `certvic/eval/output_triage.py` — per-provider stats (parse-ok rate, refusal rate, mean output length/latency, unique-raw count, top-repeat fraction, mode answer + fraction) with flags (`high_parse_failure_flag`, `answer_prior_flag`, `degenerate_repeat_flag`, `high_refusal_flag`), suspicious-row tagging (parse_failure / refusal / long_rationale / degenerate_repeat), and writer for `triage_summary.json`, `parse_failure_examples.jsonl`, `answer_distribution.csv`, `provider_output_stats.csv`, `suspicious_outputs.csv`.
- `certvic/reporting/parse_triage_report.py` — markdown report with per-provider table, flag legend, and pointers to the CSV/JSONL artifacts.

## Tests

`tests/test_v3_output_triage.py` — 10 tests: clean run → no flags; parse failures detected + high-parse-failure flag; answer-prior flag (19/20 same answer); degenerate-repeat flag (all identical) without false-positive on 50/50 binary; refusal + long-rationale tagging; per-provider split; output writing + report; standalone report CLI from summary JSON; empty predictions; no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (346 passed; was 336).
- CLI smoke on 9 synthetic predictions (8 clean binary + 1 refusal): 1 parse failure, 1 suspicious (refusal), no provider flags. Degenerate-repeat threshold tuned to 0.9 so a healthy 50/50 yes/no split does not false-positive.

## Evidence / cost discipline

No inference, no downloads, no GPU, no paid services. Descriptive only;
`evidence_claims_made=false`, `vlm_inference_run=false`. No heavy imports.

## Status

**PASSED.**

## Remaining blockers

None. Runs against any predictions JSONL produced by `run_eval`.
