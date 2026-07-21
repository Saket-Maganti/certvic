"""Plan the final conference submission package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import write_json

COMPONENTS = (
    "main paper",
    "supplement",
    "figures",
    "tables",
    "checklist",
    "artifact README",
    "data card",
    "model/eval cards",
    "claim ledger",
    "reproduction docs",
    "release package",
    "anonymization checklist",
)


def build_package_plan(paper_dir: str, out_dir: str) -> dict:
    result_placeholder = "[RESULT REQUIRED]" in (Path(paper_dir) / "sections/05_results.tex").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    plan = {
        "paper_dir": paper_dir,
        "components": list(COMPONENTS),
        "missing_result_placeholders": result_placeholder,
        "anonymization_reminders": [
            "strip private paths",
            "strip prompts/chat logs",
            "keep nonredistributable pixels pointer-only",
        ],
    }
    write_json(out / "submission_package_plan.json", plan)
    (out / "index.md").write_text(
        "# CVPR Submission Package Plan\n\n"
        + "\n".join(f"- {component}" for component in COMPONENTS)
        + "\n",
        encoding="utf-8",
    )
    Path("docs/CVPR_SUBMISSION_PACKAGE_PLAN.md").write_text((out / "index.md").read_text(encoding="utf-8"), encoding="utf-8")
    return plan


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build CVPR submission package plan")
    parser.add_argument("--paper-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    plan = build_package_plan(args.paper_dir, args.out_dir)
    print(json.dumps({"out_dir": args.out_dir, "components": len(plan["components"])}, sort_keys=True))


if __name__ == "__main__":
    main()

