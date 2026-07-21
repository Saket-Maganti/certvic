# CertVIC Pre-Registration (Analysis Plan)

This document pre-commits the CertVIC confirmatory analysis **before** any open
VLM is run on reviewed real items. It exists to defuse the strongest statistical
reviewer attacks (p-hacking, subgroup mining, inflated effective sample size,
optional-stopping abuse). It is versioned with the code; any change after the
first eligible run must be logged in the change log below and reported as a
deviation. Pre-run simulation artifacts (`SIMULATED_ONLY`) are excluded.

## 1. Primary endpoint (confirmatory)

There is exactly **one** primary confirmatory endpoint:

> The pooled intervention-consistency gap `Delta = E[a_i] - E[C_i]`, certified via
> a two-sided anytime-valid confidence sequence (CS) on the bounded transform
> `d_i = (a_i - C_i + 1)/2 in [0, 1]`, with the certified claim being that the
> CS **lower bound on `Delta` exceeds the threshold `tau`** at level `alpha`.

Defaults: `alpha = 0.05`, `tau = 0.05` (the certification policy of record is
`configs/certification_policy.yaml`). These are fixed in advance and must not be
tuned to the observed data.

`a_i` = original-image correctness; `C_i` = consistency indicator that the
original/edited answer pair respects `required_change`. Both are defined in
`certvic/metrics/score_predictions.py` and are not redefined post hoc.

## 2. Estimator and validity

* CS backend: `confseq` betting CS when installed (preferred, tighter); otherwise
  the native Hoeffding-mixture CS in `certvic/metrics/anytime_cs.py`. Both are
  time-uniform and valid under optional stopping.
* The anytime-valid guarantee is empirically verified by
  `certvic/sim/anytime_validity.py` (Type-I control and coverage under continuous
  peeking, contrasted with the inflation of a peeked fixed-n CI).
* Bootstrap / normal-approximation intervals are **descriptive only** and never
  used to make a certified claim.

## 3. Stopping rule (optional stopping)

Data collection MAY stop at any time (compute exhausted, budget reached, or the
CS lower bound crosses `tau`). Anytime-validity makes the certified claim valid
under **any** data-dependent stopping rule, so peeking is permitted. We will
report the realized stopping time and the full CS trajectory, not just the final
interval. We will **not** re-tune `alpha`, `tau`, or the endpoint after peeking.

## 4. Multiplicity / subgroup analyses (secondary, exploratory)

All per-`task_family`, per-`domain`, per-`edit_type`, and per-`required_change`
breakdowns are **secondary and exploratory**. They are reported descriptively and
are NOT used for a confirmatory certified claim unless either:

1. the subgroup is pre-registered as a primary endpoint here (currently none are), or
2. a multiplicity correction is applied across the `K` simultaneous subgroup CS
   claims (Bonferroni: run each subgroup CS at `alpha / K`), and the corrected
   lower bound still exceeds `tau`.

Subgroup findings without correction are described as hypothesis-generating only.
The failure-taxonomy gallery is exploratory and never a certified claim.

## 5. Item dependence / clustering

Multiple edited items can derive from the same source image, so `a_i`/`C_i` are
not strictly independent across items sharing a source. Mitigations:

* **Primary analysis** uses at most a pre-declared cap of items per source image
  (default: 1 confirmatory item per source; additional items per source are
  exploratory) so the confirmatory sequence is across distinct sources.
* We report the number of distinct source images and the items-per-source
  distribution alongside `n`, and we report a per-source cluster-aggregated
  sensitivity analysis (gap computed on source-level means).
* Roadmap item (tracked in the reviewer attack harness as `enhancement`): a
  dedicated cluster-aware diagnostic / cluster CS in the analysis code.

## 6. Eligibility (what counts as evidence)

A certified claim is only emitted when the certification policy passes AND the
evidence context is clean: no `smoke`/`simulation` split, no `MOCK_ONLY` or any
`*_NON_EVIDENCE`/`SIMULATED_ONLY` status, no synthetic-smoke fixtures, and an
open-local (non-mock, non-baseline) provider. See `certvic/validation/claims.py`.

## 7. Scope of claims

We claim a measured decision-update gap for the tested open VLMs on this task
distribution under controlled real-image interventions. We do **not** claim
causal understanding, broad model-class failure, or any deployment-safety
conclusion.

## 8. Change log

* 2026-06-22: Initial pre-registration created during pre-run hardening (V2.x).
  No eligible run has occurred; the plan is fully prospective.
* 2026-06-22: V5 analysis-plan lock generated at `docs/ANALYSIS_PLAN_LOCK.md`
  and `data/results/analysis_plan_lock.json`; still no eligible run has occurred.
