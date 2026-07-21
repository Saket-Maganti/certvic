"""Metrics report CLI from pair scores."""

from __future__ import annotations

import argparse
import json

from certvic.io import load_model_jsonl, write_json
from certvic.metrics.bootstrap import paired_bootstrap_ci
from certvic.metrics.certification import certify_gap
from certvic.metrics.certification_policy import evaluate_certification_policy, load_certification_policy
from certvic.metrics.summary import summarize_pair_scores
from certvic.schema import PairScore


def _gap_stat(rows: list[PairScore]) -> float:
    return sum(float(s.original_correct) - float(s.consistent) for s in rows) / len(rows)


def _mean_attr(rows: list[PairScore], attr: str) -> float:
    return sum(float(getattr(s, attr)) for s in rows) / len(rows)


def _bootstrap_block(scores: list[PairScore], alpha: float, n_boot: int = 500) -> dict:
    return {
        "label": "descriptive_only_not_anytime_valid",
        "original_accuracy": paired_bootstrap_ci(
            scores, lambda rows: _mean_attr(rows, "original_correct"), n_boot=n_boot, alpha=alpha, seed=1
        ),
        "consistency_rate": paired_bootstrap_ci(
            scores, lambda rows: _mean_attr(rows, "consistent"), n_boot=n_boot, alpha=alpha, seed=2
        ),
        "intervention_consistency_gap": paired_bootstrap_ci(
            scores, _gap_stat, n_boot=n_boot, alpha=alpha, seed=3
        ),
        "certification_eligible": False,
        "note": "Paired bootstrap CIs are descriptive only and are never anytime-valid certification.",
    }


def _group_bootstrap(scores: list[PairScore], attr: str, alpha: float) -> dict:
    groups: dict[str, list[PairScore]] = {}
    for score in scores:
        groups.setdefault(str(getattr(score, attr)), []).append(score)
    return {key: _bootstrap_block(value, alpha=alpha, n_boot=300) for key, value in sorted(groups.items())}


def build_metrics_report(
    scores: list[PairScore],
    alpha: float,
    gap_threshold: float,
    evidence_context: dict | None = None,
    claim_text: str | None = None,
) -> dict:
    summary = summarize_pair_scores(scores)
    a = [float(s.original_correct) for s in scores]
    c = [float(s.consistent) for s in scores]
    certification = certify_gap(
        a,
        c,
        delta_threshold=gap_threshold,
        alpha=alpha,
        allow_unavailable=True,
        evidence_context=evidence_context,
        claim_text=claim_text,
    )
    policy = load_certification_policy(None)
    policy.update({"alpha": alpha, "gap_threshold": gap_threshold})
    policy_decision = evaluate_certification_policy(
        summary,
        certification,
        policy,
        evidence_context,
    )
    prior_gate_errors = list(certification.get("certification_gate_errors") or [])
    policy_errors = list(policy_decision.get("errors") or [])
    certification["certified"] = bool(
        certification.get("certified") and policy_decision.get("policy_passed")
    )
    certification["policy_decision"] = policy_decision
    certification["certification_gate_errors"] = list(
        dict.fromkeys([*prior_gate_errors, *policy_errors])
    )
    if not certification["certified"]:
        certification["statement"] = "No fully policy-qualified certification claim is available for this run."
        certification["safe_claim"] = (
            "Not fully certified; report the CS threshold crossing and descriptive metrics separately."
        )
    descriptive_ci = {
        "overall": _bootstrap_block(scores, alpha=alpha),
        "by_task_family": _group_bootstrap(scores, "task_family", alpha=alpha),
        "by_domain": _group_bootstrap(scores, "domain", alpha=alpha),
        "by_required_change": _group_bootstrap(scores, "required_change", alpha=alpha),
    }
    return {
        "summary": summary,
        "bootstrap": descriptive_ci,
        "descriptive_ci": descriptive_ci,
        "certification": certification,
        "certification_policy_decision": policy_decision,
        "claim_ledger_compatible": True,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--gap-threshold", type=float, default=0.05)
    args = parser.parse_args(argv)
    scores = load_model_jsonl(args.scores, PairScore)
    report = build_metrics_report(scores, args.alpha, args.gap_threshold)
    write_json(args.out, report)
    print(json.dumps({"n": len(scores), "certified": report["certification"]["certified"]}, sort_keys=True))


if __name__ == "__main__":
    main()
