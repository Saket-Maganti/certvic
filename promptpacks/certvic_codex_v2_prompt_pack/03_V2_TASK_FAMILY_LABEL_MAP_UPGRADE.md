# CertVIC Codex V2 Prompt 03 — Task-Family and ADE20K Label-Map Upgrade

Do not use paid services. Do not download data. Do not run GPU. Do not run VLM inference. Do not make evidence claims.

## Goal

Make task-family assignment more principled with label-map support, family eligibility rules, and task-family balancing.

## Tasks

1. Add config:
   - `configs/ade20k_label_policy.yaml`

   Fields:
   - label_id
   - label_name
   - eligible_task_families
   - allowed_edit_types
   - domain_tags
   - block_reason
   - notes

2. Add module:
   - `certvic/data/label_policy.py`

   Functions:
   - load_label_policy
   - resolve_label_name
   - eligible_families_for_label
   - allowed_edits_for_label
   - is_label_blocked
   - explain_label_decision

3. Support unresolved labels like `ade20k_label_<id>` with conservative fallback eligibility.

4. Upgrade pilot selector:
   - use label policy if provided
   - prefer eligible labels
   - block forbidden labels
   - emit decision reasons
   - include label policy hash/version
   - include unresolved label count in summary

5. Upgrade edit planner:
   - reject incompatible label/family/edit combinations
   - summarize rejections by label/family/edit_type

6. Add task-family balancing:
   - target per family configurable
   - warning when target cannot be met

7. Add diagnostics command:

   `python3 -m certvic.data.label_policy_report --masks data/manifests/ade20k_masks.jsonl --policy configs/ade20k_label_policy.yaml --out-dir data/results/label_policy_report`

   Outputs:
   - label_policy_summary.json
   - label_frequency.csv
   - eligible_by_family.csv
   - blocked_labels.csv
   - unresolved_labels.csv
   - label_policy_report.md

8. Add tests:
   - `tests/test_v2_label_policy.py`

9. Update docs:
   - `docs/PILOT_ADE20K.md`
   - `docs/DATA_CARD.md`
   - `docs/REPRO.md`
   - `docs/RISK_REGISTER.md`

10. Create:
   - `docs/V2_LABEL_POLICY_TASK_FAMILY_REPORT.md`

11. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, commands added, whether label-policy upgrade passed, and next prompt: `04_V2_EDIT_ENGINE_AND_QUALITY_UPGRADE.md`.
