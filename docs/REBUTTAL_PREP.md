# Rebuttal Preparation (V3)

Generates harsh simulated CVPR reviews from the **current** artifacts and a
rebuttal pack mapping each objection to CertVIC's defense. The cardinal rule:
when empirical results are missing, the reviewers complain and reject — they
never hallucinate numbers, and the rebuttal pack marks those points as honestly
**blocked on a real run**.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.review.simulate_reviews` | Six reviewer profiles assess the current state; emit `reviews.json` + `reviews.md`. |
| `certvic.review.rebuttal_pack` | Map weaknesses/questions to defenses + action items; flag blocked-on-results points. |

## Reviewer profiles

`benchmark_skeptic`, `stats_reviewer`, `vision_editing_reviewer`,
`reproducibility_reviewer`, `construct_validity_reviewer`,
`open_model_scope_reviewer`. Scores are CVPR-style (1–5). With no results, scores
sit at strong-reject and every reviewer flags the missing empirical evidence.

## Commands

```bash
python3 -m certvic.review.simulate_reviews \
  --paper-dir paper --reports-root data/results \
  --out-dir docs/reviewer_simulation

python3 -m certvic.review.rebuttal_pack \
  --reviews docs/reviewer_simulation/reviews.json \
  --out docs/rebuttal_pack.md
```

## Honesty guarantees

`any_hallucinated_results` is always `false`; `fabricated_results` is always
`false`. Points that require a real run (e.g. "no empirical results") are tagged
`blocked_on_results` in the rebuttal pack and listed explicitly — they must be
answered with a real run, not invented numbers. Defensible, infrastructure-backed
points (anytime-valid CS, cluster diagnostics, edit detectability, recipe-first
release, baselines/IAA, number guard) are tagged `addressable_now`.
