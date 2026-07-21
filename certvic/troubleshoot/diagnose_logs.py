"""Diagnose logs offline using a static catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.troubleshoot.error_catalog import ERROR_CATALOG

DESTRUCTIVE_MARKERS = ("rm -rf", "git reset --hard", "delete all")


def diagnose_log(log: str) -> dict:
    text = Path(log).read_text(encoding="utf-8", errors="ignore") if Path(log).exists() else log
    matches = [entry for entry in ERROR_CATALOG if entry["pattern"].lower() in text.lower()]
    if not matches:
        matches = [
            {
                "pattern": "<unknown>",
                "diagnosis": text[:300],
                "playbook": "collect the failing command, inspect outputs, and run relevant dry-run audit",
                "next_command": "python3 -m certvic.recovery.inspect_run --run-dir data/results/<run> --out data/results/recovery_report.json",
            }
        ]
    for match in matches:
        if any(marker in match["next_command"] for marker in DESTRUCTIVE_MARKERS):
            raise ValueError("destructive advice is forbidden")
    return {"log": log, "matches": matches, "external_llm_used": False, "destructive_advice": False}


def render_diagnosis(result: dict) -> str:
    lines = ["# Troubleshooting Diagnosis", "", "Offline static diagnosis; no external LLM used.", ""]
    for match in result["matches"]:
        lines += [
            f"## {match['diagnosis']}",
            "",
            f"Matched pattern: `{match['pattern']}`",
            f"Playbook: {match['playbook']}",
            f"Next command: `{match['next_command']}`",
            "",
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Diagnose run logs offline")
    parser.add_argument("--log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = diagnose_log(args.log)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_diagnosis(result), encoding="utf-8")
    print(json.dumps({"out": args.out, "matches": len(result["matches"])}, sort_keys=True))


if __name__ == "__main__":
    main()

