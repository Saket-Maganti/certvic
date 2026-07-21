"""Disagreement resolution / adjudication for visual review (V3 prompt 07).

Collapses a multi-reviewer ratings CSV into one adjudicated row per item by
majority vote on each decision field, flagging ties that need a human
adjudicator. No model outputs, no paid services.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from certvic.io import ensure_parent
from certvic.validation.aggregate_visual_review import DECISION_FIELDS
from certvic.validation.iaa import normalize_rating

ADJUDICATED_COLUMNS = [
    "item_id",
    "n_reviewers",
    *DECISION_FIELDS,
    "adjudication_status",
    "disagreement_fields",
]


def _resolve_field(values: list[str]) -> tuple[str, str]:
    """Return (resolved_label, status) for one field across reviewers."""
    norm = [normalize_rating(v) for v in values if str(v).strip() != ""]
    if not norm:
        return "", "no_ratings"
    counts = Counter(norm)
    top = counts.most_common()
    if len(top) == 1:
        return top[0][0], "unanimous"
    if top[0][1] > top[1][1]:
        return top[0][0], "majority"
    return "uncertain", "tie_needs_human"


def adjudicate(rows: list[dict]) -> dict:
    by_item: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_item[str(row.get("item_id", ""))].append(row)

    adjudicated: list[dict] = []
    n_ties = 0
    n_unanimous_items = 0
    for item_id, item_rows in sorted(by_item.items()):
        resolved = {"item_id": item_id, "n_reviewers": len(item_rows)}
        statuses: list[str] = []
        disagreement_fields: list[str] = []
        for field in DECISION_FIELDS:
            label, status = _resolve_field([r.get(field, "") for r in item_rows])
            resolved[field] = label
            statuses.append(status)
            if status in {"majority", "tie_needs_human"}:
                disagreement_fields.append(field)
        if "tie_needs_human" in statuses:
            item_status = "tie_needs_human"
            n_ties += 1
        elif "majority" in statuses:
            item_status = "majority"
        elif all(s == "unanimous" for s in statuses):
            item_status = "unanimous"
            n_unanimous_items += 1
        else:
            item_status = "partial"
        resolved["adjudication_status"] = item_status
        resolved["disagreement_fields"] = ";".join(disagreement_fields)
        adjudicated.append(resolved)

    return {
        "task": "visual_review_adjudication",
        "n_items": len(adjudicated),
        "n_unanimous_items": n_unanimous_items,
        "n_tie_items": n_ties,
        "rows": adjudicated,
        "paid_annotation_services": False,
        "evidence_claims_made": False,
    }


def adjudicate_review(ratings_csv: str, out_path: str) -> dict:
    with Path(ratings_csv).open("r", encoding="utf-8") as h:
        rows = list(csv.DictReader(h))
    result = adjudicate(rows)
    ensure_parent(out_path)
    with Path(out_path).open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=ADJUDICATED_COLUMNS)
        writer.writeheader()
        for row in result["rows"]:
            writer.writerow(row)
    result["out_path"] = out_path
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC visual-review adjudication (majority vote + tie flags)")
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = adjudicate_review(args.ratings, args.out)
    print(json.dumps({
        "n_items": result["n_items"],
        "n_unanimous_items": result["n_unanimous_items"],
        "n_tie_items": result["n_tie_items"],
        "out": args.out,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
