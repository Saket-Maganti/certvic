"""Audit the real-citation related-work task scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

REQUIRED_CATEGORIES = {
    "counterfactual_vqa_edited_image_vqa",
    "vlm_robustness_and_consistency",
    "image_editing_for_evaluation",
    "dataset_validity_construct_validity",
    "human_validation_in_vlm_eval",
    "confidence_sequences_anytime_valid_inference",
    "optional_stopping_in_ml_evaluation",
    "benchmark_reproducibility_and_open_models",
}


def audit_related_work(path: str = "paper/related_work_todo.yaml") -> dict:
    raw = Path(path)
    data = yaml.safe_load(raw.read_text(encoding="utf-8")) if raw.exists() else {}
    tasks = data.get("tasks", []) if isinstance(data, dict) else []
    categories = {str(row.get("category")) for row in tasks if isinstance(row, dict)}
    fake_keys = [row.get("citation_key") for row in tasks if isinstance(row, dict) and row.get("citation_key")]
    required_fields_missing = [
        row.get("category", "unknown")
        for row in tasks
        if isinstance(row, dict)
        and not all(row.get(key) for key in ("search_query", "why_it_matters", "section_destination", "required_citation_count", "risk_if_missing"))
    ]
    return {
        "audit": "related_work_tasks",
        "passed": REQUIRED_CATEGORIES.issubset(categories) and not fake_keys and not required_fields_missing,
        "missing_categories": sorted(REQUIRED_CATEGORIES - categories),
        "fake_citation_keys": fake_keys,
        "required_fields_missing": required_fields_missing,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit related-work search tasks")
    parser.add_argument("--path", default="paper/related_work_todo.yaml")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_related_work(args.path)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": args.out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
