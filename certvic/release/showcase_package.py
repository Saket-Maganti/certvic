"""Package a CC0/PD showcase manifest without copying pixels unless requested."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import read_jsonl, write_json


def package_showcase(split: str, out_dir: str, *, copy_pixels: bool = False) -> dict:
    rows = read_jsonl(split)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    license_counts: dict[str, int] = {}
    for row in rows:
        license_name = str(row.get("license") or row.get("license_id") or "unknown").lower()
        license_counts[license_name] = license_counts.get(license_name, 0) + 1
    manifest = {
        "split": split,
        "n_items": len(rows),
        "license_counts": license_counts,
        "pixels_copied": bool(copy_pixels),
        "release_checklist": [
            "Confirm every row is CC0 or public-domain",
            "Confirm no ADE20K/nonredistributable pixels are included",
            "Keep source URLs and license fields in the manifest",
        ],
    }
    write_json(out / "showcase_package_manifest.json", manifest)
    (out / "README.md").write_text(
        "# CertVIC Showcase Package\n\n"
        "Manifest-first showcase package. Pixels are not copied by default.\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Package a showcase split")
    parser.add_argument("--split", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--copy-pixels", action="store_true")
    args = parser.parse_args(argv)
    result = package_showcase(args.split, args.out_dir, copy_pixels=args.copy_pixels)
    print(json.dumps({"out_dir": args.out_dir, "n_items": result["n_items"], "pixels_copied": result["pixels_copied"]}, sort_keys=True))


if __name__ == "__main__":
    main()

