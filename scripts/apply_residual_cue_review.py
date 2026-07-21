"""Validate + summarize a completed residual-cue review sheet (V7 prompt 04).

Reads the human-completed sheet produced by ``export_residual_cue_review.py`` and reports:
  * residual-cue rate (excluding uncertain rows);
  * model failure rate among items where the human is confident the target is absent;
  * per-edit-type breakdown;
  * the uncertain rows to exclude from strong claims;
  * an **alternate** sensitivity view (the canonical pilot result is never modified here).

Hard rules: never auto-fill human labels; unreviewed rows are not evidence; the canonical
pilot numbers are left untouched -- this only produces a separate sensitivity summary.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from certvic.io import write_json  # noqa: E402

OUT_DIR = REPO / "data/results/main_real_200/residual_cue_review"
DEFAULT_SHEET = OUT_DIR / "residual_cue_review_sheet.csv"

RESIDUAL_VISIBLE = {"yes", "no", "uncertain"}
RESIDUAL_TYPE = {"none", "silhouette", "texture", "shadow", "partial object", "context-only", "other"}
ABSENCE_CONFIDENT = {"yes", "no", "uncertain"}


def _norm(v: str | None) -> str:
    return (v or "").strip().lower()


def validate_rows(rows: list[dict]) -> list[dict]:
    violations: list[dict] = []
    for i, r in enumerate(rows):
        rv = _norm(r.get("residual_target_visible"))
        rt = _norm(r.get("residual_type"))
        ac = _norm(r.get("human_absence_confident"))
        if rv == "":
            continue  # unreviewed row -- allowed, simply excluded from analysis
        if rv not in RESIDUAL_VISIBLE:
            violations.append({"row": i, "field": "residual_target_visible", "value": rv})
        if rt and rt not in RESIDUAL_TYPE:
            violations.append({"row": i, "field": "residual_type", "value": rt})
        if ac and ac not in ABSENCE_CONFIDENT:
            violations.append({"row": i, "field": "human_absence_confident", "value": ac})
        if not _norm(r.get("reviewer_id")):
            violations.append({"row": i, "field": "reviewer_id", "value": "missing on reviewed row"})
    return violations


def _fail_count(r: dict) -> int | None:
    try:
        return int(str(r.get("model_fail_count")).strip())
    except (TypeError, ValueError):
        return None


def summarize(rows: list[dict]) -> dict:
    reviewed = [r for r in rows if _norm(r.get("residual_target_visible")) in RESIDUAL_VISIBLE]
    unreviewed = [r for r in rows if _norm(r.get("residual_target_visible")) == ""]
    uncertain = [r for r in reviewed if _norm(r.get("residual_target_visible")) == "uncertain"]

    decided = [r for r in reviewed if _norm(r.get("residual_target_visible")) in {"yes", "no"}]
    n_yes = sum(1 for r in decided if _norm(r["residual_target_visible"]) == "yes")
    residual_cue_rate = (n_yes / len(decided)) if decided else None

    # Items where the human is confident the target is absent.
    absent_confident = [r for r in reviewed if _norm(r.get("human_absence_confident")) == "yes"]
    fails = [_fail_count(r) for r in absent_confident]
    fails = [f for f in fails if f is not None]
    model_fail_rate_when_absent = None
    any_model_fail_rate = None
    if absent_confident and fails:
        model_fail_rate_when_absent = sum(fails) / (3 * len(fails))   # mean fraction of 3 models
        any_model_fail_rate = sum(1 for f in fails if f >= 1) / len(fails)

    # Per-edit-type breakdown.
    by_edit: dict[str, dict] = {}
    for r in reviewed:
        et = _norm(r.get("edit_type")) or "unknown"
        d = by_edit.setdefault(et, {"n": 0, "residual_yes": 0, "fail_sum": 0, "fail_n": 0})
        d["n"] += 1
        if _norm(r["residual_target_visible"]) == "yes":
            d["residual_yes"] += 1
        fc = _fail_count(r)
        if fc is not None:
            d["fail_sum"] += fc
            d["fail_n"] += 1
    for et, d in by_edit.items():
        d["residual_rate"] = round(d["residual_yes"] / d["n"], 4) if d["n"] else None
        d["mean_model_fail"] = round(d["fail_sum"] / d["fail_n"], 4) if d["fail_n"] else None

    # Alternate, strongest-evidence subset: human confident absent AND no residual cue.
    clean = [r for r in reviewed
             if _norm(r.get("human_absence_confident")) == "yes"
             and _norm(r.get("residual_target_visible")) == "no"]
    clean_fails = [f for f in (_fail_count(r) for r in clean) if f is not None]
    clean_model_fail_rate = (sum(clean_fails) / (3 * len(clean_fails))) if clean_fails else None

    status = "review_pending" if not reviewed else "summarized"
    return {
        "schema": "certvic.residual_cue_summary.v1",
        "evidence_status": "RESIDUAL_CUE_SENSITIVITY_NON_EVIDENCE",
        "paper_evidence": False,
        "status": status,
        "canonical_unchanged": True,
        "n_total": len(rows),
        "n_reviewed": len(reviewed),
        "n_unreviewed_excluded": len(unreviewed),
        "n_uncertain_excluded_from_strong_claims": len(uncertain),
        "uncertain_item_ids": [r.get("item_id") for r in uncertain],
        "residual_cue_rate": round(residual_cue_rate, 4) if residual_cue_rate is not None else None,
        "n_decided_for_residual_rate": len(decided),
        "model_fail_rate_when_human_absence_confident": round(model_fail_rate_when_absent, 4)
            if model_fail_rate_when_absent is not None else None,
        "any_model_fail_rate_when_absent_confident": round(any_model_fail_rate, 4)
            if any_model_fail_rate is not None else None,
        "n_absent_confident": len(absent_confident),
        "per_edit_type": by_edit,
        "alternate_clean_subset": {
            "definition": "human_absence_confident=yes AND residual_target_visible=no",
            "n": len(clean),
            "mean_model_fail_rate": round(clean_model_fail_rate, 4)
                if clean_model_fail_rate is not None else None,
            "note": "Descriptive sensitivity only. Full re-certification on this subset requires "
                    "re-running scripts/pilot_report_from_raw.py on the filtered item set; the "
                    "canonical pilot result is unchanged.",
        },
    }


def render_sensitivity_md(summary: dict, violations: list[dict]) -> str:
    L = ["# Residual-Cue Review — Sensitivity Summary", "",
         f"**Status: {summary['status']}** · "
         f"`evidence_status={summary['evidence_status']}` · canonical result unchanged.", ""]
    if summary["status"] == "review_pending":
        L += ["No rows have been reviewed yet. The blank sheet is at "
              "`data/results/main_real_200/residual_cue_review/residual_cue_review_sheet.csv`.",
              "Complete it per `docs/MAIN200_RESIDUAL_CUE_REVIEW_INSTRUCTIONS.md`, then re-run "
              "`scripts/apply_residual_cue_review.py`.", ""]
        return "\n".join(L)
    if violations:
        L += [f"⚠ {len(violations)} schema violation(s) found; fix before trusting the summary.", ""]
    L += [
        f"- Reviewed: {summary['n_reviewed']}/{summary['n_total']} "
        f"(unreviewed excluded: {summary['n_unreviewed_excluded']})",
        f"- Residual-cue rate (decided rows): {summary['residual_cue_rate']} "
        f"(n={summary['n_decided_for_residual_rate']})",
        f"- Uncertain rows excluded from strong claims: {summary['n_uncertain_excluded_from_strong_claims']}",
        f"- Model-fail rate when human is confident the target is absent: "
        f"{summary['model_fail_rate_when_human_absence_confident']} "
        f"(any-model: {summary['any_model_fail_rate_when_absent_confident']}, "
        f"n={summary['n_absent_confident']})",
        f"- Clean subset (absent-confident & no residual cue): n={summary['alternate_clean_subset']['n']}, "
        f"mean model-fail rate={summary['alternate_clean_subset']['mean_model_fail_rate']}",
        "",
        "Interpretation: a high model-fail rate on the **clean subset** (humans confident the "
        "target is absent, no residual cue visible) is the strongest available signal that the "
        "failure is not explained by residual pixels. This is a descriptive sensitivity view; "
        "the canonical pilot numbers are not modified.",
        "",
    ]
    return "\n".join(L)


def read_sheet(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def apply(sheet_path: Path = DEFAULT_SHEET, out_dir: Path = OUT_DIR) -> dict:
    if not sheet_path.exists():
        raise SystemExit(f"REFUSED: review sheet not found: {sheet_path} (run export first)")
    rows = read_sheet(sheet_path)
    violations = validate_rows(rows)
    summary = summarize(rows)
    summary["schema_violations"] = violations
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "residual_cue_summary.json", summary)
    (out_dir / "residual_cue_sensitivity.md").write_text(
        render_sensitivity_md(summary, violations), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", default=str(DEFAULT_SHEET))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args(argv)
    summary = apply(Path(args.sheet), Path(args.out_dir))
    print(json.dumps({"status": summary["status"], "n_reviewed": summary["n_reviewed"],
                      "residual_cue_rate": summary["residual_cue_rate"],
                      "schema_violations": len(summary["schema_violations"])}, sort_keys=True))


if __name__ == "__main__":
    main()
