# V2 Label Policy and Task-Family Upgrade Report

Date: 2026-06-22
Prompt: `03_V2_TASK_FAMILY_LABEL_MAP_UPGRADE.md`

## Goal

Make task-family assignment principled with an ADE20K label policy, family
eligibility rules, conservative handling of unresolved labels, and task-family
balancing — protecting construct validity before any real edits or inference.

## What was added

- `configs/ade20k_label_policy.yaml` — UNVERIFIED label-policy template
  (label_id, label_name, eligible_task_families, allowed_edit_types,
  domain_tags, block_reason, notes) plus a conservative `defaults` fallback.
- `certvic/data/label_policy.py` — core policy module: `load_label_policy`,
  `resolve_label_name`, `eligible_families_for_label`, `allowed_edits_for_label`,
  `is_label_blocked`, `explain_label_decision`, plus `policy_provenance` and an
  inspection CLI (`python3 -m certvic.data.label_policy --policy ... --label-id ...`).
- `certvic/data/label_policy_report.py` — diagnostics CLI emitting
  `label_policy_summary.json`, `label_frequency.csv`, `eligible_by_family.csv`,
  `blocked_labels.csv`, `unresolved_labels.csv`, `label_policy_report.md`.
- `certvic/data/select_pilot_items.py` — optional `--label-policy`: prefers
  eligible labels, blocks forbidden labels, restricts unresolved labels to the
  conservative fallback, records policy version/hash + unresolved-label count,
  and supports `--per-family-target-json` with shortfall warnings.
- `certvic/edit/plan_edits.py` — optional `--label-policy`: rejects
  incompatible label/family/edit combinations and summarizes rejections by
  label, family, and edit type; records policy provenance.

## Design decisions

- **Unresolved = conservative.** Labels absent from the policy resolve to
  `ade20k_label_<id>` and are eligible only for `control_irrelevant` (no-change)
  edits. We never assume a change-required question is valid for an unknown
  object — this directly defends construct validity.
- **Background "stuff" is blocked** (wall, sky, floor, ceiling, road): not a
  clean single-factor object.
- **Backward compatible.** All policy logic is gated on `--label-policy`; with no
  policy, selection/planning behave exactly as in V1.5.
- **Honesty.** The shipped policy is `verified: false`; selection warns
  `label_policy_unverified` and reports remain `DESCRIPTIVE_ONLY` /
  `CANDIDATE_ONLY` / `PLANNED_ONLY`. No evidence claims.

## Tests

- `tests/test_v2_label_policy.py` — 10 tests (policy load, resolved/blocked/
  unresolved eligibility, explain decision, invalid-family rejection, diagnostics
  outputs, selector block + unresolved handling, planner incompatibility
  rejection).
- Full suite: **128 passed** (was 118). No regressions.

## Commands added

```bash
python3 -m certvic.data.label_policy_report --masks <masks.jsonl> --policy configs/ade20k_label_policy.yaml --out-dir <dir>
python3 -m certvic.data.label_policy --policy configs/ade20k_label_policy.yaml --label-id 16 --task-family support_stability --edit-type displace
python3 -m certvic.data.select_pilot_items ... --label-policy configs/ade20k_label_policy.yaml --per-family-target-json '{"support_stability":50}'
python3 -m certvic.edit.plan_edits ... --label-policy configs/ade20k_label_policy.yaml
```

## Blockers before evidence

- Label map is unverified; resolve ADE20K names against the user's release.
- Real ADE20K root not yet supplied (selection/planning run on fixtures/dry-run).

## Status

Label-policy / task-family upgrade: **PASS** (fixtures only; no real data, GPU,
or inference).

## Next prompt (critical-path order)

`04_V2_EDIT_ENGINE_AND_QUALITY_UPGRADE.md` — the edit-realism upgrade, which is
the make-or-break construct-validity step for CVPR.
