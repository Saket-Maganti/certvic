"""Minimum viable CVPR bar checker for the empirical package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from certvic.io import read_json, write_json


def _load_yaml(path: str | Path) -> dict[str, Any]:
    raw = Path(path)
    if not raw.exists():
        return {}
    return yaml.safe_load(raw.read_text(encoding="utf-8")) or {}


def _load_metrics(results_root: str | Path) -> dict[str, Any]:
    root = Path(results_root)
    for rel in (
        "cvpr_bar_metrics.json",
        "tiny_pilot_decision.json",
        "v6_final_directional_audit.json",
        "tiny_real_pilot/cvpr_bar_metrics.json",
    ):
        path = root / rel
        if path.exists():
            data = read_json(path)
            return data if isinstance(data, dict) else {}
    return {}


def _meets(metrics: dict, thresholds: dict) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    for key, minimum in thresholds.get("minimums", {}).items():
        if metrics.get(key) is None or float(metrics.get(key) or 0) < float(minimum):
            blockers.append(f"{key}_below_{minimum}")
    for key, maximum in thresholds.get("maximums", {}).items():
        if metrics.get(key) is None or float(metrics.get(key) or 1e9) > float(maximum):
            blockers.append(f"{key}_above_{maximum}")
    for key in thresholds.get("required_true", []):
        if bool(metrics.get(key)) is not True:
            blockers.append(f"{key}_missing_or_false")
    return not blockers, blockers


def check_bar(results_root: str, thresholds_path: str = "configs/cvpr_bar_thresholds.yaml") -> dict:
    cfg = _load_yaml(thresholds_path)
    metrics = _load_metrics(results_root)
    bars = cfg.get("bars", {}) if isinstance(cfg.get("bars"), dict) else {}
    ordered = ["borderline", "weak_accept", "strong_accept", "highlight_possible"]
    decisions: dict[str, dict] = {}
    highest = "none"
    for bar in ordered:
        ok, blockers = _meets(metrics, bars.get(bar, {}))
        decisions[bar] = {"passed": ok, "blockers": blockers}
        if ok:
            highest = bar
    no_data = not metrics
    if no_data:
        decisions["borderline"] = {"passed": False, "blockers": ["no_empirical_metrics_found"]}
        highest = "none"
    missing_detectability = metrics.get("detectability_auc") is None
    if missing_detectability:
        for decision in decisions.values():
            decision.setdefault("blockers", []).append("missing_detectability_auc")
            decision["passed"] = False
        highest = "none"
    return {
        "checker": "cvpr_bar",
        "results_root": results_root,
        "metrics": metrics,
        "decisions": decisions,
        "highest_bar": highest,
        "passed": highest != "none",
        "claim_status": "BAR_CHECK_ONLY_NO_ACCEPTANCE_CLAIM",
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# CVPR Bar Check",
        "",
        f"Highest bar: {result['highest_bar']}",
        f"Passed any bar: {result['passed']}",
        "",
        "| Bar | Passed | Blockers |",
        "| --- | --- | --- |",
    ]
    for bar, decision in result["decisions"].items():
        blockers = ", ".join(sorted(set(decision.get("blockers", [])))) or "none"
        lines.append(f"| {bar} | {decision['passed']} | {blockers} |")
    lines.append("")
    return "\n".join(lines)


def write_check(results_root: str, out: str, json_out: str, thresholds_path: str = "configs/cvpr_bar_thresholds.yaml") -> dict:
    result = check_bar(results_root, thresholds_path)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(render_markdown(result), encoding="utf-8")
    write_json(json_out, result)
    return {"out": out, "json_out": json_out, "highest_bar": result["highest_bar"], "passed": result["passed"]}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Check minimum viable CVPR empirical bar")
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--thresholds", default="configs/cvpr_bar_thresholds.yaml")
    args = parser.parse_args(argv)
    print(json.dumps(write_check(args.results_root, args.out, args.json_out, args.thresholds), sort_keys=True))


if __name__ == "__main__":
    main()
