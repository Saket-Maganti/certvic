
# CertVIC Runtime Readiness Scorecard

Overall verdict: `PARTIALLY_READY_WITH_BLOCKERS`; software success is not empirical evidence.

| Dimension | Score / 100 | Boundary |
| --- | ---: | --- |
| Engineering | 92 | local implementations and synthetic failure paths built; Kaggle/model compatibility unproven |
| Execution | 70 | Level 0/1 local path built; Level 3 and all scientific runs external |
| Evidence | 30 | historical V1/V11 boundaries only; no new confirmatory or human evidence |
| Paper | 68 | substantive non-result sections; results/citations still gated |
| Release | 82 | deterministic candidate with code/config/notebooks/fixtures/docs/cards; real-data license decisions pending |

Promotion to `CVPR_PRE_EXECUTION_READY` requires successful 00A, one 00B per snapshot, one real-adapter
00C per provider, exact snapshot/commit freeze, and no unresolved implementation defect. It still would
not imply paper readiness.
