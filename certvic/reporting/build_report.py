"""Build report artifacts from scores and predictions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import load_model_jsonl, write_json, write_jsonl
from certvic.metrics.report_metrics import build_metrics_report
from certvic.reporting.claim_ledger import build_claim_ledger
from certvic.reporting.failure_gallery import build_failure_gallery
from certvic.reporting.tables import write_group_table, write_main_model_table, write_main_table, write_single_table
from certvic.schema import PairScore, PredictionRecord, TaskItem
from certvic.validation.claims import build_evidence_context


def build_report(
    tasks_path: str,
    scores_path: str,
    preds_path: str,
    out_dir: str,
    alpha: float = 0.05,
    gap_threshold: float = 0.05,
) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tasks_list = load_model_jsonl(tasks_path, TaskItem)
    scores = load_model_jsonl(scores_path, PairScore)
    preds = load_model_jsonl(preds_path, PredictionRecord)
    tasks = {task.item_id: task for task in tasks_list}

    evidence_context = build_evidence_context(tasks=tasks_list, predictions=preds, scores=scores)
    claim_text = (
        f"Under the configured item order and anytime-valid CS, the intervention-consistency "
        f"gap lower bound exceeds {gap_threshold} at alpha={alpha} for this run."
    )
    metrics_report = build_metrics_report(
        scores,
        alpha=alpha,
        gap_threshold=gap_threshold,
        evidence_context=evidence_context,
        claim_text=claim_text,
    )
    summary = metrics_report["summary"]
    certification = metrics_report["certification"]
    gallery = build_failure_gallery(tasks, scores, preds)
    ledger = build_claim_ledger(
        summary,
        certification,
        evidence_files=[tasks_path, scores_path, preds_path, str(out / "summary.json")],
    )

    write_json(out / "summary.json", metrics_report)
    write_main_model_table(summary, certification, str(out / "main_model_table.csv"), str(out / "main_model_table.tex"))
    write_group_table(summary["by_task_family"], str(out / "by_family_table.csv"))
    write_group_table(summary["by_domain"], str(out / "by_domain_table.csv"))
    write_group_table(summary["by_required_change"], str(out / "by_required_change_table.csv"))
    write_single_table(summary.get("control_edit", {}), str(out / "control_edit_table.csv"))
    write_single_table(summary.get("parse_failure_sensitivity", {}), str(out / "parse_failure_table.csv"))

    # Backward-compatible V1 artifact names.
    write_group_table(summary["by_task_family"], str(out / "metrics_by_family.csv"))
    write_group_table(summary["by_domain"], str(out / "metrics_by_domain.csv"))
    write_group_table(summary["by_required_change"], str(out / "metrics_by_required_change.csv"))
    write_main_table(summary, certification, str(out / "main_table.tex"))
    write_json(out / "certification_status.json", certification)
    write_json(out / "certification.json", certification)
    write_json(out / "claim_ledger.json", [entry.model_dump(mode="json") for entry in ledger])
    write_jsonl(out / "claim_ledger.jsonl", ledger)
    write_jsonl(out / "failure_gallery.jsonl", gallery)
    report_md = _markdown_report(summary, certification, gallery)
    (out / "report.md").write_text(report_md, encoding="utf-8")
    return {"out_dir": str(out), "n_scores": len(scores), "n_failures": len(gallery), "certified": certification["certified"]}


def _fmt(value) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _markdown_report(summary: dict, certification: dict, gallery: list[dict]) -> str:
    return "\n".join(
        [
            "# CertVIC Smoke Report",
            "",
            "Status: MOCK_ONLY synthetic fixture report.",
            "",
            "No evidence claims are made. No paid services were used. Real pilot data are required before paper claims.",
            "",
            "## Summary",
            "",
            f"- n: {summary.get('n')}",
            f"- original accuracy: {_fmt(summary.get('original_accuracy'))}",
            f"- consistency rate: {_fmt(summary.get('consistency_rate'))}",
            f"- intervention-consistency gap: {_fmt(summary.get('intervention_consistency_gap'))}",
            f"- parse failure rate: {_fmt(summary.get('parse_failure_rate'))}",
            "",
            "## Certification",
            "",
            certification.get("safe_claim", "Not certified."),
            "",
            "Certification gate errors:",
            *[f"- {error}" for error in certification.get("certification_gate_errors", [])],
            "",
            "## Failure Gallery",
            "",
            f"Selected failure cases: {len(gallery)}",
            "",
            "## Limitations",
            "",
            "- Smoke images are synthetic fixtures only.",
            "- Results are MOCK_ONLY and not paper evidence.",
            "- No paid services were used.",
            "- Real pilot data, edit validation, and open-model runs are still required.",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--scores", required=True)
    parser.add_argument("--preds", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--gap-threshold", type=float, default=0.05)
    args = parser.parse_args(argv)
    result = build_report(args.tasks, args.scores, args.preds, args.out_dir, args.alpha, args.gap_threshold)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
