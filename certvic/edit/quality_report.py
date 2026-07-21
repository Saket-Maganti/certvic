"""Quality report for tiny generated edits."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from certvic.io import read_jsonl, write_json, write_jsonl


def build_quality_report(
    generated_manifest: str,
    rejected_path: str,
    out_dir: str,
) -> dict:
    generated = read_jsonl(generated_manifest)
    rejected = read_jsonl(rejected_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    summary = _quality_summary(generated, rejected)
    write_json(out / "quality_summary.json", summary)
    _write_csv(out / "quality_by_edit_type.csv", _quality_by_edit_type(generated))
    _write_csv(out / "rejected_edits.csv", _rejected_rows(rejected))
    write_jsonl(out / "review_gallery_manifest.jsonl", _gallery_rows(generated))
    (out / "generated_edit_review.md").write_text(
        _markdown(generated_manifest, rejected_path, summary),
        encoding="utf-8",
    )
    return {
        "out_dir": str(out),
        "generated": len(generated),
        "rejected": len(rejected),
        "quality_passed": summary["quality_passed"],
        "quality_failed": summary["quality_failed"],
        "evidence_status": "GENERATED_EDIT_ONLY",
        "vlm_inference_run": False,
        "paper_evidence": False,
    }


def _quality_summary(generated: list[dict], rejected: list[dict]) -> dict:
    warning_counts: Counter[str] = Counter()
    for row in generated:
        quality = row.get("quality") or {}
        for warning in quality.get("warnings", []):
            warning_counts[warning] += 1
    return {
        "generated_manifest_rows": len(generated),
        "rejected_rows": len(rejected),
        "quality_passed": sum(1 for row in generated if row.get("quality_gate_status") == "pass"),
        "quality_failed": sum(1 for row in generated if row.get("quality_gate_status") != "pass"),
        "by_edit_type": dict(sorted(Counter(row.get("edit_type", "unknown") for row in generated).items())),
        "warning_counts": dict(sorted(warning_counts.items())),
        "rejection_reasons": dict(sorted(Counter(row.get("rejection_reason", "unknown") for row in rejected).items())),
        "evidence_status": "GENERATED_EDIT_ONLY",
        "generated_edits_are_evidence": False,
        "vlm_inference_run": False,
        "human_validity_required": True,
    }


def _quality_by_edit_type(generated: list[dict]) -> list[dict]:
    rows = []
    for edit_type in sorted({str(row.get("edit_type", "unknown")) for row in generated}):
        bucket = [row for row in generated if str(row.get("edit_type", "unknown")) == edit_type]
        rows.append(
            {
                "edit_type": edit_type,
                "generated": len(bucket),
                "quality_passed": sum(1 for row in bucket if row.get("quality_gate_status") == "pass"),
                "quality_failed": sum(1 for row in bucket if row.get("quality_gate_status") != "pass"),
                "mean_inside_mask_change_fraction": _mean_metric(bucket, "inside_mask_change_fraction"),
                "mean_outside_mask_change_fraction": _mean_metric(bucket, "outside_mask_change_fraction"),
                "mean_outside_allowed_change_fraction": _mean_metric(bucket, "outside_allowed_change_fraction"),
            }
        )
    return rows


def _mean_metric(rows: list[dict], key: str) -> float | None:
    values = []
    for row in rows:
        value = (row.get("quality") or {}).get(key)
        if value is not None:
            values.append(float(value))
    if not values:
        return None
    return sum(values) / len(values)


def _rejected_rows(rejected: list[dict]) -> list[dict]:
    return [
        {
            "edit_id": row.get("edit_id"),
            "source_id": row.get("source_id"),
            "mask_id": row.get("mask_id"),
            "edit_type": row.get("edit_type"),
            "generation_status": row.get("generation_status"),
            "rejection_reason": row.get("rejection_reason"),
        }
        for row in rejected
    ]


def _gallery_rows(generated: list[dict]) -> list[dict]:
    return [
        {
            "edit_id": row.get("edit_id"),
            "source_id": row.get("source_id"),
            "edit_type": row.get("edit_type"),
            "original_image_path": row.get("original_image_path"),
            "edited_image_path": row.get("edited_image_path"),
            "quality_gate_status": row.get("quality_gate_status"),
            "evidence_status": row.get("evidence_status"),
            "review_required": True,
        }
        for row in generated
    ]


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) or ["edit_id", "rejection_reason"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _markdown(generated_manifest: str, rejected_path: str, summary: dict) -> str:
    return "\n".join(
        [
            "# Tiny Generated Edit Quality Review",
            "",
            "Status: generated edits are only edit-quality artifacts. No VLM inference was run. "
            "No evidence claims are enabled. Human validity is still required.",
            "",
            "These outputs validate local generation and quality-gate plumbing only. They are not "
            "model-evaluation evidence and are not paper results.",
            "",
            "## Inputs",
            "",
            f"- generated manifest: `{generated_manifest}`",
            f"- rejected edits: `{rejected_path}`",
            "",
            "## Counts",
            "",
            f"- generated rows: {summary['generated_manifest_rows']}",
            f"- rejected rows: {summary['rejected_rows']}",
            f"- quality passed: {summary['quality_passed']}",
            f"- quality failed: {summary['quality_failed']}",
            f"- by edit type: `{summary['by_edit_type']}`",
            f"- warning counts: `{summary['warning_counts']}`",
            "",
            "## Next Gate",
            "",
            "Manually inspect the review gallery, run human validity checks, and keep VLM inference "
            "blocked until generated edits are accepted.",
            "",
        ]
    ) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-manifest", required=True)
    parser.add_argument("--rejected", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    summary = build_quality_report(args.generated_manifest, args.rejected, args.out_dir)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
