# Tiny Generated Edit Quality Review

Status: generated edits are only edit-quality artifacts. No VLM inference was run. No evidence claims are enabled. Human validity is still required.

These outputs validate local generation and quality-gate plumbing only. They are not model-evaluation evidence and are not paper results.

## Inputs

- generated manifest: `data/results/tiny_real_pilot/pilot_generated_edits.jsonl`
- rejected edits: `data/results/tiny_real_pilot/pilot_generated_rejected.jsonl`

## Counts

- generated rows: 13
- rejected rows: 0
- quality passed: 13
- quality failed: 0
- by edit type: `{'control_irrelevant': 7, 'displace': 6}`
- warning counts: `{}`

## Next Gate

Manually inspect the review gallery, run human validity checks, and keep VLM inference blocked until generated edits are accepted.

