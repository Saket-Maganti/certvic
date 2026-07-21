# Playbook: Low Human Agreement

**Symptoms: inter-annotator agreement (Cohen's kappa / majority agreement) is below threshold.**

## Actions

1. Clarify the review rubric for the disagreed decision fields (photorealism, single-factor).
2. Use `certvic.validation.review_progress` to find the disagreed items and fields.
3. Adjudicate with `certvic.validation.adjudicate_review`; send ties to a third reviewer.
4. Drop items that cannot reach agreement rather than forcing a label.

Do not fabricate results to clear this symptom; if the honest outcome is a null
result or an ineligible claim, report it and adjust the protocol, not the numbers.
