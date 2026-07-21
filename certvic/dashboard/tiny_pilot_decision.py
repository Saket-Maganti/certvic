"""Tiny-pilot decision dashboard builder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import read_json, read_jsonl, write_json
from certvic.validation.detectability_gate import evaluate_gate, load_detectability_summary, load_quality_summary


def _read_optional_json(path: Path) -> dict:
    return read_json(path) if path.exists() else {}


def _count_jsonl(path: Path) -> int:
    return len(read_jsonl(path)) if path.exists() else 0


def build_decision(pilot_dir: str) -> dict:
    root = Path(pilot_dir)
    quality = load_quality_summary(root / "quality_report.json") or load_quality_summary(root / "tiny_edit_quality_report")
    detectability = (
        load_detectability_summary(root / "edit_detectability")
        or load_detectability_summary(root / "detectability_summary.json")
    )
    gate = evaluate_gate(detectability, quality)
    review = _read_optional_json(root / "visual_review_summary.json")
    answerability = _read_optional_json(root / "answerability_summary.json")
    cert_summary = _read_optional_json(root / "certificate_report" / "certificate_summary.json")
    dry_run_status = _read_optional_json(root / "stage_status.json")
    blockers = list(gate["blockers"])
    if cert_summary and int(cert_summary.get("n_candidate_eligible") or 0) <= 0:
        blockers.append("no_certificate_eligible_items")
    return {
        "dashboard": "tiny_pilot_decision",
        "pilot_dir": pilot_dir,
        "dry_run_status": dry_run_status.get("status") or ("present" if dry_run_status else "missing"),
        "edit_generation_count": _count_jsonl(root / "pilot_generated_edits.jsonl"),
        "quality_pass_rate": quality.get("pass_rate") if isinstance(quality, dict) else None,
        "detectability_auc": gate["detectability_auc"],
        "visual_review_count": review.get("n_reviewed") or review.get("review_count") or 0,
        "answerability_review_count": answerability.get("n_reviewed") or answerability.get("review_count") or 0,
        "item_certificate_pass_rate": cert_summary.get("candidate_eligible_rate") if cert_summary else None,
        "may_begin_vlm_eval": gate["may_begin_vlm_inference"] and not blockers,
        "go_no_go_status": "GO" if gate["may_begin_vlm_inference"] and not blockers else gate["status"],
        "top_blockers": sorted(set(blockers)),
        "gate": gate,
        "evidence_status": "DASHBOARD_ONLY_NON_EVIDENCE",
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# Tiny Pilot Decision",
        "",
        f"Status: {result['go_no_go_status']}",
        f"May begin VLM eval: {result['may_begin_vlm_eval']}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Dry-run status | {result['dry_run_status']} |",
        f"| Generated edits | {result['edit_generation_count']} |",
        f"| Quality pass rate | {result['quality_pass_rate']} |",
        f"| Detectability AUC | {result['detectability_auc']} |",
        f"| Visual review count | {result['visual_review_count']} |",
        f"| Answerability review count | {result['answerability_review_count']} |",
        f"| Certificate pass rate | {result['item_certificate_pass_rate']} |",
        "",
        "VLM inference should not begin until detectability, visual quality, review, and item certificates pass.",
        "",
    ]
    if result["top_blockers"]:
        lines += ["## Top Blockers", ""]
        lines.extend(f"- {blocker}" for blocker in result["top_blockers"])
        lines.append("")
    return "\n".join(lines)


def write_dashboard(pilot_dir: str, out: str, json_out: str) -> dict:
    result = build_decision(pilot_dir)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(render_markdown(result), encoding="utf-8")
    write_json(json_out, result)
    return {"out": out, "json_out": json_out, "status": result["go_no_go_status"]}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build tiny-pilot decision dashboard")
    parser.add_argument("--pilot-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_dashboard(args.pilot_dir, args.out, args.json_out), sort_keys=True))


if __name__ == "__main__":
    main()
