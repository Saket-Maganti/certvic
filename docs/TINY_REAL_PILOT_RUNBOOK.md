# Tiny Real Pilot Runbook

The orchestrator chains the edit-side pipeline end to end (no VLM inference).

## One command (after you supply a local ADE20K root)

```bash
python3 -m certvic.pipeline.run_tiny_pilot \
  --config configs/real_pilot_ade20k.yaml \
  --ade20k-root /absolute/path/to/ADE20K \
  --out-dir data/results/tiny_real_pilot \
  --max-items 20 --dry-run
```

`--dry-run` runs readiness → manifests → label-policy report, then prints the
exact remaining commands. Remove `--dry-run` to run the full chain: selection →
edit planning → task preview → pilot plan report → tiny edit generation →
quality report → task materialization → visual review sheet export.

## Outputs (under --out-dir)

- `stage_status.json` — per-stage status (completed/failed/seconds)
- `command_log.txt` — every command the orchestrator represents
- `zero_cost_audit.json` — downloads/gpu/vlm_inference all false
- manifests, selection, edit plan, generated edits, quality report, eval tasks,
  `visual_review_sheet.csv`
- `tiny_pilot_summary.json`

## Guarantees

No downloads, no GPU, no VLM inference, no evidence claims. Stages resume by
default (skip completed unless `--force`). All artifacts are
`PIPELINE_NON_EVIDENCE`. VLM evaluation is a separate command
(`run_tiny_eval`) on reviewed tasks only.
