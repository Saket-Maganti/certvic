#!/usr/bin/env bash
set -euo pipefail
# CertVIC: reproduce the CPU-only smoke pipeline end to end.
# No GPU, no downloads, no paid services. Uses synthetic MOCK_ONLY fixtures
# (not evidence). Run from the repo root.

python3 -m pytest -q

python3 -m certvic.data.build_tasks --smoke --out data/manifests/smoke_tasks.jsonl
python3 -m certvic.data.manifest_checks --tasks data/manifests/smoke_tasks.jsonl --strict

python3 -m certvic.eval.run_eval \
  --config configs/smoke.yaml \
  --tasks data/manifests/smoke_tasks.jsonl \
  --out data/predictions/smoke_mock_inconsistent.jsonl \
  --provider mock_inconsistent --run-id smoke_mock_inconsistent_v1 --max-items 10

python3 -m certvic.metrics.score_predictions \
  --tasks data/manifests/smoke_tasks.jsonl \
  --preds data/predictions/smoke_mock_inconsistent.jsonl \
  --out-scores data/results/smoke_pair_scores.jsonl \
  --out-summary data/results/smoke_summary.json

python3 -m certvic.reporting.build_report \
  --tasks data/manifests/smoke_tasks.jsonl \
  --scores data/results/smoke_pair_scores.jsonl \
  --preds data/predictions/smoke_mock_inconsistent.jsonl \
  --out-dir data/results/smoke_report --alpha 0.05 --gap-threshold 0.05

echo "Smoke reproduction complete. Outputs are MOCK_ONLY and are not evidence."
