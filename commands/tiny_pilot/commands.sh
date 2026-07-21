#!/usr/bin/env bash
set -euo pipefail

echo "Refusing to run all CertVIC tiny-pilot stages in one blind script."
echo
echo "Use the staged scripts instead:"
echo "  commands/tiny_pilot/01_cpu_readiness.sh"
echo "  ADE20K_ROOT=<ADE20K_ROOT> commands/tiny_pilot/02_dry_run_only.sh"
echo "  commands/tiny_pilot/03_generate_edits_only.sh"
echo "  python3 -m certvic.validation.edit_detectability --tasks data/results/tiny_real_pilot/pilot_eval_tasks_tiny.jsonl --out-dir data/results/tiny_real_pilot/edit_detectability"
echo "  commands/tiny_pilot/04_detectability_gate_only.sh"
echo "  commands/tiny_pilot/05_vlm_eval_only_AFTER_GATES.sh"
echo
echo "VLM inference is allowed only after detectability, quality, human review, and item certificates pass."
exit 2
