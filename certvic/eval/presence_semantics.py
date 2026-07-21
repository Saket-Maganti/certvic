"""Fail-closed helpers for normalizing presence-question polarity.

The canonical pilot deliberately alternates positive ("is X visible?") and
negative ("is X absent?") wording.  Downstream ablations and mechanism probes
use positive-presence semantics, so their gold labels must first be normalized
out of the source question's wording.  Copying ``answer_original`` or
``answer_edited`` directly is wrong for every negative-worded source item.
"""

from __future__ import annotations


def invert_yes_no(answer: str) -> str:
    """Invert a yes/no answer, rejecting anything outside the locked schema."""
    normalized = str(answer or "").strip().lower()
    if normalized == "yes":
        return "no"
    if normalized == "no":
        return "yes"
    raise ValueError(f"expected yes/no answer, got {answer!r}")


def presence_question_polarity(question: str) -> str:
    """Return ``positive`` or ``negative`` for a supported presence question.

    Negative wording is checked first because the canonical negative template
    also contains the phrase "clearly visible".
    """
    normalized = " ".join(str(question or "").lower().split())
    if "absent" in normalized:
        return "negative"
    if "clearly visible" in normalized or normalized.startswith("visible "):
        return "positive"
    raise ValueError(f"unsupported presence-question wording: {question!r}")


def positive_presence_gold(question: str, answer: str) -> str:
    """Normalize a source answer to positive "target is visible" semantics."""
    normalized = str(answer or "").strip().lower()
    if normalized not in {"yes", "no"}:
        raise ValueError(f"expected yes/no answer, got {answer!r}")
    if presence_question_polarity(question) == "negative":
        return invert_yes_no(normalized)
    return normalized


def item_positive_presence_gold(item: dict, image_variant: str) -> str:
    """Return positive-presence gold for an original or edited item variant."""
    if image_variant not in {"original", "edited"}:
        raise ValueError(f"unknown image variant: {image_variant!r}")
    question = item.get(f"question_{image_variant}")
    answer = item.get(f"answer_{image_variant}")
    return positive_presence_gold(question, answer)
