# Model Output / Parse Triage

Generated: 2026-06-24

Predictions: `/tmp/vlmout/pred_qwen2_5_vl_7b_merged.jsonl`
Total predictions: 182  |  parse failures: 0  |  suspicious: 0

Descriptive post-run diagnostic. No inference run; makes no evidence claim.

Flagged providers: none

## Per-provider stats

| Provider | n | parse_ok | refusal | mean chars | unique raw | top repeat | mode answer | mode frac | flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen2_5_vl_7b` | 182 | 1.0 | 0.0 | 2.3 | 2 | 0.6593 | no | 0.6593 | ok |

## What the flags mean

- **answer prior / mode collapse**: one answer dominates → the model may ignore the image.
- **degenerate repeated output**: the same raw string repeats → broken decoding/prompt.
- **high parse-failure rate**: outputs don't fit the answer format → fix prompt/parser before trusting scores.
- **high refusal rate**: many refusals → re-prompt or exclude; refusals are not evidence of a gap.

See `provider_output_stats.csv`, `answer_distribution.csv`, `suspicious_outputs.csv`,
and `parse_failure_examples.jsonl` for the underlying rows.
