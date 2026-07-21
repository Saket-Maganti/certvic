# Edit Detectability Probe

Generated: 2026-07-12

Tasks: `data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl`
Items analyzed: 30 (skipped 0)
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
- Separability AUC (symmetric): 0.6922
- Raw oriented multivariate AUC: 0.6922
- Multivariate separability AUC: 0.6922
- Symmetric accuracy: 0.6667
- Raw oriented accuracy: 0.6667
- Most discriminative single feature: `file_size`
- Artifact-risk flag (AUC >= 0.8): **False**
- Risk band: MODERATE

### Per-feature separability (rank AUC, 0.5 = chance)

| Feature | AUC |
| --- | --- |
| `file_size` | 0.6078 |
| `sharpness` | 0.5378 |
| `std_gray` | 0.5244 |
| `uniform_fraction` | 0.5139 |
| `edge_density` | 0.5122 |
| `mean_g` | 0.5022 |
| `mean_b` | 0.5022 |
| `mean_r` | 0.5011 |

## Most-detectable items

6 item(s) flagged by largest paired low-level distance. Inspect these in human review; large low-level deltas suggest artifact confounds.

| Item | Edit type | Detectability score |
| --- | --- | --- |
| `sflip_table_ADE_train_00000233` | control_irrelevant | 0.12005 |
| `sflip_table_ADE_train_00000384` | control_irrelevant | 0.09788 |
| `sflip_sofa_ADE_train_00000671` | control_irrelevant | 0.09575 |
| `sflip_chair_ADE_train_00000928` | control_irrelevant | 0.09382 |
| `sflip_table_ADE_train_00000218` | control_irrelevant | 0.08804 |
| `sflip_sofa_ADE_train_00000653` | control_irrelevant | 0.08366 |

## Mitigations if risk is ELEVATED/HIGH

- Prefer photorealistic diffusion-inpaint edits over flat-fill/blob edits.
- Add original-only and edited-only ablations to bound artifact-driven flips.
- Route flagged items through extra human review; drop non-photorealistic edits.
- Report this probe alongside (never instead of) the certified gap.
