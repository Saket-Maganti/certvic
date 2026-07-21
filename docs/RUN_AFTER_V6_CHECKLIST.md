# Run After V6 Checklist

No command may run the full pipeline wholesale.

1. Verify tests and audits:
   `python3 -m pytest -q`
2. Generate staged tiny-pilot commands:
   `python3 -m certvic.commands.generate_real_run_commands --stage tiny_pilot --out-dir data/commands/tiny_pilot --staged-only`
3. Run CPU readiness:
   `commands/tiny_pilot/01_cpu_readiness.sh`
4. Run ADE20K dry-run:
   `ADE20K_ROOT=<ADE20K_ROOT> commands/tiny_pilot/02_dry_run_only.sh`
5. Inspect manifest, masks, and tasks by hand.
6. Generate max 20 diffusion edits:
   `commands/tiny_pilot/03_generate_edits_only.sh`
7. Inspect edited images by eye.
8. Run detectability.
9. Run tiny-pilot go/no-go:
   `commands/tiny_pilot/04_detectability_gate_only.sh`
10. If GO, run human review.
11. Generate item certificates.
12. Only then run first VLM eval:
   `commands/tiny_pilot/05_vlm_eval_only_AFTER_GATES.sh`
13. Score and inspect outputs.
14. Decide scale/no-scale.

VLM inference should not begin until detectability and visual quality pass.
