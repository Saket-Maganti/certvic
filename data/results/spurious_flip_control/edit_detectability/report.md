# Edit Detectability Probe

Generated: 2026-07-21

Tasks: `data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl`
Items analyzed: 94 (skipped 0)
Evidence status: `DIAGNOSTIC_ONLY`

**Descriptive construct-validity diagnostic — never evidence by itself.**

## Question

Can a trivial classifier tell edited images from their originals using only
cheap low-level features (file size, edge density, sharpness, color stats,
uniform-pixel fraction)? If yes, an observed VLM consistency gap may be
confounded by the edit *artifact* rather than the intended semantic change.

## Result

- Classifier backend: `sklearn_logreg_group_cv`
- Cross-validation grouped by item pair: True
- Separability AUC (symmetric): 0.7123
- Raw oriented multivariate AUC: 0.7123
- Multivariate separability AUC: 0.7123
- Symmetric accuracy: 0.6702
- Raw oriented accuracy: 0.6702
- Most discriminative single feature: `file_size`
- Artifact-risk flag (AUC >= 0.8): **False**
- Risk band: MODERATE

### Per-feature separability (rank AUC, 0.5 = chance)

| Feature | AUC |
| --- | --- |
| `file_size` | 0.6237 |
| `uniform_fraction` | 0.5261 |
| `edge_density` | 0.5199 |
| `sharpness` | 0.5187 |
| `std_gray` | 0.5181 |
| `mean_b` | 0.5012 |
| `mean_r` | 0.5011 |
| `mean_g` | 0.5008 |

## Most-detectable items

19 item(s) flagged by largest paired low-level distance. Inspect these in human review; large low-level deltas suggest artifact confounds.

| Item | Edit type | Detectability score |
| --- | --- | --- |
| `sflip_car_ADE_train_00004616` | control_irrelevant | 0.15841 |
| `sflip_car_ADE_train_00002008` | control_irrelevant | 0.15067 |
| `sflip_table_ADE_train_00000457` | control_irrelevant | 0.14462 |
| `sflip_car_ADE_train_00001421` | control_irrelevant | 0.13942 |
| `sflip_car_ADE_train_00003061` | control_irrelevant | 0.13391 |
| `sflip_sofa_ADE_train_00000704` | control_irrelevant | 0.12648 |
| `sflip_sofa_ADE_train_00000681` | control_irrelevant | 0.12445 |
| `sflip_table_ADE_train_00000233` | control_irrelevant | 0.11985 |
| `sflip_sofa_ADE_train_00000741` | control_irrelevant | 0.11288 |
| `sflip_table_ADE_train_00000246` | control_irrelevant | 0.11218 |
| `sflip_chair_ADE_train_00000839` | control_irrelevant | 0.10489 |
| `sflip_car_ADE_train_00004630` | control_irrelevant | 0.10021 |
| `sflip_table_ADE_train_00000418` | control_irrelevant | 0.0994 |
| `sflip_table_ADE_train_00000384` | control_irrelevant | 0.09787 |
| `sflip_sofa_ADE_train_00000748` | control_irrelevant | 0.0978 |
| `sflip_table_ADE_train_00000201` | control_irrelevant | 0.09659 |
| `sflip_sofa_ADE_train_00000671` | control_irrelevant | 0.09613 |
| `sflip_chair_ADE_train_00000918` | control_irrelevant | 0.09567 |
| `sflip_chair_ADE_train_00000928` | control_irrelevant | 0.09374 |

## Mitigations if risk is ELEVATED/HIGH

- Prefer photorealistic diffusion-inpaint edits over flat-fill/blob edits.
- Add original-only and edited-only ablations to bound artifact-driven flips.
- Route flagged items through extra human review; drop non-photorealistic edits.
- Report this probe alongside (never instead of) the certified gap.
