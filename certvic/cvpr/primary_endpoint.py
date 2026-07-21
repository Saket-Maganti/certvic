"""Frozen item scorer and fixed-sample two-gate prospective certificate."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from certvic.cvpr.statistics import clopper_pearson_lower, clopper_pearson_upper


def normalize_answer(value: Any) -> str | None:
    """Apply the preregistered conservative answer normalization."""
    if value is None:
        return None
    return " ".join(str(value).strip().casefold().split())


def score_item(
    *,
    original_gold: Any,
    edited_gold: Any,
    original_prediction: Any,
    edited_prediction: Any,
    required_change: bool,
    original_parse_ok: bool = True,
    edited_parse_ok: bool = True,
) -> dict[str, Any]:
    """Score one original/edited pair under the locked prospective definitions."""
    gold_original = normalize_answer(original_gold)
    gold_edited = normalize_answer(edited_gold)
    answer_original = normalize_answer(original_prediction)
    answer_edited = normalize_answer(edited_prediction)
    parse_ok = bool(
        original_parse_ok
        and edited_parse_ok
        and answer_original is not None
        and answer_edited is not None
    )
    gold_changes = gold_original != gold_edited
    model_answer_changes = parse_ok and answer_original != answer_edited
    original_correct = parse_ok and answer_original == gold_original
    edited_correct = parse_ok and answer_edited == gold_edited
    changes_to_edited_gold = bool(model_answer_changes and edited_correct)
    semantic_update_success = bool(
        required_change
        and parse_ok
        and original_correct
        and edited_correct
        and gold_changes
        and changes_to_edited_gold
    )
    irrelevant_flip_observed = bool(
        not required_change
        and parse_ok
        and not gold_changes
        and model_answer_changes
    )
    # The primary fixed-sample analysis fails closed: an unusable relevant pair is
    # not a success and an unusable irrelevant pair counts as a specificity failure.
    irrelevant_flip_primary = bool(
        not required_change and (not parse_ok or gold_changes or irrelevant_flip_observed)
    )

    if required_change:
        if not parse_ok:
            failure = "PARSER_OR_MISSING_OUTPUT"
        elif not gold_changes:
            failure = "RELEVANT_GOLD_DID_NOT_CHANGE"
        elif not original_correct:
            failure = "ORIGINAL_PREDICTION_INCORRECT"
        elif not model_answer_changes:
            failure = "MODEL_DID_NOT_UPDATE"
        elif not edited_correct:
            failure = "MODEL_CHANGED_TO_WRONG_ANSWER"
        else:
            failure = "SEMANTIC_UPDATE_SUCCESS"
    else:
        if not parse_ok:
            failure = "PARSER_OR_MISSING_OUTPUT_COUNTS_AS_FLIP"
        elif gold_changes:
            failure = "IRRELEVANT_GOLD_CHANGED_PROTOCOL_DEFECT"
        elif model_answer_changes:
            failure = "IRRELEVANT_FLIP"
        else:
            failure = "IRRELEVANT_STABLE"

    transition = (
        "PARSE_FAILURE"
        if not parse_ok
        else f"ORIGINAL_{'CORRECT' if original_correct else 'WRONG'}"
        f"_TO_EDITED_{'CORRECT' if edited_correct else 'WRONG'}"
    )
    return {
        "required_change": required_change,
        "parse_ok": parse_ok,
        "gold_answer_changes": gold_changes,
        "model_answer_changes": model_answer_changes,
        "model_answer_changes_to_edited_gold": changes_to_edited_gold,
        "original_correct": original_correct,
        "edited_correct": edited_correct,
        "semantic_update_success": semantic_update_success,
        "irrelevant_flip": irrelevant_flip_observed,
        "irrelevant_flip_primary": irrelevant_flip_primary,
        "transition": transition,
        "failure_taxonomy": failure,
    }


def summarize_items(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values = list(rows)
    if not values:
        raise ValueError("at least one scored item is required")
    relevant = [row for row in values if row["required_change"] is True]
    irrelevant = [row for row in values if row["required_change"] is False]
    originally_correct_relevant = [row for row in relevant if row["original_correct"]]

    def rate(items: list[dict[str, Any]], field: str) -> float | None:
        return sum(bool(row[field]) for row in items) / len(items) if items else None

    return {
        "items": len(values),
        "relevant_items": len(relevant),
        "irrelevant_items": len(irrelevant),
        "original_accuracy": rate(values, "original_correct"),
        "edited_accuracy": rate(values, "edited_correct"),
        "raw_answer_change_rate": rate(values, "model_answer_changes"),
        "correct_semantic_update_rate": rate(relevant, "semantic_update_success"),
        "conditional_semantic_update_rate_given_original_correct": rate(
            originally_correct_relevant, "semantic_update_success"
        ),
        "irrelevant_flip_rate": rate(irrelevant, "irrelevant_flip_primary"),
        "parse_failure_rate": 1.0 - rate(values, "parse_ok"),
        "transition_matrix": dict(sorted(Counter(row["transition"] for row in values).items())),
        "failure_taxonomy": dict(
            sorted(Counter(row["failure_taxonomy"] for row in values).items())
        ),
        "secondary_descriptive_old_gap": {
            "label": "SECONDARY_DESCRIPTIVE_NOT_A_CERTIFICATE",
            "value": rate(values, "original_correct") - rate(values, "model_answer_changes"),
        },
    }


def two_gate_certificate(
    rows: Iterable[dict[str, Any]],
    *,
    tau_update: float,
    tau_spurious: float,
    responsiveness_alpha: float,
    specificity_alpha: float,
) -> dict[str, Any]:
    """Apply the preregistered fixed-sample responsiveness and specificity gates."""
    values = list(rows)
    relevant = [row for row in values if row["required_change"] is True]
    irrelevant = [row for row in values if row["required_change"] is False]
    if not relevant or not irrelevant:
        raise ValueError("two-gate certification requires relevant and irrelevant items")
    successes = sum(bool(row["semantic_update_success"]) for row in relevant)
    flips = sum(bool(row["irrelevant_flip_primary"]) for row in irrelevant)
    update_lower = clopper_pearson_lower(
        successes, len(relevant), responsiveness_alpha
    )
    spurious_upper = clopper_pearson_upper(flips, len(irrelevant), specificity_alpha)
    update_pass = update_lower >= tau_update
    specificity_pass = spurious_upper <= tau_spurious
    return {
        "schema": "certvic.confirmatory.two_gate_certificate.v1",
        "analysis_mode": "FIXED_SAMPLE_PRIMARY",
        "responsiveness": {
            "successes": successes,
            "denominator": len(relevant),
            "observed_rate": successes / len(relevant),
            "one_sided_clopper_pearson_lower": update_lower,
            "alpha": responsiveness_alpha,
            "tau_update": tau_update,
            "pass": update_pass,
        },
        "specificity": {
            "failures": flips,
            "denominator": len(irrelevant),
            "observed_rate": flips / len(irrelevant),
            "one_sided_clopper_pearson_upper": spurious_upper,
            "alpha": specificity_alpha,
            "tau_spurious": tau_spurious,
            "pass": specificity_pass,
        },
        "decision": "PASS" if update_pass and specificity_pass else "FAIL",
        "all_gates_required": True,
        "paper_evidence": False,
    }
