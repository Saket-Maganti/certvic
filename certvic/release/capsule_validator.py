"""Validate a recipe-first reproducibility capsule without private data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.hashing import sha256_file
from certvic.io import write_json

PRIVATE_MARKERS = ("/" + "Users/", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "sk-")
PIXEL_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def validate_capsule(release_dir: str) -> dict:
    root = Path(release_dir)
    files = [p for p in root.rglob("*") if p.is_file()] if root.exists() else []
    path_leaks: list[str] = []
    pixel_files: list[str] = []
    checksums: dict[str, str] = {}
    commands_present = False
    for path in files:
        rel = path.relative_to(root).as_posix()
        checksums[rel] = sha256_file(path)
        if path.suffix.lower() in PIXEL_SUFFIXES:
            pixel_files.append(rel)
        text = ""
        if path.stat().st_size < 2_000_000:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                text = ""
        if "python" in text or "bash" in text:
            commands_present = True
        if any(marker in str(path) or marker in text for marker in PRIVATE_MARKERS):
            path_leaks.append(rel)
    return {
        "release_dir": release_dir,
        "exists": root.exists(),
        "n_files": len(files),
        "commands_present": commands_present,
        "path_leaks": path_leaks,
        "nonredistributable_pixel_risk_files": pixel_files,
        "checksums": checksums,
        "passed": root.exists() and commands_present and not path_leaks and not pixel_files,
    }


def render_report(result: dict) -> str:
    return "\n".join(
        [
            "# Capsule Validation",
            "",
            f"Release dir: `{result['release_dir']}`",
            f"Passed: {result['passed']}",
            f"Files: {result['n_files']}",
            f"Commands present: {result['commands_present']}",
            f"Path leaks: {len(result['path_leaks'])}",
            f"Pixel-risk files: {len(result['nonredistributable_pixel_risk_files'])}",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate a release capsule")
    parser.add_argument("--release-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = validate_capsule(args.release_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    write_json(str(Path(args.out).with_suffix(".json")), result)
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
