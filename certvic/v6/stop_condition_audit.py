"""Audit that V6 should stop generic infrastructure work and begin runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import write_json

REQUIRED_DOCS = (
    "docs/V6_STOP_BUILDING_BEGIN_RUNS.md",
    "docs/RUN_AFTER_V6_CHECKLIST.md",
    "docs/V6_FULL_PACK_REPORT.md",
)
ALLOWED_FUTURE_CODING = (
    "run crashes",
    "gate missing",
    "artifact contract mismatch",
    "edit generation fails",
    "detectability pipeline missing field",
    "vlm output parser fails",
)


def run_audit(repo_root: str | Path = ".") -> dict:
    root = Path(repo_root)
    missing = [path for path in REQUIRED_DOCS if not (root / path).exists()]
    stop_doc = (root / "docs/V6_STOP_BUILDING_BEGIN_RUNS.md")
    text = stop_doc.read_text(encoding="utf-8", errors="ignore").lower() if stop_doc.exists() else ""
    generic_more = ("build v7" in text and "do not build v7" not in text) or (
        "more generic infrastructure" in text and "disallowed" not in text
    )
    next_action_run = "ade20k dry-run" in text and "do not build v7" in text
    allowed_missing = [phrase for phrase in ALLOWED_FUTURE_CODING if phrase not in text]
    checks = [
        {"name": "required_stop_docs_exist", "passed": not missing, "missing": missing},
        {"name": "next_action_is_ade20k_dry_run", "passed": next_action_run},
        {"name": "generic_infrastructure_disallowed", "passed": not generic_more},
        {"name": "future_coding_exceptions_listed", "passed": not allowed_missing, "missing": allowed_missing},
    ]
    return {
        "audit": "v6_stop_condition",
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "guidance": "After V6, run the ADE20K dry-run; do not build V7.",
    }


def render_report(result: dict) -> str:
    lines = ["# V6 Stop Condition Audit", "", f"Passed: {result['passed']}", "", "| Check | Passed |", "| --- | --- |"]
    for check in result["checks"]:
        lines.append(f"| {check['name']} | {check['passed']} |")
    lines += ["", result["guidance"], ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit V6 stop condition")
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args(argv)
    result = run_audit()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    write_json(args.json_out, result)
    print(json.dumps({"out": args.out, "json_out": args.json_out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
