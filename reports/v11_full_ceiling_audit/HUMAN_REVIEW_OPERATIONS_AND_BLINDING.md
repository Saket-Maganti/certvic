# Human Review Operations and Blinding

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

No independent human label exists yet; this document is an operating protocol, not a completed review report.

## Required review lanes

1. Review all 91 intervention pairs for target change, answer update validity, single-factor validity,
   answerability, ambiguity, artifact severity, and retain/exclude recommendation.
2. Review all 94 V1 specificity pairs for target preservation, answer invariance, perturbation
   acceptability, ambiguity, and retention.
3. Review the 30 current V2 pairs only as a retrospective diagnostic set.
4. Review the 12 Qwen forensic pairs in an anonymized lane that does not disclose provider or failure status.

## Blinding and provenance

- Deterministically randomize pair order and A/B orientation; keep the key outside reviewer bundles.
- Two independent human raters must use distinct IDs and ISO timestamps.
- Do not show provider outputs, V1 failure IDs, existing assistant labels, or selection reasons.
- Preserve both raw rater sheets; adjudicate disagreements without overwriting them.
- Report per-field agreement, Cohen kappa where meaningful, exclusions, and sensitivity with and without exclusions.
- Record item ID, objective reason, rater/rule source, timestamp, evidence pointer, and pre-result flag.

The existing `assistant_visual_review_v1` decisions are `MACHINE_ASSISTED_PRELIMINARY`.
They may seed a queue but cannot be relabeled as independent human evidence.

The deterministic private reviewer packet contains 4 tracks and
227 unique pairs (91 + 94 + 30 + 12). Its current
reviewer ZIP hash is `d6e777d035fa806d0b4ffb42cd6c140e08c1187a571770ba87b70c629c3f044f`. The hash identifies a blank packet, not completed review.
