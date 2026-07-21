# Edit Detectability Probe

Generated: 2026-07-12

Tasks: `data/results/main_real_200/pilot_eval_taskitems_v2.jsonl`
Items analyzed: 91 (skipped 0)
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
- Separability AUC (symmetric): 0.5783
- Raw oriented multivariate AUC: 0.5783
- Multivariate separability AUC: 0.5783
- Symmetric accuracy: 0.5714
- Raw oriented accuracy: 0.5714
- Most discriminative single feature: `file_size`
- Artifact-risk flag (AUC >= 0.8): **False**
- Risk band: LOW (low-level features barely separate edits)

### Per-feature separability (rank AUC, 0.5 = chance)

| Feature | AUC |
| --- | --- |
| `file_size` | 0.5557 |
| `mean_b` | 0.505 |
| `uniform_fraction` | 0.5043 |
| `std_gray` | 0.504 |
| `mean_g` | 0.502 |
| `sharpness` | 0.5014 |
| `edge_density` | 0.501 |
| `mean_r` | 0.5007 |

## Most-detectable items

18 item(s) flagged by largest paired low-level distance. Inspect these in human review; large low-level deltas suggest artifact confounds.

| Item | Edit type | Detectability score |
| --- | --- | --- |
| `preview_pilot_7d1bd569f40f` | displace | 0.25193 |
| `preview_pilot_f7f706d3f9f5` | displace | 0.2477 |
| `preview_pilot_7856add436f1` | displace | 0.2423 |
| `preview_pilot_756458bc639a` | displace | 0.22357 |
| `preview_pilot_1de6086e7f7e` | displace | 0.19605 |
| `preview_pilot_b2b9037f5bc4` | displace | 0.18572 |
| `preview_pilot_200ad14905aa` | displace | 0.1595 |
| `preview_pilot_1d836c4db9c4` | displace | 0.15675 |
| `preview_pilot_fe56617894f8` | displace | 0.15239 |
| `preview_pilot_bceacc91c7dd` | displace | 0.14375 |
| `preview_pilot_f3dddd670aa6` | remove | 0.14162 |
| `preview_pilot_059c9c1b14f2` | displace | 0.13592 |
| `preview_pilot_01fc561f2ad1` | displace | 0.13531 |
| `preview_pilot_86a8762f4d70` | displace | 0.12699 |
| `preview_pilot_fe1acfafc429` | displace | 0.12352 |
| `preview_pilot_dfc7f95c2bf6` | displace | 0.11882 |
| `preview_pilot_3a04066be0bd` | displace | 0.11837 |
| `preview_pilot_0a85d722de99` | displace | 0.11745 |

## Mitigations if risk is ELEVATED/HIGH

- Prefer photorealistic diffusion-inpaint edits over flat-fill/blob edits.
- Add original-only and edited-only ablations to bound artifact-driven flips.
- Route flagged items through extra human review; drop non-photorealistic edits.
- Report this probe alongside (never instead of) the certified gap.
