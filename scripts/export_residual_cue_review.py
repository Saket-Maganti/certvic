"""Export a blank residual-cue human-review sheet (V7 prompt 04).

The absent-object control shows models perceive *natural* absence. The remaining mechanism
concern is whether the *edited* images contain subtle residual cues (silhouette, texture,
shadow, partial object) that a human might miss but a VLM exploits. This is a **separate**
review from the original visual review: it asks, per edited image, "is any visible trace of
the target still present?".

This script writes a **blank** sheet (human fields empty -- never auto-filled). It also
attaches a `model_fail_count` per item to help reviewers prioritize: the number of the three
models whose post-edit presence answer is incorrect (canonical `edited_correct == False`,
verified to match `pair_scores_v2.jsonl`). Apply the completed sheet with
`scripts/apply_residual_cue_review.py`.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from certvic.io import read_jsonl, write_json  # noqa: E402

RESULTS = REPO / "data/results/main_real_200"
REVIEWED = RESULTS / "pilot_eval_tasks_reviewed_v2.jsonl"
OUT_DIR = RESULTS / "residual_cue_review"

# provider -> its presence raw-prediction file (per-model dirs differ in filename).
PRED_FILES = {
    "qwen2_5_vl_7b": "raw_predictions/presence__pred_qwen2_5_vl_7b_merged.jsonl",
    "internvl_8b": "raw_predictions__internvl_8b/presence__pred_internvl_8b_presence_merged.jsonl",
    "llava_onevision_7b": "raw_predictions__llava_onevision_7b/presence__pred_llava_onevision_7b_presence_merged.jsonl",
}

REVIEW_COLUMNS = [
    "item_id", "edit_id", "model_fail_count",
    "original_image_path", "edited_image_path", "target_object", "edit_type",
    # ---- human-entered (left blank on export) ----
    "residual_target_visible",   # yes / no / uncertain
    "residual_type",             # none / silhouette / texture / shadow / partial object / context-only / other
    "human_absence_confident",   # yes / no / uncertain
    "notes", "reviewer_id",
]


def _edited_answers(pred_path: Path) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for r in read_jsonl(pred_path):
        if r.get("image_variant") == "edited":
            out[r["item_id"]] = r.get("parsed_answer")
    return out


def compute_model_fail(reviewed: list[dict]) -> dict[str, dict]:
    """item_id -> {fail_count, n_models_scored, per_model: {provider: 'fail'|'ok'|'no_pred'}}."""
    gold = {it["item_id"]: it.get("answer_edited") for it in reviewed}
    per_model_edits: dict[str, dict[str, str | None]] = {}
    for prov, rel in PRED_FILES.items():
        p = RESULTS / rel
        per_model_edits[prov] = _edited_answers(p) if p.exists() else {}
    out: dict[str, dict] = {}
    for it in reviewed:
        iid = it["item_id"]
        per_model: dict[str, str] = {}
        fail = 0
        scored = 0
        for prov in PRED_FILES:
            ans = per_model_edits[prov].get(iid)
            if ans is None:
                per_model[prov] = "no_pred"
                continue
            scored += 1
            # canonical edited_correct == (edited answer matches gold post-edit answer)
            if ans != gold[iid]:
                per_model[prov] = "fail"
                fail += 1
            else:
                per_model[prov] = "ok"
        out[iid] = {"fail_count": fail, "n_models_scored": scored, "per_model": per_model}
    return out


def build(reviewed_path: Path = REVIEWED, out_dir: Path = OUT_DIR) -> dict:
    if not reviewed_path.exists():
        raise SystemExit(f"REFUSED: reviewed source tasks missing: {reviewed_path}")
    reviewed = [it for it in read_jsonl(reviewed_path) if it.get("visual_review_status") == "approved"]
    if not reviewed:
        raise SystemExit(f"REFUSED: no approved reviewed items in {reviewed_path}")

    fail_info = compute_model_fail(reviewed)
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet = out_dir / "residual_cue_review_sheet.csv"
    rows = []
    for it in reviewed:
        iid = it["item_id"]
        rows.append({
            "item_id": iid,
            "edit_id": it.get("edit_id"),
            "model_fail_count": fail_info[iid]["fail_count"],
            "original_image_path": it.get("original_image_path"),
            "edited_image_path": it.get("edited_image_path"),
            "target_object": it.get("question_object"),
            "edit_type": it.get("edit_type"),
            "residual_target_visible": "", "residual_type": "",
            "human_absence_confident": "", "notes": "", "reviewer_id": "",
        })
    with sheet.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=REVIEW_COLUMNS)
        w.writeheader()
        w.writerows(rows)

    fail_dist: dict[int, int] = {}
    for info in fail_info.values():
        fail_dist[info["fail_count"]] = fail_dist.get(info["fail_count"], 0) + 1
    meta = {
        "schema": "certvic.residual_cue_review.v1",
        "evidence_status": "RESIDUAL_CUE_REVIEW_PENDING_NON_EVIDENCE",
        "paper_evidence": False,
        "n_items": len(rows),
        "sheet_path": str(sheet.relative_to(REPO)),
        "model_fail_count_definition": "number of {qwen2_5_vl_7b, internvl_8b, llava_onevision_7b} with "
                                       "post-edit presence answer != gold (canonical edited_correct=False)",
        "model_fail_count_distribution": {str(k): v for k, v in sorted(fail_dist.items())},
        "human_fields_blank": True,
        "note": "Human fields are intentionally blank. Do not auto-fill. Apply with "
                "scripts/apply_residual_cue_review.py once a reviewer completes the sheet.",
    }
    write_json(out_dir / "residual_cue_export_meta.json", meta)
    return meta


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed", default=str(REVIEWED))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args(argv)
    meta = build(Path(args.reviewed), Path(args.out_dir))
    print(json.dumps({"n_items": meta["n_items"], "sheet": meta["sheet_path"],
                      "model_fail_count_distribution": meta["model_fail_count_distribution"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
