"""Visual-review progress tracking (V3 prompt 07).

Scans a directory of (partially) filled per-reviewer review CSVs and reports
completion per reviewer, missing ratings, and disagreements on the overlap items
(with inter-annotator agreement). No model outputs, no paid services.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from certvic.io import ensure_parent
from certvic.validation.aggregate_visual_review import DECISION_FIELDS
from certvic.validation.iaa import field_iaa, normalize_rating


def _row_is_rated(row: dict) -> bool:
    return all(str(row.get(f, "")).strip() != "" for f in DECISION_FIELDS)


def _read_ratings_dir(ratings_dir: str) -> list[dict]:
    rows: list[dict] = []
    for csv_path in sorted(Path(ratings_dir).glob("*.csv")):
        with csv_path.open("r", encoding="utf-8") as h:
            for row in csv.DictReader(h):
                row.setdefault("_source_file", csv_path.name)
                rows.append(row)
    return rows


def review_progress(ratings_dir: str) -> dict:
    rows = _read_ratings_dir(ratings_dir)

    per_reviewer: dict[str, dict] = defaultdict(lambda: {"assigned": 0, "rated": 0, "missing": 0})
    by_item: dict[str, list[dict]] = defaultdict(list)
    missing_items: list[dict] = []

    for row in rows:
        reviewer = str(row.get("reviewer_id") or row.get("_source_file") or "unknown")
        iid = str(row.get("item_id") or "")
        stats = per_reviewer[reviewer]
        stats["assigned"] += 1
        if _row_is_rated(row):
            stats["rated"] += 1
        else:
            stats["missing"] += 1
            blanks = [f for f in DECISION_FIELDS if str(row.get(f, "")).strip() == ""]
            missing_items.append({"reviewer": reviewer, "item_id": iid, "blank_fields": blanks})
        by_item[iid].append(row)

    # Overlap items: rated by more than one reviewer.
    overlap_items = {iid: r for iid, r in by_item.items() if len({str(x.get("reviewer_id")) for x in r}) > 1}
    disagreements: list[dict] = []
    for iid, item_rows in sorted(overlap_items.items()):
        for field in DECISION_FIELDS:
            vals = {normalize_rating(x.get(field, "")) for x in item_rows if str(x.get(field, "")).strip() != ""}
            if len(vals) > 1:
                disagreements.append({"item_id": iid, "field": field, "values": sorted(vals)})

    # IAA per decision field over overlap items.
    iaa: dict[str, dict] = {}
    for field in DECISION_FIELDS:
        per_item_labels = [[x.get(field, "") for x in item_rows] for item_rows in overlap_items.values()]
        per_item_labels = [labels for labels in per_item_labels if any(str(v).strip() for v in labels)]
        if per_item_labels:
            iaa[field] = field_iaa(per_item_labels)

    total_assigned = sum(s["assigned"] for s in per_reviewer.values())
    total_rated = sum(s["rated"] for s in per_reviewer.values())
    return {
        "task": "visual_review_progress",
        "ratings_dir": ratings_dir,
        "n_reviewers": len(per_reviewer),
        "per_reviewer": {k: dict(v) for k, v in sorted(per_reviewer.items())},
        "total_assigned": total_assigned,
        "total_rated": total_rated,
        "completion_fraction": round(total_rated / total_assigned, 4) if total_assigned else 0.0,
        "n_missing_rows": len(missing_items),
        "missing_ratings": missing_items,
        "n_overlap_items": len(overlap_items),
        "n_disagreements": len(disagreements),
        "disagreements": disagreements,
        "iaa": iaa,
        "all_complete": total_assigned > 0 and total_rated == total_assigned,
        "paid_annotation_services": False,
        "evidence_claims_made": False,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC visual-review progress tracker")
    parser.add_argument("--ratings-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = review_progress(args.ratings_dir)
    ensure_parent(args.out)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "completion_fraction": result["completion_fraction"],
        "total_rated": result["total_rated"],
        "total_assigned": result["total_assigned"],
        "n_disagreements": result["n_disagreements"],
        "all_complete": result["all_complete"],
        "out": args.out,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
