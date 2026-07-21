
# CertVIC Human Review CLI Guide

Use one CLI throughout: `python3 -m certvic.cvpr.review <subcommand>`. The order is `build`,
`qualify`, `validate` for each independent rater, `agreement`, `adjudication-packet`, and `finalize`.
The qualification answer key/coordinator key remain separate. Reviewer identity is stored as a hash;
two distinct qualified identities are mandatory. Packet and sheet hashes, exact track-specific
columns, allowed choices, completeness, Gwet AC1, Cohen kappa, percent agreement, bootstrap intervals,
and every disagreement are fail-closed.

Specificity review judges answer invariance. Main/COCO review instead judges whether the intended
semantic transition succeeded and non-target content remained valid. Only
`FINAL_INCLUSION_VALIDATED` may enter filtered analysis. Blank templates and the synthetic fixture are
not genuine review and never set `human_reviewed=true`.
