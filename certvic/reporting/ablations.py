"""Ablation summary builder."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from certvic.eval.ablation_baselines import BASELINES
from certvic.eval.parse import parse_answer
from certvic.eval.prompt_suite import PROMPT_VARIANTS, build_prompt_variants, variant_leakage_flags
from certvic.io import read_json, read_jsonl, write_json

# Baselines that do not use the visual change; high consistency here would mean
# the task is gameable without seeing the edit.
NON_VISUAL_BASELINES = ["random_seeded", "majority_by_family", "answer_prior", "caption_only_stub", "text_only_heuristic", "prompt_shuffle_control"]
GAMEABLE_CONSISTENCY_THRESHOLD = 0.6

# Representative model-style raw outputs for parser sensitivity.
PARSER_DEMO_OUTPUTS = ["yes", "no", "Yes.", "the answer is yes", "I would say no", "maybe", "yes no", ""]


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def build_ablations_report(pred_dir: str, tasks_path: str, out_dir: str) -> dict:
    pred = Path(pred_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    index = read_json(str(pred / "ablation_index.json")) if (pred / "ablation_index.json").exists() else {"baseline_summaries": {}}
    summaries = index.get("baseline_summaries", {})
    tasks = read_jsonl(tasks_path) if tasks_path and Path(tasks_path).exists() else []

    # baseline_table.csv
    baseline_rows = []
    for name in BASELINES:
        s = summaries.get(name, {})
        baseline_rows.append([
            name,
            s.get("n", 0),
            _fmt(s.get("accuracy")),
            _fmt(s.get("consistency")),
            _fmt(s.get("gap")),
            _fmt(s.get("parse_fail_rate")),
        ])
    _write_csv(out / "baseline_table.csv", ["baseline", "n", "accuracy", "consistency", "gap", "parse_fail_rate"], baseline_rows)

    # parser_sensitivity.csv
    parser_rows = []
    for raw in PARSER_DEMO_OUTPUTS:
        strict = parse_answer(raw, "yes_no", strict=True)
        lenient = parse_answer(raw, "yes_no", strict=False)
        bucket = "ok" if strict.parse_ok else ("recovered_lenient" if lenient.parse_ok else "fail")
        parser_rows.append([repr(raw), strict.parsed_answer, strict.parse_ok, lenient.parsed_answer, lenient.parse_ok, bucket])
    _write_csv(
        out / "parser_sensitivity.csv",
        ["raw_output", "strict_parsed", "strict_ok", "lenient_parsed", "lenient_ok", "bucket"],
        parser_rows,
    )

    # prompt_sensitivity.csv
    prompt_rows = []
    sample = tasks[:20]
    for variant in PROMPT_VARIANTS:
        lengths = []
        leak = 0
        for task in sample:
            q = str(task.get("question_original") or "Is the object present")
            text = build_prompt_variants(q)[variant]
            lengths.append(len(text))
            if variant_leakage_flags(q)[variant]:
                leak += 1
        mean_len = round(sum(lengths) / len(lengths), 1) if lengths else 0
        prompt_rows.append([variant, len(sample), leak, mean_len])
    _write_csv(out / "prompt_sensitivity.csv", ["prompt_variant", "n_items", "n_leakage_flagged", "mean_len"], prompt_rows)

    # construct_validity_flags.json
    non_visual = {name: summaries.get(name, {}).get("consistency") for name in NON_VISUAL_BASELINES if name in summaries}
    max_non_visual = max((v for v in non_visual.values() if v is not None), default=None)
    flags = {
        "non_visual_baseline_consistency": non_visual,
        "max_non_visual_consistency": max_non_visual,
        "task_gameable_without_vision": bool(max_non_visual is not None and max_non_visual > GAMEABLE_CONSISTENCY_THRESHOLD),
        "single_image_baseline_consistency": {
            "original_only": summaries.get("original_only", {}).get("consistency"),
            "edited_only": summaries.get("edited_only", {}).get("consistency"),
        },
        "prompt_leakage_stress_flagged": all(
            bool(variant_leakage_flags(str(t.get("question_original") or "Is the object present"))["prompt_leakage_stress"]) for t in (sample or [{}])
        ),
        "evidence_status": "CONSTRUCT_VALIDITY_NON_EVIDENCE",
    }
    write_json(out / "construct_validity_flags.json", flags)

    # ablation_summary.md
    lines = ["# Ablation Summary", "", "Construct-validity baselines (NOT evidence).", "", "| Baseline | n | acc | consistency | gap |", "| --- | --- | --- | --- | --- |"]
    for row in baseline_rows:
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} |")
    lines += ["", f"Max non-visual baseline consistency: {_fmt(max_non_visual)} "
              f"(threshold {GAMEABLE_CONSISTENCY_THRESHOLD}; gameable={flags['task_gameable_without_vision']}).",
              "", "Parser sensitivity and prompt sensitivity in the CSVs; failures are never hidden.", ""]
    (out / "ablation_summary.md").write_text("\n".join(lines), encoding="utf-8")

    return {
        "out_dir": out_dir,
        "baselines": len(baseline_rows),
        "max_non_visual_consistency": max_non_visual,
        "task_gameable_without_vision": flags["task_gameable_without_vision"],
        "files": ["ablation_summary.md", "baseline_table.csv", "parser_sensitivity.csv", "prompt_sensitivity.csv", "construct_validity_flags.json"],
    }


def _fmt(value) -> str:
    return f"{value:.3f}" if isinstance(value, (int, float)) else "--"


def build_ablation_report(report_paths: list[str], out_path: str) -> None:
    lines = ["# CertVIC Ablation Summary", "", "This report compares available baseline/model summaries."]
    for path in report_paths:
        data = read_json(path)
        summary = data.get("summary", data)
        lines.append("")
        lines.append(f"## {path}")
        lines.append(f"- n: {summary.get('n')}")
        lines.append(f"- consistency: {summary.get('consistency_rate')}")
        lines.append(f"- gap: {summary.get('intervention_consistency_gap')}")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ablation reporting")
    parser.add_argument("--reports", nargs="+")
    parser.add_argument("--out")
    parser.add_argument("--pred-dir", help="directory of baseline predictions from run_ablations")
    parser.add_argument("--tasks")
    parser.add_argument("--out-dir", help="output directory for the V2 ablation report")
    args = parser.parse_args(argv)
    if args.pred_dir and args.out_dir:
        print(json.dumps(build_ablations_report(args.pred_dir, args.tasks or "", args.out_dir), sort_keys=True))
        return
    if args.reports and args.out:
        build_ablation_report(args.reports, args.out)
        return
    parser.error("provide either --pred-dir/--out-dir or --reports/--out")


if __name__ == "__main__":
    main()
