"""Audit paper table contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

REQUIRED_KEYS = {"id", "source_artifact", "latex_path", "claim_status"}


def audit_table_manifest(manifest: str) -> dict:
    data = yaml.safe_load(Path(manifest).read_text(encoding="utf-8")) or {}
    tables = data.get("tables") or []
    missing_fields = [row.get("id", "<unknown>") for row in tables if not REQUIRED_KEYS <= set(row)]
    fake_numbers = any(str(row.get("claim_status", "")).lower() == "fake" for row in tables)
    missing_latex = [row.get("id") for row in tables if not row.get("latex_path")]
    return {
        "manifest": manifest,
        "n_tables": len(tables),
        "missing_fields": missing_fields,
        "missing_latex": missing_latex,
        "fake_numbers": fake_numbers,
        "descriptive_vs_certified_noted": all(row.get("claim_status") for row in tables),
        "passed": not missing_fields and not missing_latex and not fake_numbers,
    }


def render_report(result: dict) -> str:
    return "\n".join(
        [
            "# Table Manifest Audit",
            "",
            f"Passed: {result['passed']}",
            f"Tables: {result['n_tables']}",
            f"Missing fields: {result['missing_fields']}",
            f"Missing LaTeX paths: {result['missing_latex']}",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit table manifest")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_table_manifest(args.manifest)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
