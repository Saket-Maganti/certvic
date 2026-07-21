# CertVIC CVPR Human Review Protocol

Seven tracks are separate: pilot intervention validity, V1 specificity validity, retrospective
V2-30 sensitivity, Qwen-12 forensics, prospective specificity, Main study, and COCO second domain.
Reviewers see anonymous IDs and randomized A/B order, never provider identity, model answers,
failure status, prior machine decisions, or paper examples. Two independent raters judge target
unaffected, expected answer unchanged, perturbation acceptable, answerability, prompt ambiguity,
retain/exclude, confidence, and reason code. Disagreement requires outcome-blind adjudication.

Primary agreement reporting is percent agreement per required binary field; Cohen's kappa and Gwet's
AC1 are secondary with per-question and confidence-stratified summaries. Raw sheets are immutable.
The inclusion rule is frozen before outcomes and failures cannot be excluded because they are
failures. Blank templates remain `HUMAN_REVIEW_PENDING` and do not constitute labels.
