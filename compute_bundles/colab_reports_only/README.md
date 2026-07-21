# CertVIC free-compute bundle: `reports_only` (colab)

CPU-only: rebuild reports from existing predictions/scores. No GPU, no model.

- Stage: `report`
- GPU required: False
- Evidence status: `JOB_PLANNED_ONLY` (planning artifact; not evidence)

## Zero-cost policy

Free GPU + open models + user-supplied local data only. No paid services, no
credentials, no private pixels in this bundle. This bundle is not executed here.

## Platform notes

- Set Runtime > Change runtime type > GPU (free T4) before running.
- Free Colab disconnects on idle and caps session length; checkpoint and resume often.
- Use `/content` for scratch; optionally mount Google Drive for inputs/outputs (free tier).
- Place data and weights locally (Drive or uploaded); CertVIC never auto-downloads them.
- Never add paid Colab Pro-only assumptions, paid endpoints, or credentials.

## 1. Preflight (no heavy work)

```bash
python3 -m pytest -q
```

## 2. Run

```bash
python3 -m certvic.reporting.build_report --tasks data/manifests/tasks.jsonl --scores data/results/pair_scores.jsonl --preds data/predictions/run.jsonl --out-dir data/results/report --alpha 0.05 --gap-threshold 0.05
```

## 3. Resume

Free sessions die often. Re-running the commands resumes from existing outputs:
generation skips items whose output already exists, `run_eval` resumes from its
JSONL + run manifest, and sharded runs continue at the next incomplete shard.
After each session, record outputs with `certvic.provenance.run_ledger add` so
progress is hash-tracked across sessions.

See `expected_inputs.md` / `expected_outputs.md` and `manifest.json`.
