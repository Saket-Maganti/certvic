"""Build machine-readable item validity certificates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.hashing import sha256_file, stable_record_hash
from certvic.io import read_json, read_jsonl, write_json, write_jsonl
from certvic.validity.certificate_report import render_certificate_report, summarize_certificates
from certvic.validity.certificate_schema import BLOCKING_FIELDS, ItemValidityCertificate, status_passes


def _by_key(rows: list[dict], keys: tuple[str, ...]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in rows:
        for key in keys:
            if row.get(key):
                out[str(row[key])] = row
    return out


def _review_by_item(path: str | None) -> dict[str, dict]:
    if not path or not Path(path).exists():
        return {}
    data = read_json(path)
    if isinstance(data, dict) and "items" in data:
        return {str(row.get("item_id")): row for row in data["items"]}
    if isinstance(data, dict):
        return {str(k): v for k, v in data.items() if isinstance(v, dict)}
    return {}


def build_certificates(tasks: str, edits: str | None, review: str | None, out: str, report_dir: str) -> dict:
    task_rows = read_jsonl(tasks)
    edit_rows = read_jsonl(edits) if edits and Path(edits).exists() else []
    edits_by_id = _by_key(edit_rows, ("edit_id", "item_id"))
    reviews = _review_by_item(review)
    input_hashes = {"tasks": sha256_file(tasks)}
    if edits and Path(edits).exists():
        input_hashes["edits"] = sha256_file(edits)
    if review and Path(review).exists():
        input_hashes["review"] = sha256_file(review)

    certificates: list[ItemValidityCertificate] = []
    for task in task_rows:
        item_id = str(task.get("item_id") or task.get("edit_id"))
        edit_id = str(task.get("edit_id") or (task.get("edit") or {}).get("edit_id") or item_id)
        edit = edits_by_id.get(edit_id, {})
        review_row = reviews.get(item_id, {})
        metadata = task.get("metadata") or {}
        quality = str(edit.get("quality_gate_status") or task.get("quality_gate_status") or "unknown")
        visual = str(review_row.get("visual_review_status") or metadata.get("visual_review_status") or "unknown")
        answerability = str(
            review_row.get("human_answerability_status")
            or metadata.get("human_answerability_status")
            or "unknown"
        )
        leakage = str(metadata.get("leakage_status") or "unknown")
        single_factor = str(review_row.get("single_factor_status") or metadata.get("single_factor_status") or "unknown")
        photorealism = str(review_row.get("photorealism_status") or metadata.get("photorealism_status") or "unknown")
        cert = ItemValidityCertificate(
            item_id=item_id,
            source_id=str(task.get("source_id") or ((task.get("source") or {}).get("source_id")) or ""),
            edit_id=edit_id,
            mask_id=str(task.get("mask_id") or ((task.get("mask") or {}).get("mask_id")) or ""),
            task_family=str(task.get("task_family") or edit.get("task_family") or ""),
            domain=str(task.get("domain") or edit.get("domain") or ""),
            label_policy_status=str(metadata.get("label_policy_status") or "unknown"),
            quality_gate_status=quality,
            detectability_status=str(metadata.get("detectability_status") or "unknown"),
            visual_review_status=visual,
            human_answerability_status=answerability,
            control_compatibility_status=str(metadata.get("control_compatibility_status") or "unknown"),
            single_factor_status=single_factor,
            photorealism_status=photorealism,
            leakage_status=leakage,
            provenance_status="ok" if task.get("source_id") or task.get("source") else "missing",
            input_hashes=input_hashes,
        )
        blocking: list[str] = []
        for field in BLOCKING_FIELDS:
            value = getattr(cert, field)
            if value != "unknown" and not status_passes(value):
                blocking.append(f"{field}:{value}")
        warnings: list[str] = []
        if cert.provenance_status == "missing":
            warnings.append("missing_provenance")
        if any(getattr(cert, field) == "unknown" for field in BLOCKING_FIELDS):
            warnings.append("incomplete_review_state")
        cert.blocking_reasons = sorted(blocking)
        cert.warnings = sorted(warnings)
        cert.evidence_eligible_candidate = not cert.blocking_reasons and not warnings
        cert.input_hashes = {**cert.input_hashes, "certificate_record": stable_record_hash(cert.model_dump())}
        certificates.append(cert)

    write_jsonl(out, [cert.model_dump(mode="json") for cert in certificates])
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    summary = summarize_certificates(out)
    write_json(report_path / "certificate_summary.json", summary)
    (report_path / "certificate_report.md").write_text(render_certificate_report(summary), encoding="utf-8")
    return {"out": out, "report_dir": str(report_path), **summary}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build item validity certificates")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--edits")
    parser.add_argument("--review")
    parser.add_argument("--out", required=True)
    parser.add_argument("--report-dir", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(build_certificates(args.tasks, args.edits, args.review, args.out, args.report_dir), sort_keys=True))


if __name__ == "__main__":
    main()

