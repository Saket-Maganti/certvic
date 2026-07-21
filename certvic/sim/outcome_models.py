"""Seeded synthetic outcome models for pre-run CertVIC stress testing."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable


BUILTIN_SCENARIOS = [
    "perfect_consistent",
    "high_accuracy_low_consistency",
    "low_accuracy_high_consistency",
    "spurious_control_flipper",
    "parse_failure_heavy",
    "family_specific_failure",
    "domain_specific_failure",
    "edit_type_specific_failure",
    "small_gap_borderline",
    "null_gap",
    "noisy_realistic_mixed",
]


@dataclass(frozen=True)
class Outcome:
    original_correct: bool
    edited_correct: bool
    consistent: bool
    parse_ok: bool
    raw_original: str
    raw_edited: str
    parsed_original: str | None
    parsed_edited: str | None
    parse_confidence: float
    behavior_note: str


def generate_outcome(task: dict, scenario: str, seed: int, index: int) -> Outcome:
    """Generate deterministic prediction behavior for one synthetic task."""

    if scenario not in BUILTIN_SCENARIOS:
        raise ValueError(f"Unknown simulation scenario: {scenario}")
    rng = random.Random(f"{scenario}|{seed}|{index}|{task['item_id']}")
    return _SCENARIOS[scenario](task, rng)


def _answers_for_state(task: dict, original_correct: bool, edited_correct: bool, consistent: bool) -> tuple[str, str]:
    orig_expected = task["answer_original"]
    edit_expected = task["answer_edited"]
    orig_wrong = _opposite(orig_expected)
    edit_wrong = _opposite(edit_expected)
    required_change = task["required_change"]

    if original_correct:
        parsed_original = orig_expected
    else:
        parsed_original = orig_wrong

    if required_change == "change":
        if consistent:
            parsed_edited = _opposite(parsed_original)
        else:
            parsed_edited = parsed_original
    else:
        if consistent:
            parsed_edited = parsed_original
        else:
            parsed_edited = _opposite(parsed_original)

    if edited_correct and parsed_edited != edit_expected:
        parsed_edited = edit_expected
        if required_change == "change" and parsed_edited == parsed_original:
            parsed_original = _opposite(parsed_edited)
        if required_change == "no_change" and parsed_edited != parsed_original:
            parsed_original = parsed_edited
    elif not edited_correct and parsed_edited == edit_expected:
        parsed_edited = edit_wrong

    return parsed_original, parsed_edited


def _make(
    task: dict,
    rng: random.Random,
    original_accuracy: float,
    consistency_rate: float,
    parse_failure_rate: float = 0.0,
    edited_accuracy: float | None = None,
    note: str = "configured_profile",
) -> Outcome:
    parse_ok = rng.random() >= parse_failure_rate
    if not parse_ok:
        return Outcome(
            original_correct=False,
            edited_correct=False,
            consistent=False,
            parse_ok=False,
            raw_original="SIMULATED_PARSE_FAILURE",
            raw_edited="SIMULATED_PARSE_FAILURE",
            parsed_original=None,
            parsed_edited=None,
            parse_confidence=0.0,
            behavior_note=note,
        )

    original_correct = rng.random() < original_accuracy
    consistent = rng.random() < consistency_rate
    if edited_accuracy is None:
        edited_correct = original_correct if consistent else rng.random() < original_accuracy
    else:
        edited_correct = rng.random() < edited_accuracy
    parsed_original, parsed_edited = _answers_for_state(
        task,
        original_correct=original_correct,
        edited_correct=edited_correct,
        consistent=consistent,
    )
    return Outcome(
        original_correct=original_correct,
        edited_correct=edited_correct,
        consistent=consistent,
        parse_ok=True,
        raw_original=f"simulated answer: {parsed_original}",
        raw_edited=f"simulated answer: {parsed_edited}",
        parsed_original=parsed_original,
        parsed_edited=parsed_edited,
        parse_confidence=0.99,
        behavior_note=note,
    )


def _perfect(task: dict, rng: random.Random) -> Outcome:
    return _make(task, rng, original_accuracy=1.0, consistency_rate=1.0, edited_accuracy=1.0, note="perfect_consistent")


def _high_accuracy_low_consistency(task: dict, rng: random.Random) -> Outcome:
    return _make(task, rng, original_accuracy=0.92, consistency_rate=0.52, edited_accuracy=0.70, note="high_accuracy_low_consistency")


def _low_accuracy_high_consistency(task: dict, rng: random.Random) -> Outcome:
    return _make(task, rng, original_accuracy=0.52, consistency_rate=0.91, edited_accuracy=0.52, note="low_accuracy_high_consistency")


def _spurious_control_flipper(task: dict, rng: random.Random) -> Outcome:
    if task["task_family"] == "control_irrelevant" or str(task["edit_type"]).startswith("control_"):
        return _make(task, rng, original_accuracy=0.90, consistency_rate=0.30, edited_accuracy=0.45, note="control_spurious_flipper")
    return _make(task, rng, original_accuracy=0.90, consistency_rate=0.88, edited_accuracy=0.88, note="control_clean_non_control")


def _parse_failure_heavy(task: dict, rng: random.Random) -> Outcome:
    return _make(task, rng, original_accuracy=0.82, consistency_rate=0.76, parse_failure_rate=0.38, edited_accuracy=0.78, note="parse_failure_heavy")


def _family_specific_failure(task: dict, rng: random.Random) -> Outcome:
    if task["task_family"] == "support_stability":
        return _make(task, rng, original_accuracy=0.88, consistency_rate=0.35, edited_accuracy=0.55, note="support_stability_failure")
    return _make(task, rng, original_accuracy=0.88, consistency_rate=0.84, edited_accuracy=0.84, note="family_non_target")


def _domain_specific_failure(task: dict, rng: random.Random) -> Outcome:
    if task["domain"] == "driving":
        return _make(task, rng, original_accuracy=0.88, consistency_rate=0.40, edited_accuracy=0.60, note="driving_failure")
    return _make(task, rng, original_accuracy=0.88, consistency_rate=0.84, edited_accuracy=0.84, note="domain_non_target")


def _edit_type_specific_failure(task: dict, rng: random.Random) -> Outcome:
    if task["edit_type"] == "occlude":
        return _make(task, rng, original_accuracy=0.90, consistency_rate=0.36, edited_accuracy=0.58, note="occlude_failure")
    return _make(task, rng, original_accuracy=0.90, consistency_rate=0.85, edited_accuracy=0.84, note="edit_type_non_target")


def _small_gap_borderline(task: dict, rng: random.Random) -> Outcome:
    original_correct = rng.random() < 0.74
    consistent = rng.random() < 0.70
    parsed_original = task["answer_original"] if original_correct else _opposite(task["answer_original"])
    if task["required_change"] == "change":
        parsed_edited = _opposite(parsed_original) if consistent else parsed_original
    else:
        parsed_edited = parsed_original if consistent else _opposite(parsed_original)
    edited_correct = parsed_edited == task["answer_edited"]
    return Outcome(
        original_correct=original_correct,
        edited_correct=edited_correct,
        consistent=consistent,
        parse_ok=True,
        raw_original=f"simulated answer: {parsed_original}",
        raw_edited=f"simulated answer: {parsed_edited}",
        parsed_original=parsed_original,
        parsed_edited=parsed_edited,
        parse_confidence=0.99,
        behavior_note="small_gap_borderline",
    )


def _null_gap(task: dict, rng: random.Random) -> Outcome:
    original_correct = rng.random() < 0.76
    consistent = original_correct
    parsed_original = task["answer_original"] if original_correct else _opposite(task["answer_original"])
    if task["required_change"] == "change":
        parsed_edited = _opposite(parsed_original) if consistent else parsed_original
    else:
        parsed_edited = parsed_original if consistent else _opposite(parsed_original)
    edited_correct = parsed_edited == task["answer_edited"]
    return Outcome(
        original_correct=original_correct,
        edited_correct=edited_correct,
        consistent=consistent,
        parse_ok=True,
        raw_original=f"simulated answer: {parsed_original}",
        raw_edited=f"simulated answer: {parsed_edited}",
        parsed_original=parsed_original,
        parsed_edited=parsed_edited,
        parse_confidence=0.99,
        behavior_note="null_gap",
    )


def _noisy_realistic_mixed(task: dict, rng: random.Random) -> Outcome:
    parse_rate = 0.06
    if task["task_family"] == "affordance_reachability":
        return _make(task, rng, original_accuracy=0.84, consistency_rate=0.68, parse_failure_rate=parse_rate, edited_accuracy=0.70, note="mixed_affordance")
    if task["domain"] == "driving":
        return _make(task, rng, original_accuracy=0.80, consistency_rate=0.62, parse_failure_rate=parse_rate, edited_accuracy=0.66, note="mixed_driving")
    if task["task_family"] == "control_irrelevant":
        return _make(task, rng, original_accuracy=0.86, consistency_rate=0.82, parse_failure_rate=parse_rate, edited_accuracy=0.82, note="mixed_control")
    return _make(task, rng, original_accuracy=0.84, consistency_rate=0.72, parse_failure_rate=parse_rate, edited_accuracy=0.73, note="mixed_default")


def _opposite(answer: str) -> str:
    if answer == "yes":
        return "no"
    if answer == "no":
        return "yes"
    return "no"


_SCENARIOS: dict[str, Callable[[dict, random.Random], Outcome]] = {
    "perfect_consistent": _perfect,
    "high_accuracy_low_consistency": _high_accuracy_low_consistency,
    "low_accuracy_high_consistency": _low_accuracy_high_consistency,
    "spurious_control_flipper": _spurious_control_flipper,
    "parse_failure_heavy": _parse_failure_heavy,
    "family_specific_failure": _family_specific_failure,
    "domain_specific_failure": _domain_specific_failure,
    "edit_type_specific_failure": _edit_type_specific_failure,
    "small_gap_borderline": _small_gap_borderline,
    "null_gap": _null_gap,
    "noisy_realistic_mixed": _noisy_realistic_mixed,
}
