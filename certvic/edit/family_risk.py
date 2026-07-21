"""Edit-family risk matrix before scaling."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from certvic.io import read_json, read_jsonl

RISK_DIMENSIONS = (
    "detectability",
    "photorealism",
    "answerability",
    "single_factor_validity",
    "ade20k_label_ambiguity",
    "expected_vlm_sensitivity",
    "free_gpu_feasibility",
)


def _family(row: dict) -> str:
    return str(row.get("edit_family") or row.get("edit_type") or (row.get("edit") or {}).get("edit_type") or "unknown")


def _load_json(path: str | None) -> dict[str, Any]:
    if not path or not Path(path).exists():
        return {}
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def build_risk_matrix(edit_manifest: str, detectability: str | None = None, review: str | None = None) -> dict:
    rows = read_jsonl(edit_manifest)
    det = _load_json(detectability)
    review_summary = _load_json(review)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[_family(row)].append(row)

    families: list[dict] = []
    per_family_auc = det.get("per_family_auc") if isinstance(det.get("per_family_auc"), dict) else {}
    per_family_review = review_summary.get("by_family") if isinstance(review_summary.get("by_family"), dict) else {}
    global_auc = det.get("auc") or (det.get("classifier") or {}).get("auc")
    for family, items in sorted(grouped.items()):
        auc = per_family_auc.get(family, global_auc)
        review_row = per_family_review.get(family, {}) if isinstance(per_family_review, dict) else {}
        pass_rate = review_row.get("pass_rate") or review_row.get("visual_pass_rate")
        risks = {dimension: "unknown" for dimension in RISK_DIMENSIONS}
        if auc is not None:
            risks["detectability"] = "high" if float(auc) > 0.70 else "medium" if float(auc) > 0.60 else "low"
        if pass_rate is not None:
            value = float(pass_rate)
            risks["photorealism"] = "high" if value < 0.70 else "medium" if value < 0.90 else "low"
            risks["single_factor_validity"] = risks["photorealism"]
            risks["answerability"] = risks["photorealism"]
        if family in {"remove", "occlude", "displace"}:
            risks["expected_vlm_sensitivity"] = "medium"
            risks["free_gpu_feasibility"] = "medium"
        if family == "control_irrelevant":
            risks["expected_vlm_sensitivity"] = "low"
            risks["free_gpu_feasibility"] = "low"
        families.append(
            {
                "edit_family": family,
                "n_items": len(items),
                "detectability_auc": auc,
                "review_pass_rate": pass_rate,
                "risks": risks,
                "scale_recommendation": "hold" if any(v == "high" for v in risks.values()) else "pilot_only",
            }
        )
    return {
        "matrix": "edit_family_risk",
        "families": families,
        "missing_data_is_unknown_not_pass": True,
        "evidence_status": "RISK_MATRIX_ONLY_NON_EVIDENCE",
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# Edit Family Risk Matrix",
        "",
        "Missing data is treated as unknown, not pass.",
        "",
        "| Family | n | Detectability AUC | Review pass | Recommendation |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in result["families"]:
        lines.append(
            f"| {row['edit_family']} | {row['n_items']} | {row['detectability_auc']} | {row['review_pass_rate']} | {row['scale_recommendation']} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_matrix(edit_manifest: str, detectability: str | None, review: str | None, out: str) -> dict:
    result = build_risk_matrix(edit_manifest, detectability, review)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(render_markdown(result), encoding="utf-8")
    json_path = Path(out).with_suffix(".json")
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"out": out, "json_out": str(json_path), "n_families": len(result["families"])}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build edit-family risk matrix")
    parser.add_argument("--edit-manifest", required=True)
    parser.add_argument("--detectability")
    parser.add_argument("--review")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_matrix(args.edit_manifest, args.detectability, args.review, args.out), sort_keys=True))


if __name__ == "__main__":
    main()
