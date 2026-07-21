"""Diffusion edit-generation job queue (V3 prompt 04).

Turns a planned edit plan into a shardable, resumable, retry-aware job queue so
free GPU sessions can split the work, resume after a crash, and avoid generating
duplicates. Planning/bookkeeping only: no image generation, no GPU, no heavy
imports (no torch/diffusers/cv2). Queue entries are ``JOB_PLANNED_ONLY`` and are
never evidence.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from certvic.edit.engines import ALL_ENGINES, default_engine_for_edit_type
from certvic.eval.sharding import item_in_shard, shard_for_item
from certvic.hashing import sha256_bytes, sha256_file, stable_json_dumps
from certvic.io import ensure_parent, read_jsonl, write_jsonl
from certvic.schema import EditType

EVIDENCE_STATUS = "JOB_PLANNED_ONLY"
DEFAULT_ENGINE = "diffusers_inpaint_optional"
DEFAULT_EDIT_OUT_DIR = "data/edits/ade20k_pilot"

# Lower number runs earlier. Controls last so the core interventions land first.
PRIORITY_BY_EDIT_TYPE = {
    EditType.REMOVE.value: 0,
    EditType.OCCLUDE.value: 1,
    EditType.DISPLACE.value: 2,
    EditType.CONTROL_IRRELEVANT.value: 3,
}

# Job statuses.
PENDING = "pending"
GENERATED = "generated"
REJECTED = "rejected"
FAILED = "failed"
DUPLICATE = "duplicate"
MISSING_OUTPUT = "missing_output"
HASH_MISMATCH = "hash_mismatch"
ALL_STATUSES = (PENDING, GENERATED, REJECTED, FAILED, DUPLICATE, MISSING_OUTPUT, HASH_MISMATCH)
# Statuses that still need (re)work.
INCOMPLETE_STATUSES = {PENDING, FAILED, MISSING_OUTPUT, HASH_MISMATCH}


class QueueEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    edit_id: str
    source_id: str | None = None
    mask_id: str | None = None
    edit_type: str | None = None
    engine: str = DEFAULT_ENGINE
    priority: int = 99
    shard_id: int = 0
    retry_count: int = 0
    status: str = PENDING
    expected_output_path: str = ""
    config_hash: str | None = None
    evidence_status: str = EVIDENCE_STATUS


def _config_hash(edit_plan_path: str, engine: str, num_shards: int) -> str:
    plan_sha = sha256_file(edit_plan_path) if Path(edit_plan_path).exists() else None
    payload = {"edit_plan": str(edit_plan_path), "edit_plan_sha256": plan_sha, "engine": engine, "num_shards": num_shards}
    return sha256_bytes(stable_json_dumps(payload).encode("utf-8"))


def build_queue(
    edit_plan_path: str,
    *,
    num_shards: int = 4,
    engine: str | None = None,
    edit_out_dir: str = DEFAULT_EDIT_OUT_DIR,
) -> dict:
    if num_shards <= 0:
        raise ValueError("num_shards must be positive")
    if engine is not None and engine not in ALL_ENGINES:
        raise ValueError(f"unknown engine '{engine}'; expected one of {sorted(ALL_ENGINES)}")
    plans = read_jsonl(edit_plan_path)
    cfg_hash = _config_hash(edit_plan_path, engine or "per_edit_type_default", num_shards)

    entries: list[QueueEntry] = []
    seen: set[str] = set()
    for plan in plans:
        edit_id = str(plan.get("edit_id"))
        if not edit_id or edit_id == "None":
            continue
        if edit_id in seen:  # the plan should already be unique; guard anyway
            continue
        seen.add(edit_id)
        edit_type = str(plan.get("edit_type") or "")
        chosen = engine or default_engine_for_edit_type(edit_type)
        entries.append(QueueEntry(
            job_id=f"job_{edit_id}",
            edit_id=edit_id,
            source_id=plan.get("source_id"),
            mask_id=plan.get("mask_id"),
            edit_type=edit_type or None,
            engine=chosen,
            priority=PRIORITY_BY_EDIT_TYPE.get(edit_type, 99),
            shard_id=shard_for_item(edit_id, num_shards),
            expected_output_path=str(Path(edit_out_dir) / f"{edit_id}.png"),
            config_hash=cfg_hash,
        ))

    return {
        "queue": "certvic_diffusion_job_queue",
        "edit_plan": edit_plan_path,
        "num_shards": num_shards,
        "engine": engine or "per_edit_type_default",
        "n_jobs": len(entries),
        "shard_sizes": dict(sorted(Counter(e.shard_id for e in entries).items())),
        "by_edit_type": dict(sorted(Counter(e.edit_type for e in entries).items())),
        "entries": entries,
        "evidence_status": EVIDENCE_STATUS,
        "downloads_attempted": False,
        "paid_services": False,
        "evidence_claims_made": False,
    }


def write_queue(result: dict, out_path: str) -> None:
    ensure_parent(out_path)
    write_jsonl(out_path, [e.model_dump(mode="json") for e in result["entries"]])


def load_queue(path: str) -> list[QueueEntry]:
    return [QueueEntry.model_validate(row) for row in read_jsonl(path)]


def verify_sharding(entries: list[QueueEntry], num_shards: int) -> dict:
    """Sharding is complete (every job assigned) and non-overlapping (one shard each)."""
    per_shard: dict[int, set[str]] = {i: set() for i in range(num_shards)}
    overlap = 0
    for e in entries:
        s = shard_for_item(e.edit_id, num_shards)
        if any(e.edit_id in per_shard[i] for i in per_shard):
            overlap += 1
        per_shard[s].add(e.edit_id)
    covered = sum(len(v) for v in per_shard.values())
    return {
        "num_shards": num_shards,
        "n_jobs": len(entries),
        "covered": covered,
        "complete": covered == len(entries),
        "no_overlap": overlap == 0,
        "shard_sizes": {i: len(per_shard[i]) for i in range(num_shards)},
    }


def _status_for(entry: QueueEntry, gen_row: dict | None, rejected_ids: set[str]) -> str:
    if entry.edit_id in rejected_ids:
        return REJECTED
    if gen_row is None:
        return PENDING
    if gen_row.get("duplicate_of"):
        return DUPLICATE
    if str(gen_row.get("generation_status", "generated")) != "generated":
        return FAILED
    path = gen_row.get("edited_image_path") or entry.expected_output_path
    if not path or not Path(path).exists():
        return MISSING_OUTPUT
    recorded = gen_row.get("edited_sha256")
    if recorded and sha256_file(path) != recorded:
        return HASH_MISMATCH
    return GENERATED


def queue_status(queue_path: str, generated_path: str, *, rejected_path: str | None = None) -> dict:
    entries = load_queue(queue_path)
    generated = read_jsonl(generated_path) if Path(generated_path).exists() else []
    gen_by_id = {str(r.get("edit_id")): r for r in generated}
    rejected_ids = {str(r.get("edit_id")) for r in read_jsonl(rejected_path)} if rejected_path and Path(rejected_path).exists() else set()

    statuses: dict[str, int] = {s: 0 for s in ALL_STATUSES}
    per_shard_done: dict[int, dict[str, int]] = {}
    remaining: list[str] = []
    for e in entries:
        st = _status_for(e, gen_by_id.get(e.edit_id), rejected_ids)
        statuses[st] += 1
        bucket = per_shard_done.setdefault(e.shard_id, {"total": 0, "done": 0})
        bucket["total"] += 1
        if st == GENERATED:
            bucket["done"] += 1
        if st in INCOMPLETE_STATUSES:
            remaining.append(e.job_id)

    n = len(entries)
    done = statuses[GENERATED]
    complete_shards = sorted(s for s, b in per_shard_done.items() if b["total"] and b["done"] == b["total"])
    return {
        "queue": queue_path,
        "generated": generated_path,
        "rejected": rejected_path,
        "n_jobs": n,
        "status_counts": statuses,
        "completion_fraction": round(done / n, 4) if n else 0.0,
        "per_shard": {str(k): v for k, v in sorted(per_shard_done.items())},
        "complete_shards": complete_shards,
        "remaining_jobs": remaining,
        "all_done": n > 0 and done == n,
        "evidence_claims_made": False,
    }


def next_shard(queue_path: str, shard_index: int, num_shards: int) -> list[QueueEntry]:
    if shard_index < 0 or shard_index >= num_shards:
        raise ValueError("shard_index must be in [0, num_shards)")
    entries = load_queue(queue_path)
    return [e for e in entries if item_in_shard(e.edit_id, shard_index, num_shards)]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC diffusion edit-generation job queue")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("build", help="build a job queue from an edit plan")
    pb.add_argument("--edit-plan", required=True)
    pb.add_argument("--out", required=True)
    pb.add_argument("--shards", type=int, default=4)
    pb.add_argument("--engine", choices=sorted(ALL_ENGINES))
    pb.add_argument("--edit-out-dir", default=DEFAULT_EDIT_OUT_DIR)

    ps = sub.add_parser("status", help="compute queue completion status")
    ps.add_argument("--queue", required=True)
    ps.add_argument("--generated", required=True)
    ps.add_argument("--rejected")
    ps.add_argument("--out", required=True)

    pn = sub.add_parser("next-shard", help="emit the jobs for one shard")
    pn.add_argument("--queue", required=True)
    pn.add_argument("--shard-index", type=int, required=True)
    pn.add_argument("--num-shards", type=int, required=True)
    pn.add_argument("--out", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "build":
        result = build_queue(args.edit_plan, num_shards=args.shards, engine=args.engine, edit_out_dir=args.edit_out_dir)
        write_queue(result, args.out)
        check = verify_sharding(result["entries"], args.shards)
        print(json.dumps({"n_jobs": result["n_jobs"], "shard_sizes": result["shard_sizes"], "sharding": check, "out": args.out}, sort_keys=True))
        return

    if args.cmd == "status":
        result = queue_status(args.queue, args.generated, rejected_path=args.rejected)
        ensure_parent(args.out)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"n_jobs": result["n_jobs"], "completion_fraction": result["completion_fraction"], "status_counts": result["status_counts"], "all_done": result["all_done"], "out": args.out}, sort_keys=True))
        return

    if args.cmd == "next-shard":
        entries = next_shard(args.queue, args.shard_index, args.num_shards)
        write_queue({"entries": entries}, args.out)
        print(json.dumps({"shard_index": args.shard_index, "num_shards": args.num_shards, "n_jobs": len(entries), "out": args.out}, sort_keys=True))
        return


if __name__ == "__main__":
    main()
