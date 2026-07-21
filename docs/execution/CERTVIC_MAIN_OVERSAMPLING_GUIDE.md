# CertVIC Main Candidate Oversampling Guide

The frozen final design remains 500 primary plus 125 same-stratum reserves. Candidate construction
now targets 1,150 items: 400 removal, 500 insertion, and 250 attribute candidates. These are 1.60x,
2.00x, and 2.00x their respective final-plus-reserve requirements.

Small targets, corner placements, low-frequency categories, and licensed insertion assets receive
separate 2.00x to 2.50x minimum planning ratios. At the frozen planning assumptions of 80% automated
QA retention followed by 80% human-review retention, projected availability is 736 items, a surplus
of 111 above the unchanged 625 final-plus-reserve requirement. Family shortages block selection and
trigger additional same-family/same-stratum construction; they never weaken a final quota.

The authoritative policy and projections are in `configs/studies/main_study_cvpr.yaml` under
`task_builder.candidate_oversampling`.
