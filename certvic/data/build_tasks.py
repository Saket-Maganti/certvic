"""Build task manifests."""

from __future__ import annotations

import argparse
import json

from certvic.data.smoke_fixtures import generate_smoke_tasks
from certvic.io import write_jsonl


def build_smoke_tasks(out_path: str, n_items: int = 12) -> dict:
    tasks = generate_smoke_tasks(n_items=n_items)
    write_jsonl(out_path, tasks)
    return {"n": len(tasks), "split": "smoke", "families": sorted({t.task_family for t in tasks})}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--source-manifest")
    parser.add_argument("--edit-manifest")
    parser.add_argument("--out", required=True)
    parser.add_argument("--split", default="pilot")
    parser.add_argument("--n-items", type=int, default=12)
    args = parser.parse_args(argv)
    if not args.smoke:
        raise SystemExit("Only --smoke task building is implemented in V1 without local data inputs.")
    summary = build_smoke_tasks(args.out, n_items=args.n_items)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
