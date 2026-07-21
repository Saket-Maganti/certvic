# Edit Detectability Probe (V3)

A CPU-only construct-validity diagnostic. It asks the question a CVPR reviewer
will ask: **can a trivial classifier tell an edited image from its original using
only cheap low-level features?** If yes, an observed VLM intervention-consistency
gap may be confounded by the edit *artifact* (a flat blob, a seam, a sharpness
change) rather than the intended semantic single-factor change.

This is **descriptive only and never evidence by itself.** Its output carries
`evidence_status = CONSTRUCT_VALIDITY_DIAGNOSTIC_NON_EVIDENCE` and the claim gates
must never treat it as certification.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.validation.edit_detectability` | Feature extraction + classifier + item flagging. |
| `certvic.reporting.edit_detectability_report` | Markdown report from a summary JSON. |

## Features (no GPU)

Per-image: file size, edge density, sharpness, mean R/G/B, grayscale std,
uniform-pixel fraction. Paired (original vs edited): grayscale histogram L1
distance, mean absolute pixel diff, edge-density delta, sharpness delta, and
outside-mask change fraction (when a mask is available).

## Classifier

If scikit-learn is present and there are enough images, a standardized
`LogisticRegression` is cross-validated (stratified K-fold) to report a
multivariate separability AUC and accuracy. Otherwise a deterministic rank-AUC
(Mann-Whitney) over the single most discriminative feature is used. Per-feature
rank AUCs are always reported (0.5 = chance).

`artifact_risk` is flagged when AUC ≥ `--flag-auc` (default 0.8). The most
detectable items (largest paired low-level distance) are written to
`highly_detectable_items.jsonl` for extra human review.

## Command

```bash
python3 -m certvic.validation.edit_detectability \
  --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl \
  --out-dir data/results/edit_detectability
```

Outputs: `detectability_summary.json`, `features.csv`, `report.md`,
`highly_detectable_items.jsonl`.

## Interpretation

- **HIGH/ELEVATED AUC** (e.g. the crude flat-fill `simple` engine produces AUC ≈
  1.0): edits are low-level separable; prefer photorealistic diffusion-inpaint
  edits, add original-only / edited-only ablations to bound artifact-driven flips,
  and route flagged items through extra review.
- **LOW AUC**: low-level features barely separate edits — supports (but does not
  prove) that any measured gap reflects the semantic change. Always report this
  probe **alongside**, never instead of, the certified gap.
