# CertVIC free-compute bundle: `diffusion_tiny` (kaggle)

Generate a tiny batch of photorealistic diffusion-inpaint edits on a free GPU.

- Stage: `edit_generation`
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
python3 -m certvic.edit.diffusion_preflight --edit-plan data/manifests/pilot_edit_plan.jsonl --engine diffusers_inpaint_optional --config configs/real_pilot_ade20k.yaml --weights-dir <WEIGHTS_DIR> --check-gpu
```

## 2. Run

```bash
python3 -m certvic.edit.generate_edits --edit-plan data/manifests/pilot_edit_plan.jsonl --out-dir data/edits/ade20k_tiny_pilot --out-manifest data/manifests/pilot_generated_edits.jsonl --rejected-out data/manifests/pilot_generated_edits_rejected.jsonl --summary-out data/results/tiny_edit_generation_summary.json --max-items 20 --mode diffusers_inpaint --seed 0
python3 -m certvic.provenance.run_ledger add --stage edit_generation --run-id diffusion_tiny --inputs data/manifests/pilot_edit_plan.jsonl --outputs data/manifests/pilot_generated_edits.jsonl --config configs/real_pilot_ade20k.yaml --evidence-status REAL_EVIDENCE
```

## 3. Resume

Free sessions die often. Re-running the commands resumes from existing outputs:
generation skips items whose output already exists, `run_eval` resumes from its
JSONL + run manifest, and sharded runs continue at the next incomplete shard.
After each session, record outputs with `certvic.provenance.run_ledger add` so
progress is hash-tracked across sessions.

See `expected_inputs.md` / `expected_outputs.md` and `manifest.json`.
