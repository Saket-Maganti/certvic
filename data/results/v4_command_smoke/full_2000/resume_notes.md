# Resume Notes — full_2000

Re-run the same command after interruption unless a command explicitly says otherwise.
Avoid `--overwrite` unless you are intentionally replacing a bad partial artifact.

- `data/results/full_real_2000/stage_status.json` lets `run_tiny_pilot` skip completed stages.
- `certvic.edit.engines --resume` skips already generated/rejected edit IDs.
- `certvic.eval.run_eval` skips completed task keys by default.
- `certvic.edit.diffusion_resume` should be rerun after each interrupted GPU session.
- Do not delete partial JSONL outputs until merge/dedup/recovery tools have inspected them.
