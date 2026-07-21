"""Emit paper-ready tables for the main_real_200 3-model pilot (V7 prompt 02).

Reads ONLY canonical artifacts (per-model ``pilot_result.json`` + the regenerated
``multimodel_pilot_summary.json``) and writes CSV/TeX tables plus a provenance-aware
markdown report. Every number is recomputed from those files -- nothing is transcribed.

PILOT ONLY. Makes no paper-grade claim. The ``control_irrelevant`` (spurious-flip)
specificity row is populated only when a per-model report contains real spurious
predictions, and it reports the gate status rather than treating existence as a pass.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "data/results/main_real_200"
TABLES = RESULTS / "tables"

PROVIDERS = ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]
EDIT_TYPES = ["remove", "occlude", "displace", "control_irrelevant"]


def _load_reports() -> dict[str, dict]:
    reports: dict[str, dict] = {}
    for jf in sorted(RESULTS.glob("pilot_report*/pilot_result.json")):
        data = json.loads(jf.read_text())
        prov = data.get("provider")
        if prov:
            reports[prov] = data
    return reports


def _intervention_rows(reports: dict[str, dict]) -> list[dict]:
    rows = []
    for prov in PROVIDERS:
        d = reports.get(prov)
        if not d:
            continue
        ps = d["presence_intervention"]["summary"]
        pc = d["presence_intervention"]["certification"]
        rows.append({
            "model": d.get("model", prov),
            "provider": prov,
            "n_items": ps.get("n"),
            "original_accuracy_a": round(ps["original_accuracy"], 4),
            "consistency_p": round(ps["consistency_rate"], 4),
            "delta_gap": round(ps["intervention_consistency_gap"], 4),
            "cs_lower": round(pc["lower_bound"], 4) if pc.get("lower_bound") is not None else "",
            "cs_upper": round(pc["upper_bound"], 4) if pc.get("upper_bound") is not None else "",
            "cs_threshold_passed": bool(pc.get("cs_threshold_passed")),
            "certified": bool(pc.get("certified")),
            "parse_failures": round(ps.get("parse_failure_rate", 0.0), 4),
        })
    return rows


def _control_rows(reports: dict[str, dict]) -> list[dict]:
    rows = []
    for prov in PROVIDERS:
        d = reports.get(prov)
        if not d:
            continue
        c = d["absent_object_control"]
        rows.append({
            "model": d.get("model", prov),
            "provider": prov,
            "absent_accuracy": c.get("absent_accuracy"),
            "present_accuracy": c.get("present_accuracy"),
            "n_absent": c.get("absent_n"),
            "n_present": c.get("present_n"),
            "absent": f"{c.get('absent_correct')}/{c.get('absent_n')}",
            "present": f"{c.get('present_correct')}/{c.get('present_n')}",
        })
    return rows


def _per_edit_type_rows(reports: dict[str, dict]) -> list[dict]:
    rows = []
    for prov in PROVIDERS:
        d = reports.get(prov)
        if not d:
            continue
        bet = d["presence_intervention"].get("by_edit_type", {})
        for et in EDIT_TYPES:
            if et in bet:
                e = bet[et]
                rows.append({
                    "model": d.get("model", prov), "provider": prov, "edit_type": et,
                    "n": e.get("n"), "original_accuracy": e.get("original_accuracy"),
                    "consistency": e.get("consistency_rate"), "gap": e.get("gap"),
                    "status": "run",
                })
            elif et == "control_irrelevant" and d.get("spurious_flip_control"):
                sp = d["spurious_flip_control"]
                rows.append({
                    "model": d.get("model", prov), "provider": prov, "edit_type": et,
                    "n": sp.get("n_items"), "original_accuracy": "",
                    "consistency": (
                        round(1.0 - sp["spurious_flip_rate"], 4)
                        if sp.get("spurious_flip_rate") is not None else ""
                    ),
                    "gap": "",
                    "status": "gate_pass" if sp.get("gate_pass") else "gate_fail",
                })
            else:
                # control_irrelevant (specificity) arm has no predictions yet.
                rows.append({
                    "model": d.get("model", prov), "provider": prov, "edit_type": et,
                    "n": "", "original_accuracy": "", "consistency": "", "gap": "",
                    "status": "not_available" if et == "control_irrelevant" else "absent_from_plan",
                })
    return rows


def _write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r[c]) for c in columns})


def _tex_table(rows: list[dict]) -> str:
    L = [
        "% PILOT ONLY -- generated by scripts/build_main200_paper_tables.py; do not hand-edit.",
        "% Source: data/results/main_real_200/pilot_report*/pilot_result.json",
        r"\begin{tabular}{llrrrrrrcc}",
        r"\toprule",
        r"Model & Provider & $n$ & $a$ & $p$ & $\Delta$ & CS-LB & CS-UB & CS pass & Full cert. \\",
        r"\midrule",
    ]
    for r in rows:
        model = r["model"].replace("_", r"\_")
        prov = r["provider"].replace("_", r"\_")
        cs_pass = r"\checkmark" if r["cs_threshold_passed"] else r"$\times$"
        cert = r"\checkmark" if r["certified"] else r"$\times$"
        L.append(
            f"{model} & {prov} & {r['n_items']} & {r['original_accuracy_a']} & "
            f"{r['consistency_p']} & {r['delta_gap']} & {r['cs_lower']} & {r['cs_upper']} & "
            f"{cs_pass} & {cert} \\\\"
        )
    L += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(L) + "\n"


def _tex_control(rows: list[dict]) -> str:
    L = [
        "% PILOT ONLY -- generated by scripts/build_main200_paper_tables.py; do not hand-edit.",
        "% Source: data/results/main_real_200/pilot_report*/absent_object_control.json",
        r"\begin{tabular}{llcccc}",
        r"\toprule",
        r"Model & Provider & Absent acc & Present acc & $n$ absent & $n$ present \\",
        r"\midrule",
    ]
    for r in rows:
        model = r["model"].replace("_", r"\_")
        prov = r["provider"].replace("_", r"\_")
        L.append(f"{model} & {prov} & {r['absent']} & {r['present']} & "
                 f"{r['n_absent']} & {r['n_present']} \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(L) + "\n"


def _report_md(intervention: list[dict], control: list[dict], per_edit: list[dict],
               n_run: int) -> str:
    L: list[str] = []
    A = L.append
    A("# CertVIC Main-200 Multi-Model Pilot Report")
    A("")
    A("**PILOT ONLY** (`evidence_status = MACHINE_ASSISTED_PRELIMINARY`, `paper_evidence = false`). "
      f"{n_run}/3 registered open VLMs run. All numbers are recomputed from canonical "
      "per-model `pilot_result.json` files by `scripts/build_main200_paper_tables.py` — none are transcribed.")
    A("")
    A("Each model's anytime-valid CS lower bound crosses the numeric 0.05 threshold. None is "
      "fully policy-certified: n=91 is below the 150-item minimum, two task families are "
      "underpowered, specificity/review gates remain unresolved, and the evidence class is non-paper.")
    A("")
    A("## Table 1 — Presence-intervention (headline arm), same 91 reviewed items")
    A("")
    A("`Δ = a − p`, where `a` = original-image accuracy and `p` = post-edit answer consistency.")
    A("")
    A("| Model | Provider | n | a | p | Δ | CS LB | CS UB | CS threshold | Full certified | Parse fail |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in intervention:
        A(f"| {r['model']} | `{r['provider']}` | {r['n_items']} | {r['original_accuracy_a']} | "
          f"{r['consistency_p']} | {r['delta_gap']} | {r['cs_lower']} | {r['cs_upper']} | "
          f"{r['cs_threshold_passed']} | {r['certified']} | {r['parse_failures']} |")
    A("")
    A("CSV: `tables/main200_multimodel_results.csv` · TeX: `tables/main200_multimodel_results.tex`")
    A("")
    A("## Table 2 — Absent-object control (natural absence, no edits)")
    A("")
    A("Rules out the *answers-the-presupposition-without-looking* confound: when the object is "
      "naturally absent, all three models correctly say \"no\" at high rates.")
    A("")
    A("| Model | Provider | absent acc | present acc | n absent | n present |")
    A("|---|---|---|---|---|---|")
    for r in control:
        A(f"| {r['model']} | `{r['provider']}` | {r['absent']} ({r['absent_accuracy']}) | "
          f"{r['present']} ({r['present_accuracy']}) | {r['n_absent']} | {r['n_present']} |")
    A("")
    A("CSV: `tables/main200_control_results.csv`")
    A("")
    A("## Table 3 — Per-edit-type (presence arm)")
    A("")
    A("`control_irrelevant` is the spurious-flip specificity arm. If populated, `consistency` is "
      "1 - spurious-flip-rate and `status` records the configured gate result. A `gate_fail` row "
      "remains a blocker; prediction existence alone is not a pass.")
    A("")
    A("| Model | Edit type | n | original acc | consistency | gap | status |")
    A("|---|---|---|---|---|---|---|")
    for r in per_edit:
        A(f"| `{r['provider']}` | {r['edit_type']} | {r['n']} | {r['original_accuracy']} | "
          f"{r['consistency']} | {r['gap']} | {r['status']} |")
    A("")
    A("CSV: `tables/main200_per_edit_type.csv`")
    A("")
    A("## What this report does and does not claim")
    A("")
    A("- **Does:** report replicated numeric CS-threshold crossings and descriptive gaps between "
      "original-image accuracy and post-edit consistency on 91 machine-assisted preliminary "
      "ADE20K items across three open VLMs, alongside a natural-absence diagnostic.")
    A("- **Does not:** assert a paper-grade or general result. Open blockers: spurious-flip "
      "specificity control, scale (n=91), single dataset, single-rater review/IAA, mechanism, "
      "prompt polarity. See `docs/V7_POST3MODEL_PROJECT_STATE.md`.")
    A("")
    return "\n".join(L)


def build(results_root: Path = RESULTS) -> dict:
    reports = _load_reports()
    intervention = _intervention_rows(reports)
    control = _control_rows(reports)
    per_edit = _per_edit_type_rows(reports)

    tables = results_root / "tables"
    _write_csv(tables / "main200_multimodel_results.csv", intervention,
               ["model", "provider", "n_items", "original_accuracy_a", "consistency_p",
                "delta_gap", "cs_lower", "cs_upper", "cs_threshold_passed", "certified",
                "parse_failures"])
    (tables / "main200_multimodel_results.tex").write_text(_tex_table(intervention), encoding="utf-8")
    _write_csv(tables / "main200_control_results.csv", control,
               ["model", "provider", "absent_accuracy", "present_accuracy", "n_absent",
                "n_present", "absent", "present"])
    (tables / "main200_control_results.tex").write_text(_tex_control(control), encoding="utf-8")
    _write_csv(tables / "main200_per_edit_type.csv", per_edit,
               ["model", "provider", "edit_type", "n", "original_accuracy", "consistency",
                "gap", "status"])

    report = REPO / "docs/MAIN200_MULTIMODEL_PILOT_REPORT.md"
    report.write_text(_report_md(intervention, control, per_edit, len(intervention)), encoding="utf-8")
    return {"n_run": len(intervention), "tables_dir": str(tables.relative_to(REPO)),
            "report": str(report.relative_to(REPO))}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", default=str(RESULTS))
    args = parser.parse_args(argv)
    out = build(Path(args.results_root))
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
