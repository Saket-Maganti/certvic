"""Run the V2.1 simulation stress scenario matrix."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from certvic.io import load_model_jsonl, write_json
from certvic.metrics.certification import certify_gap
from certvic.metrics.summary import summarize_pair_scores
from certvic.reporting.build_v2_report import build_v2_report
from certvic.schema import PairScore, PredictionRecord, TaskItem
from certvic.sim import SIMULATION_EVIDENCE_STATUS
from certvic.sim.outcome_models import BUILTIN_SCENARIOS
from certvic.sim.simulated_manifests import build_synthetic_run
from certvic.validation.claims import build_evidence_context


DEFAULT_PARSE_FAILURE_WARNING_THRESHOLD = 0.20
DEFAULT_CONTROL_SPURIOUS_FLIP_WARNING_THRESHOLD = 0.25
DEFAULT_HIGH_GAP_THRESHOLD = 0.15
DEFAULT_NULL_GAP_ABS_THRESHOLD = 0.05


def run_stress_matrix(
    out_dir: str,
    n_items: int = 500,
    seed: int = 0,
    alpha: float = 0.05,
    gap_threshold: float = 0.05,
    scenarios: list[str] | None = None,
    parse_failure_warning_threshold: float = DEFAULT_PARSE_FAILURE_WARNING_THRESHOLD,
    control_spurious_flip_warning_threshold: float = DEFAULT_CONTROL_SPURIOUS_FLIP_WARNING_THRESHOLD,
) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scenario_names = scenarios or BUILTIN_SCENARIOS
    rows = []
    for scenario in scenario_names:
        scenario_dir = out / scenario
        run = build_synthetic_run(scenario_dir, scenario=scenario, n_items=n_items, seed=seed)
        report_dir = scenario_dir / "v2_report"
        build_v2_report(
            run["scores_path"],
            preds_path=run["predictions_path"],
            tasks_path=run["tasks_path"],
            out_dir=str(report_dir),
            alpha=alpha,
            gap_threshold=gap_threshold,
        )
        row = _scenario_row(
            scenario=scenario,
            run=run,
            report_dir=str(report_dir),
            alpha=alpha,
            gap_threshold=gap_threshold,
            parse_failure_warning_threshold=parse_failure_warning_threshold,
            control_spurious_flip_warning_threshold=control_spurious_flip_warning_threshold,
        )
        rows.append(row)

    csv_path = out / "scenario_matrix_summary.csv"
    json_path = out / "scenario_matrix_summary.json"
    report_path = out / "scenario_matrix_report.md"
    _write_csv(csv_path, rows)
    write_json(json_path, {"scenarios": rows, "all_simulated_only": True, "n_items": n_items, "seed": seed})
    report_path.write_text(_matrix_markdown(rows, n_items=n_items, seed=seed), encoding="utf-8")
    return {
        "out_dir": str(out),
        "summary_csv": str(csv_path),
        "summary_json": str(json_path),
        "report": str(report_path),
        "scenarios": len(rows),
        "all_claim_gates_blocked": all(row["claim_gate_blocks_simulated"] for row in rows),
        "all_simulated_only": True,
    }


def _scenario_row(
    scenario: str,
    run: dict,
    report_dir: str,
    alpha: float,
    gap_threshold: float,
    parse_failure_warning_threshold: float,
    control_spurious_flip_warning_threshold: float,
) -> dict:
    tasks = load_model_jsonl(run["tasks_path"], TaskItem)
    preds = load_model_jsonl(run["predictions_path"], PredictionRecord)
    scores = load_model_jsonl(run["scores_path"], PairScore)
    summary = summarize_pair_scores(scores)
    certification = certify_gap(
        [int(score.original_correct) for score in scores],
        [int(score.consistent) for score in scores],
        delta_threshold=gap_threshold,
        alpha=alpha,
        allow_unavailable=True,
        evidence_context=build_evidence_context(tasks=tasks, predictions=preds, scores=scores),
    )
    parse_failure_rate = _float_or_none(summary.get("parse_failure_rate"))
    control_flip = _float_or_none((summary.get("control_edit") or {}).get("spurious_flip_rate"))
    gap = _float_or_none(summary.get("intervention_consistency_gap"))
    certification_errors = certification.get("certification_gate_errors", [])
    stress_checks = _stress_checks(
        scenario,
        gap=gap,
        parse_failure_rate=parse_failure_rate,
        control_flip=control_flip,
        certified=bool(certification.get("certified")),
        parse_failure_warning_threshold=parse_failure_warning_threshold,
        control_spurious_flip_warning_threshold=control_spurious_flip_warning_threshold,
    )
    return {
        "scenario": scenario,
        "n": int(summary.get("n") or 0),
        "original_accuracy": _float_or_none(summary.get("original_accuracy")),
        "consistency": _float_or_none(summary.get("consistency_rate")),
        "gap": gap,
        "parse_failure_rate": parse_failure_rate,
        "control_spurious_flip_rate": control_flip,
        "certified": bool(certification.get("certified")),
        "cs_available": bool((certification.get("confidence_sequence") or {}).get("available")),
        "cs_lower_bound": _float_or_none(certification.get("lower_bound")),
        "claim_gate_blocks_simulated": any(SIMULATION_EVIDENCE_STATUS in err for err in certification_errors),
        "certification_gate_errors": certification_errors,
        "parse_failure_warning": bool(parse_failure_rate is not None and parse_failure_rate >= parse_failure_warning_threshold),
        "control_spurious_flip_warning": bool(control_flip is not None and control_flip >= control_spurious_flip_warning_threshold),
        "stress_checks": stress_checks,
        "report_dir": report_dir,
        "evidence_status": SIMULATION_EVIDENCE_STATUS,
        "simulated": True,
        "zero_cost": True,
        "not_for_paper_claims": True,
    }


def _stress_checks(
    scenario: str,
    gap: float | None,
    parse_failure_rate: float | None,
    control_flip: float | None,
    certified: bool,
    parse_failure_warning_threshold: float,
    control_spurious_flip_warning_threshold: float,
) -> dict:
    checks = {
        "claim_blocked": not certified,
        "not_overclaimed": not certified,
    }
    if scenario == "high_accuracy_low_consistency":
        checks["descriptive_high_gap"] = gap is not None and gap >= DEFAULT_HIGH_GAP_THRESHOLD
    if scenario == "null_gap":
        checks["near_zero_gap"] = gap is not None and abs(gap) <= DEFAULT_NULL_GAP_ABS_THRESHOLD
    if scenario == "parse_failure_heavy":
        checks["parse_failure_warning_triggered"] = (
            parse_failure_rate is not None and parse_failure_rate >= parse_failure_warning_threshold
        )
    if scenario == "spurious_control_flipper":
        checks["control_warning_triggered"] = (
            control_flip is not None and control_flip >= control_spurious_flip_warning_threshold
        )
    if scenario == "small_gap_borderline":
        checks["small_gap_not_overclaimed"] = not certified and (gap is None or gap <= DEFAULT_HIGH_GAP_THRESHOLD)
    return checks


def _write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "scenario",
        "n",
        "original_accuracy",
        "consistency",
        "gap",
        "parse_failure_rate",
        "control_spurious_flip_rate",
        "certified",
        "cs_available",
        "cs_lower_bound",
        "claim_gate_blocks_simulated",
        "parse_failure_warning",
        "control_spurious_flip_warning",
        "evidence_status",
        "report_dir",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _matrix_markdown(rows: list[dict], n_items: int, seed: int) -> str:
    lines = [
        "# CertVIC V2.1 Simulation Stress Matrix",
        "",
        "Status: SIMULATED_ONLY. These are not real data, not VLM outputs, not model evidence, and not paper claims.",
        "",
        f"- n_items per scenario: {n_items}",
        f"- seed: {seed}",
        f"- scenarios: {len(rows)}",
        f"- claim gates blocked all simulated artifacts: {all(row['claim_gate_blocks_simulated'] for row in rows)}",
        "",
        "| scenario | orig acc | consistency | gap | parse fail | control flip | certified | claim blocked |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {scenario} | {orig:.3f} | {cons:.3f} | {gap:.3f} | {parse:.3f} | {ctrl:.3f} | {cert} | {blocked} |".format(
                scenario=row["scenario"],
                orig=row["original_accuracy"] or 0.0,
                cons=row["consistency"] or 0.0,
                gap=row["gap"] or 0.0,
                parse=row["parse_failure_rate"] or 0.0,
                ctrl=row["control_spurious_flip_rate"] or 0.0,
                cert=row["certified"],
                blocked=row["claim_gate_blocks_simulated"],
            )
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "The matrix exercises metric, certification, reporting, parser-sensitivity, and control-warning surfaces before real runs. It cannot validate ADE20K data quality, edit photorealism, human validity, or VLM behavior.",
        "",
    ]
    return "\n".join(lines)


def _float_or_none(value) -> float | None:
    return None if value is None else float(value)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run built-in SIMULATED_ONLY CertVIC stress scenarios.")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--n-items", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--gap-threshold", type=float, default=0.05)
    parser.add_argument("--scenarios", nargs="*")
    parser.add_argument("--parse-failure-threshold", type=float, default=DEFAULT_PARSE_FAILURE_WARNING_THRESHOLD)
    parser.add_argument("--control-spurious-flip-threshold", type=float, default=DEFAULT_CONTROL_SPURIOUS_FLIP_WARNING_THRESHOLD)
    args = parser.parse_args(argv)
    result = run_stress_matrix(
        args.out_dir,
        n_items=args.n_items,
        seed=args.seed,
        alpha=args.alpha,
        gap_threshold=args.gap_threshold,
        scenarios=args.scenarios,
        parse_failure_warning_threshold=args.parse_failure_threshold,
        control_spurious_flip_warning_threshold=args.control_spurious_flip_threshold,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
