# GPU Session 2 — Open-VLM eval on Kaggle T4×2

Run the open-local VLMs over each task's **original vs. edited** image pair, two
workers in parallel (GPU 0 → shard 0, GPU 1 → shard 1), inside one T4×2 notebook.
Outputs are predictions that the CPU scores into the consistency gap `Δ = a − p`
with anytime-valid confidence sequences.

- **Stage:** `vlm_eval` · **GPU:** required (2× T4 16 GB) · **Evidence:** evidence-eligible **only after gates**
- **Providers:** `qwen2_5_vl_7b`, `internvl_8b`, `llava_onevision_7b` (4-bit fits a T4).

---

## 0. Hard prerequisites (enforced in code — `run_eval --evidence-run` refuses otherwise)

1. **Detectability gate = GO** for the diffusion edits (Session 1 step 7, AUC < 0.80).
2. **Human review done** → `pilot_eval_tasks_reviewed.jsonl` exists and every task's
   `evidence_status` is `HUMAN_REVIEWED_NON_EVIDENCE`. Produce it with:
   ```bash
   D=data/results/main_real_200
   python3 -m certvic.validation.export_visual_review --tasks $D/pilot_eval_tasks_tiny.jsonl \
     --generated-edits $D/pilot_generated_edits.jsonl --out $D/visual_review_sheet.csv --seed 0
   # ... a human fills the sheet (keep/drop + single-factor/realism checks) ...
   python3 -m certvic.data.apply_visual_review --tasks $D/pilot_eval_tasks_tiny.jsonl \
     --review-sheet $D/visual_review_sheet.csv --out $D/pilot_eval_tasks_reviewed.jsonl
   ```
   `run_eval --evidence-run` will raise `evidence_run blocked: tasks must be reviewed`
   if you skip this. That guard is intentional — don't work around it.

---

## 1. Kaggle setup

1. New Notebook → **Accelerator: GPU T4 ×2**, **Internet: Off**.
2. **Add Data** (read-only inputs):
   - **certvic** — `certvic_kaggle.zip` (package + `configs/`) as before, plus
     `data/results/main_real_200/pilot_eval_tasks_reviewed.jsonl`.
   - **ADE20K** — original images (`ADEChallengeData2016/images/...`), same mount as Session 1.
   - **edited images** — the `data/edits/main_real_200/` PNGs produced in Session 1
     (`diffusion_out.zip`), uploaded as a dataset → e.g. `/kaggle/input/certvic-edits`.
   - **VLM weights** — pre-cached HF snapshots, one dataset per model, e.g.
     `/kaggle/input/qwen2-5-vl-7b`, `/kaggle/input/internvl-8b`, `/kaggle/input/llava-ov-7b`.

## 2. Notebook cell — paths + remap reviewed tasks

```python
import os, sys, json
from pathlib import Path
CERTVIC = "/kaggle/input/certvic"; sys.path.insert(0, CERTVIC)
ADE_KAGGLE  = "/kaggle/input/ade20k/ADEChallengeData2016"
EDITS_KAGGLE = "/kaggle/input/certvic-edits/edits"
WORK = Path("/kaggle/working")

rows = [json.loads(l) for l in open(f"{CERTVIC}/data/results/main_real_200/pilot_eval_tasks_reviewed.jsonl")]
# Auto-detect the local prefixes baked into the tasks — no hardcoded local paths:
LOCAL_ADE   = rows[0]["original_image_path"].split("/images/")[0]
LOCAL_EDITS = rows[0]["edited_image_path"].rsplit("/", 1)[0]
for r in rows:
    for k in ("original_image_path", "edited_image_path"):
        if r.get(k):
            r[k] = r[k].replace(LOCAL_ADE, ADE_KAGGLE).replace(LOCAL_EDITS, EDITS_KAGGLE)
open(WORK/"tasks_reviewed.jsonl","w").writelines(json.dumps(r)+"\n" for r in rows)
print(len(rows), "reviewed tasks; evidence_status set:",
      sorted({r.get("metadata",{}).get("evidence_status") for r in rows}))
```

## 3. Notebook cell — real VLM `answer()` (fills the provider scaffold)

`OpenVLMProvider.load()/answer()` are scaffolds that raise. Patch them with a real
implementation; `run_eval` then drives them with all leakage/evidence/resume logic
intact.

```python
import torch
from PIL import Image
import certvic.providers.open_vlm as ovlm

def make_qwen_answer(weights):
    from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        weights, torch_dtype=torch.float16, device_map={"": 0}, load_in_4bit=True)
    proc = AutoProcessor.from_pretrained(weights)
    @torch.inference_mode()
    def answer(self, image_path, prompt):
        img = Image.open(image_path).convert("RGB")
        msgs = [{"role":"user","content":[{"type":"image","image":img},{"type":"text","text":prompt}]}]
        text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = proc(text=[text], images=[img], return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=16, do_sample=False)
        gen = out[0][inputs.input_ids.shape[1]:]
        return proc.decode(gen, skip_special_tokens=True).strip()
    return answer

# Patch once per process; CUDA_VISIBLE_DEVICES pins device_map={"":0} to the right T4.
ovlm.OpenVLMProvider.load   = lambda self: None
ovlm.OpenVLMProvider.answer = make_qwen_answer(os.environ["WEIGHTS"])
print("patched OpenVLMProvider.answer for", os.environ.get("PROVIDER"))
```

> **InternVL / LLaVA-OneVision:** same shape, swap the model/processor classes
> (`AutoModel`/`AutoProcessor` for InternVL; `LlavaOnevisionForConditionalGeneration`
> for LLaVA-OneVision) and their chat formatting. One weights dataset + one patch each.

## 4. Notebook cell — both GPUs in parallel (`gpu0 → session 1`, `gpu1 → session 2`)

`run_eval` shards natively on `item_id` — no pre-split needed. Run shard 0 on GPU 0
and shard 1 on GPU 1, in parallel, per provider:

```python
import subprocess, sys, os
def run_shard(provider, weights, gpu, shard):
    cmd = [sys.executable, "-m", "certvic.eval.run_eval",
           "--config", f"{CERTVIC}/configs/kaggle_open_vlm.yaml",
           "--tasks", "/kaggle/working/tasks_reviewed.jsonl",
           "--out", f"/kaggle/working/pred_{provider}_shard{shard}.jsonl",
           "--provider", provider, "--run-id", f"main200_{provider}_shard{shard}",
           "--shard-index", str(shard), "--num-shards", "2",
           "--strict-leakage", "--evidence-run", "--fail-fast"]
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(gpu), "PROVIDER": provider, "WEIGHTS": weights}
    return subprocess.Popen(cmd, env=env,
                            stdout=open(f"/kaggle/working/log_{provider}_s{shard}.txt","w"),
                            stderr=subprocess.STDOUT)

PROVIDERS = {
    "qwen2_5_vl_7b": "/kaggle/input/qwen2-5-vl-7b",
    # "internvl_8b": "/kaggle/input/internvl-8b",
    # "llava_onevision_7b": "/kaggle/input/llava-ov-7b",
}
for provider, weights in PROVIDERS.items():
    p0 = run_shard(provider, weights, gpu=0, shard=0)   # Session 1 → GPU 0
    p1 = run_shard(provider, weights, gpu=1, shard=1)   # Session 2 → GPU 1
    p0.wait(); p1.wait()
    print(provider, "done:", open(f"/kaggle/working/log_{provider}_s0.txt").read()[-300:])
```

> Each worker is a fresh `run_eval` process: its cell-3 patch is applied at import.
> Put cell 3's body in a `sitecustomize.py` on `sys.path`, or prepend it via a
> `PYTHONSTARTUP` file, so the subprocess applies the patch before `run_eval` builds
> the provider. (Same mechanism as Session 1's `engine_patch.py`.)

## 5. Merge + download

```python
import glob, shutil
for provider in PROVIDERS:
    merged = []
    for s in (0,1):
        merged += [l for l in open(f"/kaggle/working/pred_{provider}_shard{s}.jsonl")]
    open(f"/kaggle/working/pred_{provider}_merged.jsonl","w").writelines(merged)
shutil.make_archive("/kaggle/working/vlm_preds","zip","/kaggle/working",
                    *[f for f in os.listdir("/kaggle/working") if f.startswith("pred_")])
```
Download the `pred_*_merged.jsonl` files.

## 6. Resume

`run_eval` resumes from its output JSONL + `.run_manifest.json`: re-running skips
completed `(run_id, item_id, variant)` keys. Re-launch the notebook and re-run cell
4 after a session death; only the remainder runs.

## 7. Back on the Mac — score, certify, report

```bash
D=data/results/main_real_200; mkdir -p data/predictions/main_real_200
# drop pred_*_merged.jsonl into data/predictions/main_real_200/ and concatenate to merged.jsonl
cat data/predictions/main_real_200/pred_*_merged.jsonl > data/predictions/main_real_200/merged.jsonl

python3 -m certvic.eval.output_triage --preds data/predictions/main_real_200/merged.jsonl \
  --tasks $D/pilot_eval_tasks_reviewed.jsonl --out-dir $D/output_triage
python3 -m certvic.metrics.score_predictions --tasks $D/pilot_eval_tasks_reviewed.jsonl \
  --preds data/predictions/main_real_200/merged.jsonl \
  --out-scores $D/pair_scores.jsonl --out-summary $D/score_summary.json
python3 -m certvic.reporting.build_v2_report --tasks $D/pilot_eval_tasks_reviewed.jsonl \
  --preds data/predictions/main_real_200/merged.jsonl --scores $D/pair_scores.jsonl \
  --out-dir $D/v2_report
```

`score_summary.json` carries `a`, `p`, `Δ = a − p`, and the anytime-valid confidence
sequence. **Certified claims only after** the certification gates pass on real,
reviewed, gate-cleared predictions — output triage clean, detectability GO, CS
available. Paper-number injection stays gated (no `.bib`/results lockfile yet).
