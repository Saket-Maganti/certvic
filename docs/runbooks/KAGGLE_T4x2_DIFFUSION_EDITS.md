# GPU Session 1 — Diffusion edits on Kaggle T4×2

Generate the **168 photorealistic single-factor edits** the pilot needs, running
**two workers in parallel** (GPU 0 → shard 0, GPU 1 → shard 1) inside one T4×2
notebook. Inputs are the CPU-produced edit-plan shards; outputs feed the CPU
detectability gate.

- **Stage:** `edit_generation` · **GPU:** required (2× T4 16 GB) · **Evidence:** `GENERATED_EDIT_ONLY`
- **Edit realism is the make-or-break risk.** Crude CPU edits already scored
  detectability **AUC 0.92 (NO_GO)**. These diffusion edits must clear **AUC < 0.80**
  on the CPU gate (next stage) or VLM eval stays blocked. Expect to iterate prompts.

---

## 0. Why this is a notebook, not a repo command

`certvic.edit.generate_edits --mode diffusers_inpaint` and the
`diffusers_inpaint_optional` engine are deliberate **stubs** — they validate the
plan, then raise (no weights are ever auto-downloaded). This runbook fills the one
missing function, `certvic.edit.engines._diffusers_inpaint`, with a real
implementation and then calls CertVIC's **own** `batch_generate`, so resume,
de-duplication, the quality gates, replay-metadata hashing and the manifest schema
are all reused unchanged.

---

## 1. Kaggle setup

1. New Notebook → Settings → **Accelerator: GPU T4 ×2** → **Internet: Off**.
2. **Add Data** (three read-only input datasets):
   - **ADE20K** — upload `ADEChallengeData2016/` (or just `images/` + `annotations/`).
     Mounts at e.g. `/kaggle/input/ade20k/ADEChallengeData2016`.
   - **Weights** — a pre-cached HF inpainting model dir (no download at run time),
     e.g. `stabilityai/stable-diffusion-2-inpainting` snapshot. Mounts at e.g.
     `/kaggle/input/sd2-inpaint`. *(SD-2-inpaint fp16 ≈ 5 GB, fits one T4.)*
   - **certvic** — upload the prebuilt bundle (no git, no pixels, no weights):
     ```bash
     # run locally, then upload dist/certvic_kaggle_main200_bundle.zip as a Kaggle dataset
     python3 -m scripts.build_kaggle_main200_bundle
     python3 -m certvic.security.audit_kaggle_bundle \
       --bundle dist/certvic_kaggle_main200_bundle.zip --strict \
       --out docs/KAGGLE_BUNDLE_SECURITY_AUDIT.md \
       --json-out data/results/kaggle_bundle_security_audit.json
     ```
     Mounts at e.g. `/kaggle/input/certvic`. Bundled planning manifests use the
     `__ADE20K_ROOT__` token (no private paths); the remap below swaps it for the mount.

## 2. Notebook cell — environment + path remap

```python
import os, sys, shutil, json, subprocess
from pathlib import Path

# --- mounts (edit slugs to match your Kaggle datasets) ---
CERTVIC = "/kaggle/input/certvic"                  # the uploaded bundle
WEIGHTS = "/kaggle/input/sd2-inpaint"              # local/cached diffusers snapshot
# Set ADE20K_ROOT to the real mount (README step 4-5). Auto-detect if you forget:
import glob
ADE20K_ROOT = os.environ.get("ADE20K_ROOT") or next(
    iter(glob.glob("/kaggle/input/**/ADEChallengeData2016", recursive=True)), None)
assert ADE20K_ROOT, "Attach an ADE20K dataset and set ADE20K_ROOT (see README step 5)."

WORK = Path("/kaggle/working"); (WORK/"edits").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, CERTVIC)                        # import certvic without pip install
# diffusers/torch are preinstalled on Kaggle GPU images; if not: pip install (internet on only for this).

# --- copy the two shard plans into /kaggle/working and remap the baked-in token/path ---
shard_src = f"{CERTVIC}/data/results/main_real_200/gpu_shards"
# Bundled manifests carry the "__ADE20K_ROOT__" token; un-sanitized ones carry a real
# prefix. Detect either (everything before "/images/") and swap it for the mount:
_r0 = json.loads(open(f"{shard_src}/pilot_edit_plan_shard0_of_2.jsonl").readline())
LOCAL_ROOT = os.environ.get("CERTVIC_LOCAL_ADE20K_ROOT") or _r0["image_path"].split("/images/")[0]
print("remap:", LOCAL_ROOT, "->", ADE20K_ROOT)

def remap_plan(src, dst):
    rows = [json.loads(l) for l in open(src) if l.strip()]
    for r in rows:
        for k in ("image_path", "mask_path", "original_image_path", "annotation_path"):
            if r.get(k):
                r[k] = r[k].replace(LOCAL_ROOT, ADE20K_ROOT)
    with open(dst, "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    return len(rows)

for i in (0, 1):
    n = remap_plan(f"{shard_src}/pilot_edit_plan_shard{i}_of_2.jsonl", str(WORK/f"plan_shard{i}.jsonl"))
    print(f"shard {i}: {n} edits, paths remapped")
```

## 3. Notebook cell — the real inpainting engine (the only new code)

```python
import numpy as np, torch, random
from PIL import Image, ImageFilter
from diffusers import StableDiffusionInpaintPipeline
import certvic.edit.engines as engines

# One pipeline per process; CUDA_VISIBLE_DEVICES (set per worker) pins it to one T4.
_PIPE = None
def _pipe():
    global _PIPE
    if _PIPE is None:
        p = StableDiffusionInpaintPipeline.from_pretrained(WEIGHTS, torch_dtype=torch.float16, safety_checker=None)
        p = p.to("cuda"); p.set_progress_bar_config(disable=True)
        _PIPE = p
    return _PIPE

# Per-edit-type prompt. THIS is the realism lever to tune against the detectability gate.
def _prompt_for(plan):
    label = plan.get("label_name") or "object"
    et = plan.get("edit_type")
    if et == "remove":            return (f"empty background where the {label} was, photorealistic, consistent lighting", "the {label}, object, artifacts")
    if et == "occlude":           return (f"a plain cardboard box partially covering the {label}, photorealistic", "")
    if et == "displace":          return (f"empty background, the {label} removed, photorealistic", "")  # source-side removal; see note
    if et == "control_irrelevant":return (f"the same scene with a repainted wall, the {label} unchanged", "")
    return (f"photorealistic edited region", "")

def real_diffusers_inpaint(image, mask, plan, rng, seed):
    """Drop-in for engines._diffusers_inpaint: returns (edited_PIL, actual_params)."""
    pipe = _pipe()
    # certvic gives `mask` as a bool/uint8 array aligned to the image; diffusers wants white=inpaint.
    m = Image.fromarray((np.asarray(mask) > 0).astype("uint8") * 255, mode="L")
    m = m.filter(ImageFilter.MaxFilter(7))        # dilate a touch so edges blend
    W, H = image.size
    base = image.convert("RGB").resize((512, 512))
    mres = m.resize((512, 512))
    prompt, negative = _prompt_for(plan)
    g = torch.Generator(device="cuda").manual_seed(seed)
    out = pipe(prompt=prompt, negative_prompt=negative or None, image=base, mask_image=mres,
               num_inference_steps=30, guidance_scale=7.5, generator=g).images[0]
    edited = out.resize((W, H))
    return edited, {"operation": "diffusers_inpaint", "model": WEIGHTS, "prompt": prompt,
                    "steps": 30, "guidance_scale": 7.5, "seed": seed}

# Patch the single stub. ALL other batch logic (resume, dedup, quality, replay) is reused.
engines._diffusers_inpaint = real_diffusers_inpaint
print("patched engines._diffusers_inpaint ->", engines._diffusers_inpaint.__name__)
```

> **`displace` note.** True displacement (move the object elsewhere) needs
> cut-paste + source inpaint, not inpaint alone. The stub above only removes at the
> source. Decide per your task design whether displace stays in the pilot or is
> approximated; the visual-review + detectability gates will flag bad ones.

## 4. Notebook cell — run both GPUs in parallel (`gpu0 → session 1`, `gpu1 → session 2`)

Write a tiny worker script, then launch one process per GPU and `wait`:

```python
worker = r'''
import os, sys, json
sys.path.insert(0, os.environ["CERTVIC"])
exec(open(os.environ["ENGINE_PATCH"]).read())   # defines + patches real_diffusers_inpaint
import certvic.edit.engines as engines
shard = int(os.environ["SHARD"])
summary = engines.batch_generate(
    edit_plan_path=f"/kaggle/working/plan_shard{shard}.jsonl",
    out_dir=f"/kaggle/working/edits/shard{shard}",
    out_manifest=f"/kaggle/working/generated_shard{shard}.jsonl",
    rejected_out=f"/kaggle/working/rejected_shard{shard}.jsonl",
    summary_out=f"/kaggle/working/gen_summary_shard{shard}.json",
    engine="diffusers_inpaint_optional",
    max_items=1000, seed=0, resume=True, fail_fast=False,
)
print("shard", shard, json.dumps(summary))
'''
open("/kaggle/working/worker.py","w").write(worker)
# Save the cell-3 engine code to a file so each worker process re-applies the patch:
# (paste cell 3's body into /kaggle/working/engine_patch.py, or write it the same way)

import subprocess, os
def launch(gpu, shard):
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(gpu), "SHARD": str(shard),
           "CERTVIC": CERTVIC, "WEIGHTS": WEIGHTS, "ADE20K_ROOT": ADE20K_ROOT,
           "ENGINE_PATCH": "/kaggle/working/engine_patch.py"}
    return subprocess.Popen([sys.executable, "/kaggle/working/worker.py"],
                            env=env, stdout=open(f"/kaggle/working/log_shard{shard}.txt","w"),
                            stderr=subprocess.STDOUT)

p0 = launch(gpu=0, shard=0)   # Session 1 → GPU 0 → shard 0 (81 edits)
p1 = launch(gpu=1, shard=1)   # Session 2 → GPU 1 → shard 1 (87 edits)
p0.wait(); p1.wait()
print("both GPUs done"); print(open("/kaggle/working/log_shard0.txt").read()[-500:])
```

> Put cell 3's body (imports through the `engines._diffusers_inpaint = ...` patch)
> into `/kaggle/working/engine_patch.py` so each worker subprocess applies it. Each
> worker writes to its **own** manifest/out-dir — no cross-GPU write races.

## 5. Merge + sanity-check + download

```python
import json, glob, hashlib
merged = []
for s in (0, 1):
    merged += [json.loads(l) for l in open(f"/kaggle/working/generated_shard{s}.jsonl")]
with open("/kaggle/working/pilot_generated_edits.jsonl","w") as f:
    for r in merged: f.write(json.dumps(r)+"\n")
print("total generated:", len(merged),
      "| quality pass:", sum(r.get("quality_gate_status")=="pass" for r in merged))
# zip edited PNGs + manifest for download back to the Mac:
import shutil; shutil.make_archive("/kaggle/working/diffusion_out", "zip", "/kaggle/working", "edits")
```

Download `pilot_generated_edits.jsonl` + `diffusion_out.zip` (the edited PNGs) from
the Kaggle output panel.

## 6. Resume after a session dies

Re-open the notebook and re-run cells 2–4. `batch_generate(resume=True)` reads each
shard's existing manifest and **skips finished `edit_id`s**, so only the remainder
runs. For shard-level accounting use the queue:
```bash
python3 -m certvic.edit.diffusion_resume \
  --queue data/results/main_real_200/diffusion_job_queue.jsonl \
  --generated data/results/main_real_200/pilot_generated_edits.jsonl \
  --out data/results/main_real_200/diffusion_resume.jsonl
```

## 7. Back on the Mac — the detectability gate (decides whether VLM eval may start)

Unzip the edited PNGs under `data/edits/main_real_200/`, drop
`pilot_generated_edits.jsonl` into `data/results/main_real_200/`, then:

```bash
D=data/results/main_real_200
python3 -m certvic.edit.quality_report --generated-manifest $D/pilot_generated_edits.jsonl \
  --rejected $D/pilot_generated_rejected.jsonl --out-dir $D/tiny_edit_quality_report
python3 -m certvic.data.materialize_tasks --task-preview $D/pilot_task_preview.jsonl \
  --generated-edits $D/pilot_generated_edits.jsonl --out $D/pilot_eval_tasks_tiny.jsonl \
  --summary-out $D/pilot_eval_tasks_tiny_summary.json
python3 -m certvic.validation.edit_detectability --tasks $D/pilot_eval_tasks_tiny.jsonl \
  --out-dir $D/edit_detectability
python3 -m certvic.pipeline.tiny_pilot_go_no_go --detectability $D/edit_detectability \
  --quality $D/tiny_edit_quality_report --out docs/MAIN200_GO_NO_GO.md \
  --json-out $D/go_no_go.json
```

- **GO (AUC < 0.80):** proceed to human review, then GPU Session 2.
- **NO_GO (AUC ≥ 0.80):** edits are still artifact-detectable — tune prompts/masks
  in cell 3 and regenerate the flagged items. **Do not start VLM eval.**

→ Next: [`KAGGLE_T4x2_VLM_EVAL.md`](KAGGLE_T4x2_VLM_EVAL.md)
