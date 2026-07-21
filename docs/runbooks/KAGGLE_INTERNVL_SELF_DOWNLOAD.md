# Kaggle InternVL2-8B eval — self-download (no weights dataset)

Notebook: `notebooks/kaggle/certvic_internvl_T4_eval_SELF_DOWNLOAD.ipynb`

Runs **InternVL2-8B** over the CertVIC pilot pairs and the absent-object control, writing
predictions in the exact CertVIC schema via the in-process `certvic.eval.run_eval` (leakage /
evidence / resume / manifest gates intact, `provider_name=internvl_8b`). The model is
**downloaded at runtime** — you do **not** create or attach an InternVL weights dataset.

This is a **pilot** run (`evidence_status=HUMAN_REVIEWED_NON_EVIDENCE`). No paper-grade claims.

## Why this notebook exists (two Kaggle breakages it fixes)

1. **`AttributeError: 'InternVLChatModel' object has no attribute 'all_tied_weights_keys'`**
   (+ a `GenerationMixin` warning). InternVL2's remote modeling code predates the Transformers
   ≥4.50 weight-tying/generation refactor. Fix: the **first cell pins `transformers==4.37.2`
   before importing transformers** (install-before-import ⇒ no kernel restart in the normal case;
   a stale import triggers a clear "Restart & Run All" message, and a sentinel makes the reinstall
   instant on the second pass). Pinned stack:
   ```
   transformers==4.37.2  tokenizers==0.15.2  huggingface_hub==0.23.4
   accelerate==0.30.1  timm==0.9.12  einops  sentencepiece
   ```
2. **`ModuleNotFoundError: No module named 'triton.ops'`** / `libbitsandbytes_cuda128.so ...
   compiled without GPU support`. On the Py3.12 / CUDA 12.8 Kaggle image, `bitsandbytes` 0.43.x is
   broken (Triton 3.x removed `triton.ops`; no matching CUDA binary). Fix: **avoid bitsandbytes** —
   load InternVL2-8B in **bf16 sharded across both T4s** with InternVL's official `split_model`
   device map. (Single GPU falls back to 4-bit, installing a current bitsandbytes on demand.)
3. **`ValidationError: ... TaskItem ... source / edit Field required`**. `run_eval` loads the
   strict nested `TaskItem` schema, but the presence bundle ships the *flat* reviewed schema. Fix:
   the run cell **projects flat rows onto `TaskItem`** (only when `source` is absent — the control
   bundle is already nested and passes through). Same projection as the proven Qwen run.

## Kaggle settings

- **Accelerator: GPU T4 ×2 (recommended).** InternVL2-8B in bf16 is ~16 GB — it does **not** fit
  on one 16 GB T4 but fits **sharded across two**. A single T4/P100 falls back to 4-bit (needs a
  working bitsandbytes; less reliable on the newest images).
- **Internet: ON** — required, the notebook downloads the model from Hugging Face.
- Optional: add an `HF_TOKEN` **Kaggle Secret** (not required — InternVL2-8B is public).

## Inputs to attach (only 3 — auto-detected)

| # | Input | Detected by |
|---|---|---|
| 1 | **CertVIC code** — dir containing the `certvic/` package (`dist/certvic_kaggle_main200_bundle.zip` or the repo) | a `certvic/eval/run_eval.py` under `/kaggle/input` |
| 2 | **presence data** — `dist/certvic_main200_session2_data.zip` | a `pilot_eval_tasks_reviewed.jsonl` with **91** tasks |
| 3 | **absent-object control** — `dist/certvic_absent_object_control.zip` | a `pilot_eval_tasks_reviewed.jsonl` with **120** tasks |

**No InternVL weights input.** The notebook prints the resolved `CERTVIC_DIR`, `PRESENCE_INPUT`,
`CONTROL_INPUT`, `MODEL_DIR` and **refuses to run** if either task bundle is missing. If
auto-detect fails, set the override variables `CERTVIC_DIR` / `PRESENCE_INPUT` / `CONTROL_INPUT`
at the top of the detect cell.

## Run order

Top-to-bottom. **Stop at the smoke-test cell** and confirm it prints `yes`/`no` with `ok=True`
for 2 presence + 2 control examples before launching the full run (catches any chat-format/dtype
issue in ~10 s).

## Expected runtime (T4 ×2, bf16)

| Step | Work | Time |
|---|---|---|
| Pip install (one-time) | pinned stack | ~2–4 min |
| Model download (one-time) | ~16 GB snapshot | ~5–15 min (bandwidth-bound) |
| Model load (bf16, sharded) | — | ~1–3 min |
| Smoke test | 4 generations | ~10–20 s |
| Presence | 182 generations | ~6–12 min |
| Control | 240 generations | ~8–16 min |
| **Total** | ~420 generations | **~25–45 min** |

Well inside Kaggle's free 9–12 h GPU session. `run_eval` resumes from its output JSONL +
`.run_manifest.json`, so a re-run after a session death only completes the remainder.

## Outputs to download

- `/kaggle/working/pred_internvl_8b_presence_merged.jsonl`
- `/kaggle/working/pred_internvl_8b_control_merged.jsonl`
- `/kaggle/working/internvl_preds.zip` (both of the above + run manifests)

## Local ingest after download

```bash
cd /path/to/certVIC
python3 scripts/pilot_report_from_raw.py \
  --provider internvl_8b --model-name OpenGVLab/InternVL2-8B --run-label internvl_8b \
  --raw-presence /path/to/pred_internvl_8b_presence_merged.jsonl \
  --raw-control  /path/to/pred_internvl_8b_control_merged.jsonl
```

Writes `data/results/main_real_200/pilot_report__internvl_8b/` (+ sha256-locked
`raw_predictions__internvl_8b/`) and refreshes `multimodel_pilot_summary.{md,csv,json}` with the
InternVL row **from its own run**. It **REFUSES** if a file is missing or its `provider_name`
≠ `internvl_8b`. No paid services; pilot-only; gates unchanged.
