"""Export a blinded second-rater review sheet for the same 91 items (V7 prompt 07).

Produces a CSV in **randomized (seeded) order** with **no model results and no first-rater
labels** (so the second rater is not biased). Human fields are blank -- never auto-filled.
Compute agreement later with ``scripts/compute_review_iaa.py``.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from certvic.io import read_jsonl, write_json  # noqa: E402

RESULTS = REPO / "data/results/main_real_200"
REVIEWED = RESULTS / "pilot_eval_tasks_reviewed_v2.jsonl"
OUT_DIR = RESULTS / "review_iaa"

# Pre-filled context (NOT labels) + blank human fields. No rater-1 / model columns => no leakage.
COLUMNS = [
    "blind_order", "item_id", "edit_id", "target_object", "edit_type",
    "original_image_path", "edited_image_path", "question",
    # ---- human-entered (blank on export) ----
    "photorealism",                         # yes/no
    "single_factor",                        # yes/no
    "target_absent_after_edit",             # yes/no/uncertain  (rater-2 only)
    "answerability",                        # yes/no
    "required_answer_change_unambiguous",   # yes/no
    "residual_target_cue_visible",          # yes/no/uncertain  (rater-2 only)
    "confidence",                           # high/med/low       (rater-2 only)
    "keep_for_eval",                        # yes/no  (the pass/fail gate)
    "notes", "reviewer_id",
]


def build(reviewed_path: Path = REVIEWED, out_dir: Path = OUT_DIR, seed: int = 1337) -> dict:
    if not reviewed_path.exists():
        raise SystemExit(f"REFUSED: reviewed source tasks missing: {reviewed_path}")
    items = [it for it in read_jsonl(reviewed_path) if it.get("visual_review_status") == "approved"]
    if not items:
        raise SystemExit(f"REFUSED: no approved reviewed items in {reviewed_path}")

    order = list(range(len(items)))
    random.Random(seed).shuffle(order)  # blinded, reproducible row order

    out_dir.mkdir(parents=True, exist_ok=True)
    sheet = out_dir / "second_rater_review_sheet.csv"
    with sheet.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for blind_order, idx in enumerate(order, start=1):
            it = items[idx]
            row = {c: "" for c in COLUMNS}
            row.update({
                "blind_order": blind_order,
                "item_id": it.get("item_id"),
                "edit_id": it.get("edit_id"),
                "target_object": it.get("question_object"),
                "edit_type": it.get("edit_type"),
                "original_image_path": it.get("original_image_path"),
                "edited_image_path": it.get("edited_image_path"),
                "question": it.get("question_edited"),
            })
            w.writerow(row)

    meta = {
        "schema": "certvic.second_rater_export.v1",
        "evidence_status": "SECOND_RATER_PENDING_NON_EVIDENCE", "paper_evidence": False,
        "n_items": len(items), "seed": seed,
        "sheet_path": str(sheet.relative_to(REPO)),
        "blinded": True, "leakage_free": True,
        "leakage_policy": "no model outcomes and no first-rater labels are included",
        "human_fields_blank": True,
        "note": "Do not auto-fill. A real second rater completes this; then run compute_review_iaa.py.",
    }
    write_json(out_dir / "second_rater_export_meta.json", meta)
    return meta


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed", default=str(REVIEWED))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--seed", type=int, default=1337)
    args = parser.parse_args(argv)
    meta = build(Path(args.reviewed), Path(args.out_dir), args.seed)
    print(json.dumps({"n_items": meta["n_items"], "sheet": meta["sheet_path"],
                      "blinded": meta["blinded"], "leakage_free": meta["leakage_free"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
