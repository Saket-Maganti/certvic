"""Assemble qualitative figure candidate manifests with license checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import read_jsonl, write_json
from certvic.paper.figure_contact_sheet import write_contact_sheet

ALLOWED_LICENSES = {"cc0", "public_domain", "pd", "public domain"}


def build_qualitative_figures(gallery: str, out_dir: str, *, dry_run: bool = True) -> dict:
    rows = read_jsonl(gallery)
    eligible: list[dict] = []
    rejected = 0
    for row in rows:
        license_name = str(row.get("license") or row.get("license_id") or "").lower()
        if license_name in ALLOWED_LICENSES or row.get("figure_use_ok"):
            item = dict(row)
            item["caption_stub"] = "[CAPTION REQUIRED - do not fabricate]"
            item["pixels_copied"] = False
            eligible.append(item)
        else:
            rejected += 1
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "figure_manifest.json", {"items": eligible, "dry_run": dry_run, "pixels_copied": False})
    (out / "latex_include_stubs.tex").write_text("% Qualitative figure stubs; captions required.\n", encoding="utf-8")
    contact = write_contact_sheet(eligible, str(out / "contact_sheet.html"))
    return {
        "gallery": gallery,
        "out_dir": str(out),
        "eligible": len(eligible),
        "rejected": rejected,
        "dry_run": dry_run,
        "pixels_copied": False,
        "fake_captions": False,
        "contact_sheet": contact["out"],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build qualitative figure candidates")
    parser.add_argument("--gallery", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(build_qualitative_figures(args.gallery, args.out_dir, dry_run=not args.apply), sort_keys=True))


if __name__ == "__main__":
    main()

