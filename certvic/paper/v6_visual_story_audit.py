"""Audit V6 figure/table manifests for the new visual story."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

REQUIRED_FIGURE_SLOTS = {
    "detectability_vs_certified_gap",
    "qualitative_triptychs",
}
REQUIRED_TABLE_COLUMNS = {
    "n_valid",
    "naive_gap",
    "validity_gated_gap",
    "certified_lower_bound",
    "detectability_auc",
    "control_spurious_flip_rate",
    "parse_failure_rate",
    "human_iaa",
    "certificate_pass_rate",
}


def _load_yaml(path: str | Path) -> dict:
    raw = Path(path)
    if not raw.exists():
        return {}
    return yaml.safe_load(raw.read_text(encoding="utf-8")) or {}


def audit_manifests(figure_manifest: str = "paper/figure_manifest_v6.yaml", table_manifest: str = "paper/table_manifest_v6.yaml") -> dict:
    fig = _load_yaml(figure_manifest)
    table = _load_yaml(table_manifest)
    figure_slots = {str(row.get("id")) for row in fig.get("figures", []) if isinstance(row, dict)}
    table_columns: set[str] = set()
    for row in table.get("tables", []):
        if isinstance(row, dict):
            table_columns.update(str(col) for col in row.get("columns", []))
    source_missing = []
    for row in fig.get("figures", []) + table.get("tables", []):
        if isinstance(row, dict) and not row.get("source_artifacts"):
            source_missing.append(row.get("id"))
    checks = [
        {"name": "required_figure_slots", "passed": REQUIRED_FIGURE_SLOTS.issubset(figure_slots)},
        {"name": "required_table_columns", "passed": REQUIRED_TABLE_COLUMNS.issubset(table_columns)},
        {"name": "slots_map_to_source_artifacts", "passed": not source_missing, "missing": source_missing},
        {"name": "placeholders_result_required_only", "passed": "RESULT_REQUIRED" in json.dumps({**fig, **table})},
    ]
    return {"audit": "v6_visual_story", "passed": all(c["passed"] for c in checks), "checks": checks}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit V6 figure/table manifests")
    parser.add_argument("--figure-manifest", default="paper/figure_manifest_v6.yaml")
    parser.add_argument("--table-manifest", default="paper/table_manifest_v6.yaml")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_manifests(args.figure_manifest, args.table_manifest)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
