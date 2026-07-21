#!/usr/bin/env bash
set -euo pipefail
# CertVIC: reproduce CPU-only planning/report artifacts (no GPU, no downloads,
# no paid services, no model inference). Run from the repo root.

# Storage and scale plans.
python3 -m certvic.storage.plan_storage --config configs/real_pilot_ade20k.yaml --scale 200  --out data/results/storage_plan_200.json
python3 -m certvic.planning.scale_planner --scale 200  --out data/results/scale_plan_200.md
python3 -m certvic.planning.scale_planner --scale 2000 --out data/results/scale_plan_2000.md

# Local dashboard over whatever artifacts exist.
python3 -m certvic.dashboard.build_dashboard --results-root data/results --out-dir data/dashboard

# Paper number guard + reviewer simulation (honest about missing results).
python3 -m certvic.validation.paper_numbers_guard --no-fail || true
python3 -m certvic.review.simulate_reviews --paper-dir paper --reports-root data/results --out-dir docs/reviewer_simulation

echo "Report reproduction complete. No evidence claims; planning/diagnostic artifacts only."
