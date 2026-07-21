# V6 Staged Command Safety Report

Status: passed pending final test run.

`commands.sh` is now a guarded command index. It refuses wholesale execution
unless `CERTVIC_RUN_ALL_DANGEROUS_STAGES=1` is set after manual review.

Stage-specific scripts:
- `commands/tiny_pilot/01_cpu_readiness.sh`
- `commands/tiny_pilot/02_dry_run_only.sh`
- `commands/tiny_pilot/03_generate_edits_only.sh`
- `commands/tiny_pilot/04_detectability_gate_only.sh`
- `commands/tiny_pilot/05_vlm_eval_only_AFTER_GATES.sh`

Safety rule: VLM inference should not begin until detectability, visual quality,
human review, and item certificates pass.
