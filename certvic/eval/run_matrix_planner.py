"""Model run matrix planner CLI (V3 prompt 08).

Builds the provider × prompt × shard run matrix and writes `run_matrix.json`,
`commands.sh`, and a markdown report. No inference, no downloads, no paid
providers.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from certvic.eval.model_matrix import DEFAULT_CONFIG, DEFAULT_PRED_ROOT, build_matrix, commands_sh


def render_report(matrix: dict) -> str:
    lines = [
        "# Model Run Matrix",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Tasks: `{matrix['tasks_path']}`  |  config: `{matrix['config']}`",
        f"Cells: {matrix['n_cells']} ({len(matrix['providers'])} providers × "
        f"{len(matrix['prompt_variants'])} prompt variants × {matrix['num_shards']} shards)",
        f"Max items per shard run: {matrix['max_items']}",
        "",
        "No inference is run here. Commands resume from existing predictions + run manifest.",
        "",
        "## Providers",
        "",
        "| Provider | Type | Cost | Evidence-eligible | GPU (full) | GPU (4-bit) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for p, s in matrix["provider_summaries"].items():
        m = s["memory_estimate"]
        lines.append(
            f"| `{p}` | {s['provider_type']} | {s['cost_status']} | {s['evidence_eligible']} | "
            f"{m['expected_gpu_memory_gb']} GB | {m['expected_gpu_memory_gb_4bit']} GB |"
        )
    lines += [
        "",
        "## Run cells",
        "",
        "| Run ID | Provider | Variant | Shard | Output |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c in matrix["cells"]:
        lines.append(f"| `{c['run_id']}` | {c['provider']} | {c['prompt_variant']} | {c['shard_index']}/{c['num_shards']} | `{c['expected_output_path']}` |")
    lines.append("")
    return "\n".join(lines)


def write_matrix(matrix: dict, out_dir: str) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "run_matrix": str(out / "run_matrix.json"),
        "commands": str(out / "commands.sh"),
        "report": str(out / "model_run_matrix_report.md"),
    }
    Path(paths["run_matrix"]).write_text(json.dumps(matrix, indent=2, sort_keys=True), encoding="utf-8")
    Path(paths["commands"]).write_text(commands_sh(matrix), encoding="utf-8")
    Path(paths["report"]).write_text(render_report(matrix), encoding="utf-8")
    return paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC model run matrix planner")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--providers", nargs="+", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--pred-root", default=DEFAULT_PRED_ROOT)
    parser.add_argument("--max-items", type=int, default=200)
    parser.add_argument("--num-shards", type=int, default=4)
    parser.add_argument("--prompt-variants", nargs="*", default=None)
    args = parser.parse_args(argv)
    matrix = build_matrix(
        args.tasks,
        args.providers,
        max_items=args.max_items,
        num_shards=args.num_shards,
        prompt_variants=args.prompt_variants,
        config=args.config,
        pred_root=args.pred_root,
    )
    paths = write_matrix(matrix, args.out_dir)
    print(json.dumps({
        "n_cells": matrix["n_cells"],
        "providers": matrix["providers"],
        "any_evidence_eligible": matrix["any_evidence_eligible"],
        **paths,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
