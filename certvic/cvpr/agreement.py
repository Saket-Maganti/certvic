"""Agreement statistics for completed, independent blinded review sheets."""

from __future__ import annotations

import csv
import hashlib
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any

from certvic.cvpr.human_review import JUDGMENT_FIELDS


def _rows(path: str | Path) -> dict[str, dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {str(row.get("blind_pair_id", "")): row for row in rows}
    if "" in result or len(result) != len(rows):
        raise ValueError("review sheet has blank or duplicate pair IDs")
    return result


def _cohen(left: list[str], right: list[str]) -> float:
    if not left:
        return math.nan
    agreement = sum(a == b for a, b in zip(left, right, strict=True)) / len(left)
    labels = set(left) | set(right)
    expected = sum((left.count(label) / len(left)) * (right.count(label) / len(right))
                   for label in labels)
    return 1.0 if expected == 1 and agreement == 1 else (agreement - expected) / (1 - expected)


def _gwet_ac1(left: list[str], right: list[str]) -> float:
    if not left:
        return math.nan
    observed = sum(a == b for a, b in zip(left, right, strict=True)) / len(left)
    labels = set(left) | set(right)
    if len(labels) <= 1:
        return 1.0
    probabilities = [
        (left.count(label) + right.count(label)) / (2 * len(left)) for label in labels
    ]
    chance = sum(probability * (1 - probability) for probability in probabilities) / (len(labels) - 1)
    return (observed - chance) / (1 - chance) if chance < 1 else 1.0


def _bootstrap(left: list[str], right: list[str], seed: int, draws: int) -> list[float]:
    if not left:
        return []
    rng = random.Random(seed)
    values = []
    for _ in range(draws):
        indices = [rng.randrange(len(left)) for _ in left]
        values.append(sum(left[index] == right[index] for index in indices) / len(indices))
    return sorted(values)


def agreement_report(
    rater_1: str | Path,
    rater_2: str | Path,
    *,
    rater_1_id: str,
    rater_2_id: str,
    seed: int = 12013,
    bootstrap_draws: int = 1000,
    fields: tuple[str, ...] = JUDGMENT_FIELDS,
) -> dict[str, Any]:
    if not rater_1_id or not rater_2_id or rater_1_id == rater_2_id:
        raise ValueError("two distinct nonblank rater identities are required")
    left_rows, right_rows = _rows(rater_1), _rows(rater_2)
    if set(left_rows) != set(right_rows):
        raise ValueError("rater sheets contain different pair IDs")
    per_question: dict[str, Any] = {}
    all_left: list[str] = []
    all_right: list[str] = []
    for field in fields:
        left = [left_rows[key].get(field, "").strip() for key in sorted(left_rows)]
        right = [right_rows[key].get(field, "").strip() for key in sorted(right_rows)]
        if any(not value for value in left + right):
            raise ValueError(f"review sheet is incomplete for {field}")
        samples = _bootstrap(left, right, seed + len(per_question), bootstrap_draws)
        lower_index = int(0.025 * (len(samples) - 1))
        upper_index = int(0.975 * (len(samples) - 1))
        per_question[field] = {
            "percent_agreement": sum(a == b for a, b in zip(left, right, strict=True)) / len(left),
            "cohen_kappa": _cohen(left, right),
            "gwet_ac1": _gwet_ac1(left, right),
            "agreement_bootstrap_95": [samples[lower_index], samples[upper_index]],
        }
        all_left.extend(left)
        all_right.extend(right)
    confidence_pairs = Counter(
        f"{left_rows[key]['confidence']}|{right_rows[key]['confidence']}" for key in sorted(left_rows)
    )
    return {
        "schema": "certvic.cvpr.review_agreement.v1",
        "rows": len(left_rows),
        "primary_statistic": "gwet_ac1_retain",
        "percent_agreement": sum(a == b for a, b in zip(all_left, all_right, strict=True)) / len(all_left),
        "cohen_kappa": _cohen(all_left, all_right),
        "gwet_ac1": _gwet_ac1(all_left, all_right),
        "per_question": per_question,
        "confidence_strata": dict(confidence_pairs),
        "rater_identities_distinct": True,
        "rater_identity_hashes": {
            "rater_1": hashlib.sha256(rater_1_id.encode()).hexdigest(),
            "rater_2": hashlib.sha256(rater_2_id.encode()).hexdigest(),
        },
        "input_sheet_sha256": {
            "rater_1": hashlib.sha256(Path(rater_1).read_bytes()).hexdigest(),
            "rater_2": hashlib.sha256(Path(rater_2).read_bytes()).hexdigest(),
        },
        "agreement_computed_from_exact_inputs": True,
        "paper_evidence": False,
    }
