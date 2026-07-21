"""Tiny reviewed-task VLM evaluation + scoring path.

Stages: preflight -> run_eval -> score_predictions -> report_metrics ->
build_v2_report (best effort) -> audit claims.

Enforces: tasks must be HUMAN_REVIEWED_NON_EVIDENCE or stronger; the provider
cannot be mock for the evidence path (a mock run is allowed only with
--allow-mock-smoke and is marked non-evidence); paid providers are blocked;
max_items is required unless --allow-full-run; resume preserved; raw outputs kept.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from certvic.eval.run_eval import run_eval
from certvic.io import load_model_jsonl, write_json
from certvic.metrics.certification import certify_gap
from certvic.metrics.certification_policy import evaluate_certification_policy, load_certification_policy
from certvic.metrics.score_predictions import score_predictions
from certvic.metrics.summary import summarize_pair_scores
from certvic.providers.registry import PAID_PROVIDER_NAMES
from certvic.schema import PredictionRecord, TaskItem
from certvic.validation.claims import build_evidence_context

REVIEWED_OR_STRONGER = {"HUMAN_REVIEWED_NON_EVIDENCE", "EVIDENCE", "CERTIFIED"}


class TinyEvalError(ValueError):
    """Raised when the tiny eval path is misconfigured or used unsafely."""


def _is_mock(provider: str) -> bool:
    return provider.startswith("mock")


def run_tiny_eval(
    config_path: str,
    tasks_path: str,
    provider: str,
    out_dir: str,
    run_id: str,
    max_items: int | None = None,
    allow_full_run: bool = False,
    allow_mock_smoke: bool = False,
    certification_policy_path: str | None = None,
    alpha: float = 0.05,
    gap_threshold: float = 0.05,
) -> dict:
    if max_items is None and not allow_full_run:
        raise TinyEvalError("max_items is required unless --allow-full-run is set")
    if provider in PAID_PROVIDER_NAMES:
        raise TinyEvalError(f"paid provider blocked: {provider}")
    if _is_mock(provider) and not allow_mock_smoke:
        raise TinyEvalError("mock providers are blocked for the evidence path; use --allow-mock-smoke for a non-evidence smoke run")

    tasks = load_model_jsonl(tasks_path, TaskItem)
    statuses = {str(t.metadata.get("evidence_status", "UNKNOWN")).upper() for t in tasks}
    reviewed_ok = bool(statuses) and statuses <= REVIEWED_OR_STRONGER
    if not reviewed_ok and not allow_mock_smoke:
        raise TinyEvalError(
            f"tasks must be HUMAN_REVIEWED_NON_EVIDENCE or stronger for the evidence path; found {sorted(statuses)}"
        )

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    preds_path = str(out / "predictions.jsonl")
    scores_path = str(out / "pair_scores.jsonl")
    summary_path = str(out / "metrics_summary.json")
    is_evidence_path = (not _is_mock(provider)) and reviewed_ok

    stage_status: dict = {}

    def stage(name: str, fn):
        start = time.time()
        try:
            result = fn()
            stage_status[name] = {"status": "completed", "seconds": round(time.time() - start, 3)}
            return result
        except Exception as exc:
            stage_status[name] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            raise

    # 1. preflight (lightweight; full vlm_preflight is a separate command)
    stage("preflight", lambda: _preflight(tasks_path, tasks, provider, allow_mock_smoke))

    # 2. run_eval (resume = do not overwrite)
    eval_summary = stage("run_eval", lambda: run_eval(
        config_path=config_path, tasks_path=tasks_path, out_path=preds_path,
        provider_name=provider, run_id=run_id, max_items=max_items, overwrite=False,
    ))

    # 3. score predictions
    from certvic.io import write_jsonl

    def _score():
        scores = score_predictions(tasks_path, preds_path)
        write_jsonl(scores_path, scores)
        return scores

    scores = stage("score_predictions", _score)

    # 4. report metrics + certification gate
    def _metrics():
        summary = summarize_pair_scores(scores)
        a = [int(s.original_correct) for s in scores]
        c = [int(s.consistent) for s in scores]
        preds = load_model_jsonl(preds_path, PredictionRecord)
        evidence_context = build_evidence_context(tasks=tasks, predictions=preds, scores=scores)
        certification = certify_gap(a, c, delta_threshold=gap_threshold, alpha=alpha, allow_unavailable=True, evidence_context=evidence_context)
        policy = load_certification_policy(certification_policy_path)
        policy_decision = evaluate_certification_policy(summary, certification, policy, evidence_context)
        payload = {
            "metrics": summary,
            "certification": certification,
            "certification_policy_decision": policy_decision,
            "evidence_context": evidence_context,
            "is_evidence_path": is_evidence_path,
            "certified": bool(certification.get("certified") and policy_decision.get("policy_passed")),
        }
        write_json(summary_path, payload)
        return payload

    metrics_payload = stage("report_metrics", _metrics)

    # 5. build_v2_report (best effort; available once Prompt 08 is built)
    def _v2_report():
        try:
            from certvic.reporting.build_v2_report import build_v2_report
        except Exception:
            return {"skipped": "build_v2_report not available"}
        return build_v2_report(scores_path, preds_path, tasks_path, str(out / "v2_report"))

    stage("build_v2_report", _v2_report)

    write_json(str(out / "stage_status.json"), stage_status)
    summary = {
        "config": config_path,
        "tasks_path": tasks_path,
        "provider": provider,
        "run_id": run_id,
        "out_dir": out_dir,
        "is_evidence_path": is_evidence_path,
        "allow_mock_smoke": allow_mock_smoke,
        "eval_summary": eval_summary,
        "n_scores": len(scores),
        "certified": metrics_payload["certified"],
        "certification_policy_passed": metrics_payload["certification_policy_decision"]["policy_passed"],
        "stage_status": stage_status,
        "evidence_status": "OPEN_MODEL_RESULT" if is_evidence_path else "MOCK_SMOKE_NON_EVIDENCE",
        "raw_outputs_preserved": True,
    }
    write_json(str(out / "tiny_eval_summary.json"), summary)
    return summary


def _preflight(tasks_path: str, tasks: list, provider: str, allow_mock_smoke: bool) -> dict:
    if not Path(tasks_path).exists():
        raise TinyEvalError(f"tasks manifest not found: {tasks_path}")
    return {
        "tasks_exist": True,
        "n_tasks": len(tasks),
        "provider": provider,
        "provider_is_mock": _is_mock(provider),
        "allow_mock_smoke": allow_mock_smoke,
        "paid_services": False,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC tiny reviewed-task eval + scoring")
    parser.add_argument("--config", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--run-id", default="tiny_eval_v1")
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--allow-full-run", action="store_true")
    parser.add_argument("--allow-mock-smoke", action="store_true")
    parser.add_argument("--certification-policy")
    args = parser.parse_args(argv)
    try:
        summary = run_tiny_eval(
            args.config, args.tasks, args.provider, args.out_dir, args.run_id,
            max_items=args.max_items, allow_full_run=args.allow_full_run,
            allow_mock_smoke=args.allow_mock_smoke, certification_policy_path=args.certification_policy,
        )
    except TinyEvalError as exc:
        raise SystemExit(f"Tiny eval failed: {exc}") from None
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
