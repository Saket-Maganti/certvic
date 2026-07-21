"""Build prompt-polarity / phrasing ablation task manifests (V7 prompt 08).

A reviewer may argue the effect depends on awkward prompt polarity (the v2 set mixes positive
and negated phrasing). This script generates clean single-phrasing task sets over the same 91
reviewed items, with **correctly inverted gold answers** for the negated form, a polarity
validator, task hashes, provenance, and a distinct run label per ablation. It runs no GPU
inference and fabricates no results.

Ablation forms:
  1. positive   (abl_positive)  "Is there a clearly visible {obj} in the image? Answer yes or no."
  2. negative   (abl_negative)  "Is the {obj} absent from the image? Answer yes or no."   [gold inverts]
  3. pixel_only (abl_pixelonly) "Answer from visible pixels only, not scene context: is there a clearly visible {obj}?"
  4. short      (abl_short)     "Visible {obj}? yes/no."
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from certvic.hashing import stable_record_hash  # noqa: E402
from certvic.eval.presence_semantics import (  # noqa: E402
    invert_yes_no,
    item_positive_presence_gold,
    presence_question_polarity,
)
from certvic.io import read_jsonl, write_json, write_jsonl  # noqa: E402

RESULTS = REPO / "data/results/main_real_200"
REVIEWED = RESULTS / "pilot_eval_tasks_reviewed_v2.jsonl"
OUT_ROOT = RESULTS / "prompt_ablations"
EVIDENCE = "PROMPT_ABLATION_NON_EVIDENCE"

FORMS = {
    "positive": {"run_label": "abl_positive", "polarity": "positive",
                 "template": "Is there a clearly visible {obj} in the image? Answer yes or no."},
    "negative": {"run_label": "abl_negative", "polarity": "negative",
                 "template": "Is the {obj} absent from the image? Answer yes or no."},
    "pixel_only": {"run_label": "abl_pixelonly", "polarity": "positive",
                   "template": "Answer from visible pixels only, not scene context: "
                               "is there a clearly visible {obj}? Answer yes or no."},
    "short": {"run_label": "abl_short", "polarity": "positive",
              "template": "Visible {obj}? yes/no."},
}


def _invert(yn: str) -> str:
    return invert_yes_no(yn)


def expected_gold(polarity: str, base_gold: str) -> str:
    """Polarity validator core: negated phrasing inverts the presence (base) gold."""
    base = (base_gold or "").strip().lower()
    if polarity == "negative":
        return _invert(base)
    return base


def validate_task(task: dict) -> list[str]:
    errs = []
    want = expected_gold(task["polarity"], task["base_gold"])
    if task["gold_answer"] != want:
        errs.append(f"{task['run_label']}/{task['item_id']}/{task['image_variant']}: "
                    f"gold {task['gold_answer']!r} != expected {want!r} for polarity {task['polarity']}")
    if task["gold_answer"] not in {"yes", "no"}:
        errs.append(f"{task['run_label']}/{task['item_id']}: non yes/no gold {task['gold_answer']!r}")
    if task["polarity"] == "negative" and "absent" not in task["question"].lower():
        errs.append(f"{task['run_label']}/{task['item_id']}: negative polarity but no 'absent' in question")
    return errs


def _task(item: dict, form_name: str, cfg: dict, variant: str) -> dict:
    obj = item.get("question_object")
    source_question = item.get(f"question_{variant}")
    # ``base_gold`` is always the semantic answer to the positive-presence
    # question.  The reviewed source alternates wording, so copying its answer
    # directly would reverse 45/91 items in every uniform-prompt ablation.
    base_gold = item_positive_presence_gold(item, variant)
    gold = expected_gold(cfg["polarity"], base_gold)
    image_path = item.get("original_image_path") if variant == "original" else item.get("edited_image_path")
    rec = {
        "ablation_family": form_name, "run_label": cfg["run_label"], "polarity": cfg["polarity"],
        "item_id": item.get("item_id"), "edit_id": item.get("edit_id"),
        "source_id": item.get("source_id"), "edit_type": item.get("edit_type"),
        "target_object": obj, "image_variant": variant, "image_path": image_path,
        "question": cfg["template"].format(obj=obj), "answer_format": "yes_no",
        "base_gold": base_gold,          # the positive-form (presence) gold, for traceability
        "source_question_polarity": presence_question_polarity(source_question),
        "gold_answer": gold,             # the correct answer under THIS phrasing/polarity
        "evidence_status": EVIDENCE, "paper_evidence": False, "vlm_inference_run": False,
    }
    rec["task_hash"] = stable_record_hash({
        "item_id": rec["item_id"], "run_label": rec["run_label"],
        "image_variant": variant, "question": rec["question"], "gold_answer": gold,
    })
    return rec


def build(reviewed_path: Path = REVIEWED) -> dict:
    if not reviewed_path.exists():
        raise SystemExit(f"REFUSED: reviewed source tasks missing: {reviewed_path}")
    items = [it for it in read_jsonl(reviewed_path) if it.get("visual_review_status") == "approved"]
    if not items:
        raise SystemExit(f"REFUSED: no approved reviewed items in {reviewed_path}")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    families = {}
    all_errors: list[str] = []
    for form_name, cfg in FORMS.items():
        records = []
        for item in items:
            for variant in ("original", "edited"):
                t = _task(item, form_name, cfg, variant)
                all_errors.extend(validate_task(t))
                records.append(t)
        fam_dir = OUT_ROOT / form_name
        fam_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(fam_dir / "tasks.jsonl", records)
        summ = {
            "ablation_family": form_name, "run_label": cfg["run_label"], "polarity": cfg["polarity"],
            "template": cfg["template"], "n_tasks": len(records),
            "n_items": len(items), "variants_per_item": 2,
            "evidence_status": EVIDENCE, "paper_evidence": False,
            "tasks_path": str((fam_dir / "tasks.jsonl").relative_to(REPO)),
        }
        write_json(fam_dir / "summary.json", summ)
        families[form_name] = summ

    if all_errors:  # fail closed: never emit a manifest with wrong gold under polarity change
        raise SystemExit("POLARITY VALIDATION FAILED:\n" + "\n".join(all_errors[:20]))

    top = {
        "schema": "certvic.prompt_ablations.v1",
        "evidence_status": EVIDENCE, "paper_evidence": False,
        "source_reviewed_tasks": str(reviewed_path.relative_to(REPO)),
        "n_reviewed_items": len(items),
        "polarity_validation": "passed",
        "families": families,
        "note": "Distinct run labels per ablation; source labels are first normalized to "
                "positive-presence semantics, then negated-form gold is inverted and validated. "
                "Run later on Kaggle; not evidence.",
    }
    write_json(OUT_ROOT / "summary.json", top)
    return top


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed", default=str(REVIEWED))
    args = parser.parse_args(argv)
    top = build(Path(args.reviewed))
    print(json.dumps({"n_reviewed_items": top["n_reviewed_items"],
                      "polarity_validation": top["polarity_validation"],
                      "families": {k: v["n_tasks"] for k, v in top["families"].items()}},
                     sort_keys=True))


if __name__ == "__main__":
    main()
