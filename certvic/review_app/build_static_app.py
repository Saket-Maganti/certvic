"""Build a self-contained static review app from a visual-review CSV."""

from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path


RATING_COLUMNS = [
    "item_id",
    "reviewer_id",
    "single_factor_valid",
    "edit_realism",
    "answer_visible",
    "notes",
]


def build_static_app(review_sheet: str, out_dir: str, *, reveal_ground_truth: bool = False) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with Path(review_sheet).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    items: list[dict] = []
    for row in rows:
        item = {
            "item_id": row.get("item_id"),
            "original_image_path": row.get("original_image_path"),
            "edited_image_path": row.get("edited_image_path"),
            "task_family": row.get("task_family"),
            "edit_type": row.get("edit_type"),
        }
        if reveal_ground_truth:
            item["required_change"] = row.get("required_change")
        items.append(item)
    (out / "items.json").write_text(json.dumps(items, indent=2, sort_keys=True), encoding="utf-8")
    (out / "instructions.md").write_text(
        "# Visual QA Review\n\nUse keyboard-friendly ratings. Ground truth is hidden by default.\n",
        encoding="utf-8",
    )
    with (out / "ratings_template.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RATING_COLUMNS)
        writer.writeheader()
        for item in items:
            writer.writerow({"item_id": item.get("item_id"), "reviewer_id": ""})
    body = "\n".join(
        f"<article data-item='{html.escape(str(item.get('item_id')))}'>"
        f"<h2>{html.escape(str(item.get('item_id')))}</h2>"
        f"<p>{html.escape(str(item.get('task_family')))} / {html.escape(str(item.get('edit_type')))}</p>"
        "</article>"
        for item in items
    )
    (out / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>CertVIC Review</title>"
        "<h1>CertVIC Visual QA Review</h1><p>No external services. Pixels are referenced, not copied.</p>"
        f"<script type='application/json' id='items'>{html.escape(json.dumps(items))}</script>{body}",
        encoding="utf-8",
    )
    return {
        "review_sheet": review_sheet,
        "out_dir": str(out),
        "n_items": len(items),
        "external_services": False,
        "pixels_copied": False,
        "ground_truth_hidden": not reveal_ground_truth,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build static visual QA review app")
    parser.add_argument("--review-sheet", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--reveal-ground-truth", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(build_static_app(args.review_sheet, args.out_dir, reveal_ground_truth=args.reveal_ground_truth), sort_keys=True))


if __name__ == "__main__":
    main()

