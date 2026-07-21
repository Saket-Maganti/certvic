"""Run construct-validity baselines over reviewed tasks.

Writes one prediction file per baseline plus an index. These are not evidence;
they defend construct validity (the task cannot be solved without seeing the
change).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.eval.ablation_baselines import (
    BASELINES,
    baseline_raw_outputs,
    build_context,
    score_item,
    summarize,
)
from certvic.io import read_jsonl, write_json, write_jsonl


def run_ablations(tasks_path: str, out_dir: str, max_items: int = 50, seed: int = 0) -> dict:
    tasks = read_jsonl(tasks_path)[:max_items]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    context = build_context(tasks)

    index: dict[str, dict] = {}
    for name in BASELINES:
        rows = []
        for task in tasks:
            raw_o, raw_e = baseline_raw_outputs(name, task, context, seed)
            rows.append(score_item(task, raw_o, raw_e))
        write_jsonl(out / f"{name}.jsonl", rows)
        index[name] = summarize(rows)

    summary = {
        "tasks_path": tasks_path,
        "out_dir": out_dir,
        "n_tasks": len(tasks),
        "seed": seed,
        "baselines": BASELINES,
        "baseline_summaries": index,
        "evidence_status": "CONSTRUCT_VALIDITY_NON_EVIDENCE",
        "vlm_inference_run": False,
        "paper_evidence": False,
    }
    write_json(out / "ablation_index.json", summary)
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run construct-validity baseline ablations")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-items", type=int, default=50)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    print(json.dumps(run_ablations(args.tasks, args.out_dir, max_items=args.max_items, seed=args.seed), sort_keys=True))


if __name__ == "__main__":
    main()
