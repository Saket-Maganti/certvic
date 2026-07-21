"""Report how item-validity gates shift the measured decision-update gap."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from certvic.io import write_json
from certvic.validity.load_bearing import analyze_load_bearing


def _fmt(value) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_markdown(result: dict) -> str:
    lines = [
        "# Validity-Shift Report",
        "",
        f"Status: {result['analysis_status']}",
        f"Claim status: {result['claim_status']}",
        f"Certificate load-bearing: {result['certificate_is_load_bearing']}",
        f"Gap shift: {_fmt(result['gap_shift'])}",
        "",
        "| Stage | n | Original accuracy | Consistency rate | Gap | Parse failure |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["stages"]:
        lines.append(
            "| {stage} | {n} | {oa} | {cr} | {gap} | {pf} |".format(
                stage=row["stage"],
                n=row["n"],
                oa=_fmt(row["original_accuracy"]),
                cr=_fmt(row["consistency_rate"]),
                gap=_fmt(row["intervention_consistency_gap"]),
                pf=_fmt(row["parse_failure_rate"]),
            )
        )
    lines += [
        "",
        "This report is descriptive until real, certificate-eligible scores pass the claim gates.",
        "",
    ]
    return "\n".join(lines)


def write_report(scores: str, certificates: str, out_dir: str) -> dict:
    result = analyze_load_bearing(scores, certificates)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "validity_shift_summary.json", result)
    with (out / "validity_shift_table.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "stage",
            "n",
            "original_accuracy",
            "consistency_rate",
            "intervention_consistency_gap",
            "parse_failure_rate",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in result["stages"]:
            writer.writerow({key: row.get(key) for key in fieldnames})
    (out / "validity_shift_report.md").write_text(render_markdown(result), encoding="utf-8")
    write_json(
        out / "validity_shift_plot_spec.json",
        {
            "kind": "line",
            "x": "stage",
            "y": "intervention_consistency_gap",
            "source": "validity_shift_table.csv",
            "requires_heavy_plotting_deps": False,
        },
    )
    return {"out_dir": str(out), "passed": True, "certificate_is_load_bearing": result["certificate_is_load_bearing"]}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build a validity-shift report")
    parser.add_argument("--scores", required=True)
    parser.add_argument("--certificates", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_report(args.scores, args.certificates, args.out_dir), sort_keys=True))


if __name__ == "__main__":
    main()
