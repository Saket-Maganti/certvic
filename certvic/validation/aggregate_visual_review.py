"""Aggregate visual-review ratings into keep/drop decisions with IAA."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from certvic.io import write_json
from certvic.validation.iaa import field_iaa, normalize_rating

# Fields that must hold for an item to be kept.
DECISION_FIELDS = [
    "photorealistic",
    "single_factor",
    "target_object_clear",
    "required_change_unambiguous",
    "prompt_answerable",
    "keep_for_eval",
]


def _drop_item(field_to_values: dict[str, list[str]]) -> tuple[bool, list[str]]:
    """Drop if any decision field is majority-no or uncertain-heavy."""
    reasons: list[str] = []
    for field in DECISION_FIELDS:
        values = [normalize_rating(v) for v in field_to_values.get(field, []) if str(v).strip() != ""]
        if not values:
            reasons.append(f"{field}: no ratings")
            continue
        n = len(values)
        if values.count("no") > n / 2:
            reasons.append(f"{field}: majority no")
        elif values.count("uncertain") >= n / 2:
            reasons.append(f"{field}: uncertain-heavy")
        elif values.count("yes") <= n / 2:
            reasons.append(f"{field}: not majority yes")
    return (bool(reasons), reasons)


def aggregate_visual_review(ratings_csv: str, out_path: str, keep_list_path: str, drop_list_path: str) -> dict:
    rows = list(csv.DictReader(Path(ratings_csv).open("r", encoding="utf-8")))
    by_item: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_item[str(row.get("item_id", ""))].append(row)

    keep: list[str] = []
    drop: list[str] = []
    drop_reasons: dict[str, list[str]] = {}
    item_field_values: dict[str, dict[str, list[str]]] = {}
    for item_id, item_rows in by_item.items():
        field_to_values = {field: [r.get(field, "") for r in item_rows] for field in DECISION_FIELDS}
        item_field_values[item_id] = field_to_values
        dropped, reasons = _drop_item(field_to_values)
        if dropped:
            drop.append(item_id)
            drop_reasons[item_id] = reasons
        else:
            keep.append(item_id)

    # Per-field IAA across items.
    iaa: dict[str, dict] = {}
    single_rater_warnings: list[str] = []
    for field in DECISION_FIELDS:
        matrix = [item_field_values[item_id][field] for item_id in by_item]
        iaa[field] = field_iaa(matrix)
        if iaa[field]["single_rater_warning"]:
            single_rater_warnings.append(field)

    summary = {
        "ratings_csv": ratings_csv,
        "n_items": len(by_item),
        "keep_count": len(keep),
        "drop_count": len(drop),
        "keep_items": sorted(keep),
        "drop_items": sorted(drop),
        "drop_reasons": drop_reasons,
        "iaa": iaa,
        "single_rater_warning_fields": single_rater_warnings,
        "decision_fields": DECISION_FIELDS,
        "evidence_status": "HUMAN_REVIEWED_NON_EVIDENCE",
        "field_yes_no_uncertain": {
            field: dict(Counter(normalize_rating(r.get(field, "")) for r in rows)) for field in DECISION_FIELDS
        },
    }
    write_json(out_path, summary)
    _write_list(keep_list_path, sorted(keep))
    _write_list(drop_list_path, sorted(drop))
    return summary


def _write_list(path: str, items: list[str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(items) + ("\n" if items else ""), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Aggregate visual-review ratings")
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--keep-list", required=True)
    parser.add_argument("--drop-list", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(aggregate_visual_review(args.ratings, args.out, args.keep_list, args.drop_list), sort_keys=True))


if __name__ == "__main__":
    main()
