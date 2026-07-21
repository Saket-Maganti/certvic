"""Compute inter-annotator agreement between rater 1 and a second rater (V7 prompt 07).

Joins the first-rater labels (``visual_review_completed.csv``) with a completed second-rater
sheet on ``item_id`` and reports Cohen's kappa + simple agreement per overlapping pass/fail
field, an item exclusion/sensitivity set where raters disagree on the gate, and a report that
keeps the **preliminary single-rater** result separate from the **two-rater** result.

Reuses ``certvic.validation.iaa``. Never auto-fills labels, never fabricates a rater, never
overwrites existing review labels, and makes no paper-grade claim until two-rater IAA exists.
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
from certvic.validation.iaa import cohens_kappa, normalize_rating, percent_agreement  # noqa: E402

RESULTS = REPO / "data/results/main_real_200"
OUT_DIR = RESULTS / "review_iaa"
RATER1 = RESULTS / "visual_review_completed.csv"
DEFAULT_RATER2 = OUT_DIR / "second_rater_review_sheet.csv"

# second-rater field -> rater-1 column (overlapping pass/fail fields only).
FIELD_MAP = {
    "photorealism": "photorealistic",
    "single_factor": "single_factor",
    "answerability": "prompt_answerable",
    "required_answer_change_unambiguous": "required_change_unambiguous",
    "keep_for_eval": "keep_for_eval",
}
RATER2_ONLY_FIELDS = ["target_absent_after_edit", "residual_target_cue_visible", "confidence"]
GATE_FIELD = "keep_for_eval"


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _norm_binary(v: str | None) -> str:
    """Map 1/0/yes/no/true/false -> yes/no/uncertain via iaa.normalize_rating."""
    t = (v or "").strip().lower()
    if t in {"1", "1.0", "true", "y"}:
        return "yes"
    if t in {"0", "0.0", "false", "n"}:
        return "no"
    return normalize_rating(t)


def compute(rater1_rows: list[dict], rater2_rows: list[dict]) -> dict:
    r1 = {r["item_id"]: r for r in rater1_rows if r.get("item_id")}
    # A second-rater row counts as "reviewed" only if it has any non-blank label field.
    def reviewed(r: dict) -> bool:
        return any((r.get(f) or "").strip() for f in list(FIELD_MAP) + RATER2_ONLY_FIELDS)

    r2 = {r["item_id"]: r for r in rater2_rows if r.get("item_id") and reviewed(r)}
    joined_ids = [i for i in r1 if i in r2]

    single_rater = {
        "rater_id": rater1_rows[0].get("reviewer_id") if rater1_rows else None,
        "n_items": len(r1),
        "keep_for_eval_pass": sum(1 for r in rater1_rows if _norm_binary(r.get("keep_for_eval")) == "yes"),
        "note": "Preliminary single-rater review (current canonical visual review). Not IAA.",
    }

    if not r2 or not joined_ids:
        return {
            "schema": "certvic.review_iaa.v1",
            "evidence_status": "REVIEW_IAA_PENDING_NON_EVIDENCE", "paper_evidence": False,
            "status": "second_rater_pending",
            "single_rater_preliminary": single_rater,
            "two_rater": None,
            "note": "No completed second-rater labels found. Two-rater IAA is pending; no "
                    "paper-grade review claim yet.",
        }

    per_field = {}
    for f2, c1 in FIELD_MAP.items():
        a, b = [], []
        for i in joined_ids:
            la = _norm_binary(r1[i].get(c1))
            lb = _norm_binary(r2[i].get(f2))
            if la and lb:
                a.append(la)
                b.append(lb)
        per_field[f2] = {
            "n": len(a),
            "percent_agreement": round(percent_agreement(a, b), 4) if a else None,
            "cohens_kappa": round(cohens_kappa(a, b), 4) if a else None,
            "rater1_column": c1,
        }

    # Exclusion/sensitivity set: disagreement on the gate field.
    disagree = []
    for i in joined_ids:
        if _norm_binary(r1[i].get(GATE_FIELD)) != _norm_binary(r2[i].get(GATE_FIELD)):
            disagree.append(i)

    return {
        "schema": "certvic.review_iaa.v1",
        "evidence_status": "REVIEW_IAA_TWO_RATER_NON_EVIDENCE", "paper_evidence": False,
        "status": "two_rater_computed",
        "n_joined_items": len(joined_ids),
        "single_rater_preliminary": single_rater,
        "two_rater": {
            "per_field": per_field,
            "gate_field": GATE_FIELD,
            "n_gate_disagreements": len(disagree),
            "exclusion_sensitivity_item_ids": disagree,
            "rater2_only_fields": RATER2_ONLY_FIELDS,
            "note": "Cohen's kappa over items both raters labeled. Items in the exclusion set "
                    "should drive a sensitivity check (recompute the gap with them dropped).",
        },
    }


def render_md(result: dict) -> str:
    L = ["# Human Review — IAA Report", "",
         f"**Status: {result['status']}** · `evidence_status={result['evidence_status']}`", ""]
    sr = result["single_rater_preliminary"]
    L += ["## Preliminary single-rater (current canonical)",
          f"- rater: `{sr['rater_id']}` · items: {sr['n_items']} · "
          f"keep_for_eval=pass: {sr['keep_for_eval_pass']}", ""]
    if result["status"] == "second_rater_pending":
        L += ["## Two-rater IAA", "Pending — no completed second-rater labels yet. "
              "Export with `scripts/export_second_rater_review.py`; no paper-grade review "
              "claim until this is done.", ""]
        return "\n".join(L)
    tr = result["two_rater"]
    L += [f"## Two-rater IAA (n joined = {result['n_joined_items']})", "",
          "| field | n | % agreement | Cohen's κ |", "|---|---|---|---|"]
    for f, d in tr["per_field"].items():
        L.append(f"| {f} | {d['n']} | {d['percent_agreement']} | {d['cohens_kappa']} |")
    L += ["",
          f"Gate field `{tr['gate_field']}` disagreements: **{tr['n_gate_disagreements']}** "
          f"(exclusion/sensitivity set). Rater-2-only fields (no IAA yet): "
          f"{', '.join(tr['rater2_only_fields'])}.", ""]
    return "\n".join(L)


def run(rater1: Path = RATER1, rater2: Path = DEFAULT_RATER2, out_dir: Path = OUT_DIR) -> dict:
    if not rater1.exists():
        raise SystemExit(f"REFUSED: first-rater review not found: {rater1}")
    rater1_rows = _read_csv(rater1)
    rater2_rows = _read_csv(rater2) if rater2.exists() else []
    result = compute(rater1_rows, rater2_rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "iaa_report.json", result)
    (out_dir / "iaa_report.md").write_text(render_md(result), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rater1", default=str(RATER1))
    parser.add_argument("--rater2", default=str(DEFAULT_RATER2))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args(argv)
    result = run(Path(args.rater1), Path(args.rater2), Path(args.out_dir))
    print(json.dumps({"status": result["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
