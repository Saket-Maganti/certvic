# CertVIC — Kaggle main-200 diffusion bundle

## 1. What this bundle is
A self-contained, zero-pixel upload for the **next GPU step only**: generating the
**168 photorealistic single-factor edits** of the CertVIC main-200 pilot on a free
Kaggle **T4×2** notebook. It carries the CertVIC package, configs, scripts, the
main-200 **planning artifacts** (selection, edit plan, the two GPU shards, the
diffusion job queue + resume worklist), the markdown runbooks, and ready-to-run
notebooks. All coordination, resume, quality-gate and schema logic is reused from
`certvic/`.

**Run the notebooks directly** (`notebooks/kaggle/`):
- `00_precache_weights.ipynb` — optional one-time weight download (Internet ON).
- `certvic_main200_diffusion_T4x2.ipynb` — the next step (this bundle).
- `certvic_main200_vlm_T4x2_AFTER_GATES.ipynb` — blocked until the gates pass (§9).

## 2. What it does NOT contain
- **No ADE20K image or annotation pixels** — attach ADE20K as a separate Kaggle dataset.
- **No model weights** — add the non-gated Kaggle model
  `kaggle.com/refs/hf-model/stable-diffusion-v1-5/stable-diffusion-inpainting` via
  **+ Add Input → Models** (no HF token, Internet OFF); the diffusion notebook auto-detects it.
- No generated edited images, no `.git`, no virtualenvs, no caches, no secrets.
- No private local absolute paths: planning manifests are sanitized to the token
  `__ADE20K_ROOT__`, swapped for the real mount at run time (step 5).

## 3. Attach the ADE20K Kaggle dataset
ADE20K is the **MIT Scene Parsing** release (`ADEChallengeData2016/`, semantic-PNG
annotations). In the notebook: **Add Data → Datasets** and attach an ADE20K
dataset that contains `ADEChallengeData2016/{images,annotations}/{training,validation}/`.
Do **not** upload pixels inside this bundle.

## 4. Find the actual Kaggle mount
Mounts are read-only under `/kaggle/input/<dataset-slug>/`. Confirm the real path:
```python
import glob
print([p for p in glob.glob("/kaggle/input/**/ADEChallengeData2016", recursive=True)])
```

## 5. Set `ADE20K_ROOT`
Point it at the mounted `ADEChallengeData2016` directory (use the path from step 4):
```bash
export ADE20K_ROOT=/kaggle/input/<actual-ade20k-dataset>/ADEChallengeData2016
```
The runbook's remap step replaces the bundled `__ADE20K_ROOT__` token in each
edit-plan shard with `$ADE20K_ROOT`. (If you ever use an un-sanitized manifest,
set `CERTVIC_LOCAL_ADE20K_ROOT` to the local root baked into it; the remap falls
back to auto-detecting the prefix before `/images/`.)

## 6. Run GPU0 / GPU1 diffusion workers (parallel)
Two workers in one notebook, one pinned per T4, processing disjoint shards:
- **GPU 0 → session 1 → shard 0** (81 edits): `CUDA_VISIBLE_DEVICES=0`
- **GPU 1 → session 2 → shard 1** (87 edits): `CUDA_VISIBLE_DEVICES=1`

Launch both, then `wait`. Each writes a **separate** out-dir, manifest and log, so
there are no cross-GPU races and the run is resume-safe (re-running skips finished
`edit_id`s). Just run the cells in `notebooks/kaggle/certvic_main200_diffusion_T4x2.ipynb`
(prose: `docs/runbooks/KAGGLE_T4x2_DIFFUSION_EDITS.md`).

## 7. Merge outputs
After both workers finish, concatenate the per-shard manifests into one
`pilot_generated_edits.jsonl` and zip the edited PNGs (see the runbook's merge cell).

## 8. Download back to the local repo
Pull these from the Kaggle output panel into `data/results/main_real_200/` and
`data/edits/main_real_200/` on the Mac:
- `pilot_generated_edits.jsonl` (merged manifest)
- `diffusion_out.zip` (edited PNGs)
- `gen_summary_shard0.json`, `gen_summary_shard1.json`, `log_shard*.txt`

## 9. Gates that must pass before any VLM eval
VLM inference is **out of scope for this bundle** and is blocked until ALL of:
1. **quality** gates pass on the generated edits,
2. **detectability** AUC **< 0.80** (`certvic.validation.edit_detectability` + go/no-go),
3. **human visual review** complete → `pilot_eval_tasks_reviewed.jsonl`,
4. **item certificates** pass.

`run_eval --evidence-run` refuses non-open-local providers and any task set not
marked `HUMAN_REVIEWED_NON_EVIDENCE`/`EVIDENCE`/`CERTIFIED`. The VLM runbook
(`docs/runbooks/KAGGLE_T4x2_VLM_EVAL.md`) is **after-gates only**.

## 10. Why crude CPU edits are non-evidence and blocked
The local CPU "simple" engine produces crude fills/occluders that are trivially
artifact-detectable (pilot detectability **AUC ≈ 0.92 → NO_GO**). They are
plumbing checks, never evidence (`GENERATED_EDIT_ONLY`). Only realistic diffusion
edits that clear the detectability gate may proceed toward VLM scoring — and even
then nothing is an evidence claim until the full certification gates pass.
