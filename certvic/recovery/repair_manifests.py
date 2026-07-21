"""Dry-run manifest repair helpers."""

from __future__ import annotations

import argparse
import json

from certvic.io import read_jsonl, write_json, write_jsonl


def repair_manifest(input_path: str, out: str, *, dry_run: bool = True) -> dict:
    rows = read_jsonl(input_path)
    repaired: list[dict] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for row in rows:
        key = str(row.get("item_id") or row.get("edit_id") or row.get("job_id") or len(repaired))
        if key in seen:
            duplicates.append(key)
            continue
        seen.add(key)
        repaired.append(row)
    if not dry_run:
        write_jsonl(out, repaired)
    plan = {
        "input": input_path,
        "out": out,
        "dry_run": dry_run,
        "n_input": len(rows),
        "n_repaired": len(repaired),
        "duplicates": duplicates,
        "hash_mismatches_fixed": False,
    }
    write_json(out + ".repair_plan.json", plan)
    return plan


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Repair JSONL manifests")
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", help="write repaired JSONL")
    args = parser.parse_args(argv)
    print(json.dumps(repair_manifest(args.input, args.out, dry_run=not args.apply), sort_keys=True))


if __name__ == "__main__":
    main()

