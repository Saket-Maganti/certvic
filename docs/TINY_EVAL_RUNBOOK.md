# Tiny Eval Runbook (open-local VLM)

Runs VLM evaluation + scoring over reviewed tasks on free local/Kaggle compute.

```bash
python3 -m certvic.pipeline.run_tiny_eval \
  --config configs/tiny_reviewed_eval.yaml \
  --tasks data/manifests/pilot_eval_tasks_tiny_reviewed.jsonl \
  --provider qwen2_5_vl_7b \
  --out-dir data/results/tiny_eval_qwen --max-items 20
```

Stages: preflight -> run_eval -> score_predictions -> report_metrics ->
build_v2_report (when available) -> audit.

Enforced: tasks must be HUMAN_REVIEWED_NON_EVIDENCE or stronger; mock providers
are blocked for the evidence path (use `--allow-mock-smoke` for a non-evidence
plumbing check); paid providers blocked; `--max-items` required unless
`--allow-full-run`; resume on; raw outputs preserved. Certification is gated by
`configs/certification_policy.yaml` and an available anytime-valid CS.
