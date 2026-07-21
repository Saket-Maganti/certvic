"""Human validation sheet export."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

from certvic.io import load_model_jsonl
from certvic.schema import TaskItem


def export_human_sheet(
    tasks_path: str,
    out_path: str,
    max_items: int = 300,
    seed: int = 0,
    include_answers: bool = False,
) -> int:
    tasks = load_model_jsonl(tasks_path, TaskItem)
    rng = random.Random(seed)
    rng.shuffle(tasks)
    tasks = tasks[:max_items]
    fields = [
        "item_id",
        "original_path_or_pointer",
        "edited_path_or_pointer",
        "task_family",
        "domain",
        "neutral_question",
        "photorealistic",
        "single_factor",
        "required_change_unambiguous",
        "notes",
    ]
    if include_answers:
        fields.extend(["answer_original", "answer_edited"])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(out_path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for task in tasks:
            row = {
                "item_id": task.item_id,
                "original_path_or_pointer": task.original_image_path,
                "edited_path_or_pointer": task.edited_image_path,
                "task_family": task.task_family,
                "domain": task.domain,
                "neutral_question": task.question_original,
                "photorealistic": "",
                "single_factor": "",
                "required_change_unambiguous": "",
                "notes": "",
            }
            if include_answers:
                row["answer_original"] = task.answer_original
                row["answer_edited"] = task.answer_edited
            writer.writerow(row)
    return len(tasks)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-items", type=int, default=300)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--include-answers", action="store_true")
    args = parser.parse_args(argv)
    n = export_human_sheet(args.tasks, args.out, args.max_items, args.seed, args.include_answers)
    print(f"wrote {n} rows")


if __name__ == "__main__":
    main()
