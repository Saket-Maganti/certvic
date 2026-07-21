# Edit Detectability Probe

Generated: 2026-06-23

Tasks: `data/results/tiny_real_pilot/pilot_eval_tasks_tiny.jsonl`
Items analyzed: 13 (skipped 0)
Evidence status: `CONSTRUCT_VALIDITY_DIAGNOSTIC_NON_EVIDENCE`

**Descriptive construct-validity diagnostic — never evidence by itself.**

## Question

Can a trivial classifier tell edited images from their originals using only
cheap low-level features (file size, edge density, sharpness, color stats,
uniform-pixel fraction)? If yes, an observed VLM consistency gap may be
confounded by the edit *artifact* rather than the intended semantic change.

## Result

- Classifier backend: `sklearn_logreg_cv`
- Separability AUC: 0.9231
- Multivariate AUC: 0.9231
- Accuracy: 0.9615
- Most discriminative single feature: `file_size`
- Artifact-risk flag (AUC >= 0.8): **True**
- Risk band: HIGH (edits trivially separable from low-level features)

### Per-feature separability (rank AUC, 0.5 = chance)

| Feature | AUC |
| --- | --- |
| `file_size` | 1.0 |
| `uniform_fraction` | 0.5947 |
| `mean_r` | 0.5503 |
| `sharpness` | 0.5385 |
| `mean_b` | 0.5385 |
| `std_gray` | 0.5385 |
| `mean_g` | 0.5118 |
| `edge_density` | 0.5059 |

## Most-detectable items

3 item(s) flagged by largest paired low-level distance. Inspect these in human review; large low-level deltas suggest artifact confounds.

| Item | Edit type | Detectability score |
| --- | --- | --- |
| `preview_pilot_5d2cf5bb3931` | displace | 0.05695 |
| `preview_pilot_23dab8b932a7` | control_irrelevant | 0.05623 |
| `preview_pilot_a5f649c8901b` | displace | 0.05344 |

## Mitigations if risk is ELEVATED/HIGH

- Prefer photorealistic diffusion-inpaint edits over flat-fill/blob edits.
- Add original-only and edited-only ablations to bound artifact-driven flips.
- Route flagged items through extra human review; drop non-photorealistic edits.
- Report this probe alongside (never instead of) the certified gap.
