#!/usr/bin/env bash
set -euo pipefail

# Stage 04: detectability gate only. VLM inference should not begin unless this gate is GO.
python3 -m certvic.validation.edit_detectability --tasks data/results/tiny_real_pilot/pilot_eval_tasks_tiny.jsonl --out-dir data/results/tiny_real_pilot/edit_detectability
python3 -m certvic.pipeline.tiny_pilot_go_no_go --detectability data/results/tiny_real_pilot/edit_detectability --quality data/results/tiny_real_pilot/tiny_edit_quality_report --out docs/TINY_PILOT_GO_NO_GO.md --json-out data/results/tiny_pilot_go_no_go.json
python3 -m certvic.dashboard.tiny_pilot_decision --pilot-dir data/results/tiny_real_pilot --out docs/TINY_PILOT_DECISION.md --json-out data/results/tiny_pilot_decision.json
