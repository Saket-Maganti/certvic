"""Smoke edit-building CLI."""

from __future__ import annotations

import argparse
import json

from certvic.io import load_model_jsonl, write_jsonl
from certvic.schema import TaskItem


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--mode", default="smoke")
    args = parser.parse_args(argv)
    tasks = load_model_jsonl(args.tasks, TaskItem)
    edits = [task.edit for task in tasks]
    write_jsonl(args.out_manifest, edits)
    print(json.dumps({"n": len(edits), "mode": args.mode}, sort_keys=True))


if __name__ == "__main__":
    main()
