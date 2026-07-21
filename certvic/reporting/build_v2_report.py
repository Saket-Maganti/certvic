"""V2 paper-ready report builder: CVPR-style tables, figures, and markdown.

Produces tables (CSV + LaTeX), matplotlib figures, a figure manifest, and a claim
ledger from real run outputs. Unavailable cells render as `--`; descriptive and
certified results are kept separate. Makes no evidence claims by itself.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from certvic.io import load_model_jsonl
from certvic.metrics.certification import certify_gap
from certvic.metrics.summary import summarize_pair_scores
from certvic.schema import PairScore, PredictionRecord, TaskItem
from certvic.validation.claims import build_evidence_context


def _fmt(value) -> str:
    if value is None:
        return "--"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{value:.3f}"
    return str(value)


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _write_tex(path: Path, header: list[str], rows: list[list], caption: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\begin{tabular}{" + "l" * len(header) + "}",
        "\\toprule",
        " & ".join(header) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(_fmt(c) for c in row) + " \\\\")
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        f"\\caption{{{caption}}}",
        "\\end{table}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _group_rows(group: dict) -> list[list]:
    rows = []
    for key, metrics in sorted(group.items()):
        rows.append([
            key,
            metrics.get("n"),
            metrics.get("original_accuracy"),
            metrics.get("consistency_rate"),
            metrics.get("intervention_consistency_gap"),
        ])
    return rows


def _by_edit_type(scores: list[PairScore]) -> dict:
    buckets: dict[str, list[PairScore]] = defaultdict(list)
    for s in scores:
        buckets[str(s.metadata.get("edit_type", "unknown"))].append(s)
    out = {}
    for key, rows in buckets.items():
        n = len(rows)
        acc = sum(float(r.original_correct) for r in rows) / n
        cons = sum(float(r.consistent) for r in rows) / n
        out[key] = {"n": n, "original_accuracy": acc, "consistency_rate": cons, "intervention_consistency_gap": acc - cons}
    return out


def build_v2_report(scores_path: str, preds_path: str, tasks_path: str, out_dir: str, alpha: float = 0.05, gap_threshold: float = 0.05) -> dict:
    scores = load_model_jsonl(scores_path, PairScore)
    preds = load_model_jsonl(preds_path, PredictionRecord) if preds_path and Path(preds_path).exists() else []
    tasks = load_model_jsonl(tasks_path, TaskItem) if tasks_path and Path(tasks_path).exists() else []
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    summary = summarize_pair_scores(scores)
    a = [int(s.original_correct) for s in scores]
    c = [int(s.consistent) for s in scores]
    evidence_context = build_evidence_context(tasks=tasks, predictions=preds, scores=scores)
    simulation_only = "SIMULATED_ONLY" in {
        str(status).upper() for status in evidence_context.get("evidence_statuses", [])
    }
    certification = certify_gap(a, c, delta_threshold=gap_threshold, alpha=alpha, allow_unavailable=True, evidence_context=evidence_context)

    # main_results_table
    main_header = ["n", "orig_acc", "consistency", "gap", "cs_lower", "certified"]
    main_row = [summary.get("n"), summary.get("original_accuracy"), summary.get("consistency_rate"), summary.get("intervention_consistency_gap"), certification.get("lower_bound"), certification.get("certified")]
    _write_csv(out / "main_results_table.csv", main_header, [main_row])
    _write_tex(out / "main_results_table.tex", main_header, [main_row], "Main consistency results. `--' denotes unavailable; certification requires an anytime-valid CS lower bound above the threshold.")

    # by_family / by_domain / by_edit_type / control
    grp_header = ["group", "n", "orig_acc", "consistency", "gap"]
    _write_csv(out / "by_family_table.csv", grp_header, _group_rows(summary.get("by_task_family", {})))
    _write_tex(out / "by_family_table.tex", grp_header, _group_rows(summary.get("by_task_family", {})), "Consistency by task family.")
    _write_csv(out / "by_domain_table.csv", grp_header, _group_rows(summary.get("by_domain", {})))
    _write_csv(out / "by_edit_type_table.csv", grp_header, _group_rows(_by_edit_type(scores)))

    control = summary.get("control_edit", {})
    _write_csv(out / "control_edit_table.csv", ["n", "spurious_flip_rate", "consistency_rate"], [[control.get("n"), control.get("spurious_flip_rate"), control.get("consistency_rate")]])

    pfs = summary.get("parse_failure_sensitivity", {})
    _write_csv(out / "parser_sensitivity_table.csv", ["n_parse_failures", "parse_failure_rate"], [[pfs.get("n_parse_failures"), pfs.get("parse_failure_rate")]])

    _write_csv(out / "certification_table.csv", ["alpha", "gap_threshold", "cs_available", "cs_lower", "cs_upper", "certified"], [[alpha, gap_threshold, certification.get("confidence_sequence", {}).get("available"), certification.get("lower_bound"), certification.get("upper_bound"), certification.get("certified")]])

    # figures
    figure_manifest = _build_figures(out, summary, certification, scores)

    # claim ledger
    claim_ledger = {
        "descriptive_consistency_rate": summary.get("consistency_rate"),
        "descriptive_gap": summary.get("intervention_consistency_gap"),
        "certified": bool(certification.get("certified")),
        "cs_lower_bound": certification.get("lower_bound"),
        "evidence_context": evidence_context,
        "simulation_only": simulation_only,
        "allowed_claim": certification.get("safe_claim"),
        "note": (
            "SIMULATED_ONLY artifacts are not real data, not model evidence, and not paper claims."
            if simulation_only
            else "Descriptive metrics are not certification; certified requires CS lower bound above threshold and a clean evidence context."
        ),
    }
    (out / "claim_ledger.json").write_text(json.dumps(claim_ledger, indent=2, sort_keys=True), encoding="utf-8")

    # report.md
    lines = [
        "# CertVIC V2 Report",
        "",
        *(
            [
                "Status: SIMULATED_ONLY. This report is a stress-test artifact only: not real data, not model evidence, and not for paper claims.",
                "",
            ]
            if simulation_only
            else []
        ),
        f"n={summary.get('n')}, orig_acc={_fmt(summary.get('original_accuracy'))}, consistency={_fmt(summary.get('consistency_rate'))}, gap={_fmt(summary.get('intervention_consistency_gap'))}",
        f"certified={certification.get('certified')} (cs_lower={_fmt(certification.get('lower_bound'))})",
        "",
        "Descriptive results are not certification. See tables and figure_manifest.json.",
        "",
        "## Tables",
        "main_results_table, by_family_table, by_domain_table, by_edit_type_table, control_edit_table, parser_sensitivity_table, certification_table (csv/tex).",
        "",
    ]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")

    result = {
        "out_dir": out_dir,
        "n": summary.get("n"),
        "certified": bool(certification.get("certified")),
        "simulation_only": simulation_only,
        "figures": figure_manifest,
        "tables": ["main_results_table", "by_family_table", "by_domain_table", "by_edit_type_table", "control_edit_table", "parser_sensitivity_table", "certification_table"],
    }
    (out / "v2_report_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def _build_figures(out: Path, summary: dict, certification: dict, scores: list[PairScore]) -> list[dict]:
    manifest: list[dict] = []
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        (out / "figure_manifest.json").write_text(json.dumps([{"status": "matplotlib_unavailable"}]), encoding="utf-8")
        return [{"status": "matplotlib_unavailable"}]

    figdir = out / "figures"
    figdir.mkdir(parents=True, exist_ok=True)

    def _fig(figure_id: str, source: str, command: str, draw) -> None:
        path = figdir / f"{figure_id}.png"
        try:
            fig, ax = plt.subplots(figsize=(4, 3))
            drew = draw(ax)
            fig.tight_layout()
            fig.savefig(path, dpi=120)
            plt.close(fig)
            manifest.append({"figure_id": figure_id, "source_data": source, "command": command, "claim_status": "descriptive", "paper_ready": bool(drew), "path": str(path)})
        except Exception as exc:
            plt.close("all")
            manifest.append({"figure_id": figure_id, "source_data": source, "command": command, "claim_status": "descriptive", "paper_ready": False, "error": str(exc)})

    def gap_bar(ax):
        fam = summary.get("by_task_family", {})
        keys = list(fam.keys())
        vals = [fam[k].get("intervention_consistency_gap") or 0 for k in keys]
        if not keys:
            return False
        ax.bar(range(len(keys)), vals)
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels(keys, rotation=45, ha="right", fontsize=6)
        ax.set_ylabel("gap")
        ax.set_title("Consistency gap by family")
        return True

    def cs_traj(ax):
        cs = certification.get("confidence_sequence", {})
        lo = cs.get("lo") or []
        hi = cs.get("hi") or []
        if not lo:
            ax.text(0.5, 0.5, "CS unavailable", ha="center")
            return False
        ax.plot(lo, label="lower")
        ax.plot(hi, label="upper")
        ax.set_title("CS trajectory (gap)")
        ax.legend(fontsize=6)
        return True

    def parse_fail(ax):
        pfs = summary.get("parse_failure_sensitivity", {})
        rate = pfs.get("parse_failure_rate") or 0
        ax.bar(["parse_fail"], [rate])
        ax.set_ylim(0, 1)
        ax.set_title("Parse failure rate")
        return True

    def control_flip(ax):
        flip = (summary.get("control_edit") or {}).get("spurious_flip_rate") or 0
        ax.bar(["control_flip"], [flip])
        ax.set_ylim(0, 1)
        ax.set_title("Control spurious flip")
        return True

    def family_heat(ax):
        fam = summary.get("by_task_family", {})
        keys = list(fam.keys())
        if not keys:
            return False
        data = [[fam[k].get("original_accuracy") or 0, fam[k].get("consistency_rate") or 0] for k in keys]
        ax.imshow(data, aspect="auto", vmin=0, vmax=1)
        ax.set_yticks(range(len(keys)))
        ax.set_yticklabels(keys, fontsize=6)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["acc", "cons"], fontsize=6)
        ax.set_title("By-family heatmap")
        return True

    def sample_count(ax):
        fam = summary.get("by_task_family", {})
        keys = list(fam.keys())
        if not keys:
            return False
        ax.bar(range(len(keys)), [fam[k].get("n") or 0 for k in keys])
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels(keys, rotation=45, ha="right", fontsize=6)
        ax.set_title("Sample count by family")
        return True

    _fig("consistency_gap_bar", "by_family_table", "build_v2_report", gap_bar)
    _fig("cs_trajectory", "certification_table", "build_v2_report", cs_traj)
    _fig("by_family_heatmap", "by_family_table", "build_v2_report", family_heat)
    _fig("parse_failure", "parser_sensitivity_table", "build_v2_report", parse_fail)
    _fig("control_spurious_flip", "control_edit_table", "build_v2_report", control_flip)
    _fig("sample_count", "by_family_table", "build_v2_report", sample_count)

    (out / "figure_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC V2 report builder")
    parser.add_argument("--scores", required=True)
    parser.add_argument("--preds", default="")
    parser.add_argument("--tasks", default="")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--gap-threshold", type=float, default=0.05)
    args = parser.parse_args(argv)
    result = build_v2_report(args.scores, args.preds, args.tasks, args.out_dir, alpha=args.alpha, gap_threshold=args.gap_threshold)
    print(json.dumps({"out_dir": result["out_dir"], "n": result["n"], "figures": len(result["figures"])}, sort_keys=True))


if __name__ == "__main__":
    main()
