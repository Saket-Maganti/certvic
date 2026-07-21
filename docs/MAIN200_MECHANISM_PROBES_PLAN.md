# Main-200 Mechanism Probes Plan

**Status: probe tasks generated (CPU), not yet run, NOT evidence**
(`evidence_status = MECHANISM_PROBE_NON_EVIDENCE`, `paper_evidence = false`).

The presence-arm result replicates across three open VLMs, but the *mechanism* is open. A
reviewer will ask whether the post-edit failure is driven by **scene-context anchoring**,
by **residual cues** in the edited pixels, or by **prompt priors**. These probes are
designed to separate those explanations. They reuse the **same 91 reviewed presence items**
and are meant to run later on free Kaggle GPU with the existing single-image VLM notebook.

Generate / regenerate:
```bash
python3 scripts/build_mechanism_probe_tasks.py
```
Outputs under `data/results/main_real_200/mechanism_probes/` (one dir per family +
`summary.json`). Every task traces to its reviewed item via `item_id`, `edit_id`,
`source_id`, `mask_id`.

## Probe families

| family | run label | image | prompt (abridged) | flag = mechanism signal |
|---|---|---|---|---|
| object_list | `mech_objlist` | edited | "List the clearly visible objects…" | target listed ⇒ anchoring / residual |
| region_focused | `mech_region` | edited **crop** (bbox + 15% margin) | "Looking only at this region, is there a clearly visible {target}?" | yes ⇒ **residual cue** (localizes evidence to the edited pixels) |
| two_step | `mech_2step` | edited | "Describe, then yes/no" | confident description of absent target ⇒ anchoring |
| context_suppression | `mech_ctxsupp` | edited | "Answer from pixels only, not scene context…" | still yes ⇒ not mere prompt framing |
| original_vs_edited | `mech_origvsedit` | **two images** | "In which image is {target} visible?" | **BLOCKED** — needs a 2-image interface |

The `region_focused` family uses `bbox_xyxy` from `ade20k_masks.jsonl` (91/91 items have a
bbox); the crop is applied at inference time from `crop_spec`, so no image files are
duplicated on CPU.

## Why these dissociate the explanations

- **Scene-context anchoring** predicts failure in the full-image probes (object_list,
  two_step) but *recovery* in `region_focused` (no scene context in a tight crop).
- **Residual cue** predicts failure even in `region_focused` (the evidence is in the pixels).
- **Prompt prior / framing** predicts that `context_suppression` reduces the failure.

## Scoring (later, from real predictions only)

Each task carries a `scoring` spec (gold post-edit answer = the reviewed `answer_edited`,
plus a `flag_condition`). Scoring is performed **after** real predictions exist; this plan
records specs only and asserts no result. Distinct run labels keep each family's
predictions in their own scored report.

## Hard rules honored

- Probes are **not** marked evidence by default.
- The forced-comparison family is **blocked**, not faked (single-image interface).
- The generator **refuses** if the reviewed source tasks are missing or empty.

## Next step (only if you want to run probes)

See `notebooks/kaggle/07_mechanism_probes.md`. In short: point the existing T4×2 VLM
notebook at each family's `tasks.jsonl`, set the matching `run_label`, run per provider,
then score locally against the `scoring` specs.
