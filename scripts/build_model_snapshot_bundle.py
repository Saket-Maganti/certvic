#!/usr/bin/env python3
"""CLI wrapper for the CertVIC immutable snapshot bundle builder."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certvic.cvpr.snapshot_bundle_builder import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
