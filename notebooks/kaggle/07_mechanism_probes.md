# Kaggle runbook 07 — Mechanism probes (run later, free T4×2)

These probes test *why* the models fail to update (context anchoring vs residual cue vs
prompt prior). They are **not evidence** and are optional. Run only after the headline
3-model result is locked.

## Inputs (generated on CPU first)

```bash
python3 scripts/build_mechanism_probe_tasks.py
```

Per-family task manifests:
- `data/results/main_real_200/mechanism_probes/object_list/tasks.jsonl`        (`mech_objlist`)
- `data/results/main_real_200/mechanism_probes/region_focused/tasks.jsonl`     (`mech_region`)
- `data/results/main_real_200/mechanism_probes/two_step/tasks.jsonl`           (`mech_2step`)
- `data/results/main_real_200/mechanism_probes/context_suppression/tasks.jsonl`(`mech_ctxsupp`)

`original_vs_edited` is **blocked** (needs a two-image interface) — skip it.

## Steps (per provider: qwen2_5_vl_7b, internvl_8b, llava_onevision_7b)

1. Reuse the existing single-image eval notebook
   (`certvic_main200_vlm_T4x2_AFTER_GATES.ipynb` style). Add the probe `tasks.jsonl` and the
   `data/edits/main_real_200/` images as a Kaggle dataset.
2. For each task: load `edited_image_path` (basename remapped to the Kaggle dataset). For
   `mech_region`, crop to `crop_spec.bbox_xyxy` expanded by `margin_frac` **before** sending
   to the model.
3. Send `prompt`; capture the raw model text. Do **not** post-process into a verdict in the
   notebook — keep raw text so scoring is reproducible locally.
4. Save predictions as `…__pred_<provider>_<run_label>_merged.jsonl` with a `run_manifest.json`
   (model id, dtype, seed, commit), exactly like the main runs.

## Score locally (after predictions land)

Each task's `scoring` block gives the gold post-edit answer (`answer_edited`) and a
`flag_condition`. Compute, per family per provider: flag-rate (anchoring/residual signal),
agreement with the reviewed gold, and parse-failure rate. Compare across families using the
dissociation logic in `docs/MAIN200_MECHANISM_PROBES_PLAN.md`. Keep
`evidence_status = MECHANISM_PROBE_NON_EVIDENCE` until/unless the evidence gates say otherwise.

## Cost

Zero. Free Kaggle T4×2 only; no paid APIs, no paid storage. ~91 items × 4 families × 3
models is a small inference load (well within a free session).
