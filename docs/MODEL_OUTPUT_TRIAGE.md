# Model Output / Parse Triage (V3)

Run this immediately after the first tiny VLM run. It triages raw outputs for the
failure modes that quietly wreck a consistency study **before** you trust any
scores: parse failures, degenerate repeated outputs, answer priors / mode
collapse, refusals, and over-long rationales. Descriptive only; no inference, no
evidence claims.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.eval.output_triage` | Compute per-provider stats, flags, and suspicious rows. |
| `certvic.reporting.parse_triage_report` | Markdown report from the triage summary. |

## Flags (per provider)

| Flag | Trips when | Meaning |
| --- | --- | --- |
| `high_parse_failure_flag` | `parse_ok_rate < 0.8` | outputs don't fit the answer format; fix prompt/parser first |
| `answer_prior_flag` | one answer ≥ 90% of parsed answers | model may ignore the image (mode collapse) |
| `degenerate_repeat_flag` | one raw string ≥ 90% of outputs | broken decoding/prompt |
| `high_refusal_flag` | refusal rate > 0.2 | many refusals; re-prompt or exclude — refusals are not a gap |

The degenerate-repeat threshold is set high (0.9) so a healthy ~50/50 yes/no
split on a binary task does not false-positive.

## Command

```bash
python3 -m certvic.eval.output_triage \
  --preds data/predictions/run.jsonl \
  --tasks data/manifests/tasks.jsonl \
  --out-dir data/results/output_triage
```

Outputs: `triage_summary.json`, `parse_failure_examples.jsonl`,
`answer_distribution.csv`, `provider_output_stats.csv`, `suspicious_outputs.csv`,
`parse_triage_report.md`.
