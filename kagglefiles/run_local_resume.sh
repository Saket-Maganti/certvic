#!/usr/bin/env bash
set -euo pipefail
cd /Users/saketmaganti/Projects/certVIC
python3 scripts/run_all_cpu_workflows.py --resume
python3 -m certvic.cvpr.doctor --json
python3 -m certvic.cvpr.next_action
python3 -m certvic.cvpr.run_graph status
