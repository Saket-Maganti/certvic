"""Generate CPU-side mechanism-probe task manifests (V7 prompt 03).

The 3-model result is robust, but the *mechanism* is open: are models anchored by scene
context, by residual cues in the edited pixels, or by prompt priors? This script builds
probe task manifests over the **same 91 reviewed presence items**, to be run later on
Kaggle with the existing single-image VLM notebook style. It runs **no** GPU inference and
fabricates **no** results -- each task carries a scoring *spec*, not a score.

Probe families (each gets a distinct run label):
  1. object_list        (mech_objlist)   -- "list visible objects"; flag if target listed
  2. region_focused     (mech_region)    -- crop to the edited region; ask if target visible
  3. two_step           (mech_2step)     -- describe, then yes/no
  4. context_suppression(mech_ctxsupp)   -- "answer from pixels only, not scene context"
  5. original_vs_edited (mech_origvsedit)-- forced 2-image comparison; BLOCKED (single-image iface)

Every task traces to a reviewed item (item_id, edit_id, source_id, mask_id). Probes are
NOT evidence (evidence_status=MECHANISM_PROBE_NON_EVIDENCE).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from certvic.io import read_jsonl, write_json, write_jsonl  # noqa: E402
from certvic.eval.presence_semantics import (  # noqa: E402
    item_positive_presence_gold,
    presence_question_polarity,
)
RESULTS = REPO / "data/results/main_real_200"
REVIEWED = RESULTS / "pilot_eval_tasks_reviewed_v2.jsonl"
MASKS = RESULTS / "ade20k_masks.jsonl"
OUT_ROOT = RESULTS / "mechanism_probes"

EVIDENCE = "MECHANISM_PROBE_NON_EVIDENCE"

FAMILIES = {
    "object_list": {
        "run_label": "mech_objlist",
        "image": "edited",
        "answer_format": "object_list",
        "prompt": "List the clearly visible objects in this image. "
                  "Respond with a comma-separated list of object names only.",
        "flag_condition": "target_appears_in_list",
        "interpretation": "If the reviewed gold says the target is no longer clearly visible "
                          "but the model still lists it, that indicates context-anchoring or a residual cue.",
    },
    "region_focused": {
        "run_label": "mech_region",
        "image": "edited_crop",
        "answer_format": "yes_no",
        "prompt": "Looking only at this cropped region of an image, is there a clearly visible "
                  "{target}? Answer with exactly one token: yes or no.",
        "flag_condition": "model_says_yes",
        "interpretation": "A 'yes' inside the edited region (where the target was removed/occluded) "
                          "points to a residual visual cue rather than scene-context anchoring.",
    },
    "two_step": {
        "run_label": "mech_2step",
        "image": "edited",
        "answer_format": "describe_then_yes_no",
        "prompt": "First, briefly describe what you see in this image in one sentence. "
                  "Then answer: is there a clearly visible {target}? "
                  "Finish your reply with exactly one token on its own: yes or no.",
        "flag_condition": "final_token_yes",
        "interpretation": "Lets us separate the model's free description from its yes/no decision; "
                          "a confident description of the absent target signals anchoring.",
    },
    "context_suppression": {
        "run_label": "mech_ctxsupp",
        "image": "edited",
        "answer_format": "yes_no",
        "prompt": "Answer only from the visible pixels, not from scene context or what is usually "
                  "present in such scenes. Is there a clearly visible {target}? "
                  "Answer with exactly one token: yes or no.",
        "flag_condition": "model_says_yes",
        "interpretation": "If an explicit pixel-only instruction does not reduce the failure, "
                          "the effect is unlikely to be mere prompt framing.",
    },
}

ORIG_VS_EDITED_SPEC = {
    "run_label": "mech_origvsedit",
    "status": "blocked",
    "reason": "Forced original-vs-edited comparison needs a two-image prompt; the current free "
              "Kaggle VLM notebooks (and the registered providers' single-image eval path) accept "
              "one image per turn. Marked blocked rather than faked.",
    "planned_prompt": "Here are two images of the same scene (left=A, right=B). In which image, "
                      "if any, is there a clearly visible {target}? Answer A, B, both, or neither.",
    "interface_change_required": "Add a two-image (or side-by-side composite) input path to the "
                                 "VLM eval notebook + provider adapter, then re-generate this family.",
    "evidence_status": EVIDENCE,
    "paper_evidence": False,
}


def _bbox_lookup() -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for rec in read_jsonl(MASKS):
        mid = rec.get("mask_id")
        bbox = rec.get("bbox_xyxy")
        if mid and isinstance(bbox, list) and len(bbox) == 4:
            out[mid] = bbox
    return out


def _trace(item: dict) -> dict:
    return {
        "item_id": item.get("item_id"),
        "edit_id": item.get("edit_id"),
        "source_id": item.get("source_id"),
        "mask_id": item.get("mask_id"),
        "edit_type": item.get("edit_type"),
        "task_family": item.get("task_family"),
    }


def _base_record(item: dict, family: str, cfg: dict) -> dict:
    target = item.get("question_object")
    # Every mechanism prompt uses positive target-visibility semantics.  The
    # reviewed source alternates positive/negative wording, so its edited answer
    # must be normalized before it can be reused here.
    gold = item_positive_presence_gold(item, "edited")
    rec = {
        "probe_family": family,
        "run_label": cfg["run_label"],
        **_trace(item),
        "target_object": target,
        "image_role": cfg["image"],
        "original_image_path": item.get("original_image_path"),
        "edited_image_path": item.get("edited_image_path"),
        "edited_sha256": item.get("edited_sha256"),
        "prompt": cfg["prompt"].format(target=target),
        "answer_format": cfg["answer_format"],
        "scoring": {
            "gold_post_edit_answer": gold,
            "gold_semantics": "positive_target_visibility",
            "source_question_polarity": presence_question_polarity(item.get("question_edited")),
            "flag_condition": cfg["flag_condition"],
            "mechanism_interpretation": cfg["interpretation"],
            "note": "Scoring spec only -- no result is recorded here.",
        },
        "evidence_status": EVIDENCE,
        "paper_evidence": False,
        "vlm_inference_run": False,
    }
    return rec


def build(reviewed_path: Path = REVIEWED) -> dict:
    if not reviewed_path.exists():
        raise SystemExit(f"REFUSED: reviewed source tasks missing: {reviewed_path}")
    items = read_jsonl(reviewed_path)
    items = [it for it in items if it.get("visual_review_status") == "approved"]
    if not items:
        raise SystemExit(f"REFUSED: no approved reviewed items in {reviewed_path}")

    bboxes = _bbox_lookup()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    family_summaries: dict[str, dict] = {}

    for family, cfg in FAMILIES.items():
        records = []
        for item in items:
            rec = _base_record(item, family, cfg)
            if family == "region_focused":
                bbox = bboxes.get(item.get("mask_id"))
                if bbox:
                    rec["crop_spec"] = {"bbox_xyxy": bbox, "margin_frac": 0.15,
                                        "applies_to": "edited_image_path"}
                    rec["crop_status"] = "bbox_available"
                else:
                    rec["crop_spec"] = None
                    rec["crop_status"] = "no_bbox"  # cannot build region crop for this item
            records.append(rec)
        fam_dir = OUT_ROOT / family
        fam_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(fam_dir / "tasks.jsonl", records)
        summ = {
            "probe_family": family, "run_label": cfg["run_label"],
            "n_tasks": len(records),
            "image_role": cfg["image"], "answer_format": cfg["answer_format"],
            "prompt_template": cfg["prompt"], "flag_condition": cfg["flag_condition"],
            "mechanism_interpretation": cfg["interpretation"],
            "evidence_status": EVIDENCE, "paper_evidence": False,
            "tasks_path": str((fam_dir / "tasks.jsonl").relative_to(REPO)),
        }
        if family == "region_focused":
            summ["n_with_bbox"] = sum(1 for r in records if r.get("crop_status") == "bbox_available")
            summ["n_without_bbox"] = sum(1 for r in records if r.get("crop_status") == "no_bbox")
        write_json(fam_dir / "summary.json", summ)
        family_summaries[family] = summ

    # Blocked forced-comparison family: spec only, no runnable tasks.
    blocked_dir = OUT_ROOT / "original_vs_edited"
    blocked_dir.mkdir(parents=True, exist_ok=True)
    write_json(blocked_dir / "SPEC_BLOCKED.json", ORIG_VS_EDITED_SPEC)
    family_summaries["original_vs_edited"] = {**ORIG_VS_EDITED_SPEC, "n_tasks": 0}

    top = {
        "schema": "certvic.mechanism_probes.v1",
        "evidence_status": EVIDENCE, "paper_evidence": False,
        "source_reviewed_tasks": str(reviewed_path.relative_to(REPO)),
        "n_reviewed_items": len(items),
        "families": family_summaries,
        "note": "Mechanism probes are not evidence. Run later on Kaggle; see "
                "notebooks/kaggle/07_mechanism_probes.md.",
    }
    write_json(OUT_ROOT / "summary.json", top)
    return top


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed", default=str(REVIEWED))
    args = parser.parse_args(argv)
    top = build(Path(args.reviewed))
    print(json.dumps({"n_reviewed_items": top["n_reviewed_items"],
                      "families": {k: v.get("n_tasks") for k, v in top["families"].items()}},
                     sort_keys=True))


if __name__ == "__main__":
    main()
