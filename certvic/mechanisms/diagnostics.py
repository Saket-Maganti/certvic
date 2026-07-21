"""Plan diagnostic prompts for visual decision-update mechanisms."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import read_jsonl, write_jsonl

DIAGNOSTIC_PROMPTS = {
    "direct_answer": {
        "analysis_role": "primary_if_preregistered_else_diagnostic",
        "prompt": "Answer the visual question directly from the image only.",
    },
    "localize_then_answer": {
        "analysis_role": "exploratory_diagnostic",
        "prompt": "First localize the relevant changed region, then answer the question.",
    },
    "describe_changed_region_then_answer": {
        "analysis_role": "exploratory_diagnostic",
        "prompt": "Describe the changed region visible in the image, then answer the question.",
    },
    "crop_focused_diagnostic": {
        "analysis_role": "exploratory_diagnostic",
        "prompt": "Focus on the provided crop or target region and answer the question.",
    },
    "multiple_choice_diagnostic": {
        "analysis_role": "exploratory_diagnostic",
        "prompt": "Choose the best answer from the provided choices using only the image.",
    },
}

MECHANISM_FAMILIES = (
    "answer_inertia",
    "localization_failure",
    "text_prior_anchoring",
    "prompt_form_sensitivity",
    "edit_type_sensitivity",
    "crop_region_sensitivity",
)


def plan_diagnostics(tasks_path: str) -> list[dict]:
    rows = read_jsonl(tasks_path)
    planned: list[dict] = []
    for task in rows:
        item_id = str(task.get("item_id") or task.get("edit_id"))
        for label, spec in DIAGNOSTIC_PROMPTS.items():
            planned.append(
                {
                    "item_id": item_id,
                    "diagnostic_prompt_label": label,
                    "prompt": spec["prompt"],
                    "analysis_role": spec["analysis_role"],
                    "primary_claim_default": False,
                    "mechanism_families": list(MECHANISM_FAMILIES),
                    "task_family": task.get("task_family"),
                    "edit_type": (task.get("edit") or {}).get("edit_type") or task.get("edit_type"),
                    "evidence_status": "DIAGNOSTIC_PLAN_ONLY_NON_EVIDENCE",
                }
            )
    return planned


def write_plan(tasks_path: str, out_path: str) -> dict:
    planned = plan_diagnostics(tasks_path)
    write_jsonl(out_path, planned)
    return {
        "tasks": tasks_path,
        "out": out_path,
        "n_tasks": len(read_jsonl(tasks_path)),
        "n_diagnostic_rows": len(planned),
        "prompt_labels": sorted(DIAGNOSTIC_PROMPTS),
        "evidence_status": "DIAGNOSTIC_PLAN_ONLY_NON_EVIDENCE",
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Mechanism diagnostic planner")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="write diagnostic prompt manifest")
    plan.add_argument("--tasks", required=True)
    plan.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "plan":
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        print(json.dumps(write_plan(args.tasks, args.out), sort_keys=True))


if __name__ == "__main__":
    main()
