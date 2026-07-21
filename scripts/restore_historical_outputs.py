#!/usr/bin/env python3
"""Restore the separately distributed historical Kaggle outputs without overwrites."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certvic.cvpr.historical_outputs import restore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--manifest", default="PROJECT_DISTRIBUTION_MANIFEST.json")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = restore(
        args.archive,
        manifest=args.manifest,
        project_root=args.project_root,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
