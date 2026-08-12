# C12 confirmatory power decision

Decision: `AMEND_BEFORE_OUTCOME_EXECUTION`.

This decision was made before any prospective provider outcome existed. The endpoint definitions,
thresholds, one-sided exact Clopper-Pearson tests, missing-data semantics, and six-gate Bonferroni
family remain unchanged.

## Scientific claim regimes

- Regime A, `ALL_THREE_MODELS_MUST_JOINTLY_CERTIFY`, requires all six gates to pass.
- Regime B, `MODEL_LEVEL_CERTIFICATES_WITH_FAMILYWISE_ERROR_CONTROL`, permits scoped per-model
  certificates while retaining the same familywise correction. Optional models never enter the
  primary family retroactively.

## Design-scenario comparison

At true responsiveness 0.70 and true irrelevant-flip rate 0.03:

| Allocation | Response power | Specificity power | Per-model joint | All-three joint |
| --- | ---: | ---: | ---: | ---: |
| 120 relevant / 120 irrelevant | 0.980029 | 0.707629 | 0.693496 | 0.333528 |
| 120 relevant / 240 irrelevant | 0.980029 | 0.985543 | 0.965860 | 0.901036 |

The old allocation over-invested in an already high-powered responsiveness endpoint while leaving
the specificity endpoint as the dominant false-negative risk. Doubling only the controls raises
the declared all-three design-scenario power from 0.334
to 0.901. It also preserves the original 120-item
responsiveness commitment and avoids changing any scientific threshold.

This is a design calculation, not model evidence. Power remains truth-dependent: the full grid is
recorded in `allocation_power_grid.csv`, including unfavorable rates where neither design is likely
to certify. The amendment does not guarantee a positive result.
