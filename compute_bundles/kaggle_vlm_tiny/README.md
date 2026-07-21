# CertVIC free-compute bundle: `vlm_tiny` (kaggle)

Run open-local VLM inference + scoring on a tiny reviewed task set.

- Stage: `vlm_inference`
- GPU required: True
- Evidence status: `JOB_PLANNED_ONLY` (planning artifact; not evidence)

## Zero-cost policy

Free GPU + open models + user-supplied local data only. No paid services, no
credentials, no private pixels in this bundle. This bundle is not executed here.

## Platform notes

- Enable the GPU accelerator (free T4 or P100) in Notebook settings.
- Free GPU sessions are capped (~12 h) and weekly GPU quota is limited; shard long jobs.
- Mount data and weights as read-only Kaggle **input** datasets under `/kaggle/input`.
- Write outputs to `/kaggle/working` (~20 GB); offload finished shards before it fills.
- Keep internet **off** unless a step truly needs it; never add paid endpoints or keys.

## 1. Preflight (no heavy work)

```bash
python3 -m certvic.eval.vlm_preflight --config configs/tiny_reviewed_eval.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b --check-gpu
```

## 2. Run

```bash
python3 -m certvic.pipeline.run_tiny_eval --config configs/tiny_reviewed_eval.yaml --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl --provider qwen2_5_vl_7b --out-dir data/results/tiny_eval_qwen --max-items 20
```

## 3. Resume

Free sessions die often. Re-running the commands resumes from existing outputs:
generation skips items whose output already exists, `run_eval` resumes from its
JSONL + run manifest, and sharded runs continue at the next incomplete shard.
After each session, record outputs with `certvic.provenance.run_ledger add` so
progress is hash-tracked across sessions.

See `expected_inputs.md` / `expected_outputs.md` and `manifest.json`.
