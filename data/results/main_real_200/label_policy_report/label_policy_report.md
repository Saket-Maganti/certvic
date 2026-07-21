# Label Policy Report

Policy: `certvic.ade20k_label_policy.v1` (sha256:4bd9136f2940176a), verified=False

> WARNING: the label policy is UNVERIFIED. Confirm the label_id -> name map
> against your ADE20K release before any evidence run.

- masks: 12737
- distinct labels: 132 (resolved 14, unresolved 118, blocked 5)
- unresolved masks: 7469, blocked masks: 2558

## Eligible masks by family

| Task family | Eligible labels | Eligible masks |
| --- | --- | --- |
| affordance_reachability | 6 | 1903 |
| control_irrelevant | 127 | 10179 |
| occlusion_safety | 6 | 1375 |
| support_stability | 5 | 1812 |

Generated files: label_frequency.csv, eligible_by_family.csv, blocked_labels.csv, unresolved_labels.csv, label_policy_summary.json
