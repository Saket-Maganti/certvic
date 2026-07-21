# Specificity (spurious-flip) + scaled/held-out perception controls

Two CPU-built, ground-truth controls that strengthen the pilot. No diffusion, no human
review, no paid anything. Each is `no_change` pairs in the strict `TaskItem` schema, so the
existing self-download notebooks run them with the model already loaded.

## What they are

| control | builder | what it shows |
|---|---|---|
| **spurious-flip (specificity)** | `scripts/build_spurious_flip_control.py` (94 items) | object-present images; the "edited" arm has an **irrelevant** blur+jitter patch in an **object-free** region (object pixels untouched, verified diff=0). Gold answer stays "yes". A low **spurious-flip rate** (gate ≤ 0.10) means the certified gap is *specific* to object-removing edits, not sensitivity to any pixel change. |
| **scaled + held-out perception** | `scripts/build_absent_object_control.py --split validation --objects ext` (369 items) | the absent-object perception control at ~3× scale, **8 objects** (table/sofa/chair/car/bed/door/painting/plant), on the ADE20K **validation** split (unseen vs the training-split intervention). Shows the perception result replicates at scale on held-out images. |

Bundles: `dist/certvic_spurious_flip_control.zip`, `dist/certvic_perception_control_scaled.zip`.

## Run on each model (model already loaded in a self-download notebook)

After the model load + smoke cells have run, attach the control bundle as a Kaggle input and
paste this cell (it reuses the loaded+patched model — no reload). Set the two variables:

```python
import json, os
from certvic.eval.run_eval import run_eval
CTRL_INPUT = "/kaggle/input/<the-control-bundle>"     # dir with pilot_eval_tasks_reviewed.jsonl + imgs + orig/
NAME, PROVIDER = "spurious", "internvl_8b"             # NAME in {spurious, perception_scaled}; PROVIDER = the loaded model

rows = [json.loads(l) for l in open(f"{CTRL_INPUT}/pilot_eval_tasks_reviewed.jsonl")]
for r in rows:                                        # already nested TaskItem -> just remap paths
    r["original_image_path"] = f"{CTRL_INPUT}/orig/{os.path.basename(r['original_image_path'])}"
    r["edited_image_path"]   = f"{CTRL_INPUT}/{os.path.basename(r['edited_image_path'])}"
open(f"/kaggle/working/tasks_{NAME}.jsonl", "w").writelines(json.dumps(r) + "\n" for r in rows)
_PROG["n"], _PROG["tag"], _PROG["t0"] = 0, NAME, None
print(run_eval(config_path=CFG, tasks_path=f"/kaggle/working/tasks_{NAME}.jsonl",
               out_path=f"/kaggle/working/pred_{PROVIDER}_{NAME}_merged.jsonl",
               provider_name=PROVIDER, run_id=f"main200_{PROVIDER}_{NAME}",
               num_shards=1, strict_leakage=True, evidence_run=True, overwrite=False))
```

Download `pred_<provider>_{spurious,perception_scaled}_merged.jsonl`. (~190 spurious + ~740
scaled generations per model; minutes on the bf16 path.)

## Ingest locally (folds into the same per-model report)

```bash
cd /path/to/certVIC
python3 scripts/pilot_report_from_raw.py \
  --provider internvl_8b --model-name OpenGVLab/InternVL2-8B --run-label internvl_8b \
  --raw-presence <pred_..._presence_merged.jsonl> \
  --raw-control  <pred_..._control_merged.jsonl> \
  --raw-spurious <pred_internvl_8b_spurious_merged.jsonl> \
  --raw-perception-scaled <pred_internvl_8b_perception_scaled_merged.jsonl>
```

This adds `spurious_flip_control` (rate + `≤0.10` gate) and `perception_control_scaled`
(absent/present accuracy, held-out) to that model's `pilot_result.{md,json}`, and the
spurious-flip column to `multimodel_pilot_summary`. The report also now reports a
**positive-only presence subset** automatically (negated questions dropped) — confirming the
gap is not a phrasing artifact.

Pilot-only throughout; ground-truth labels; no gates weakened; raw image pixels not redistributed.
