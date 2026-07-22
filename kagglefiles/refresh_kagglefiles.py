#!/usr/bin/env python3
"""Refresh the unified CertVIC Kaggle operator pack without fabricating inputs."""
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.cvpr.kagglefiles_pack import refresh_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(refresh_main())
