# CertVIC CVPR Statistical Analysis Plan

Current authority is `configs/studies/certvic_confirmatory_authority.json`; exact machine policy is
`configs/statistics/certvic_confirmatory_primary_analysis.json`. The fixed sample contains 120
relevant and 120 irrelevant primary items per model. Relevant success requires original correctness,
edited correctness, a changed gold answer, and a model change to the edited gold. Irrelevant failure
requires an unchanged gold and a changed normalized model answer.

The certificate has two co-required gates per model: the one-sided exact lower bound for semantic
update success must be at least 0.50, and the one-sided exact upper bound for irrelevant flips must be
at most 0.10. Familywise alpha 0.05 is Bonferroni-allocated over three models by two gates, giving
alpha 1/120 per bound. The all-model claim requires all six bounds to pass. Missing, abstaining, and
parser-failed relevant rows fail responsiveness; corresponding irrelevant rows count as flips.

Report original and edited accuracy, raw answer change, correct and conditional semantic update,
transition and failure-taxonomy tables, paired risk differences, exact McNemar tests, Holm-adjusted
exploratory comparisons, raw results, preregistered human-validity-filtered results, and sensitivities.
The old accuracy-minus-change gap is secondary descriptive output only. Confidence sequences are
secondary operational displays, not the fixed-sample primary certificate.
