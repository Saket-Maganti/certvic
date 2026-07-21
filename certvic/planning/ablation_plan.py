"""Plan realistic ablations under free-compute constraints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_ablation_plan(scale: int, models: list[str]) -> dict:
    required = [
        "main_prompt",
        "text_only_baseline",
        "caption_only_baseline",
        "parse_failure_sensitivity",
    ]
    optional = ["prompt_variant", "edit_type_breakdown", "cluster_sensitivity"]
    gpu_hours = round(scale * max(1, len(models)) * 0.015, 2)
    return {
        "scale": scale,
        "models": models,
        "required_ablations": required,
        "optional_ablations": optional,
        "estimated_gpu_hours": gpu_hours,
        "free_compute_budget_respected": gpu_hours <= 100,
        "fallback_plan": ["drop optional ablations", "reduce scale", "run one model first"],
        "paper_table_mapping": {
            "main_results": "required",
            "ablation_table": "required + optional when compute allows",
        },
        "evidence_status": "ABLATION_PLAN_ONLY",
    }


def render_ablation_plan(plan: dict) -> str:
    lines = [
        "# Ablation Plan",
        "",
        f"Scale: {plan['scale']}",
        f"Models: {', '.join(plan['models'])}",
        f"Estimated GPU hours: {plan['estimated_gpu_hours']}",
        f"Free-compute budget respected: {plan['free_compute_budget_respected']}",
        "",
        "Required ablations:",
        *[f"- {item}" for item in plan["required_ablations"]],
        "",
        "Optional ablations:",
        *[f"- {item}" for item in plan["optional_ablations"]],
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Plan paper ablations")
    parser.add_argument("--scale", type=int, required=True)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    plan = build_ablation_plan(args.scale, args.models)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_ablation_plan(plan), encoding="utf-8")
    print(json.dumps({"out": args.out, "estimated_gpu_hours": plan["estimated_gpu_hours"]}, sort_keys=True))


if __name__ == "__main__":
    main()

