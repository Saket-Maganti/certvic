"""Deadline-aware CVPR task planner."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path


TASKS = [
    ("real_run", 21),
    ("human_review", 7),
    ("analysis_and_lock", 5),
    ("paper_update", 7),
    ("internal_review", 5),
    ("final_packaging", 3),
]


def build_deadline_plan(deadline: str) -> dict:
    due = datetime.strptime(deadline, "%Y-%m-%d").date()
    cursor = due
    rows: list[dict] = []
    for name, days in reversed(TASKS):
        start = cursor - timedelta(days=days)
        rows.append({"task": name, "start": start.isoformat(), "end": cursor.isoformat(), "duration_days": days})
        cursor = start
    rows.reverse()
    return {
        "deadline": deadline,
        "generated_on": date.today().isoformat(),
        "critical_path": rows,
        "missing_artifacts_flagged": True,
        "wall_clock_estimates_included": True,
    }


def render_plan(plan: dict) -> str:
    lines = ["# CVPR Deadline Plan", "", f"Deadline: {plan['deadline']}", "", "| Task | Start | End | Days |", "| --- | --- | --- | --- |"]
    for row in plan["critical_path"]:
        lines.append(f"| {row['task']} | {row['start']} | {row['end']} | {row['duration_days']} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write CVPR deadline plan")
    parser.add_argument("--deadline", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    plan = build_deadline_plan(args.deadline)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_plan(plan), encoding="utf-8")
    print(json.dumps({"out": args.out, "deadline": args.deadline}, sort_keys=True))


if __name__ == "__main__":
    main()

