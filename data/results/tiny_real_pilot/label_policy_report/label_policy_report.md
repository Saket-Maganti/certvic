# Label Policy Report

Policy: `certvic.ade20k_label_policy.v1` (sha256:4bd9136f2940176a), verified=False

> WARNING: the label policy is UNVERIFIED. Confirm the label_id -> name map
> against your ADE20K release before any evidence run.

- masks: 1108
- distinct labels: 65 (resolved 10, unresolved 55, blocked 4)
- unresolved masks: 746, blocked masks: 241

## Eligible masks by family

| Task family | Eligible labels | Eligible masks |
| --- | --- | --- |
| affordance_reachability | 4 | 60 |
| control_irrelevant | 61 | 867 |
| occlusion_safety | 4 | 113 |
| support_stability | 3 | 73 |

Generated files: label_frequency.csv, eligible_by_family.csv, blocked_labels.csv, unresolved_labels.csv, label_policy_summary.json
