"""Build a qualitative failure taxonomy + gallery from the 3-model canonical results (V7 prompt 10).

Categorizes the 91 reviewed presence items by the per-model update behavior (computed from the
canonical raw predictions only), then selects a small, deterministic set of examples per
category with full provenance. References image paths + sha256 -- it does NOT duplicate image
pixels. Recorded selection criteria per category (no hand-picking). Makes no evidence claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from certvic.io import read_jsonl, write_json  # noqa: E402

RESULTS = REPO / "data/results/main_real_200"
REVIEWED = RESULTS / "pilot_eval_tasks_reviewed_v2.jsonl"
OUT_DIR = RESULTS / "failure_gallery"
K_PER_CATEGORY = 3

PRED_FILES = {
    "qwen2_5_vl_7b": "raw_predictions/presence__pred_qwen2_5_vl_7b_merged.jsonl",
    "internvl_8b": "raw_predictions__internvl_8b/presence__pred_internvl_8b_presence_merged.jsonl",
    "llava_onevision_7b": "raw_predictions__llava_onevision_7b/presence__pred_llava_onevision_7b_presence_merged.jsonl",
}
REPORT_DIRS = {
    "qwen2_5_vl_7b": "pilot_report",
    "internvl_8b": "pilot_report__internvl_8b",
    "llava_onevision_7b": "pilot_report__llava_onevision_7b",
}
PROVIDERS = list(PRED_FILES)


def _presence_provenance_sha() -> dict[str, str | None]:
    out = {}
    for prov, rdir in REPORT_DIRS.items():
        try:
            d = json.loads((RESULTS / rdir / "pilot_result.json").read_text())
            ing = {i["arm"]: i for i in d.get("provenance", {}).get("ingested", [])}
            out[prov] = ing.get("presence", {}).get("sha256")
        except (OSError, json.JSONDecodeError, KeyError):
            out[prov] = None
    return out


def _per_model_answers() -> dict[str, dict[str, dict[str, str | None]]]:
    """provider -> item_id -> {'original':ans, 'edited':ans}."""
    out: dict[str, dict[str, dict[str, str | None]]] = {}
    for prov, rel in PRED_FILES.items():
        m: dict[str, dict[str, str | None]] = {}
        for r in read_jsonl(RESULTS / rel):
            m.setdefault(r["item_id"], {})[r.get("image_variant")] = r.get("parsed_answer")
        out[prov] = m
    return out


def _item_view(item: dict, ans: dict, sha: dict) -> dict:
    iid = item["item_id"]
    gold_edited = (item.get("answer_edited") or "").strip().lower()
    gold_original = (item.get("answer_original") or "").strip().lower()
    per_model = {}
    for prov in PROVIDERS:
        a = ans[prov].get(iid, {})
        op, ep = a.get("original"), a.get("edited")
        per_model[prov] = {
            "original_pred": op, "edited_pred": ep,
            "edited_correct": (ep == gold_edited),
            "updated": (op is not None and ep is not None and op != ep),
            "presence_pred_sha256": sha.get(prov),
        }
    fail_count = sum(1 for p in per_model.values() if not p["edited_correct"])
    update_count = sum(1 for p in per_model.values() if p["updated"])
    correct_count = 3 - fail_count
    return {
        "item_id": iid, "edit_id": item.get("edit_id"), "source_id": item.get("source_id"),
        "target_object": item.get("question_object"), "edit_type": item.get("edit_type"),
        "task_family": item.get("task_family"),
        "question": item.get("question_edited"),
        "expected_original_answer": gold_original, "expected_edited_answer": gold_edited,
        "original_image_path": item.get("original_image_path"),
        "edited_image_path": item.get("edited_image_path"),
        "edited_sha256": item.get("edited_sha256"),
        "visual_review_status": item.get("visual_review_status"),
        "quality_gate_status": item.get("quality_gate_status"),
        "model_answers": per_model,
        "model_fail_count": fail_count, "model_update_count": update_count,
        "model_correct_count": correct_count,
    }


CATEGORIES = {
    "all_model_failure": {
        "criteria": "all 3 models post-edit-incorrect (edited_correct=False)",
        "pred": lambda v: v["model_fail_count"] == 3,
    },
    "full_non_update_after_removal": {
        "criteria": "edit_type=remove AND all 3 models kept their original answer (no update)",
        "pred": lambda v: v["edit_type"] == "remove" and v["model_update_count"] == 0,
    },
    "partial_update_single_model": {
        "criteria": "exactly 1 of 3 models post-edit-correct, other 2 fail",
        "pred": lambda v: v["model_correct_count"] == 1,
    },
    "llava_only_update": {
        "criteria": "llava_onevision_7b post-edit-correct AND qwen & internvl both fail",
        "pred": lambda v: (v["model_answers"]["llava_onevision_7b"]["edited_correct"]
                           and not v["model_answers"]["qwen2_5_vl_7b"]["edited_correct"]
                           and not v["model_answers"]["internvl_8b"]["edited_correct"]),
    },
    "natural_absence_success_vs_edited_failure": {
        "criteria": "edit_type=remove, gold edited='no', >=2 models fail on edited absence "
                    "(contrast with absent-object control success rates)",
        "pred": lambda v: v["edit_type"] == "remove" and v["expected_edited_answer"] == "no"
                          and v["model_fail_count"] >= 2,
    },
    "residual_cue_candidate_uncertain": {
        "criteria": "models DISAGREE (model_fail_count in {1,2}) -> candidate for residual-cue "
                    "review; NOT an asserted residual cue (no human label yet)",
        "pred": lambda v: v["model_fail_count"] in {1, 2},
    },
}


def build(reviewed_path: Path = REVIEWED) -> dict:
    if not reviewed_path.exists():
        raise SystemExit(f"REFUSED: reviewed source tasks missing: {reviewed_path}")
    items = [it for it in read_jsonl(reviewed_path) if it.get("visual_review_status") == "approved"]
    if not items:
        raise SystemExit(f"REFUSED: no approved reviewed items in {reviewed_path}")

    ans = _per_model_answers()
    sha = _presence_provenance_sha()
    views = sorted((_item_view(it, ans, sha) for it in items), key=lambda v: v["item_id"])

    gallery = {}
    counts = {}
    for cat, cfg in CATEGORIES.items():
        matching = [v for v in views if cfg["pred"](v)]
        counts[cat] = len(matching)
        # deterministic selection: lowest item_id first (criteria recorded, no hand-picking)
        gallery[cat] = {
            "selection_criteria": cfg["criteria"],
            "selection_rule": f"deterministic: items matching criteria, sorted by item_id, first {K_PER_CATEGORY}",
            "n_matching": len(matching),
            "examples": matching[:K_PER_CATEGORY],
        }

    # prompt-polarity-sensitive: requires ablation predictions (not run) -> pending, no entries.
    gallery["prompt_polarity_sensitive"] = {
        "selection_criteria": "items whose verdict flips across abl_positive/abl_negative/abl_pixelonly/abl_short",
        "selection_rule": "pending: requires prompt-ablation predictions (see prompt 08); none yet",
        "n_matching": 0, "examples": [], "status": "pending_ablation_predictions",
    }

    top = {
        "schema": "certvic.failure_gallery.v1",
        "evidence_status": "QUALITATIVE_GALLERY_NON_EVIDENCE", "paper_evidence": False,
        "source_reviewed_tasks": str(reviewed_path.relative_to(REPO)),
        "n_reviewed_items": len(items),
        "absent_object_control_context": _control_context(),
        "taxonomy_counts": counts,
        "k_per_category": K_PER_CATEGORY,
        "categories": gallery,
        "note": "Examples reference image paths + sha256; pixels are not duplicated. All items are "
                "human-approved. Model answers come only from canonical raw predictions.",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUT_DIR / "gallery.json", top)
    (REPO / "docs/MAIN200_FAILURE_TAXONOMY.md").write_text(_doc_md(top), encoding="utf-8")
    return top


def _control_context() -> dict:
    out = {}
    for prov, rdir in REPORT_DIRS.items():
        try:
            c = json.loads((RESULTS / rdir / "pilot_result.json").read_text())["absent_object_control"]
            out[prov] = {"absent": f"{c['absent_correct']}/{c['absent_n']}",
                         "present": f"{c['present_correct']}/{c['present_n']}"}
        except (OSError, json.JSONDecodeError, KeyError):
            out[prov] = None
    return out


def _doc_md(top: dict) -> str:
    L: list[str] = []
    P = L.append
    P("# Main-200 Failure Taxonomy & Qualitative Gallery")
    P("")
    P("**Qualitative, NOT evidence** (`evidence_status = QUALITATIVE_GALLERY_NON_EVIDENCE`). Built "
      "from canonical raw predictions over the 91 human-approved presence items. Examples "
      "reference image paths + sha256 (pixels not duplicated); machine-readable in "
      "`data/results/main_real_200/failure_gallery/gallery.json`.")
    P("")
    P("## Taxonomy counts (of 91)")
    P("")
    P("| category | n matching |")
    P("|---|---|")
    for cat, n in top["taxonomy_counts"].items():
        P(f"| {cat} | {n} |")
    P("| prompt_polarity_sensitive | pending (needs ablation predictions) |")
    P("")
    P("## Natural-absence vs edited-absence (the headline dissociation)")
    P("")
    P("Absent-object control (natural absence, no edits) vs the edited-absence failures below:")
    P("")
    P("| model | control absent | control present |")
    P("|---|---|---|")
    for prov, c in top["absent_object_control_context"].items():
        if c:
            P(f"| `{prov}` | {c['absent']} | {c['present']} |")
    P("")
    P("Models are near-perfect at *natural* absence yet frequently fail to revise after a "
      "controlled *edited* removal — that contrast is the qualitative core.")
    P("")
    P("## Example categories")
    P("")
    for cat, blk in top["categories"].items():
        P(f"### {cat}")
        P("")
        P(f"- Criteria: {blk['selection_criteria']}")
        P(f"- Selection: {blk['selection_rule']} · matching: {blk['n_matching']}")
        for ex in blk["examples"]:
            ma = ex["model_answers"]
            ans = ", ".join(f"{p.split('_')[0]}:{ma[p]['edited_pred']}" for p in ma)
            P(f"  - `{ex['item_id']}` ({ex['edit_type']}, target={ex['target_object']}): "
              f"expected edited={ex['expected_edited_answer']}; edited answers [{ans}]; "
              f"sha256=`{(ex['edited_sha256'] or '')[:12]}`")
        P("")
    P("## Hard rules honored")
    P("")
    P("- Only human-approved items; only canonical raw predictions for model answers.")
    P("- Deterministic selection (recorded criteria); no hand-picking.")
    P("- No image pixels duplicated (paths + hashes only).")
    P("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed", default=str(REVIEWED))
    args = parser.parse_args(argv)
    top = build(Path(args.reviewed))
    print(json.dumps({"n_reviewed_items": top["n_reviewed_items"],
                      "taxonomy_counts": top["taxonomy_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
