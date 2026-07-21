# Tiny Generated Edit Quality Review

Status: generated edits are only edit-quality artifacts. No VLM inference was run. No evidence claims are enabled. Human validity is still required.

These outputs validate local generation and quality-gate plumbing only. They are not model-evaluation evidence and are not paper results.

## Inputs

- generated manifest: `data/results/main_real_200/pilot_generated_edits.jsonl`
- rejected edits: `data/results/main_real_200/pilot_generated_rejected.jsonl`

## Counts

- generated rows: 168
- rejected rows: 0
- quality passed: 103
- quality failed: 65
- by edit type: `{'control_irrelevant': 65, 'displace': 64, 'occlude': 6, 'remove': 33}`
- warning counts: `{'control edit changed too much of the image': 2, 'control edit mean difference too large': 3, 'outside allowed change too large': 65}`

## Next Gate

Manually inspect the review gallery, run human validity checks, and keep VLM inference blocked until generated edits are accepted.

