"""Metric summaries."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

from certvic.schema import PairScore, RequiredChange


def _safe_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _summarize_subset(scores: list[PairScore]) -> dict:
    n = len(scores)
    if n == 0:
        return {
            "n": 0,
            "original_accuracy": None,
            "edited_accuracy": None,
            "consistency_rate": None,
            "intervention_consistency_gap": None,
            "parse_failure_rate": None,
            "spurious_flip_rate": None,
            "correct_semantic_update_rate": None,
            "conditional_semantic_update_rate_given_original_correct": None,
            "raw_answer_change_rate": None,
            "transition_matrix": {},
            "failure_taxonomy": {},
        }
    original_accuracy = _safe_mean([float(s.original_correct) for s in scores])
    consistency_rate = _safe_mean([float(s.consistent) for s in scores])
    no_change_scores = [s for s in scores if s.required_change == RequiredChange.NO_CHANGE.value]
    spurious_flip_rate = None
    if no_change_scores:
        spurious_flip_rate = 1.0 - mean([float(s.consistent) for s in no_change_scores])
    relevant = [s for s in scores if s.required_change == RequiredChange.CHANGE.value]
    originally_correct_relevant = [s for s in relevant if s.original_correct]
    semantic_rate = _safe_mean([
        float(bool(s.metadata.get("semantic_update_success", s.consistent))) for s in relevant
    ])
    conditional_rate = _safe_mean([
        float(bool(s.metadata.get("semantic_update_success", s.consistent)))
        for s in originally_correct_relevant
    ])
    answer_changes = [
        bool(s.metadata.get(
            "model_answer_changes",
            not s.consistent if s.required_change == RequiredChange.NO_CHANGE.value else s.consistent,
        ))
        for s in scores
    ]
    transitions: dict[str, int] = defaultdict(int)
    failures: dict[str, int] = defaultdict(int)
    for score in scores:
        transition = (
            "PARSE_FAILURE" if not score.parse_ok else
            f"ORIGINAL_{'CORRECT' if score.original_correct else 'WRONG'}"
            f"_TO_EDITED_{'CORRECT' if score.edited_correct else 'WRONG'}"
        )
        transitions[transition] += 1
        if score.required_change == RequiredChange.CHANGE.value:
            if bool(score.metadata.get("semantic_update_success", score.consistent)):
                failure = "SEMANTIC_UPDATE_SUCCESS"
            elif not score.parse_ok:
                failure = "PARSER_OR_MISSING_OUTPUT"
            elif not score.original_correct:
                failure = "ORIGINAL_PREDICTION_INCORRECT"
            elif not bool(score.metadata.get("model_answer_changes", score.consistent)):
                failure = "MODEL_DID_NOT_UPDATE"
            else:
                failure = "MODEL_CHANGED_TO_WRONG_ANSWER"
        else:
            failure = "IRRELEVANT_FLIP" if not score.consistent else "IRRELEVANT_STABLE"
        failures[failure] += 1
    return {
        "n": n,
        "original_accuracy": original_accuracy,
        "edited_accuracy": _safe_mean([float(s.edited_correct) for s in scores]),
        "consistency_rate": consistency_rate,
        "intervention_consistency_gap": (
            original_accuracy - consistency_rate
            if original_accuracy is not None and consistency_rate is not None
            else None
        ),
        "intervention_consistency_gap_status": "SECONDARY_DESCRIPTIVE_NOT_A_CERTIFICATE",
        "correct_semantic_update_rate": semantic_rate,
        "conditional_semantic_update_rate_given_original_correct": conditional_rate,
        "raw_answer_change_rate": _safe_mean([float(value) for value in answer_changes]),
        "transition_matrix": dict(sorted(transitions.items())),
        "failure_taxonomy": dict(sorted(failures.items())),
        "parse_failure_rate": _safe_mean([float(not s.parse_ok) for s in scores]),
        "spurious_flip_rate": spurious_flip_rate,
    }


def summarize_pair_scores(scores: list[PairScore]) -> dict:
    summary = _summarize_subset(scores)
    control_scores = [
        score
        for score in scores
        if score.task_family == "control_irrelevant"
        or str(score.metadata.get("edit_type", "")).startswith("control_")
    ]
    summary["control_edit"] = {
        "n": len(control_scores),
        "spurious_flip_rate": (
            1.0 - mean([float(score.consistent) for score in control_scores])
            if control_scores
            else None
        ),
        "consistency_rate": _safe_mean([float(score.consistent) for score in control_scores]),
    }
    parse_failed = [score for score in scores if not score.parse_ok]
    parse_ok = [score for score in scores if score.parse_ok]
    summary["parse_failure_sensitivity"] = {
        "n_parse_failures": len(parse_failed),
        "parse_failure_rate": _safe_mean([float(not score.parse_ok) for score in scores]),
        "metrics_parse_ok_only": _summarize_subset(parse_ok),
        "metrics_parse_fail_as_inconsistent": _summarize_subset(scores),
        "note": "Descriptive sensitivity only; parse-failure handling is never a certification substitute.",
    }
    for field, attr in [
        ("by_task_family", "task_family"),
        ("by_domain", "domain"),
        ("by_required_change", "required_change"),
    ]:
        buckets: dict[str, list[PairScore]] = defaultdict(list)
        for score in scores:
            buckets[str(getattr(score, attr))].append(score)
        summary[field] = {key: _summarize_subset(value) for key, value in sorted(buckets.items())}
    return summary
