"""Main-study dry-run orchestrator (V3 prompt 18).

Plans the full 200/1k/2k study WITHOUT executing any GPU/VLM jobs. Emits
stage_plan.json, commands.sh, required_inputs.md, expected_outputs.md,
gate_sequence.md, runtime_estimates.md, and report.md. No execution.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from certvic.pipeline.main_study_plan import build_main_study_plan


def _commands_sh(plan: dict) -> str:
    lines = ["#!/usr/bin/env bash", "set -euo pipefail",
             f"# CertVIC main study plan (scale {plan['scale']}). DRY-RUN PLAN -- review before running.",
             "# Set ADE20K_ROOT and weights dirs first; gates must pass between stages.", ""]
    gate_cmd = {g["gate"]: g["command"] for g in plan["gate_sequence"]}
    lines.append("# Pre-run audit")
    lines.append(gate_cmd.get("pre_run_master_audit", ""))
    lines.append("")
    for s in plan["stages"]:
        lines.append(f"# [{s['id']}] {s['name']}{'  (GPU)' if s['gpu'] else ''}")
        lines.append(s["command"])
        if s.get("gate_after"):
            lines.append(f"# GATE: {s['gate_after']}")
            lines.append(gate_cmd.get(s["gate_after"], ""))
        lines.append("")
    lines.append("# Final audits")
    lines.append(gate_cmd.get("security_privacy_audit", ""))
    lines.append(gate_cmd.get("final_pre_real_run_audit", ""))
    lines.append("")
    return "\n".join(lines)


def _md_list(title: str, items: list[str], note: str = "") -> str:
    lines = [f"# {title}", ""]
    if note:
        lines += [note, ""]
    lines += [f"- `{i}`" for i in items]
    lines.append("")
    return "\n".join(lines)


def _gate_md(plan: dict) -> str:
    lines = ["# Gate Sequence", "", "Gates must pass in order; cross-cutting audits bracket the study.", "",
             "| Gate | Checks | Command |", "| --- | --- | --- |"]
    for g in plan["gate_sequence"]:
        lines.append(f"| `{g['gate']}` | {g['checks']} | `{g['command']}` |")
    lines.append("")
    return "\n".join(lines)


def _runtime_md(plan: dict) -> str:
    r = plan["runtime_estimate"]
    return "\n".join([
        f"# Runtime Estimates — scale {plan['scale']}", "",
        "Conservative; from `certvic.planning.scale_planner`. No execution.", "",
        f"- Total GPU hours: {r['total_gpu_hours']}",
        f"- Wall-clock weeks under free GPU quota: {r['wall_clock_weeks_under_quota']}",
        f"- Human review hours: {r['human_hours']}",
        f"- Working storage: {r['storage_gb']} GB",
        f"- Bottleneck: {r['bottleneck']}",
        f"- GPU stages: {plan['n_gpu_stages']} of {plan['n_stages']}",
        "",
    ])


def _report_md(plan: dict) -> str:
    lines = [
        f"# Main Study Dry Run — scale {plan['scale']}", "",
        f"Generated: {date.today().isoformat()}", "",
        f"Stages: {plan['n_stages']} ({plan['n_gpu_stages']} GPU)  |  bottleneck: {plan['runtime_estimate']['bottleneck']}", "",
        "**No GPU/VLM jobs executed. This is a plan only.**", "",
        "## Stages", "",
        "| # | Stage | GPU | Evidence status | Gate after |", "| --- | --- | --- | --- | --- |",
    ]
    for i, s in enumerate(plan["stages"], 1):
        lines.append(f"| {i} | {s['name']} | {'yes' if s['gpu'] else 'no'} | {s['evidence_status']} | {s.get('gate_after', '')} |")
    lines += ["", "See stage_plan.json, commands.sh, gate_sequence.md, runtime_estimates.md,",
              "required_inputs.md, and expected_outputs.md in this directory.", ""]
    return "\n".join(lines)


def write_dry_run(scale: int, out_dir: str) -> dict:
    plan = build_main_study_plan(scale)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "stage_plan.json": json.dumps(plan, indent=2, sort_keys=True),
        "commands.sh": _commands_sh(plan),
        "required_inputs.md": _md_list("Required Inputs (user-provided)", plan["required_inputs"],
                                       "Provide these before running; pixels/weights are never rehosted."),
        "expected_outputs.md": _md_list("Expected Outputs", plan["expected_outputs"]),
        "gate_sequence.md": _gate_md(plan),
        "runtime_estimates.md": _runtime_md(plan),
        "report.md": _report_md(plan),
    }
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")
    plan["out_dir"] = str(out)
    plan["files"] = sorted(files)
    return plan


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC main study dry-run planner (no execution)")
    parser.add_argument("--scale", type=int, required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    plan = write_dry_run(args.scale, args.out_dir)
    print(json.dumps({
        "scale": plan["scale"],
        "n_stages": plan["n_stages"],
        "n_gpu_stages": plan["n_gpu_stages"],
        "bottleneck": plan["runtime_estimate"]["bottleneck"],
        "executed": plan["executed"],
        "out_dir": plan["out_dir"],
        "files": plan["files"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
