"""CSV and LaTeX table writers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_group_table(groups: dict, out_csv: str, out_tex: str | None = None) -> None:
    rows = []
    for key, metrics in groups.items():
        row = {"group": key}
        row.update(metrics)
        rows.append(row)
    df = pd.DataFrame(rows)
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    if out_tex:
        Path(out_tex).parent.mkdir(parents=True, exist_ok=True)
        Path(out_tex).write_text(df.to_latex(index=False), encoding="utf-8")


def write_main_table(summary: dict, certification: dict, out_tex: str) -> None:
    row = {
        "n": summary.get("n"),
        "orig_acc": summary.get("original_accuracy"),
        "consistency": summary.get("consistency_rate"),
        "gap": summary.get("intervention_consistency_gap"),
        "cs_lower": certification.get("lower_bound"),
        "certified": certification.get("certified"),
    }
    df = pd.DataFrame([row])
    Path(out_tex).parent.mkdir(parents=True, exist_ok=True)
    Path(out_tex).write_text(df.to_latex(index=False), encoding="utf-8")


def write_main_model_table(summary: dict, certification: dict, out_csv: str, out_tex: str) -> None:
    row = {
        "n": summary.get("n"),
        "original_accuracy": summary.get("original_accuracy"),
        "edited_accuracy": summary.get("edited_accuracy"),
        "consistency_rate": summary.get("consistency_rate"),
        "intervention_consistency_gap": summary.get("intervention_consistency_gap"),
        "parse_failure_rate": summary.get("parse_failure_rate"),
        "control_spurious_flip_rate": (summary.get("control_edit") or {}).get("spurious_flip_rate"),
        "cs_available": (certification.get("confidence_sequence") or {}).get("available"),
        "cs_lower_bound": certification.get("lower_bound"),
        "certified": certification.get("certified"),
        "certification_gate_errors": "; ".join(certification.get("certification_gate_errors") or []),
    }
    df = pd.DataFrame([row])
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    Path(out_tex).parent.mkdir(parents=True, exist_ok=True)
    Path(out_tex).write_text(df.to_latex(index=False), encoding="utf-8")


def write_single_table(row: dict, out_csv: str) -> None:
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(out_csv, index=False)
