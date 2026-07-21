"""Build non-runnable task previews from planned edits."""

from __future__ import annotations

import argparse
import json
from collections import Counter

from certvic.data.task_templates import template_for_family
from certvic.io import read_jsonl, write_json, write_jsonl
from certvic.schema import AnswerFormat
from certvic.validation.leakage import check_path_no_leakage, check_prompt_no_leakage


class TaskPreviewError(ValueError):
    """Raised when task previews cannot be written."""


def build_task_preview(edit_plan_path: str, out_path: str, summary_out: str) -> dict:
    plans = read_jsonl(edit_plan_path)
    previews = [_preview_record(row) for row in plans]
    write_jsonl(out_path, previews)
    leakage_warnings = [
        warning
        for preview in previews
        for warning in preview.get("leakage_warnings", [])
    ]
    summary = {
        "edit_plan_path": edit_plan_path,
        "task_preview_path": out_path,
        "input_planned_edits": len(plans),
        "preview_tasks": len(previews),
        "runnable_eval_tasks": 0,
        "edited_images_required": False,
        "edited_images_available": 0,
        "by_task_family": dict(sorted(Counter(row["task_family"] for row in previews).items())),
        "by_required_change": dict(sorted(Counter(row["required_change"] for row in previews).items())),
        "leakage_warning_count": len(leakage_warnings),
        "leakage_warnings": leakage_warnings,
        "evidence_status": "PREVIEW_ONLY",
        "generation_status": "not_generated",
        "edits_generated": False,
        "vlm_inference_run": False,
    }
    write_json(summary_out, summary)
    return summary


def _preview_record(plan: dict) -> dict:
    family = str(plan["task_family"])
    try:
        template = template_for_family(family)
    except ValueError as exc:
        raise TaskPreviewError(f"Cannot build preview for unknown task family {family}") from exc
    required_change = str(plan.get("required_change") or template["required_change"])
    answer_original = str(template["answer_original"])
    answer_edited = str(template["answer_edited"])
    if required_change == "no_change":
        answer_edited = answer_original
    edited_image_path = str(plan.get("planned_edited_image_path") or f"planned://pilot/{plan['edit_id']}")
    question = str(template["question"])
    leakage_warnings = _leakage_warnings(
        question,
        question,
        answer_original,
        answer_edited,
        str(plan.get("image_path") or ""),
        edited_image_path,
    )
    return {
        "item_id": f"preview_{plan['edit_id']}",
        "edit_id": plan["edit_id"],
        "source_id": plan["source_id"],
        "mask_id": plan.get("mask_id"),
        "task_family": family,
        "domain": plan.get("domain", "household"),
        "split": plan.get("split", "pilot"),
        "edit_type": plan["edit_type"],
        "required_change": required_change,
        "answer_format": AnswerFormat.YES_NO.value,
        "original_image_path": plan.get("image_path"),
        "edited_image_path": edited_image_path,
        "edited_image_status": "planned_unavailable",
        "question_original": question,
        "question_edited": question,
        "answer_original": answer_original,
        "answer_edited": answer_edited,
        "expected_effect": plan.get("expected_effect"),
        "single_factor": bool(plan.get("single_factor", True)),
        "runnable_eval_task": False,
        "not_runnable_reason": "edited image has not been generated or quality-gated",
        "evidence_status": "PREVIEW_ONLY",
        "generation_status": "not_generated",
        "zero_cost": True,
        "leakage_warnings": leakage_warnings,
    }


def _leakage_warnings(
    question_original: str,
    question_edited: str,
    answer_original: str,
    answer_edited: str,
    original_image_path: str,
    edited_image_path: str,
) -> list[str]:
    warnings: list[str] = []
    answers = [answer_original, answer_edited]
    warnings.extend(check_prompt_no_leakage(question_original, answers=answers))
    warnings.extend(check_prompt_no_leakage(question_edited, answers=answers))
    warnings.extend(check_path_no_leakage(original_image_path))
    warnings.extend(check_path_no_leakage(edited_image_path))
    return warnings


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edit-plan", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--summary-out", required=True)
    args = parser.parse_args(argv)
    try:
        summary = build_task_preview(args.edit_plan, args.out, args.summary_out)
    except TaskPreviewError as exc:
        raise SystemExit(f"Task preview failed: {exc}") from None
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
