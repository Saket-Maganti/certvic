"""Check user-managed model-cache manifests without network access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.hashing import sha256_file
from certvic.io import read_json, write_json


def check_cache_manifest(manifest_path: str) -> dict:
    manifest = read_json(manifest_path)
    root = Path(manifest["cache_root"])
    missing: list[str] = []
    changed: list[str] = []
    checked = 0
    if not root.exists():
        missing.append("cache_root_missing")
    for entry in manifest.get("files", []):
        path = root / entry["path"]
        if not path.exists():
            missing.append(entry["path"])
            continue
        checked += 1
        if "sha256" in entry and sha256_file(path) != entry["sha256"]:
            changed.append(entry["path"])
    return {
        "manifest": manifest_path,
        "provider": manifest.get("provider"),
        "checked_files": checked,
        "missing": missing,
        "changed": changed,
        "passed": not missing and not changed,
        "downloads_attempted": False,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Check a model-cache manifest")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = check_cache_manifest(args.manifest)
    write_json(args.out, result)
    print(json.dumps({"out": args.out, "passed": result["passed"], "missing": result["missing"]}, sort_keys=True))


if __name__ == "__main__":
    main()

