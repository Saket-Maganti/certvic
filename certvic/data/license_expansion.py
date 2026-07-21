"""Write V4 dataset-license expansion reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.data.license_matrix import dataset_license_matrix


def render_license_expansion() -> str:
    lines = [
        "# Dataset License Expansion",
        "",
        "This is a conservative planning report, not legal advice. No downloads occur.",
        "",
        "| Dataset | Primary | Release mode | Figure-safe | Recommendation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in dataset_license_matrix():
        lines.append(
            f"| {row['dataset']} | {row['primary']} | {row['default_release_mode']} | "
            f"{row['figure_safe']} | {row['recommendation']} |"
        )
    lines += [
        "",
        "Risk register:",
        "- Keep ADE20K pointer-only unless redistribution is explicitly verified.",
        "- Prefer CC0/public-domain showcase rows for paper figures.",
        "- Do not claim legal certainty from this matrix.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write dataset license expansion report")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_license_expansion(), encoding="utf-8")
    print(json.dumps({"out": args.out, "downloads_attempted": False}, sort_keys=True))


if __name__ == "__main__":
    main()

