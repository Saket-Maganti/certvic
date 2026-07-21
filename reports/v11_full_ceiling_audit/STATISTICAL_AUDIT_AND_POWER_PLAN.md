# Statistical Audit and Power Plan

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

This audit distinguishes descriptive point estimates, time-uniform pilot bounds, and prospective specificity decisions.

## Verified estimands

For intervention item i, `a = mean(original correctness)`, `p = mean(raw answer change)`, and
`gap = a - p`. The bounded gap variable is mapped to `(A_i - C_i + 1)/2` for the confidence
sequence. Parser failures must be reported and may not be dropped to improve a gate.

| Model | n | a | p | gap | CS LB | full certified |
|---|---|---|---|---|---|---|
| Qwen2.5-VL-7B | 91 | 0.9231 | 0.1758 | 0.7473 | 0.363958 | false |
| InternVL2-8B | 91 | 0.9231 | 0.0989 | 0.8242 | 0.440881 | false |
| LLaVA-OneVision-7B | 91 | 0.8901 | 0.1758 | 0.7143 | 0.330991 | false |

## Specificity decisions

- Frozen V1 continuity rule: observed flip rate <= 0.10. Do not retrofit an interval rule to V1.
- Prospective independent V2 primary: one-sided 95% Clopper-Pearson upper bound <= 0.10 for Qwen.
- Joint three-model statement: Bonferroni one-sided alpha=0.05/3 and every upper bound <= 0.10.
- Missing or unparseable pairs count as flips in the primary endpoint and are reported separately.
- Raw and pre-result validity-filtered results must both be shown.

With zero observed flips, the one-model bound first falls to at most 0.10 at n=29; under the
three-model Bonferroni level it requires n=39. Those best-case thresholds do not constitute a
power analysis for nonzero true rates. Design should report operating characteristics across
plausible rates (for example 0.01, 0.03, 0.05, 0.08, and 0.12) and choose n before outputs.

The deterministic planning tables under `analysis/supported_results/` provide: exact-binomial
specificity pass probability for n=30, 60, 94, 150, 200, 300, and 500 over six true-rate
assumptions; paired-model normal-approximation sensitivity over discordance 0.10--0.30 and risk
differences 0.05--0.15; conservative two-domain interaction sensitivity over effects 0.05--0.20;
and two-rater raw-agreement precision for agreement 0.80/0.90 and half-width 0.05--0.10. Every row
is `PLANNED_NOT_EXECUTED`; exact simulation and prevalence-sensitive kappa planning must be frozen
before a confirmatory design.

Main-500 is not justified merely because 500 is larger. Its value is balanced family/category
coverage and interaction estimation after the simple specificity gate is resolved. If the locked
analysis only needs an overall one-model specificity decision, the prospective table may justify a
smaller independent set; if it targets strata or domain interactions, sparse-cell requirements may
justify 500 or more. The design owner must state which question determines n before outcomes.

## Paired exploratory comparisons

See `V11_PAIRED_COMPARISONS.csv`. Exact McNemar tests use discordant same-item pairs; deterministic
paired bootstrap intervals use 20,000 resamples and fixed seeds. These tests are retrospective.
Holm correction across three comparisons leaves Qwen--InternVL below 0.05 but not Qwen--LLaVA.

## Confidence-sequence audit

The active fallback is `certvic.anytime_cs.hoeffding_mixture` because optional `confseq` is absent.
It applies a two-sided Gaussian-mixture Hoeffding boundary to the bounded transform
`(A_i-C_i+1)/2`, then maps back to the gap scale. Closed-form numerical reference, range, empty-input,
width, backend, and continuous-peeking simulation tests are present. The guarantee assumes the
mixture horizon/tuning, item order, and endpoint are fixed independently of outcomes and that the
bounded conditional-mean supermartingale condition is defensible. Historical n=91 was a fixed task
set; an adaptively chosen stopping-time horizon must not be reused as `t_opt` after looking at data.
No finite-population correction is used, and the bound does not turn the ADE20K items into a random
sample from a broader VLM population. Report the CS numerical crossing separately from sample,
family, validity, specificity, revision, and claim-eligibility gates.
