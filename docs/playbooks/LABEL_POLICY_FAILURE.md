# Playbook: Label Policy Failure

**Symptoms: label-policy rejections dominate; too few eligible (label, family, edit) combinations.**

## Actions

1. Inspect `certvic.data.label_policy_report`; see which labels/families are blocked and why.
2. Verify the ADE20K label map is correct; unresolved labels fall back to conservative names and controls only.
3. Relax the policy only where justified (documented), never to manufacture eligible items.
4. Broaden source selection (more images/labels) rather than weakening single-factor validity.

Do not fabricate results to clear this symptom; if the honest outcome is a null
result or an ineligible claim, report it and adjust the protocol, not the numbers.
