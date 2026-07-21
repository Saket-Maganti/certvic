"""Materialize tiny non-evidence eval-task manifests from previews and generated edits."""

from __future__ import annotations

import argparse
import json
from collections import Counter

from certvic.io import read_jsonl, write_json, write_jsonl
from certvic.validation.leakage import check_path_no_leakage, check_prompt_no_leakage


def materialize_tasks(
    task_preview_path: str,
    generated_edits_path: str,
    out_path: str,
    summary_out: str,
) -> dict:
    previews = read_jsonl(task_preview_path)
    generated = read_jsonl(generated_edits_path)
    generated_by_edit_id = {
        row["edit_id"]: row
        for row in generated
        if row.get("generation_status") == "generated" and row.get("quality_gate_status") == "pass"
    }
    materialized: list[dict] = []
    leakage_rejected = 0
    missing_or_failed = 0
    for preview in previews:
        edit = generated_by_edit_id.get(preview.get("edit_id"))
        if edit is None:
            missing_or_failed += 1
            continue
        row = _materialized_row(preview, edit)
        if row["leakage_warnings"]:
            leakage_rejected += 1
            continue
        materialized.append(row)

    write_jsonl(out_path, materialized)
    summary = {
        "task_preview_path": task_preview_path,
        "generated_edits_path": generated_edits_path,
        "out": out_path,
        "preview_rows": len(previews),
        "generated_quality_pass_rows": len(generated_by_edit_id),
        "materialized_tasks": len(materialized),
        "missing_or_quality_failed": missing_or_failed,
        "leakage_rejected": leakage_rejected,
        "by_task_family": dict(sorted(Counter(row.get("task_family") for row in materialized).items())),
        "evidence_status": "EDIT_READY_NON_EVIDENCE",
        "paper_evidence": False,
        "vlm_inference_run": False,
    }
    write_json(summary_out, summary)
    return summary


def _materialized_row(preview: dict, edit: dict) -> dict:
    row = dict(preview)
    row.update(
        {
            "edited_image_path": edit["edited_image_path"],
            "edited_image_status": "generated_quality_passed",
            "generated_edit_id": edit["edit_id"],
            "edited_sha256": edit.get("edited_sha256"),
            "generator_mode": edit.get("generator_mode"),
            "quality_gate_status": edit.get("quality_gate_status"),
            "quality": edit.get("quality"),
            "runnable_eval_task": True,
            "not_runnable_reason": None,
            "evidence_status": "EDIT_READY_NON_EVIDENCE",
            "generation_status": "generated",
            "paper_evidence": False,
            "vlm_inference_run": False,
        }
    )
    row["original_image_path"] = preview.get("original_image_path") or edit.get("original_image_path")
    row["leakage_warnings"] = _leakage_warnings(row)
    return row


def _leakage_warnings(row: dict) -> list[str]:
    answers = [str(row.get("answer_original", "")), str(row.get("answer_edited", ""))]
    warnings: list[str] = []
    warnings.extend(check_prompt_no_leakage(str(row.get("question_original", "")), answers=answers))
    warnings.extend(check_prompt_no_leakage(str(row.get("question_edited", "")), answers=answers))
    warnings.extend(check_path_no_leakage(str(row.get("original_image_path", ""))))
    warnings.extend(check_path_no_leakage(str(row.get("edited_image_path", ""))))
    return warnings


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-preview", required=True)
    parser.add_argument("--generated-edits", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--summary-out", required=True)
    args = parser.parse_args(argv)
    summary = materialize_tasks(args.task_preview, args.generated_edits, args.out, args.summary_out)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
