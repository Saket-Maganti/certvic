"""Simple inter-annotator agreement metrics."""

from __future__ import annotations

from collections import Counter


def percent_agreement(labels_a: list[str], labels_b: list[str]) -> float:
    if len(labels_a) != len(labels_b):
        raise ValueError("label lists must have same length")
    if not labels_a:
        return 0.0
    return sum(a == b for a, b in zip(labels_a, labels_b)) / len(labels_a)


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    observed = percent_agreement(labels_a, labels_b)
    n = len(labels_a)
    if n == 0:
        return 0.0
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)
    expected = sum((counts_a[k] / n) * (counts_b[k] / n) for k in set(counts_a) | set(counts_b))
    if expected == 1:
        return 1.0
    return (observed - expected) / (1 - expected)


def normalize_rating(value: str) -> str:
    """Robust yes/no/uncertain normalization."""
    text = str(value).strip().lower()
    if text in {"y", "yes", "true", "1"}:
        return "yes"
    if text in {"n", "no", "false", "0"}:
        return "no"
    if text in {"u", "uncertain", "maybe", "?", ""}:
        return "uncertain"
    return text


def majority_agreement(labels: list[str]) -> float:
    """Fraction of raters agreeing with the modal label, for one item."""
    if not labels:
        return 0.0
    return Counter(labels).most_common(1)[0][1] / len(labels)


def field_iaa(per_item_rater_labels: list[list[str]]) -> dict:
    """Inter-annotator agreement for one field across items.

    `per_item_rater_labels` is a list (one entry per item) of the raw rater
    labels for that item. Uses Cohen's kappa when every item has exactly two
    raters, average per-item majority agreement for three or more, and warns on
    a single rater. Yes/No/Uncertain values are normalized robustly.
    """
    items = [[normalize_rating(v) for v in labels if str(v).strip() != ""] for labels in per_item_rater_labels]
    items = [it for it in items if it]
    rater_counts = [len(it) for it in items]
    max_raters = max(rater_counts) if rater_counts else 0
    per_item_majority = [majority_agreement(it) for it in items]
    mean_majority = sum(per_item_majority) / len(per_item_majority) if per_item_majority else 0.0
    result = {
        "n_items": len(items),
        "max_raters": max_raters,
        "mean_majority_agreement": mean_majority,
        "single_rater_warning": max_raters < 2,
        "method": "no_data",
        "kappa": None,
        "percent_agreement": None,
    }
    if items and all(len(it) == 2 for it in items):
        a = [it[0] for it in items]
        b = [it[1] for it in items]
        result["method"] = "cohens_kappa"
        result["kappa"] = cohens_kappa(a, b)
        result["percent_agreement"] = percent_agreement(a, b)
    elif max_raters >= 3:
        result["method"] = "majority_agreement"
    elif max_raters == 1:
        result["method"] = "single_rater"
    elif max_raters == 2:
        result["method"] = "two_rater_uneven"
    return result
