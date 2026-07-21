"""Build text/HTML contact sheets for qualitative figure candidates."""

from __future__ import annotations

from pathlib import Path


def write_contact_sheet(items: list[dict], out: str) -> dict:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(
        f"<tr><td>{item.get('item_id')}</td><td>{item.get('original_image_path')}</td>"
        f"<td>{item.get('edited_image_path')}</td><td>{item.get('caption_stub', '')}</td></tr>"
        for item in items
    )
    path.write_text(
        "<!doctype html><meta charset='utf-8'><title>CertVIC contact sheet</title>"
        "<h1>Qualitative Figure Candidates</h1><table>"
        "<tr><th>Item</th><th>Original</th><th>Edited</th><th>Caption stub</th></tr>"
        f"{rows}</table>",
        encoding="utf-8",
    )
    return {"out": str(path), "n_items": len(items), "pixels_copied": False}

