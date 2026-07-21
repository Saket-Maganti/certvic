"""Resume planner for the diffusion edit-generation job queue (V3 prompt 04).

Given a job queue plus whatever a prior (possibly crashed) session produced,
compute the set of jobs that still need (re)running, increment their retry
counts, and flag jobs that have exhausted their retry budget. Pure bookkeeping:
no generation, no GPU, no heavy imports.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from certvic.edit.job_queue import (
    INCOMPLETE_STATUSES,
    QueueEntry,
    _status_for,
    load_queue,
)
from certvic.io import read_jsonl, write_jsonl

DEFAULT_MAX_RETRIES = 3


def resume_plan(
    queue_path: str,
    generated_path: str,
    *,
    rejected_path: str | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> dict:
    entries = load_queue(queue_path)
    generated = read_jsonl(generated_path) if Path(generated_path).exists() else []
    gen_by_id = {str(r.get("edit_id")): r for r in generated}
    rejected_ids = {str(r.get("edit_id")) for r in read_jsonl(rejected_path)} if rejected_path and Path(rejected_path).exists() else set()

    to_run: list[QueueEntry] = []
    give_up: list[QueueEntry] = []
    for e in entries:
        st = _status_for(e, gen_by_id.get(e.edit_id), rejected_ids)
        if st not in INCOMPLETE_STATUSES:
            continue
        next_entry = e.model_copy(update={"status": st, "retry_count": e.retry_count + 1})
        if next_entry.retry_count > max_retries:
            give_up.append(next_entry)
        else:
            to_run.append(next_entry)

    # Run highest-priority, lowest-shard first for predictable session ordering.
    to_run.sort(key=lambda x: (x.priority, x.shard_id, x.edit_id))

    return {
        "resume": "certvic_diffusion_resume_plan",
        "queue": queue_path,
        "max_retries": max_retries,
        "n_total": len(entries),
        "n_to_run": len(to_run),
        "n_give_up": len(give_up),
        "to_run_by_shard": dict(sorted(Counter(e.shard_id for e in to_run).items())),
        "to_run_by_status": dict(sorted(Counter(e.status for e in to_run).items())),
        "to_run": to_run,
        "give_up": give_up,
        "evidence_status": "JOB_PLANNED_ONLY",
        "evidence_claims_made": False,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC diffusion resume planner")
    parser.add_argument("--queue", required=True)
    parser.add_argument("--generated", required=True)
    parser.add_argument("--rejected")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--out", required=True, help="JSONL of jobs to (re)run")
    parser.add_argument("--give-up-out", help="optional JSONL of retry-exhausted jobs")
    args = parser.parse_args(argv)
    plan = resume_plan(args.queue, args.generated, rejected_path=args.rejected, max_retries=args.max_retries)
    write_jsonl(args.out, [e.model_dump(mode="json") for e in plan["to_run"]])
    if args.give_up_out:
        write_jsonl(args.give_up_out, [e.model_dump(mode="json") for e in plan["give_up"]])
    print(json.dumps({
        "n_total": plan["n_total"],
        "n_to_run": plan["n_to_run"],
        "n_give_up": plan["n_give_up"],
        "to_run_by_shard": plan["to_run_by_shard"],
        "out": args.out,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
