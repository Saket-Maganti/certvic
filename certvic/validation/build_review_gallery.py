"""Build a local HTML review gallery from a visual-review sheet.

Uses local relative links only; does not copy pixels by default and contacts no
external services. The gallery is an inspection aid, not evidence.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
from pathlib import Path

GALLERY_FIELDS = [
    "photorealistic",
    "single_factor",
    "target_object_clear",
    "required_change_unambiguous",
    "prompt_answerable",
    "keep_for_eval",
]


def _rel(path: str, start: Path) -> str:
    if not path:
        return ""
    try:
        return os.path.relpath(path, start)
    except ValueError:
        return path


def build_review_gallery(review_sheet: str, out_dir: str, copy_pixels: bool = False) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(Path(review_sheet).open("r", encoding="utf-8")))
    cards = []
    for row in rows:
        orig = _rel(row.get("original_image_path", ""), out)
        edited = _rel(row.get("edited_image_path", ""), out)
        fields = "".join(
            f"<li>{html.escape(f)}: <b>{html.escape(row.get(f, '') or '-')}</b></li>" for f in GALLERY_FIELDS
        )
        cards.append(
            f"""
<div class="card">
  <h3>{html.escape(str(row.get('item_id', '')))} <small>({html.escape(str(row.get('edit_type', '')))})</small></h3>
  <div class="imgs">
    <figure><img src="{html.escape(orig)}" loading="lazy"><figcaption>original</figcaption></figure>
    <figure><img src="{html.escape(edited)}" loading="lazy"><figcaption>edited</figcaption></figure>
  </div>
  <p class="q">{html.escape(str(row.get('neutral_question', '')))}</p>
  <p class="qg">quality: {html.escape(str(row.get('quality_gate_status', '')))} — {html.escape(str(row.get('quality_warnings', '')))}</p>
  <ul>{fields}</ul>
</div>"""
        )
    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>CertVIC Visual Review</title>
<style>
body{{font-family:sans-serif;margin:1rem;}}
.card{{border:1px solid #ccc;border-radius:8px;padding:1rem;margin:1rem 0;}}
.imgs{{display:flex;gap:1rem;}}
.imgs img{{max-width:320px;height:auto;border:1px solid #eee;}}
.q{{font-weight:bold;}} .qg{{color:#666;font-size:.9em;}}
</style></head>
<body>
<h1>CertVIC Visual Review Gallery</h1>
<p>Local inspection only. Human review validates edit/item quality; it is not model evidence.</p>
{''.join(cards)}
</body></html>"""
    index = out / "index.html"
    index.write_text(page, encoding="utf-8")
    summary = {"review_sheet": review_sheet, "out_dir": out_dir, "cards": len(rows), "index": str(index), "pixels_copied": bool(copy_pixels), "external_services": False}
    (out / "gallery_summary.json").write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build a local HTML visual-review gallery")
    parser.add_argument("--review-sheet", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--copy-pixels", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(build_review_gallery(args.review_sheet, args.out_dir, copy_pixels=args.copy_pixels), sort_keys=True))


if __name__ == "__main__":
    main()
