"""CVPR submission checklist writer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ITEMS = [
    "Real ADE20K/local-data run complete",
    "Human review and IAA/adjudication complete",
    "Open-local VLM predictions scored",
    "Result lockfile created before paper injection",
    "Privacy/security audit clean",
    "Supplement and artifact capsule validated",
]


def render_checklist() -> str:
    return "\n".join(["# CVPR Submission Checklist", "", *[f"- [ ] {item}" for item in ITEMS], ""])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Write CVPR submission checklist")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_checklist(), encoding="utf-8")
    print(json.dumps({"out": args.out, "n_items": len(ITEMS), "fabricated_completion": False}, sort_keys=True))


if __name__ == "__main__":
    main()

