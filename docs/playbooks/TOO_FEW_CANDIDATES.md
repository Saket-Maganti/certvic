# Playbook: Too Few Candidates

**Symptoms: the candidate/edit count is far below the target scale.**

## Actions

1. Increase overgeneration factor and broaden eligible labels/families (see label policy).
2. Check edit-plan rejections (`pilot_edit_plan_rejected.jsonl`) for infeasible-edit reasons.
3. Add more source images via `certvic.data.select_pilot_items` within the policy.
4. Re-estimate with `certvic.planning.scale_planner` to confirm the target is feasible on free compute.

Do not fabricate results to clear this symptom; if the honest outcome is a null
result or an ineligible claim, report it and adjust the protocol, not the numbers.
