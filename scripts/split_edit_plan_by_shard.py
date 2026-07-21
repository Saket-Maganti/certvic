"""Split an edit plan into deterministic per-shard files (CPU-only, no evidence).

Hands disjoint edit-plan subsets to parallel free-GPU diffusion workers (one
shard per GPU). Sharding matches ``certvic.edit.job_queue`` (``shard_for_item``
keyed on ``edit_id``), so per-shard files line up exactly with the diffusion job
queue and its resume planner. No GPU, no downloads, no heavy imports.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.eval.sharding import shard_for_item
from certvic.io import read_jsonl, write_jsonl


def split_edit_plan(edit_plan_path: str, out_dir: str, num_shards: int) -> dict:
    if num_shards <= 0:
        raise ValueError("num_shards must be positive")
    rows = read_jsonl(edit_plan_path)
    buckets: dict[int, list[dict]] = {i: [] for i in range(num_shards)}
    for row in rows:
        edit_id = str(row.get("edit_id"))
        buckets[shard_for_item(edit_id, num_shards)].append(row)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files: dict[str, int] = {}
    for i in range(num_shards):
        path = out / f"pilot_edit_plan_shard{i}_of_{num_shards}.jsonl"
        write_jsonl(str(path), buckets[i])
        files[str(path)] = len(buckets[i])
    return {
        "edit_plan": edit_plan_path,
        "num_shards": num_shards,
        "n_rows": len(rows),
        "shard_sizes": {i: len(buckets[i]) for i in range(num_shards)},
        "files": files,
        "evidence_status": "JOB_PLANNED_ONLY",
        "evidence_claims_made": False,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Split an edit plan into per-shard files for parallel GPU workers"
    )
    parser.add_argument("--edit-plan", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--num-shards", type=int, default=2)
    args = parser.parse_args(argv)
    print(json.dumps(split_edit_plan(args.edit_plan, args.out_dir, args.num_shards), sort_keys=True))


if __name__ == "__main__":
    main()
