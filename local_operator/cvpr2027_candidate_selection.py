"""Prospective candidate census and exact outcome-blind selection wrapper."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.cvpr.candidate_selection import balanced_select  # noqa: E402
from certvic.cvpr.contracts import load_yaml  # noqa: E402
from local_operator.cvpr2027_common import (  # noqa: E402
    REPO,
    REPORT_ROOT,
    artifact_manifest,
    read_jsonl,
    write_csv,
    write_json,
)


CONFIG = REPO / "configs/studies/specificity_confirmatory_cvpr.yaml"


def census(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cells: dict[tuple[str, str, str, str, str], int] = defaultdict(int)
    exclusions = Counter()
    for row in rows:
        category = str(row.get("category", "UNSPECIFIED"))
        endpoint = str(row.get("endpoint", row.get("endpoint_arm", "UNSPECIFIED")))
        polarity = str(row.get("expected_answer", "UNSPECIFIED"))
        size = str(row.get("target_size_stratum", "UNSPECIFIED"))
        position = str(row.get("target_position_stratum", "UNSPECIFIED"))
        cells[(category, endpoint, polarity, size, position)] += 1
        for reason in row.get("rejection_reasons", []):
            exclusions[str(reason)] += 1
    census_rows = [
        {
            "category": key[0],
            "endpoint": key[1],
            "answer_polarity": key[2],
            "size_stratum": key[3],
            "position_stratum": key[4],
            "eligible_count": count,
        }
        for key, count in sorted(cells.items())
    ]
    return census_rows, {
        "eligible_total": len(rows),
        "exclusion_losses": dict(sorted(exclusions.items())),
    }


def run(
    output_root: Path = REPORT_ROOT,
    *,
    source_manifest: Path | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    selection_root = output_root / "selection"
    configured = source_manifest or (
        Path(os.environ["CERTVIC_CONFIRMATORY_SOURCE_MANIFEST"])
        if os.environ.get("CERTVIC_CONFIRMATORY_SOURCE_MANIFEST")
        else None
    )
    if configured is None or not configured.is_file():
        census_rows = [
            {
                "category": "ALL",
                "endpoint": "ALL",
                "answer_polarity": "ALL",
                "size_stratum": "ALL",
                "position_stratum": "ALL",
                "eligible_count": 0,
                "status": "CONFIRMATORY_SOURCE_BYTES_MISSING",
            }
        ]
        feasibility = {
            "schema": "certvic.cvpr2027.confirmatory_feasibility.v1",
            "status": "CONFIRMATORY_SOURCE_BYTES_MISSING",
            "required": {
                "dataset": "ADE20K",
                "split": "validation",
                "source_manifest": "JSONL with licensed local image/annotation pointers",
                "license_eligible": True,
                "minimum_short_side": 384,
                "annotation_required": True,
            },
            "provider_outputs_used": False,
            "paper_evidence": False,
        }
        trace = {
            "schema": "certvic.cvpr2027.selection_trace.v1",
            "status": "NOT_STARTED_SOURCE_BYTES_MISSING",
            "sequence": [
                "source_eligible",
                "generation_qa",
                "blinded_review",
                "adjudication",
                "same_stratum_replacement",
                "final_primary_reserve",
            ],
            "selection_seed": 12013,
            "provider_output_fields_allowed": [],
            "provider_outputs_used": False,
            "paper_evidence": False,
        }
        output_paths = [
            write_csv(selection_root / "candidate_census.csv", census_rows),
            write_json(selection_root / "stratum_feasibility.json", feasibility),
            write_json(selection_root / "selection_trace.json", trace),
        ]
        return {
            "status": "BLOCKED_LICENSE",
            "runtime_seconds": time.perf_counter() - started,
            "verdict": feasibility["status"],
            "outputs": [path.relative_to(REPO).as_posix() for path in output_paths],
        }
    rows = read_jsonl(configured)
    forbidden = {
        "provider",
        "provider_name",
        "raw_output",
        "parsed_answer",
        "model_output",
        "flip",
        "semantic_update_success",
    }
    contaminated = [
        str(row.get("item_id", index))
        for index, row in enumerate(rows)
        if forbidden & set(row)
    ]
    if contaminated:
        raise ValueError(f"candidate manifest contains provider outcomes: {contaminated[:5]}")
    census_rows, census_summary = census(rows)
    config = load_yaml(CONFIG)
    selection = balanced_select(rows, config, seed=int(config["seed"]))
    feasible = selection["status"] == "BALANCED_SELECTION_COMPLETE"
    feasibility = {
        "schema": "certvic.cvpr2027.confirmatory_feasibility.v1",
        "status": (
            "CONFIRMATORY_DESIGN_FEASIBLE"
            if feasible
            else "CONFIRMATORY_DESIGN_INFEASIBLE"
        ),
        **census_summary,
        "primary_selected": len(selection["primary"]),
        "reserve_selected": len(selection["reserve"]),
        "shortages": selection["shortage"],
        "provider_outputs_used": False,
        "paper_evidence": False,
    }
    trace = {
        "schema": "certvic.cvpr2027.selection_trace.v1",
        "status": selection["status"],
        "selection_sha256": selection["selection_sha256"],
        "seed": selection["seed"],
        "balance": selection["balance"],
        "solution_report": selection["solution_report"],
        "primary_item_ids": [row["item_id"] for row in selection["primary"]],
        "reserve_item_ids": [row["item_id"] for row in selection["reserve"]],
        "provider_outputs_used": False,
        "paper_evidence": False,
    }
    output_paths = [
        write_csv(selection_root / "candidate_census.csv", census_rows),
        write_json(selection_root / "stratum_feasibility.json", feasibility),
        write_json(selection_root / "selection_trace.json", trace),
    ]
    output_paths.append(
        write_json(selection_root / "SELECTION_ARTIFACT_MANIFEST.json", artifact_manifest(output_paths))
    )
    return {
        "status": "COMPLETE" if feasible else "FAILED_LOCAL_REPAIR_REQUIRED",
        "runtime_seconds": time.perf_counter() - started,
        "verdict": feasibility["status"],
        "outputs": [path.relative_to(REPO).as_posix() for path in output_paths],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPORT_ROOT)
    parser.add_argument("--source-manifest", type=Path)
    args = parser.parse_args(argv)
    result = run(args.output_root, source_manifest=args.source_manifest)
    print(json.dumps(result, sort_keys=True))
    return 2 if result["status"] == "FAILED_LOCAL_REPAIR_REQUIRED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
