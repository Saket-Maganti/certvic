"""Generate the Kaggle T4x2 .ipynb runbooks for the CertVIC main-200 pilot.

Two notebooks, matching docs/runbooks/*.md:
  - certvic_main200_diffusion_T4x2.ipynb       (next step: diffusion edits)
  - certvic_main200_vlm_T4x2_AFTER_GATES.ipynb (blocked until gates pass)

Each runs two workers in parallel, one pinned per T4 (CUDA_VISIBLE_DEVICES 0/1),
on disjoint shards, then merges. No private paths: ADE20K_ROOT is read from env or
auto-detected; the bundled plans carry the __ADE20K_ROOT__ token. Built with
nbformat so the JSON is always valid. CPU-only generation; runs no GPU here.
"""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

OUT_DIR = Path(__file__).resolve().parents[1] / "notebooks" / "kaggle"

NB_META = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
    "accelerator": "GPU",
}

# ----------------------------------------------------------------------------- diffusion
DIFF_CELLS = [
    new_markdown_cell(
        "# CertVIC main-200 — Diffusion edits (Kaggle T4×2)\n\n"
        "Generates the **168 photorealistic single-factor edits** of the pilot. Two\n"
        "workers run in parallel — **GPU 0 → shard 0 (81)**, **GPU 1 → shard 1 (87)**.\n\n"
        "**Settings:** Accelerator = **GPU T4 ×2**. **Internet = On for run 1** (to fetch\n"
        "the open SD-2-inpaint weights), or **Off** if you pre-cached them as a dataset\n"
        "(`00_precache_weights.ipynb`). The weights cell finds a mounted snapshot if present,\n"
        "else downloads the free model automatically.\n\n"
        "**This notebook does NOT run VLM inference.** VLM eval is a separate notebook,\n"
        "blocked until quality + detectability (AUC < 0.80) + human review + item\n"
        "certificates pass.\n\n"
        "**Estimated runtime (T4×2):** model load ~1–2 min; generation ~10–15 min\n"
        "(~84 edits/GPU at ~6–8 s each, in parallel). Single-T4 would be ~20–25 min."
    ),
    new_markdown_cell(
        "## 1. Attach inputs (Add Data)\n"
        "- **certvic** — this bundle (`certvic_kaggle_main200_bundle.zip`); Kaggle mounts it at\n"
        "  `/kaggle/input/<your-slug>/` and the setup cell **auto-detects** it (slug can be anything).\n"
        "- **ADE20K** — a dataset containing `ADEChallengeData2016/{images,annotations}/...`.\n"
        "- **weights (recommended)** — click **+ Add Input → Models** and add the non-gated\n"
        "  mirror **`kaggle.com/refs/hf-model/stable-diffusion-v1-5/stable-diffusion-inpainting`**\n"
        "  (no HF token, runs **Internet OFF**). The weights cell auto-detects its\n"
        "  `model_index.json`. *Alternatives:* skip it and the cell downloads the same model\n"
        "  on first run (Internet ON); or set `HF_TOKEN` + `SD_MODEL_ID` for a gated repo\n"
        "  (a **401** just means the repo you picked is gated).\n\n"
        "Then set `ADE20K_ROOT` (next cell auto-detects if you forget)."
    ),
    new_code_cell(
        r'''# Dependency check (Kaggle GPU images usually ship these). If MISSING, enable
# Internet briefly and run:  %pip install -q diffusers transformers accelerate safetensors
import importlib.util
for m in ("torch", "diffusers", "huggingface_hub", "PIL", "numpy"):
    print(m, "OK" if importlib.util.find_spec(m) else "MISSING -> %pip install")'''
    ),
    new_code_cell(
        r'''# --- mounts + path remap (no hardcoded private paths) ---
import os, sys, json, glob
from pathlib import Path

# Find the bundle wherever Kaggle mounted it (the dataset slug is derived from its
# title, not necessarily "certvic"; an un-extracted .zip is handled too).
def find_certvic():
    hits = glob.glob("/kaggle/input/**/main_real_200/gpu_shards/pilot_edit_plan_shard0_of_2.jsonl", recursive=True)
    if hits:
        return hits[0].split("/data/results/")[0]
    zips = glob.glob("/kaggle/input/**/certvic_kaggle_main200_bundle.zip", recursive=True)
    if zips:
        import zipfile
        with zipfile.ZipFile(zips[0]) as z:
            z.extractall("/kaggle/working/certvic_bundle")
        return "/kaggle/working/certvic_bundle"
    raise FileNotFoundError("Attach the certvic bundle dataset (must contain data/results/main_real_200/...).")
CERTVIC = find_certvic()
print("CERTVIC:", CERTVIC)

# Weights resolution (best first): a mounted Kaggle snapshot needs no HF call at all.
# Default download id is a NON-GATED inpaint mirror so no token is required; override
# with env SD_MODEL_ID, and pass HF_TOKEN (Kaggle Add-ons > Secrets) for gated repos.
SD_MODEL_ID = os.environ.get("SD_MODEL_ID", "stable-diffusion-v1-5/stable-diffusion-inpainting")
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

def resolve_sd_weights():
    explicit = os.environ.get("SD_WEIGHTS")
    if explicit and os.path.exists(explicit):
        return explicit                                  # exact mount path, if you set SD_WEIGHTS
    hits = glob.glob("/kaggle/input/**/model_index.json", recursive=True)
    if hits:
        return os.path.dirname(hits[0])                  # any mounted diffusers snapshot (e.g. the Kaggle model)
    cached = "/kaggle/working/sd-inpaint"
    if os.path.exists(cached + "/model_index.json"):
        return cached                                    # already fetched this session
    from huggingface_hub import snapshot_download
    try:
        return snapshot_download(SD_MODEL_ID, local_dir=cached, token=HF_TOKEN, ignore_patterns=["*.ckpt"])
    except Exception as e:
        raise RuntimeError(
            f"No mounted weights and download of '{SD_MODEL_ID}' failed ({type(e).__name__}). Do ANY one: "
            "(0) BEST - click '+ Add Input' > Models and add the non-gated Kaggle mirror "
            "kaggle.com/refs/hf-model/stable-diffusion-v1-5/stable-diffusion-inpainting "
            "(no token, runs Internet OFF); this cell then auto-detects it. "
            "(1) Or set env SD_WEIGHTS to its exact /kaggle/input/... path. "
            "(2) Or for a gated repo, set HF_TOKEN (Add-ons > Secrets) + SD_MODEL_ID.") from e

WEIGHTS = resolve_sd_weights()
print("WEIGHTS:", WEIGHTS)

ADE20K_ROOT = os.environ.get("ADE20K_ROOT") or next(
    iter(glob.glob("/kaggle/input/**/ADEChallengeData2016", recursive=True)), None)
assert ADE20K_ROOT, "Attach an ADE20K dataset and set ADE20K_ROOT."
os.environ["ADE20K_ROOT"] = ADE20K_ROOT
sys.path.insert(0, CERTVIC)

WORK = Path("/kaggle/working"); (WORK / "edits").mkdir(parents=True, exist_ok=True)
shard_src = f"{CERTVIC}/data/results/main_real_200/gpu_shards"
# Detect the baked-in prefix (the __ADE20K_ROOT__ token in the bundle) and swap for the mount:
_r0 = json.loads(open(f"{shard_src}/pilot_edit_plan_shard0_of_2.jsonl").readline())
LOCAL_ROOT = os.environ.get("CERTVIC_LOCAL_ADE20K_ROOT") or _r0["image_path"].split("/images/")[0]

def remap(src, dst):
    rows = [json.loads(l) for l in open(src) if l.strip()]
    for r in rows:
        for k in ("image_path", "mask_path", "original_image_path", "annotation_path"):
            if r.get(k):
                r[k] = r[k].replace(LOCAL_ROOT, ADE20K_ROOT)
    open(dst, "w").writelines(json.dumps(r) + "\n" for r in rows)
    return len(rows)

for i in (0, 1):
    n = remap(f"{shard_src}/pilot_edit_plan_shard{i}_of_2.jsonl", str(WORK / f"plan_shard{i}.jsonl"))
    print(f"shard {i}: {n} edits remapped  {LOCAL_ROOT} -> {ADE20K_ROOT}")'''
    ),
    new_code_cell(
        r'''%%writefile /kaggle/working/engine_patch.py
# Real diffusion-inpaint engine, patched onto certvic.edit.engines._diffusers_inpaint.
# Tune _prompt_for / steps to pass the CPU detectability gate (AUC < 0.80).
import os, numpy as np, torch
from PIL import Image, ImageFilter
from diffusers import StableDiffusionInpaintPipeline
import certvic.edit.engines as engines

WEIGHTS = os.environ["WEIGHTS"]
_PIPE = None
def _pipe():
    global _PIPE
    if _PIPE is None:
        try:                                            # prefer the smaller fp16 variant
            p = StableDiffusionInpaintPipeline.from_pretrained(WEIGHTS, torch_dtype=torch.float16, variant="fp16", safety_checker=None)
        except Exception:                                # else default precision (also handles HF-id download)
            p = StableDiffusionInpaintPipeline.from_pretrained(WEIGHTS, torch_dtype=torch.float16, safety_checker=None)
        _PIPE = p.to("cuda"); _PIPE.set_progress_bar_config(disable=True)
    return _PIPE

def _prompt_for(plan):
    label = plan.get("label_name") or "object"
    et = plan.get("edit_type")
    if et == "remove":             return (f"empty background where the {label} was, photorealistic, consistent lighting", f"the {label}, object, artifacts")
    if et == "occlude":            return (f"a plain cardboard box partially covering the {label}, photorealistic", "")
    if et == "displace":           return (f"empty background, the {label} removed, photorealistic", "")
    if et == "control_irrelevant": return (f"the same scene with a repainted wall, the {label} unchanged", "")
    return ("photorealistic edited region", "")

def real_diffusers_inpaint(image, mask, plan, rng, seed):
    pipe = _pipe()
    exact = (np.asarray(mask) > 0).astype("uint8") * 255
    m = Image.fromarray(exact).filter(ImageFilter.MaxFilter(7))   # dilate for the inpaint only
    W, H = image.size
    base = image.convert("RGB").resize((512, 512)); mres = m.resize((512, 512))
    prompt, negative = _prompt_for(plan)
    g = torch.Generator(device="cuda").manual_seed(seed)
    out = pipe(prompt=prompt, negative_prompt=negative or None, image=base, mask_image=mres,
               num_inference_steps=30, guidance_scale=7.5, generator=g).images[0].resize((W, H))
    # Composite: keep ORIGINAL pixels OUTSIDE the object mask -> a true single-factor edit.
    # (Without this the VAE round-trip changes the whole image and fails the single-factor gate.)
    edited = Image.composite(out, image.convert("RGB"), Image.fromarray(exact))
    return edited, {"operation": "diffusers_inpaint_composited", "model": WEIGHTS,
                    "prompt": prompt, "steps": 30, "guidance_scale": 7.5, "seed": seed}

engines._diffusers_inpaint = real_diffusers_inpaint
print("patched engines._diffusers_inpaint")'''
    ),
    new_code_cell(
        r'''%%writefile /kaggle/working/worker.py
# One worker = one shard on one GPU. Reuses certvic.batch_generate (resume, dedup,
# quality gates, replay metadata, manifest schema) — only the engine is new.
import os, sys, json
sys.path.insert(0, os.environ["CERTVIC"])
exec(open("/kaggle/working/engine_patch.py").read())
import certvic.edit.engines as engines
shard = int(os.environ["SHARD"])
summary = engines.batch_generate(
    edit_plan_path=f"/kaggle/working/plan_shard{shard}.jsonl",
    out_dir=f"/kaggle/working/edits/shard{shard}",
    out_manifest=f"/kaggle/working/generated_shard{shard}.jsonl",
    rejected_out=f"/kaggle/working/rejected_shard{shard}.jsonl",
    summary_out=f"/kaggle/working/gen_summary_shard{shard}.json",
    engine="diffusers_inpaint_optional", max_items=1000, seed=0, resume=True, fail_fast=False)
print("shard", shard, json.dumps(summary))'''
    ),
    new_code_cell(
        r'''# --- launch GPU0 (shard0) + GPU1 (shard1) in parallel, with LIVE progress ---
# Worker output goes to log files; this cell polls the edited-PNG count every 20s so
# you can SEE it working (no output for ~1-2 min at first = model loading, not a hang).
import os, sys, time, glob, subprocess
EXPECT = {s: sum(1 for _ in open(f"/kaggle/working/plan_shard{s}.jsonl")) for s in (0, 1)}
def launch(gpu, shard):
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(gpu), "SHARD": str(shard),
           "CERTVIC": CERTVIC, "WEIGHTS": WEIGHTS, "ADE20K_ROOT": ADE20K_ROOT, "PYTHONUNBUFFERED": "1"}
    return subprocess.Popen([sys.executable, "-u", "/kaggle/working/worker.py"], env=env,
                            stdout=open(f"/kaggle/working/log_shard{shard}.txt", "w"),
                            stderr=subprocess.STDOUT)

procs = {0: launch(0, 0), 1: launch(1, 1)}       # GPU0 -> shard0, GPU1 -> shard1
t0 = time.time()
print(f"launched: GPU0={EXPECT[0]} edits, GPU1={EXPECT[1]} edits | first PNGs after ~1-2 min model load", flush=True)
while any(p.poll() is None for p in procs.values()):
    time.sleep(20)
    line = []
    for s in (0, 1):
        n = len(glob.glob(f"/kaggle/working/edits/shard{s}/*.png"))
        line.append(f"GPU{s} {n}/{EXPECT[s]} {'run' if procs[s].poll() is None else 'done'}")
    print(f"[{int(time.time()-t0):4d}s] " + " | ".join(line), flush=True)
for s in (0, 1):
    print(f"--- shard{s} log tail ---\n" + open(f"/kaggle/working/log_shard{s}.txt").read()[-600:])'''
    ),
    new_code_cell(
        r'''# --- merge shards + package edits + MANIFEST + summaries into ONE zip ---
import json, os, glob, zipfile
merged = []
for s in (0, 1):
    merged += [json.loads(l) for l in open(f"/kaggle/working/generated_shard{s}.jsonl")]
with open("/kaggle/working/pilot_generated_edits.jsonl", "w") as f:
    for r in merged:
        f.write(json.dumps(r) + "\n")
print("total generated:", len(merged),
      "| quality pass:", sum(r.get("quality_gate_status") == "pass" for r in merged))
with zipfile.ZipFile("/kaggle/working/diffusion_out.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.write("/kaggle/working/pilot_generated_edits.jsonl", "pilot_generated_edits.jsonl")
    for s in (0, 1):
        gs = f"/kaggle/working/gen_summary_shard{s}.json"
        if os.path.exists(gs):
            z.write(gs, f"gen_summary_shard{s}.json")
        for png in glob.glob(f"/kaggle/working/edits/shard{s}/*.png"):
            z.write(png, os.path.relpath(png, "/kaggle/working"))   # -> edits/shardN/<id>.png
print("DOWNLOAD just diffusion_out.zip — it now contains edits/ + pilot_generated_edits.jsonl + summaries")'''
    ),
    new_markdown_cell(
        "## Back on the Mac — run the gate (decides whether VLM may start)\n"
        "Unzip `diffusion_out.zip` into `data/edits/main_real_200/`, drop\n"
        "`pilot_generated_edits.jsonl` into `data/results/main_real_200/`, then run\n"
        "quality + `certvic.validation.edit_detectability` + `tiny_pilot_go_no_go`.\n"
        "**GO only if AUC < 0.80.** See `docs/runbooks/KAGGLE_T4x2_DIFFUSION_EDITS.md` §7."
    ),
]

# ----------------------------------------------------------------------------- VLM (after gates)
VLM_CELLS = [
    new_markdown_cell(
        "# CertVIC main-200 — Open-VLM eval (Kaggle T4×2) — AFTER GATES ONLY\n\n"
        "> **Do not run until ALL pass:** quality gates · detectability **AUC < 0.80** ·\n"
        "> human review (`pilot_eval_tasks_reviewed.jsonl`) · item certificates.\n"
        "> `run_eval --evidence-run` refuses unreviewed tasks and non-open-local providers.\n\n"
        "Two workers in parallel — **GPU 0 → shard 0**, **GPU 1 → shard 1** — per provider.\n\n"
        "**Estimated runtime (T4×2):** ~10–15 min for 1 provider — 4-bit load ~2–3 min, then\n"
        "~103 task-pairs (206 inferences) split over the 2 GPUs at ~3–4 s each. Each extra\n"
        "provider adds ~10–15 min."
    ),
    new_markdown_cell(
        "## Attach inputs\n"
        "- **certvic** bundle (this `.zip`) — auto-detected wherever it mounts.\n"
        "- **edits dataset** — upload `data/edits/main_real_200/` (it holds `<id>.jpg` + `orig/<id>.jpg`)\n"
        "  and drop `pilot_eval_tasks_reviewed.jsonl` beside it. Both original and edited images\n"
        "  live here now (re-encoded identically by the local ingest — no separate ADE20K needed).\n"
        "- **VLM weights** — a Kaggle Model ref or open HF id (the launch cell fetches it; set\n"
        "  `HF_TOKEN` in Add-ons > Secrets only if you pick a gated model).\n\n"
        "Settings: **GPU T4 ×2**, **Internet = On** for run 1 (weights download)."
    ),
    new_code_cell(
        r'''# --- deps + bundle/reviewed-tasks discovery + path remap (all slug-agnostic) ---
import os, sys, json, glob, importlib.util
from pathlib import Path

# VLM deps. bitsandbytes is REQUIRED (4-bit) to fit a 7B VLM on a 14.5 GB T4 -> install if absent.
import subprocess
_missing = [m for m in ("accelerate", "bitsandbytes") if importlib.util.find_spec(m) is None]
if _missing:
    print("installing", _missing, "(needs Internet On)...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", *_missing], check=False)
    importlib.invalidate_caches()
for m in ("torch", "transformers", "accelerate", "bitsandbytes"):
    print(m, "OK" if importlib.util.find_spec(m) else "MISSING -> %pip install -U " + m)

def find_certvic():
    h = glob.glob("/kaggle/input/**/main_real_200/gpu_shards/pilot_edit_plan_shard0_of_2.jsonl", recursive=True)
    if h:
        return h[0].split("/data/results/")[0]
    z = glob.glob("/kaggle/input/**/certvic_kaggle_main200_bundle.zip", recursive=True)
    if z:
        import zipfile
        with zipfile.ZipFile(z[0]) as zf:
            zf.extractall("/kaggle/working/certvic_bundle")
        return "/kaggle/working/certvic_bundle"
    r = glob.glob("/kaggle/input/**/README_KAGGLE_BUNDLE.md", recursive=True)
    if r:
        return os.path.dirname(r[0])
    raise FileNotFoundError("Attach the certvic bundle dataset.")
CERTVIC = find_certvic(); sys.path.insert(0, CERTVIC)
WORK = Path("/kaggle/working")

_t = glob.glob("/kaggle/input/**/pilot_eval_tasks_reviewed.jsonl", recursive=True)
assert _t, "Add pilot_eval_tasks_reviewed.jsonl (produced AFTER human review)."
rows = [json.loads(l) for l in open(_t[0])]

# Both original (orig/<id>.jpg) and edited (<id>.jpg) live in the edits dataset. Detect the
# local edits root from the tasks and the Kaggle mount (dir that contains the 'orig' subdir):
LOCAL_EDITS = os.path.commonpath([rows[0]["original_image_path"], rows[0]["edited_image_path"]])
_o = glob.glob("/kaggle/input/**/orig", recursive=True)
EDITS_KAGGLE = os.environ.get("EDITS_ROOT") or (os.path.dirname(_o[0]) if _o else None)
assert EDITS_KAGGLE, "Attach the edits dataset (data/edits/main_real_200 with <id>.jpg + orig/<id>.jpg)."
for r in rows:
    for k in ("original_image_path", "edited_image_path"):
        if r.get(k):
            r[k] = r[k].replace(LOCAL_EDITS, EDITS_KAGGLE)
# run_eval loads the strict TaskItem schema (nested source+edit, extra=forbid). The
# materialized/reviewed rows are the richer preview format -> project them onto TaskItem.
if rows and "source" not in rows[0]:
    from certvic.schema import TaskItem
    from certvic.schema.edit import EditSpec
    from certvic.schema.source import SourceImageRecord
    def _to_taskitem(r):
        src = SourceImageRecord(source_id=r["source_id"], source_name="ADE20K", license_category="pointer_only")
        ed = EditSpec(edit_id=r["edit_id"], source_id=r["source_id"], edit_type=r["edit_type"],
                      task_family=r["task_family"], domain=r["domain"], expected_effect=r["expected_effect"])
        m = dict(r.get("metadata") or {}); m.setdefault("evidence_status", r.get("evidence_status", "HUMAN_REVIEWED_NON_EVIDENCE"))
        return TaskItem(item_id=r["item_id"], source=src, edit=ed,
                        original_image_path=r["original_image_path"], edited_image_path=r["edited_image_path"],
                        question_original=r["question_original"], question_edited=r["question_edited"],
                        answer_original=r["answer_original"], answer_edited=r["answer_edited"],
                        required_change=r["required_change"], answer_format=r["answer_format"],
                        task_family=r["task_family"], domain=r["domain"], split=r["split"], metadata=m)
    rows = [json.loads(_to_taskitem(r).model_dump_json()) for r in rows]
open(WORK / "tasks_reviewed.jsonl", "w").writelines(json.dumps(r) + "\n" for r in rows)
miss = sum(1 for r in rows for k in ("original_image_path", "edited_image_path") if not os.path.exists(r[k]))
ev = sorted({r.get("metadata", {}).get("evidence_status") or r.get("evidence_status") for r in rows})
print(len(rows), "reviewed tasks | missing images:", miss, "(must be 0) | evidence:", ev)'''
    ),
    new_code_cell(
        r'''%%writefile /kaggle/working/provider_patch.py
# Real VLM answer(), patched onto certvic OpenVLMProvider. run_eval keeps all
# leakage/evidence/resume logic; only model loading + generation are new.
import os, importlib.util, torch
from PIL import Image
import certvic.providers.open_vlm as ovlm
WEIGHTS = os.environ["WEIGHTS"]; PROVIDER = os.environ["PROVIDER"]

def _qwen():
    from transformers import AutoProcessor, BitsAndBytesConfig
    try:
        from transformers import Qwen2_5_VLForConditionalGeneration as Model
    except Exception:
        from transformers import AutoModelForImageTextToText as Model
    # 4-bit is REQUIRED on a 14.5 GB T4 (fp16 7B ~15 GB OOMs). Must go through
    # BitsAndBytesConfig -- the bare load_in_4bit kwarg is ignored in recent transformers.
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    model = Model.from_pretrained(WEIGHTS, device_map={"": 0},
                                  quantization_config=bnb, low_cpu_mem_usage=True)
    proc = AutoProcessor.from_pretrained(WEIGHTS, max_pixels=768 * 768)  # cap vision tokens -> less VRAM
    @torch.inference_mode()
    def answer(self, image_path, prompt):
        img = Image.open(image_path).convert("RGB")
        msgs = [{"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": prompt}]}]
        text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = proc(text=[text], images=[img], return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=16, do_sample=False)
        return proc.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    return answer

LOADERS = {"qwen2_5_vl_7b": _qwen}                        # add internvl_8b / llava_onevision_7b similarly
ovlm.OpenVLMProvider.load = lambda self: None
ovlm.OpenVLMProvider.answer = LOADERS[PROVIDER]()
print("patched OpenVLMProvider.answer for", PROVIDER)'''
    ),
    new_code_cell(
        r'''%%writefile /kaggle/working/worker_vlm.py
import os, sys
sys.path.insert(0, os.environ["CERTVIC"])
exec(open("/kaggle/working/provider_patch.py").read())
from certvic.eval.run_eval import main as run_eval_main
shard = int(os.environ["SHARD"]); provider = os.environ["PROVIDER"]
run_eval_main([
    "--config", f"{os.environ['CERTVIC']}/configs/kaggle_open_vlm.yaml",
    "--tasks", "/kaggle/working/tasks_reviewed.jsonl",
    "--out", f"/kaggle/working/pred_{provider}_shard{shard}.jsonl",
    "--provider", provider, "--run-id", f"main200_{provider}_shard{shard}",
    "--shard-index", str(shard), "--num-shards", "2",
    "--strict-leakage", "--evidence-run", "--fail-fast"])'''
    ),
    new_code_cell(
        r'''# --- per provider: GPU0 shard0 + GPU1 shard1 in parallel, with LIVE progress ---
import os, sys, time, glob, subprocess
PROVIDERS = {
    "qwen2_5_vl_7b": "Qwen/Qwen2.5-VL-7B-Instruct",    # mounted dir OR open HF id
    # "internvl_8b": "OpenGVLab/InternVL2-8B",
    # "llava_onevision_7b": "llava-hf/llava-onevision-qwen2-7b-ov-hf",
}
_HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
def ensure_local(repo):
    if os.path.exists(repo):
        return repo
    hits = glob.glob(f"/kaggle/input/**/{repo.split('/')[-1]}*/config.json", recursive=True)
    if hits:
        return os.path.dirname(hits[0])                  # mounted snapshot (no HF call)
    from huggingface_hub import snapshot_download        # ~16 GB, Internet ON; HF_TOKEN if gated
    return snapshot_download(repo, local_dir=f"/kaggle/working/{repo.split('/')[-1]}", token=_HF_TOKEN)
PROVIDERS = {name: ensure_local(src) for name, src in PROVIDERS.items()}
print("resolved provider weights:", PROVIDERS, flush=True)
EXPECT = 2 * sum(1 for _ in open("/kaggle/working/tasks_reviewed.jsonl"))   # 2 variants/task

def run_shard(provider, weights, gpu, shard):
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(gpu), "SHARD": str(shard),
           "PROVIDER": provider, "WEIGHTS": weights, "CERTVIC": CERTVIC, "PYTHONUNBUFFERED": "1",
           "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}
    return subprocess.Popen([sys.executable, "-u", "/kaggle/working/worker_vlm.py"], env=env,
                            stdout=open(f"/kaggle/working/log_{provider}_s{shard}.txt", "w"),
                            stderr=subprocess.STDOUT)

for provider, weights in PROVIDERS.items():
    procs = {0: run_shard(provider, weights, 0, 0), 1: run_shard(provider, weights, 1, 1)}
    t0 = time.time()
    print(f"[{provider}] launched; 4-bit load ~2-3 min before first predictions", flush=True)
    while any(p.poll() is None for p in procs.values()):
        time.sleep(20)
        line = []
        for s in (0, 1):
            f = f"/kaggle/working/pred_{provider}_shard{s}.jsonl"
            n = sum(1 for _ in open(f)) if os.path.exists(f) else 0
            line.append(f"GPU{s} {n} preds {'run' if procs[s].poll() is None else 'done'}")
        print(f"[{int(time.time()-t0):4d}s {provider}] ~{EXPECT} total | " + " | ".join(line), flush=True)
    # Auto-recover: if a shard died (transient CUBLAS/OOM from launch-time contention),
    # retry it ALONE -- the other GPU is free now and run_eval resumes from what it wrote.
    for s in (0, 1):
        if procs[s].returncode not in (0, None):
            print(f"[{provider}] shard{s} exited {procs[s].returncode}; retrying alone (resume-safe)...", flush=True)
            rp = run_shard(provider, weights, s, s)
            while rp.poll() is None:
                time.sleep(20)
                f = f"/kaggle/working/pred_{provider}_shard{s}.jsonl"
                print(f"  retry shard{s}: {sum(1 for _ in open(f)) if os.path.exists(f) else 0} preds", flush=True)
            print(f"[{provider}] shard{s} retry exit {rp.returncode}", flush=True)
    for s in (0, 1):
        print(f"--- {provider} shard{s} log tail ---\n" + open(f"/kaggle/working/log_{provider}_s{s}.txt").read()[-500:])'''
    ),
    new_code_cell(
        r'''# --- merge predictions + package preds + logs + run-manifests into ONE zip ---
import os, zipfile
total = 0
for provider in PROVIDERS:
    merged = []
    for s in (0, 1):
        f = f"/kaggle/working/pred_{provider}_shard{s}.jsonl"
        if os.path.exists(f):
            lines = list(open(f)); merged += lines; total += len(lines)
        else:
            print("WARNING: no predictions from", f, "- check that shard's log below (likely OOM/load error).")
    open(f"/kaggle/working/pred_{provider}_merged.jsonl", "w").writelines(merged)
with zipfile.ZipFile("/kaggle/working/vlm_out.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in os.listdir("/kaggle/working"):
        if (f.startswith("pred_") and f.endswith(".jsonl")) or (f.startswith("log_") and f.endswith(".txt")) \
           or f.endswith(".run_manifest.json"):
            z.write(f"/kaggle/working/{f}", f)
print(f"predictions written: {total} | DOWNLOAD: vlm_out.zip (preds + logs + run manifests)")'''
    ),
    new_markdown_cell(
        "## Back on the Mac — score & certify\n"
        "Concatenate `pred_*_merged.jsonl` → `merged.jsonl`, then run\n"
        "`certvic.eval.output_triage`, `certvic.metrics.score_predictions`,\n"
        "`certvic.reporting.build_v2_report`. `score_summary.json` carries `a`, `p`,\n"
        "`Δ = a − p` and the anytime-valid CS. Certified claims only after all gates pass."
    ),
]


# ----------------------------------------------------------------------------- precache (one-time)
PRECACHE_CELLS = [
    new_markdown_cell(
        "# Pre-cache open weights (one-time, Internet ON, no GPU)\n\n"
        "Optional helper: download the **free, open** model weights into `/kaggle/working`,\n"
        "then **Output → Create Dataset** so the diffusion / VLM notebooks can attach them\n"
        "read-only (Internet OFF, deterministic, no re-download per session). Skip this if\n"
        "you let those notebooks fetch weights directly on first run.\n\n"
        "**Settings:** Internet = **On**; Accelerator = none (CPU is fine)."
    ),
    new_code_cell(r'''%pip install -q "huggingface_hub>=0.23"'''),
    new_code_cell(
        r'''# Diffusion inpaint weights (~2-5 GB). Default is a NON-GATED mirror (no token).
# For a gated model (e.g. stabilityai/stable-diffusion-2-inpainting): accept its license
# on huggingface.co, then set HF_TOKEN via Kaggle Add-ons > Secrets and SD_MODEL_ID below.
import os
from huggingface_hub import snapshot_download
SD_MODEL_ID = os.environ.get("SD_MODEL_ID", "stable-diffusion-v1-5/stable-diffusion-inpainting")
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
p = snapshot_download(SD_MODEL_ID, local_dir="/kaggle/working/sd-inpaint",
                      token=HF_TOKEN, ignore_patterns=["*.ckpt"])
print("saved ->", p, "| has model_index.json:", os.path.exists(p + "/model_index.json"))'''
    ),
    new_markdown_cell(
        "Now **Output → Create Dataset** from `/kaggle/working/sd-inpaint` and attach it to\n"
        "`certvic_main200_diffusion_T4x2.ipynb`. Its weights cell auto-detects any mounted\n"
        "`model_index.json`, so no code change is needed.\n\n"
        "**No HF account / hit a 401?** Skip downloading entirely: in the diffusion notebook\n"
        "click **+ Add Input → Models** and add\n"
        "**`kaggle.com/refs/hf-model/stable-diffusion-v1-5/stable-diffusion-inpainting`** —\n"
        "it mounts read-only (no token, Internet OFF) and the weights cell auto-detects it."
    ),
    new_code_cell(
        r'''# OPTIONAL - VLM weights, only for the AFTER-GATES eval (~16 GB each). Uncomment to fetch.
# from huggingface_hub import snapshot_download
# snapshot_download("Qwen/Qwen2.5-VL-7B-Instruct", local_dir="/kaggle/working/qwen2-5-vl-7b")
print("VLM pre-cache is optional and only needed after the gates pass.")'''
    ),
]


def _build(cells) -> nbformat.NotebookNode:
    nb = new_notebook(cells=cells, metadata=NB_META)
    nbformat.validate(nb)
    return nb


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = {
        "00_precache_weights.ipynb": PRECACHE_CELLS,
        "certvic_main200_diffusion_T4x2.ipynb": DIFF_CELLS,
        "certvic_main200_vlm_T4x2_AFTER_GATES.ipynb": VLM_CELLS,
    }
    for name, cells in targets.items():
        nb = _build(cells)
        path = OUT_DIR / name
        nbformat.write(nb, str(path))
        print(f"wrote {path.relative_to(OUT_DIR.parents[1])}  ({len(cells)} cells)")


if __name__ == "__main__":
    main()
