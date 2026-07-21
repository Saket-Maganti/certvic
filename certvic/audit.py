"""Project-wide audit CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import load_model_jsonl, write_json
from certvic.metrics.summary import summarize_pair_scores
from certvic.schema import PairScore, PredictionRecord, TaskItem
from certvic.validation.claims import build_evidence_context, validate_certified_claim_eligibility
from certvic.validation.leakage import validate_task_no_leakage
from certvic.validation.paper_claims import scan_paper
from certvic.validation.zero_cost import validate_zero_cost_config


def run_audit(
    config: str | None = None,
    tasks: str | None = None,
    preds: str | None = None,
    scores: str | None = None,
    paper: str | None = None,
    strict: bool = False,
) -> dict:
    checks: dict = {}
    checks["zero_cost"] = validate_zero_cost_config(config)
    task_records: list[TaskItem] = []
    pred_records: list[PredictionRecord] = []
    score_records: list[PairScore] = []

    if tasks:
        task_errors: list[str] = []
        task_records = load_model_jsonl(tasks, TaskItem)
        for task in task_records:
            leakage = validate_task_no_leakage(task)
            if leakage:
                task_errors.extend([f"{task.item_id}: {msg}" for msg in leakage])
        checks["schemas"] = {"passed": True, "n": len(task_records), "errors": []}
        checks["leakage"] = {"passed": not task_errors, "errors": task_errors}
        checks["licenses"] = {"passed": True, "errors": [], "note": "smoke/pointer license policy checked by manifest builder"}
    elif strict:
        checks["schemas"] = {"passed": True, "n": 0, "errors": [], "note": "no task path provided"}

    if preds:
        pred_records = load_model_jsonl(preds, PredictionRecord)
        checks["predictions"] = {"passed": True, "n": len(pred_records), "errors": []}
    if scores:
        score_records = load_model_jsonl(scores, PairScore)
        summary = summarize_pair_scores(score_records)
        checks["metrics"] = {"passed": bool(score_records), "summary": summary, "errors": [] if score_records else ["no scores"]}
        evidence_context = build_evidence_context(
            tasks=task_records,
            predictions=pred_records,
            scores=score_records,
        )
        hypothetical_certification = {
            "confidence_sequence": {"available": True, "latest": {"lo": 1.0, "hi": 1.0}},
            "lower_bound": 1.0,
            "upper_bound": 1.0,
        }
        blocked_reasons = validate_certified_claim_eligibility(
            hypothetical_certification,
            claim_text="Under the configured item order and anytime-valid CS, the intervention-consistency gap lower bound exceeds 0.05 at alpha=0.05 for this run.",
            evidence_context=evidence_context,
            threshold=0.05,
        )
        checks["claims"] = {
            "passed": True,
            "status": "no certified claims made in smoke audit",
            "certified_claim_allowed_for_current_artifacts": not blocked_reasons,
            "certification_blocking_reasons": blocked_reasons,
            "evidence_context": evidence_context,
            "errors": [],
        }
    if paper:
        checks["paper"] = scan_paper(paper)
    elif strict:
        default_paper = Path("paper/main.tex")
        checks["paper"] = scan_paper(str(default_paper)) if default_paper.exists() else {"passed": True, "warnings": ["paper not provided"], "errors": []}

    passed = all(check.get("passed", False) for check in checks.values())
    return {"passed": passed, "checks": checks}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--tasks")
    parser.add_argument("--preds")
    parser.add_argument("--scores")
    parser.add_argument("--paper")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    result = run_audit(args.config, args.tasks, args.preds, args.scores, args.paper, args.strict)
    if args.out:
        write_json(args.out, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
