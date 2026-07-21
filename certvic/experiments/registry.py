"""Strict experiment registry and run naming."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

REQUIRED_STAGES = {"tiny_pilot", "main_200", "main_1000", "main_2000", "paper_figures"}
RUN_ID_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def load_registry(config: str) -> dict:
    return yaml.safe_load(Path(config).read_text(encoding="utf-8")) or {}


def validate_registry(config: str) -> dict:
    registry = load_registry(config)
    experiments = registry.get("experiments") or []
    ids = [str(row.get("run_id")) for row in experiments]
    errors: list[str] = []
    if len(ids) != len(set(ids)):
        errors.append("duplicate run IDs")
    invalid = [run_id for run_id in ids if not RUN_ID_RE.match(run_id)]
    if invalid:
        errors.append("invalid run IDs: " + ", ".join(invalid))
    missing = sorted(REQUIRED_STAGES - set(ids))
    if missing:
        errors.append("missing required stages: " + ", ".join(missing))
    return {"config": config, "n_experiments": len(experiments), "errors": errors, "passed": not errors}


def render_registry(config: str, out: str) -> dict:
    registry = load_registry(config)
    rows = registry.get("experiments") or []
    lines = ["# Experiment Registry", "", "| Run ID | Type | Evidence status |", "| --- | --- | --- |"]
    for row in rows:
        lines.append(f"| `{row['run_id']}` | {row.get('type')} | {row.get('evidence_status')} |")
    lines.append("")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(lines), encoding="utf-8")
    return {"out": out, "n_experiments": len(rows)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate/render experiment registry")
    sub = parser.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("validate")
    pv.add_argument("--config", required=True)
    pr = sub.add_parser("render")
    pr.add_argument("--config", required=True)
    pr.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "validate":
        print(json.dumps(validate_registry(args.config), sort_keys=True))
    else:
        print(json.dumps(render_registry(args.config, args.out), sort_keys=True))


if __name__ == "__main__":
    main()

