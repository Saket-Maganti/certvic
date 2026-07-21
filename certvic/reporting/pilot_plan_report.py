"""Review report for pilot candidate and edit-plan artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from certvic.io import read_jsonl, write_json


def build_pilot_plan_report(
    selection_path: str,
    edit_plan_path: str,
    task_preview_path: str,
    out_dir: str,
) -> dict:
    selection = read_jsonl(selection_path)
    edit_plan = read_jsonl(edit_plan_path)
    task_preview = read_jsonl(task_preview_path)
    rejected_path = Path(edit_plan_path).with_name("pilot_edit_plan_rejected.jsonl")
    rejected = read_jsonl(rejected_path) if rejected_path.exists() else []

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    selection_by_family = _count_rows(selection, ["proposed_task_family"])
    selection_by_label = _count_rows(selection, ["label_id", "label_name"])
    edit_plan_by_type = _count_rows(edit_plan, ["edit_type"])
    _write_csv(out / "selection_by_family.csv", selection_by_family)
    _write_csv(out / "selection_by_label.csv", selection_by_label)
    _write_csv(out / "edit_plan_by_type.csv", edit_plan_by_type)
    if rejected:
        _write_csv(out / "rejected_candidates.csv", _rejected_rows(rejected))

    leakage_summary = _leakage_summary(task_preview)
    feasibility_summary = _feasibility_summary(selection, edit_plan, rejected)
    write_json(out / "leakage_check_summary.json", leakage_summary)
    write_json(out / "feasibility_summary.json", feasibility_summary)
    (out / "pilot_plan_report.md").write_text(
        _markdown_report(
            selection_path=selection_path,
            edit_plan_path=edit_plan_path,
            task_preview_path=task_preview_path,
            rejected_path=str(rejected_path),
            selection=selection,
            edit_plan=edit_plan,
            task_preview=task_preview,
            rejected=rejected,
            leakage_summary=leakage_summary,
            feasibility_summary=feasibility_summary,
        ),
        encoding="utf-8",
    )

    return {
        "out_dir": str(out),
        "report_path": str(out / "pilot_plan_report.md"),
        "selection": len(selection),
        "planned_edits": len(edit_plan),
        "task_previews": len(task_preview),
        "rejected_candidates": len(rejected),
        "leakage_warning_count": leakage_summary["leakage_warning_count"],
        "evidence_status": "NON_EVIDENCE_REVIEW_ONLY",
        "edits_generated": False,
        "vlm_inference_run": False,
    }


def _count_rows(rows: list[dict], keys: list[str]) -> list[dict]:
    counter: Counter[tuple[str, ...]] = Counter()
    for row in rows:
        counter[tuple(str(row.get(key, "unknown")) for key in keys)] += 1
    output = []
    for values, count in sorted(counter.items()):
        record = {key: value for key, value in zip(keys, values)}
        record["count"] = count
        output.append(record)
    return output


def _rejected_rows(rows: list[dict]) -> list[dict]:
    output = []
    for row in rows:
        output.append(
            {
                "candidate_id": row.get("candidate_id"),
                "source_id": row.get("source_id"),
                "mask_id": row.get("mask_id"),
                "attempted_edit_type": row.get("attempted_edit_type"),
                "rejection_reason": row.get("rejection_reason"),
            }
        )
    return output


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) or ["count"]
    if "count" in fieldnames:
        fieldnames = [key for key in fieldnames if key != "count"] + ["count"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _leakage_summary(task_preview: list[dict]) -> dict:
    warnings = [
        warning
        for row in task_preview
        for warning in row.get("leakage_warnings", [])
    ]
    return {
        "task_previews": len(task_preview),
        "leakage_warning_count": len(warnings),
        "records_with_warnings": sum(1 for row in task_preview if row.get("leakage_warnings")),
        "warnings": warnings,
        "passed": len(warnings) == 0,
        "evidence_status": "PREVIEW_ONLY",
    }


def _feasibility_summary(selection: list[dict], edit_plan: list[dict], rejected: list[dict]) -> dict:
    reason_counts: Counter[str] = Counter()
    for row in rejected:
        for reason in row.get("rejection_reasons", []):
            reason_counts[reason] += 1
    return {
        "candidate_count": len(selection),
        "planned_count": len(edit_plan),
        "rejected_count": len(rejected),
        "rejection_reasons": dict(sorted(reason_counts.items())),
        "all_planned_statuses": sorted({row.get("evidence_status", "unknown") for row in edit_plan}),
        "generation_statuses": sorted({row.get("generation_status", "unknown") for row in edit_plan}),
        "edits_generated": False,
        "vlm_inference_run": False,
        "evidence_claims_allowed": False,
    }


def _markdown_report(
    selection_path: str,
    edit_plan_path: str,
    task_preview_path: str,
    rejected_path: str,
    selection: list[dict],
    edit_plan: list[dict],
    task_preview: list[dict],
    rejected: list[dict],
    leakage_summary: dict,
    feasibility_summary: dict,
) -> str:
    return "\n".join(
        [
            "# CertVIC Pilot Candidate + Edit-Plan Review",
            "",
            "Status: candidate/edit-plan only. No edits generated. No VLM inference. No evidence claims.",
            "",
            "This report reviews manifest artifacts before generation. It is not a benchmark result, "
            "not a model evaluation, and not paper evidence.",
            "",
            "## Inputs",
            "",
            f"- selection: `{selection_path}`",
            f"- edit plan: `{edit_plan_path}`",
            f"- task preview: `{task_preview_path}`",
            f"- rejected candidates sidecar: `{rejected_path}`",
            "",
            "## Counts",
            "",
            f"- selected candidates: {len(selection)}",
            f"- planned edits: {len(edit_plan)}",
            f"- task previews: {len(task_preview)}",
            f"- rejected candidates: {len(rejected)}",
            f"- leakage warnings: {leakage_summary['leakage_warning_count']}",
            "",
            "## Feasibility",
            "",
            f"- planned statuses: `{feasibility_summary['all_planned_statuses']}`",
            f"- generation statuses: `{feasibility_summary['generation_statuses']}`",
            f"- rejection reasons: `{feasibility_summary['rejection_reasons']}`",
            "",
            "## Review Requirements Before Generation",
            "",
            "- inspect selected source and mask rows",
            "- inspect label IDs and unresolved label names",
            "- confirm mask areas and bounding boxes are plausible",
            "- confirm task-family and edit-type mapping",
            "- confirm release mode remains recipe-first or otherwise verified",
            "- confirm leakage summary is clean",
            "",
            "## Next Gate",
            "",
            "The next gate is actual edit generation plus quality gates. Evidence claims remain blocked "
            "until real edited images, human validity checks, model outputs, scoring, and certification "
            "artifacts exist.",
            "",
        ]
    ) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", required=True)
    parser.add_argument("--edit-plan", required=True)
    parser.add_argument("--task-preview", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    summary = build_pilot_plan_report(
        args.selection,
        args.edit_plan,
        args.task_preview,
        args.out_dir,
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
