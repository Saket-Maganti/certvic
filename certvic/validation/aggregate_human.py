"""Aggregate human validity ratings."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from certvic.io import write_json

FIELDS = ["photorealistic", "single_factor", "required_change_unambiguous"]


def aggregate_ratings(ratings_csv: str, out_path: str, drop_list_path: str) -> dict:
    rows = list(csv.DictReader(Path(ratings_csv).open("r", encoding="utf-8")))
    by_item: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_item[row["item_id"]].append(row)
    drops: list[str] = []
    keep: list[str] = []
    for item_id, item_rows in by_item.items():
        drop = False
        for field in FIELDS:
            values = [row.get(field, "").strip().lower() for row in item_rows]
            if values.count("no") > len(values) / 2 or values.count("uncertain") >= len(values):
                drop = True
        (drops if drop else keep).append(item_id)
    summary = {"n_items": len(by_item), "drop_count": len(drops), "keep_count": len(keep), "drop_items": drops, "keep_items": keep}
    write_json(out_path, summary)
    Path(drop_list_path).parent.mkdir(parents=True, exist_ok=True)
    Path(drop_list_path).write_text("\n".join(drops) + ("\n" if drops else ""), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--drop-list", required=True)
    args = parser.parse_args(argv)
    aggregate_ratings(args.ratings, args.out, args.drop_list)


if __name__ == "__main__":
    main()
