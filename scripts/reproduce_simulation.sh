#!/usr/bin/env bash
set -euo pipefail
# CertVIC: reproduce the simulation / anytime-validity stress lab.
# No GPU, no downloads, no paid services. All outputs are SIMULATED_ONLY and are
# NOT evidence and NOT for paper claims. Run from the repo root.

python3 -m certvic.sim.stress_scenarios \
  --out-dir data/results/v2_1_sim_matrix \
  --n-items 500 --seed 0

echo "Simulation reproduction complete. Outputs are SIMULATED_ONLY (not evidence)."
