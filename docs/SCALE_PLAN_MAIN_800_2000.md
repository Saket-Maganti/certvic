# Scale Plan — main_500 to main_2000 (without breaking gates)

**PROJECTION, NOT A RESULT** (`evidence_status = SCALE_PROJECTION_NON_EVIDENCE`). The n=91 pilot is strong but below CVPR main-claim scale. This plan projects the resources to reach larger reviewed-approved sets while preserving every validity gate. No GPU job is launched here; no threshold is weakened.

## Observed pilot survival (from real artifacts — measured, not projected)

- Source candidates → planned edits: 168/200 = 0.840
- Planned edits → generated/quality-passed tasks: 103/168 = 0.613
- Tasks → human-approved: 91/103 = 0.883
- **Overall candidate → approved: 91/200 = 0.455**

## Projected resources per target

| target (approved) | source items | planned edits | diffusion sessions | VLM sessions ×3 | review h | storage MB | cost |
|---|---|---|---|---|---|---|---|
| 500 | 1100 | 924 | 1 | 3 | 23.6 | 121.9 | $0 |
| 800 | 1760 | 1478 | 2 | 3 | 37.8 | 190.6 | $0 |
| 1000 | 2199 | 1847 | 2 | 3 | 47.2 | 236.3 | $0 |
| 2000 | 4397 | 3693 | 3 | 3 | 94.3 | 465.0 | $0 |

All rows are **projections** computed by `scripts/plan_scaled_main_run.py` from the observed survival rates above.

## Planning assumptions (not measurements)

- Diffusion: 25.0 s/edit on a free T4 (conservative, incl. load).
- Usable GPU hours per free session: 9.0 h.
- VLM latency: 1.488 s/inference observed × 2.0 safety.
- Review pace: 1.5 + 1.0 min/item (primary + residual-cue).
- Image size: 63.4 KB/image observed; control held at 120 items.

## Stop / go gates (scaling halts if any trips)

- **detectability_auc** — halt_if: edit-detectability AUC > 0.7; conditional_if: AUC > 0.6; confounded_if: AUC >= 0.8; source: certvic.validation.detectability_gate (canonical thresholds, not weakened); pilot_observed: 0.349
- **human_review_pass_rate** — halt_if: approve_rate < 0.50 (collapsed); warn_if: approve_rate < 0.70; pilot_observed: 0.883
- **controls** — halt_if: absent-object control accuracy drops materially, OR spurious-flip specificity control fails when run
- **parse_failures** — halt_if: parse_failure_rate > 0.05; warn_if: > 0.02; pilot_observed: 0.0; note: policy threshold (pilot had 0.0); not an existing gate being weakened
- **result_ledger_hashing** — halt_if: certvic.v7.result_ledger_audit cannot hash all artifacts or any hash mismatches

## Cost

Zero. Local Mac/M4 CPU for planning + free Kaggle T4 for diffusion/VLM. No paid APIs, GPUs, datasets, annotation, or credits.

## First safe scale command

```bash
python3 scripts/plan_scaled_main_run.py
# Then execute main_500 ONLY after the spurious-flip specificity control passes and the
# result-ledger audit is clean. Do not use any projected number as a paper result.
```
