# Playbook: No Certified Gap

**Symptoms: the anytime-valid CS lower bound does not exceed the gap threshold; no certified claim.**

## Actions

1. This may be the honest truth — report the null result; never fabricate a gap.
2. Check power: `certvic.metrics.power_plan` for the minimum detectable gap at the current n; scale n if the budget allows.
3. Verify the gap is not suppressed by parse failures or refusals (run output triage first).
4. Confirm edits genuinely change the expected answer (single-factor validity, human review).
5. Install `certvic[stats]` for the tighter betting CS; the native CS is conservative.

Do not fabricate results to clear this symptom; if the honest outcome is a null
result or an ineligible claim, report it and adjust the protocol, not the numbers.
