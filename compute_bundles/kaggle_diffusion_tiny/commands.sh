#!/usr/bin/env bash
set -euo pipefail
# Run commands

python3 -m certvic.edit.generate_edits --edit-plan data/manifests/pilot_edit_plan.jsonl --out-dir data/edits/ade20k_tiny_pilot --out-manifest data/manifests/pilot_generated_edits.jsonl --rejected-out data/manifests/pilot_generated_edits_rejected.jsonl --summary-out data/results/tiny_edit_generation_summary.json --max-items 20 --mode diffusers_inpaint --seed 0
python3 -m certvic.provenance.run_ledger add --stage edit_generation --run-id diffusion_tiny --inputs data/manifests/pilot_edit_plan.jsonl --outputs data/manifests/pilot_generated_edits.jsonl --config configs/real_pilot_ade20k.yaml --evidence-status REAL_EVIDENCE
