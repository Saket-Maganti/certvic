#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR/.."
python3 local_operator/runtime_materializer.py --clean-operator-metadata
python3 scripts/run_all_cpu_workflows.py --resume
python3 -m certvic.cvpr.doctor --json
python3 -m certvic.cvpr.next_action
python3 -m certvic.cvpr.run_graph status
