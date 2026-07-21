"""Deterministic failure taxonomy classifier.

Rule-based classification from PairScore + predictions + metadata. No LLM calls,
no pixel copies. Supports a manual override file (item_id -> label). Makes no
deployment or causal-understanding claims.
"""

from __future__ import annotations

TAXONOMY = [
    "missed_required_change",
    "spurious_flip_on_control",
    "original_recognition_failure",
    "edited_recognition_failure",
    "parse_failure",
    "answer_inertia",
    "overreaction_to_irrelevant_edit",
    "safety_prompt_bias",
    "caption_like_behavior",
    "ambiguous_item",
]


def _is_control(task_family: str, edit_type: str) -> bool:
    return task_family == "control_irrelevant" or str(edit_type).startswith("control_") or edit_type == "control_irrelevant"


def classify_failure(
    score: dict,
    pred_original: dict | None,
    pred_edited: dict | None,
    edit_type: str = "",
    overrides: dict | None = None,
) -> dict:
    """Return {primary, applicable, ...} for one item. `score` is a PairScore dict."""
    item_id = str(score.get("item_id"))
    if overrides and item_id in overrides:
        label = overrides[item_id]
        return {"item_id": item_id, "primary": label, "applicable": [label], "source": "manual_override"}

    required_change = str(score.get("required_change"))
    task_family = str(score.get("task_family"))
    parse_ok = bool(score.get("parse_ok"))
    original_correct = bool(score.get("original_correct"))
    edited_correct = bool(score.get("edited_correct"))
    consistent = bool(score.get("consistent"))
    po = (pred_original or {}).get("parsed_answer")
    pe = (pred_edited or {}).get("parsed_answer")
    po_ok = (pred_original or {}).get("parse_ok", parse_ok)
    pe_ok = (pred_edited or {}).get("parse_ok", parse_ok)
    low_conf = min(
        float((pred_original or {}).get("parse_confidence", 1.0)),
        float((pred_edited or {}).get("parse_confidence", 1.0)),
    )

    applicable: list[str] = []
    if not parse_ok or not po_ok or not pe_ok:
        applicable.append("parse_failure")
    if required_change == "no_change" and not consistent and parse_ok:
        applicable.append("spurious_flip_on_control" if _is_control(task_family, edit_type) else "overreaction_to_irrelevant_edit")
    if required_change == "change" and not consistent and parse_ok:
        applicable.append("missed_required_change")
        if po is not None and po == pe:
            applicable.append("answer_inertia")
    if parse_ok and not original_correct:
        applicable.append("original_recognition_failure")
    if parse_ok and not edited_correct:
        applicable.append("edited_recognition_failure")
    if parse_ok and low_conf < 0.5:
        applicable.append("ambiguous_item")

    # de-duplicate, preserve taxonomy priority order
    ordered = [t for t in TAXONOMY if t in applicable]
    primary = ordered[0] if ordered else "none"
    return {
        "item_id": item_id,
        "primary": primary,
        "applicable": ordered,
        "is_failure": primary != "none",
        "parsed_original": po,
        "parsed_edited": pe,
        "source": "rule_based",
    }
