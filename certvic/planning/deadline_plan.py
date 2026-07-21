"""Deadline and critical-path planner."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

TASK_DURATIONS = [
    ("real_data_available", 7),
    ("tiny_pilot_complete", 7),
    ("main_200_complete", 14),
    ("scale_1000_2000_complete", 28),
    ("paper_draft_complete", 10),
    ("artifact_freeze", 5),
    ("submission_package", 3),
]


def build_critical_path(target_date: str) -> dict:
    target = datetime.strptime(target_date, "%Y-%m-%d").date()
    cursor = target
    rows = []
    for task, days in reversed(TASK_DURATIONS):
        start = cursor - timedelta(days=days)
        rows.append({"task": task, "start": start.isoformat(), "end": cursor.isoformat(), "duration_days": days})
        cursor = start
    rows.reverse()
    impossible = rows[0]["start"] < date.today().isoformat()
    return {
        "target_date": target_date,
        "critical_path": rows,
        "buffer_days": max(0, (target - date.today()).days - sum(days for _, days in TASK_DURATIONS)),
        "impossible_schedule": impossible,
    }


def render_critical_path(plan: dict) -> str:
    lines = ["# CVPR 2027 Critical Path", "", f"Target date: {plan['target_date']}", f"Buffer days: {plan['buffer_days']}", "", "| Task | Start | End | Days |", "| --- | --- | --- | --- |"]
    for row in plan["critical_path"]:
        lines.append(f"| {row['task']} | {row['start']} | {row['end']} | {row['duration_days']} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build deadline critical path")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    plan = build_critical_path(args.target_date)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_critical_path(plan), encoding="utf-8")
    print(json.dumps({"out": args.out, "impossible_schedule": plan["impossible_schedule"]}, sort_keys=True))


if __name__ == "__main__":
    main()
