
# CertVIC Human Review Operations Guide

Build one track-specific visual packet with `certvic.cvpr.review_packets.build_visual_packet`. It
copies anonymous A/B images, randomizes order deterministically, displays the task question and
candidate expected answer, and omits model outcomes and original/edited identity. Keep the
coordinator key and qualification answer key outside reviewer delivery.

Each reviewer reads the codebook, completes the five-item qualification quiz, and must score at
least 80%. Two distinct qualified identities independently complete copies of the blank sheets. Never
edit the packet templates or hash manifest; completed sheets are new immutable files. Compute percent
agreement, Cohen kappa, the preregistered primary Gwet AC1 statistic, per-question results,
confidence strata, and bootstrap intervals. Extract only disagreements for the adjudicator. Preserve
both raw sheets and adjudication separately.

Final inclusion fails closed unless packet image/document hashes match, sheets are complete, rater
identities differ, every disagreement has an adjudicated value, and all validity fields satisfy the
frozen rule. A structurally valid blank sheet remains `HUMAN_REVIEW_PENDING`; it is never completion.
