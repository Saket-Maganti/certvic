#!/usr/bin/env bash
set -euo pipefail
# Preflight (no heavy work)

python3 -m pytest -q
