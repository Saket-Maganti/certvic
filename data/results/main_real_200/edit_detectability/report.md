# Edit Detectability Probe

Generated: 2026-06-23

Tasks: `data/results/main_real_200/pilot_eval_tasks_tiny.jsonl`
Items analyzed: 103 (skipped 0)
Evidence status: `CONSTRUCT_VALIDITY_DIAGNOSTIC_NON_EVIDENCE`

**Descriptive construct-validity diagnostic — never evidence by itself.**

## Question

Can a trivial classifier tell edited images from their originals using only
cheap low-level features (file size, edge density, sharpness, color stats,
uniform-pixel fraction)? If yes, an observed VLM consistency gap may be
confounded by the edit *artifact* rather than the intended semantic change.

## Result

- Classifier backend: `sklearn_logreg_cv`
- Separability AUC: 0.3492
- Multivariate AUC: 0.3492
- Accuracy: 0.3786
- Most discriminative single feature: `file_size`
- Artifact-risk flag (AUC >= 0.8): **False**
- Risk band: LOW (low-level features barely separate edits)

### Per-feature separability (rank AUC, 0.5 = chance)

| Feature | AUC |
| --- | --- |
| `file_size` | 0.5581 |
| `uniform_fraction` | 0.5065 |
| `edge_density` | 0.5057 |
| `sharpness` | 0.5054 |
| `mean_b` | 0.504 |
| `mean_r` | 0.5037 |
| `mean_g` | 0.5016 |
| `std_gray` | 0.5013 |

## Most-detectable items

21 item(s) flagged by largest paired low-level distance. Inspect these in human review; large low-level deltas suggest artifact confounds.

| Item | Edit type | Detectability score |
| --- | --- | --- |
| `preview_pilot_7d6936907e1b` | remove | 0.49554 |
| `preview_pilot_ae14631f3809` | displace | 0.28399 |
| `preview_pilot_7d1bd569f40f` | displace | 0.25193 |
| `preview_pilot_f7f706d3f9f5` | displace | 0.2477 |
| `preview_pilot_7856add436f1` | displace | 0.2423 |
| `preview_pilot_756458bc639a` | displace | 0.22357 |
| `preview_pilot_8725099680e4` | displace | 0.20985 |
| `preview_pilot_1de6086e7f7e` | displace | 0.19605 |
| `preview_pilot_b2b9037f5bc4` | displace | 0.18572 |
| `preview_pilot_200ad14905aa` | displace | 0.1595 |
| `preview_pilot_1d836c4db9c4` | displace | 0.15675 |
| `preview_pilot_619cc6330cc9` | displace | 0.15557 |
| `preview_pilot_fe56617894f8` | displace | 0.15239 |
| `preview_pilot_bceacc91c7dd` | displace | 0.14375 |
| `preview_pilot_f3dddd670aa6` | remove | 0.14162 |
| `preview_pilot_059c9c1b14f2` | displace | 0.13592 |
| `preview_pilot_01fc561f2ad1` | displace | 0.13531 |
| `preview_pilot_86a8762f4d70` | displace | 0.12699 |
| `preview_pilot_fe1acfafc429` | displace | 0.12352 |
| `preview_pilot_dfc7f95c2bf6` | displace | 0.11882 |
| `preview_pilot_3a04066be0bd` | displace | 0.11837 |

## Mitigations if risk is ELEVATED/HIGH

- Prefer photorealistic diffusion-inpaint edits over flat-fill/blob edits.
- Add original-only and edited-only ablations to bound artifact-driven flips.
- Route flagged items through extra human review; drop non-photorealistic edits.
- Report this probe alongside (never instead of) the certified gap.
