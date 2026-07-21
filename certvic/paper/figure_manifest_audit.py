"""Audit paper figure placeholders and contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

REQUIRED_KEYS = {"id", "path", "generator", "source_artifact", "claim_status"}


def audit_figure_manifest(manifest: str, paper_dir: str) -> dict:
    data = yaml.safe_load(Path(manifest).read_text(encoding="utf-8")) or {}
    figures = data.get("figures") or []
    missing = [
        row.get("id", "<unknown>")
        for row in figures
        if not REQUIRED_KEYS <= set(row)
    ]
    ids = {row.get("id") for row in figures}
    required = {
        "pipeline_overview",
        "edit_examples",
        "cs_trajectory",
        "main_result_gap",
        "control_spurious_flip",
        "ablation_summary",
        "failure_gallery",
        "artifact_release_diagram",
    }
    return {
        "manifest": manifest,
        "paper_dir": paper_dir,
        "n_figures": len(figures),
        "missing_fields": missing,
        "missing_slots": sorted(required - ids),
        "passed": not missing and not (required - ids),
    }


def render_report(result: dict) -> str:
    return "\n".join(
        [
            "# Figure Manifest Audit",
            "",
            f"Passed: {result['passed']}",
            f"Figures: {result['n_figures']}",
            f"Missing fields: {result['missing_fields']}",
            f"Missing slots: {result['missing_slots']}",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit figure manifest")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--paper-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_figure_manifest(args.manifest, args.paper_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()

