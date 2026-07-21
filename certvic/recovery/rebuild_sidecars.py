"""Rebuild lightweight sidecar metadata from available manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.hashing import sha256_file
from certvic.io import write_json


def rebuild_sidecars(input_path: str, out: str, *, dry_run: bool = True) -> dict:
    path = Path(input_path)
    sidecar = {
        "source": input_path,
        "source_exists": path.exists(),
        "source_sha256": sha256_file(path) if path.exists() else None,
        "reconstructed_from_available_metadata": True,
        "dry_run": dry_run,
    }
    if not dry_run:
        write_json(out, sidecar)
    return sidecar


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Rebuild sidecar metadata")
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(rebuild_sidecars(args.input, args.out, dry_run=not args.apply), sort_keys=True))


if __name__ == "__main__":
    main()

