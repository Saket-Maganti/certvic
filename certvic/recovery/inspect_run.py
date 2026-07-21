"""Inspect partial run directories for missing/duplicate artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import read_jsonl, write_json


def inspect_run(run_dir: str) -> dict:
    root = Path(run_dir)
    jsonl_files = sorted(root.rglob("*.jsonl")) if root.exists() else []
    duplicates: list[dict] = []
    counts: dict[str, int] = {}
    for path in jsonl_files:
        rows = read_jsonl(path)
        seen: set[str] = set()
        for row in rows:
            key = str(row.get("item_id") or row.get("edit_id") or row.get("job_id") or "")
            if not key:
                continue
            if key in seen:
                duplicates.append({"file": str(path), "key": key})
            seen.add(key)
        counts[str(path)] = len(rows)
    return {
        "run_dir": run_dir,
        "exists": root.exists(),
        "jsonl_counts": counts,
        "duplicates": duplicates,
        "missing_sidecar_candidates": [
            str(p) for p in jsonl_files if not Path(str(p) + ".provider_metadata.json").exists()
        ],
        "dry_run": True,
        "hash_mismatches_fixed": False,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Inspect a partial run directory")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = inspect_run(args.run_dir)
    write_json(args.out, result)
    print(json.dumps({"out": args.out, "duplicates": len(result["duplicates"])}, sort_keys=True))


if __name__ == "__main__":
    main()

