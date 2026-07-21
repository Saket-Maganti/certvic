"""Edit-generation progress plan/report over the diffusion job queue (V3 prompt 04).

A thin reporting layer that combines a job queue with whatever has been generated
so far into a human-readable progress report: overall completion, per-shard
progress, per-edit-type breakdown, and the remaining/at-risk jobs. Planning only;
no generation, no GPU, no heavy imports.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from pathlib import Path

from certvic.edit.diffusion_resume import resume_plan
from certvic.edit.job_queue import load_queue, queue_status, verify_sharding
from certvic.io import ensure_parent


def build_plan_report(
    queue_path: str,
    generated_path: str,
    *,
    rejected_path: str | None = None,
    num_shards: int | None = None,
    max_retries: int = 3,
) -> dict:
    entries = load_queue(queue_path)
    shards = num_shards if num_shards is not None else (max((e.shard_id for e in entries), default=-1) + 1)
    status = queue_status(queue_path, generated_path, rejected_path=rejected_path)
    sharding = verify_sharding(entries, max(shards, 1))
    resume = resume_plan(queue_path, generated_path, rejected_path=rejected_path, max_retries=max_retries)
    return {
        "plan": "certvic_edit_generation_plan",
        "queue": queue_path,
        "n_jobs": status["n_jobs"],
        "num_shards": max(shards, 1),
        "completion_fraction": status["completion_fraction"],
        "status_counts": status["status_counts"],
        "per_shard": status["per_shard"],
        "complete_shards": status["complete_shards"],
        "sharding": sharding,
        "by_edit_type": dict(sorted(Counter(e.edit_type for e in entries).items())),
        "n_to_run": resume["n_to_run"],
        "n_give_up": resume["n_give_up"],
        "all_done": status["all_done"],
        "evidence_claims_made": False,
    }


def render_report(plan: dict) -> str:
    lines = [
        "# Edit Generation Plan / Progress",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Queue: `{plan['queue']}`",
        f"Jobs: {plan['n_jobs']} across {plan['num_shards']} shards",
        f"Completion: {plan['completion_fraction'] * 100:.1f}%  (all done: {plan['all_done']})",
        f"Remaining to run: {plan['n_to_run']}  |  retry-exhausted: {plan['n_give_up']}",
        "",
        "Planning artifact only (`JOB_PLANNED_ONLY`); not evidence.",
        "",
        "## Status counts",
        "",
        "| Status | Count |",
        "| --- | --- |",
        *[f"| {k} | {v} |" for k, v in plan["status_counts"].items()],
        "",
        "## Per-shard progress",
        "",
        "| Shard | Done | Total |",
        "| --- | --- | --- |",
        *[f"| {sid} | {b['done']} | {b['total']} |" for sid, b in plan["per_shard"].items()],
        "",
        "## By edit type",
        "",
        *[f"- {et}: {n}" for et, n in plan["by_edit_type"].items()],
        "",
        f"Sharding complete: {plan['sharding']['complete']}; no overlap: {plan['sharding']['no_overlap']}.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC edit-generation progress report")
    parser.add_argument("--queue", required=True)
    parser.add_argument("--generated", required=True)
    parser.add_argument("--rejected")
    parser.add_argument("--num-shards", type=int)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    plan = build_plan_report(args.queue, args.generated, rejected_path=args.rejected, num_shards=args.num_shards)
    ensure_parent(args.out)
    Path(args.out).write_text(render_report(plan), encoding="utf-8")
    import json

    print(json.dumps({"n_jobs": plan["n_jobs"], "completion_fraction": plan["completion_fraction"], "n_to_run": plan["n_to_run"], "out": args.out}, sort_keys=True))


if __name__ == "__main__":
    main()
