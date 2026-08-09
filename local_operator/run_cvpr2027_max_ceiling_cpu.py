"""Run every currently safe C11 CPU stage with resumable fail-closed checkpoints."""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator import (  # noqa: E402
    cvpr2027_candidate_selection,
    cvpr2027_image_audit,
    cvpr2027_infrastructure,
    cvpr2027_leakage_audit,
    cvpr2027_pilot_analysis,
    cvpr2027_statistics,
    human_review_status,
)
from local_operator.cvpr2027_common import REPORT_ROOT, REPO, write_json  # noqa: E402


Stage = tuple[str, Callable[[], dict[str, Any]]]
TERMINAL = {
    "COMPLETE",
    "SKIPPED_INPUT_NOT_AVAILABLE",
    "BLOCKED_HUMAN",
    "BLOCKED_GPU",
    "BLOCKED_LICENSE",
}


def _peak_ram_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def _candidate(output_root: Path) -> dict[str, Any]:
    result = cvpr2027_candidate_selection.run(output_root)
    if result["status"] == "BLOCKED_LICENSE":
        return result
    return result


def _human(output_root: Path) -> dict[str, Any]:
    human_review_status.initialize_infrastructure(output_root / "human_review")
    result = human_review_status.status(
        REPO / "data/studies/specificity_confirmatory_cvpr/review"
    )
    write_json(output_root / "human_review/STATUS.json", result)
    if result["state"] in {"COMPLETE", "ADJUDICATION_COMPLETE"}:
        return {"status": "COMPLETE", "state": result["state"], "outputs": ["human_review/STATUS.json"]}
    if result["state"] == "INVALID_REVIEW_STATE":
        return {"status": "FAILED_LOCAL_REPAIR_REQUIRED", "state": result["state"], "errors": result["errors"]}
    return {
        "status": "BLOCKED_HUMAN",
        "state": result["state"],
        "blocking_reason": result["external_action"],
        "outputs": ["human_review/STATUS.json"],
    }


def _input_item_count(name: str, result: dict[str, Any]) -> int:
    if name == "statistics_and_confidence_sequences":
        return 0
    if name == "pilot_baselines_ablations_heterogeneity":
        inputs = result.get("inputs", {})
        model_count = len(inputs.get("models", []))
        return model_count * (
            int(inputs.get("intervention_items", 0))
            + int(inputs.get("specificity_items", 0))
        )
    if name == "image_quality_and_detectability":
        return int(result.get("pairs", 0))
    if name == "duplicate_leakage_contamination":
        return 185
    return 0


def run(output_root: Path = REPORT_ROOT, *, mode: str = "full", force: bool = False) -> dict[str, Any]:
    cpu_root = output_root / "cpu"
    checkpoint_path = cpu_root / "C11_CPU_CHECKPOINT.json"
    previous = {}
    if checkpoint_path.is_file() and not force:
        previous = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if previous.get("mode") != mode:
            previous = {}
    results: dict[str, Any] = dict(previous.get("stages", {}))
    for previous_name, previous_result in results.items():
        previous_result.setdefault(
            "input_item_count", _input_item_count(previous_name, previous_result)
        )
    stages: list[Stage] = [
        ("statistics_and_confidence_sequences", lambda: cvpr2027_statistics.run(output_root, mode=mode)),
        ("pilot_baselines_ablations_heterogeneity", lambda: cvpr2027_pilot_analysis.run(output_root)),
        ("image_quality_and_detectability", lambda: cvpr2027_image_audit.run(output_root, mode=mode)),
        ("duplicate_leakage_contamination", lambda: cvpr2027_leakage_audit.run(output_root)),
        ("human_review_infrastructure", lambda: _human(output_root)),
        ("prospective_candidate_selection", lambda: _candidate(output_root)),
    ]
    started_all = time.perf_counter()
    for name, function in stages:
        if not force and results.get(name, {}).get("status") in TERMINAL:
            continue
        started = time.perf_counter()
        peak_before = _peak_ram_bytes()
        try:
            result = function()
            result.setdefault("status", "COMPLETE")
        except Exception as exc:  # checkpoint exact local failure before propagating status
            result = {
                "status": "FAILED_LOCAL_REPAIR_REQUIRED",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        result["runtime_seconds"] = result.get("runtime_seconds", time.perf_counter() - started)
        result["peak_ram_bytes"] = max(peak_before, _peak_ram_bytes())
        result["input_item_count"] = _input_item_count(name, result)
        result["paper_evidence"] = False
        results[name] = result
        write_json(
            checkpoint_path,
            {
                "schema": "certvic.cvpr2027.cpu_checkpoint.v1",
                "mode": mode,
                "stages": results,
                "all_local_stages_terminal": all(
                    row.get("status") in TERMINAL for row in results.values()
                ),
                "paper_evidence": False,
            },
        )
    infrastructure_started = time.perf_counter()
    infrastructure = cvpr2027_infrastructure.run(output_root, stage_results=results)
    infrastructure["runtime_seconds"] = time.perf_counter() - infrastructure_started
    infrastructure["peak_ram_bytes"] = _peak_ram_bytes()
    results["audit_claims_redteam_gpu_planning_operator_pack"] = infrastructure
    failures = {
        name: row for name, row in results.items()
        if row.get("status") == "FAILED_LOCAL_REPAIR_REQUIRED"
    }
    blocked = {
        name: row.get("status") for name, row in results.items()
        if str(row.get("status", "")).startswith("BLOCKED")
    }
    summary = {
        "schema": "certvic.cvpr2027.cpu_execution_summary.v1",
        "status": "COMPLETE_ALL_AVAILABLE_CPU_WORK" if not failures else "FAILED_LOCAL_REPAIR_REQUIRED",
        "mode": mode,
        "runtime_seconds": sum(
            float(row.get("runtime_seconds", 0.0)) for row in results.values()
        ),
        "latest_resume_invocation_seconds": time.perf_counter() - started_all,
        "stages": results,
        "blocked_external_stages": blocked,
        "local_failure_count": len(failures),
        "local_failures": failures,
        "next_external_boundary": "PROVIDE_TWO_REAL_LICENSED_SMOKE_ITEMS",
        "paper_evidence": False,
    }
    write_json(cpu_root / "C11_CPU_EXECUTION_SUMMARY.json", summary)
    write_json(
        checkpoint_path,
        {
            "schema": "certvic.cvpr2027.cpu_checkpoint.v1",
            "mode": mode,
            "stages": results,
            "all_local_stages_terminal": not failures,
            "paper_evidence": False,
        },
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["quick", "full"], default="full")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output-root", type=Path, default=REPORT_ROOT)
    args = parser.parse_args(argv)
    result = run(args.output_root, mode=args.mode, force=args.force)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["local_failure_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
