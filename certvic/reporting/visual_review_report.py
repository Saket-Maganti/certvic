"""Render a visual-review report from an aggregation summary + approved tasks."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from certvic.io import read_jsonl


def build_visual_review_report(summary_path: str, tasks_path: str, out_dir: str) -> dict:
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    tasks = read_jsonl(tasks_path) if tasks_path and Path(tasks_path).exists() else []
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    by_family = dict(sorted(Counter(t.get("task_family") for t in tasks).items()))
    lines = [
        "# Visual Review Report",
        "",
        f"- items reviewed: {summary.get('n_items')}",
        f"- kept: {summary.get('keep_count')}, dropped: {summary.get('drop_count')}",
        f"- approved tasks materialized: {len(tasks)} (evidence_status=HUMAN_REVIEWED_NON_EVIDENCE)",
        "",
        "## Inter-annotator agreement (per field)",
        "",
        "| Field | Method | Raters | Kappa | Mean majority | Single-rater warning |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for field, iaa in (summary.get("iaa") or {}).items():
        kappa = iaa.get("kappa")
        kappa_s = f"{kappa:.3f}" if isinstance(kappa, (int, float)) else "--"
        lines.append(
            f"| {field} | {iaa.get('method')} | {iaa.get('max_raters')} | {kappa_s} | "
            f"{iaa.get('mean_majority_agreement', 0):.3f} | {iaa.get('single_rater_warning')} |"
        )
    lines += ["", "## Approved tasks by family", ""]
    for family, count in by_family.items():
        lines.append(f"- {family}: {count}")
    if summary.get("single_rater_warning_fields"):
        lines += ["", f"> WARNING: single-rater fields: {summary['single_rater_warning_fields']}. Add raters before claims."]
    lines += ["", "Human review validates edit/item quality only; it is not model evidence.", ""]
    (out / "visual_review_report.md").write_text("\n".join(lines), encoding="utf-8")
    report_summary = {
        "out_dir": out_dir,
        "n_items": summary.get("n_items"),
        "keep_count": summary.get("keep_count"),
        "drop_count": summary.get("drop_count"),
        "approved_tasks": len(tasks),
        "by_task_family": by_family,
        "single_rater_warning_fields": summary.get("single_rater_warning_fields", []),
        "evidence_status": "HUMAN_REVIEWED_NON_EVIDENCE",
    }
    (out / "visual_review_report_summary.json").write_text(json.dumps(report_summary, sort_keys=True), encoding="utf-8")
    return report_summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render a visual-review report")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--tasks", default="")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(build_visual_review_report(args.summary, args.tasks, args.out_dir), sort_keys=True))


if __name__ == "__main__":
    main()
