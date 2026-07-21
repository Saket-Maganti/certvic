"""Write and verify preregistration analysis-plan locks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from certvic.analysis.preregistration import default_analysis_plan, validate_analysis_plan
from certvic.hashing import stable_record_hash
from certvic.io import write_json


def build_analysis_plan_lock(config: str, out: str, json_out: str) -> dict:
    policy = yaml.safe_load(Path(config).read_text(encoding="utf-8")) or {}
    plan = default_analysis_plan(policy)
    plan_hash = stable_record_hash(plan)
    result = {
        "analysis_plan": plan,
        "analysis_plan_hash": plan_hash,
        "validation_errors": validate_analysis_plan(plan),
        "config": config,
    }
    result["passed"] = not result["validation_errors"]
    write_json(json_out, result)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(render_analysis_plan_lock(result), encoding="utf-8")
    return result


def render_analysis_plan_lock(result: dict) -> str:
    plan = result["analysis_plan"]
    lines = [
        "# Analysis Plan Lock",
        "",
        f"Passed: {result['passed']}",
        f"Hash: `{result['analysis_plan_hash']}`",
        "",
        f"- Primary estimand: `{plan['primary_estimand']}`",
        f"- Primary population: {plan['primary_population']}",
        f"- Primary model set: {', '.join(plan['primary_model_set'])}",
        f"- Alpha: {plan['alpha']}",
        f"- Gap threshold: {plan['gap_threshold']}",
        f"- Parse failure threshold: {plan['parse_failure_threshold']}",
        f"- Control spurious flip threshold: {plan['control_spurious_flip_threshold']}",
        f"- Frozen before results: {plan['frozen_before_results']}",
        "",
        "Exploratory analyses remain descriptive unless promoted by a predeclared correction.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build analysis-plan lock")
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args(argv)
    result = build_analysis_plan_lock(args.config, args.out, args.json_out)
    print(json.dumps({"out": args.out, "json_out": args.json_out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()

