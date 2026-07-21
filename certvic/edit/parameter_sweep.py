"""Plan edit-engine parameter sweeps without running generation."""

from __future__ import annotations

import argparse
import json
from itertools import product

from certvic.io import read_jsonl, write_json, write_jsonl

DEFAULT_GRID = {
    "diffusers_inpaint_optional": {
        "guidance_scale": [5.0, 7.5],
        "strength": [0.55, 0.75],
        "num_inference_steps": [25, 40],
    },
    "simple_fill": {"fill_strategy": ["median", "edge"], "dilate_px": [0, 3]},
}
EVIDENCE_STATUS = "SWEEP_PLANNED_ONLY"


def build_sweep_plan(edit_plan: str, out: str, *, max_combinations: int = 20) -> dict:
    if max_combinations <= 0:
        raise ValueError("max_combinations must be positive")
    edits = read_jsonl(edit_plan)
    rows: list[dict] = []
    for engine, grid in sorted(DEFAULT_GRID.items()):
        keys = sorted(grid)
        for values in product(*(grid[key] for key in keys)):
            params = dict(zip(keys, values))
            for edit in edits[: max(1, min(3, len(edits)))]:
                rows.append(
                    {
                        "sweep_id": f"{engine}_{len(rows):04d}",
                        "engine": engine,
                        "edit_id": edit.get("edit_id"),
                        "edit_type": edit.get("edit_type"),
                        "params": params,
                        "estimated_runtime_seconds": 45 if "diffusers" in engine else 1,
                        "risk_notes": ["planned_only", "inspect visual quality before scaling"],
                        "evidence_status": EVIDENCE_STATUS,
                    }
                )
                if len(rows) >= max_combinations:
                    break
            if len(rows) >= max_combinations:
                break
        if len(rows) >= max_combinations:
            break
    write_jsonl(out, rows)
    summary = {
        "edit_plan": edit_plan,
        "out": out,
        "n_combinations": len(rows),
        "max_combinations": max_combinations,
        "estimated_runtime_seconds": sum(r["estimated_runtime_seconds"] for r in rows),
        "executed": False,
        "evidence_status": EVIDENCE_STATUS,
    }
    write_json(out.replace(".jsonl", "_summary.json"), summary)
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Plan edit parameter sweeps")
    parser.add_argument("--edit-plan", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-combinations", type=int, default=20)
    args = parser.parse_args(argv)
    print(json.dumps(build_sweep_plan(args.edit_plan, args.out, max_combinations=args.max_combinations), sort_keys=True))


if __name__ == "__main__":
    main()

