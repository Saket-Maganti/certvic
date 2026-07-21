# Human Review Operations (V3)

Human review is the likely bottleneck at 1k–2k scale. This scales the visual
review process: balanced reviewer batching, overlap for inter-annotator
agreement (IAA), progress tracking, disagreement detection, and adjudication.
No paid annotation services; review sheets contain no model outputs.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.validation.review_batches` | Split tasks into balanced per-reviewer batches + overlap subset; estimate workload. |
| `certvic.validation.review_progress` | Track completion, missing ratings, overlap disagreements, IAA. |
| `certvic.validation.adjudicate_review` | Majority-vote one row per item; flag ties for a human adjudicator. |

## Batching

Items are stratified by `(task_family, edit_type)`. A fraction (`--overlap-rate`,
default 0.2) of each stratum is assigned to **every** reviewer for IAA; the rest
are round-robined within each stratum so per-reviewer loads stay balanced (within
one item). Each reviewer gets a CSV sheet with the standard decision columns
(`photorealistic`, `single_factor`, `target_object_clear`,
`required_change_unambiguous`, `prompt_answerable`, `keep_for_eval`) and
`reviewer_id` prefilled. Workload is estimated at ~30 s/item; wall-clock is the
busiest reviewer (reviewers work in parallel).

## Commands

```bash
python3 -m certvic.validation.review_batches \
  --tasks data/manifests/pilot_eval_tasks_tiny.jsonl \
  --out-dir data/annotations/review_batches \
  --reviewers reviewer_a reviewer_b --overlap-rate 0.2 --seed 0

python3 -m certvic.validation.review_progress \
  --ratings-dir data/annotations/review_batches \
  --out data/annotations/review_progress.json

python3 -m certvic.validation.adjudicate_review \
  --ratings data/annotations/visual_review_ratings.csv \
  --out data/annotations/visual_review_adjudicated.csv
```

## Progress and disagreements

`review_progress` reports per-reviewer assigned/rated/missing, overall completion,
the specific blank decision fields per unrated row, overlap-item disagreements
(per field), and IAA (Cohen's κ for two raters, majority agreement for 3+) on the
overlap subset.

## Adjudication

`adjudicate_review` collapses a multi-reviewer ratings CSV into one row per item.
Each decision field is resolved by majority vote with status `unanimous` /
`majority` / `tie_needs_human` (ties resolve to `uncertain` and are flagged in
`disagreement_fields` for manual adjudication). Downstream, the adjudicated keep
decisions feed `certvic.data.apply_visual_review` exactly as the single-reviewer
flow does.
