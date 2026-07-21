# Playbook: Kaggle / Colab Session Failure

**Symptoms: a free GPU session died mid-run (timeout, disconnect, OOM).**

## Actions

1. Resume: re-run the same command — generation skips done items and `run_eval` resumes from its JSONL + run manifest.
2. For edits, use `certvic.edit.diffusion_resume` to re-queue only incomplete jobs (retry-capped).
3. Shard the work (`certvic.edit.job_queue next-shard`, `run_eval --num-shards`) so a session handles one shard.
4. If OOM, enable 4-bit loading; check `certvic.planning.scale_planner` batch sizes per session.
5. Record each session's outputs with `certvic.provenance.run_ledger add` so progress is hash-tracked.

Do not fabricate results to clear this symptom; if the honest outcome is a null
result or an ineligible claim, report it and adjust the protocol, not the numbers.
