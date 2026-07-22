#!/usr/bin/env python3
"""Authenticate and import one unchanged Kaggle return into CertVIC."""
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.cvpr.kagglefiles_pack import import_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(import_main())
