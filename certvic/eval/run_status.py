"""Model run matrix status tracker (V3 prompt 08).

Reads a run matrix and the predictions root and reports which run cells have
completed predictions, which are missing, and the resume commands for the
missing ones. No inference, no downloads.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from certvic.io import ensure_parent, read_json


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def run_status(matrix_path: str, pred_root: str) -> dict:
    matrix = read_json(matrix_path)
    cells = matrix.get("cells", [])

    results: list[dict] = []
    per_provider: dict[str, dict] = defaultdict(lambda: {"completed": 0, "missing": 0, "total": 0})
    for cell in cells:
        # The matrix stores absolute-ish relative output paths; re-root onto pred_root
        # by taking the path as-is (it already encodes the predictions root).
        out_path = Path(cell["expected_output_path"])
        n_pred = _count_lines(out_path)
        sidecars_present = {s: Path(s).exists() for s in cell.get("expected_sidecars", [])}
        completed = n_pred > 0 and all(sidecars_present.values()) if sidecars_present else n_pred > 0
        status = "completed" if completed else "missing"
        per_provider[cell["provider"]]["total"] += 1
        per_provider[cell["provider"]][status] += 1
        results.append({
            "run_id": cell["run_id"],
            "provider": cell["provider"],
            "shard_index": cell["shard_index"],
            "status": status,
            "n_predictions": n_pred,
            "sidecars_present": sidecars_present,
            "output_path": str(out_path),
            "resume_command": cell.get("command") if status == "missing" else None,
        })

    n_completed = sum(1 for r in results if r["status"] == "completed")
    return {
        "status": "model_run_matrix_status",
        "matrix_path": matrix_path,
        "pred_root": pred_root,
        "n_cells": len(results),
        "n_completed": n_completed,
        "n_missing": len(results) - n_completed,
        "completion_fraction": round(n_completed / len(results), 4) if results else 0.0,
        "per_provider": {k: dict(v) for k, v in sorted(per_provider.items())},
        "cells": results,
        "all_complete": bool(results) and n_completed == len(results),
        "resume_commands": [r["resume_command"] for r in results if r["resume_command"]],
        "evidence_claims_made": False,
    }


def render_report(result: dict) -> str:
    lines = [
        "# Model Run Matrix Status",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Matrix: `{result['matrix_path']}`  |  predictions root: `{result['pred_root']}`",
        f"Completed: {result['n_completed']}/{result['n_cells']} "
        f"({result['completion_fraction'] * 100:.1f}%)  |  all complete: {result['all_complete']}",
        "",
        "| Provider | Completed | Missing | Total |",
        "| --- | --- | --- | --- |",
    ]
    for p, s in result["per_provider"].items():
        lines.append(f"| `{p}` | {s['completed']} | {s['missing']} | {s['total']} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC model run matrix status")
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--pred-root", default="data/predictions")
    parser.add_argument("--out", required=True)
    parser.add_argument("--report-out")
    args = parser.parse_args(argv)
    result = run_status(args.matrix, args.pred_root)
    ensure_parent(args.out)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    if args.report_out:
        ensure_parent(args.report_out)
        Path(args.report_out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({
        "n_completed": result["n_completed"],
        "n_missing": result["n_missing"],
        "completion_fraction": result["completion_fraction"],
        "all_complete": result["all_complete"],
        "out": args.out,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
