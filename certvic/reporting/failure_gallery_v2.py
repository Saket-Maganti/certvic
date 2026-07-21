"""V2 failure gallery builder.

Classifies failures deterministically and emits a manifest, taxonomy summary,
markdown, and a local HTML gallery. No pixel copies by default, local links only,
prompts/raw outputs/parsed answers included, safe paper caption text, claim
eligibility and license/release mode recorded. No deployment/causal claims.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
from collections import Counter
from pathlib import Path

from certvic.io import read_jsonl
from certvic.reporting.failure_taxonomy import classify_failure


def _load_overrides(path: str | None) -> dict:
    if not path or not Path(path).exists():
        return {}
    out = {}
    for row in read_jsonl(path):
        if row.get("item_id") and row.get("label"):
            out[str(row["item_id"])] = str(row["label"])
    return out


def _safe_caption(entry: dict) -> str:
    return (
        f"{entry['primary'].replace('_', ' ')} on a {entry.get('task_family')} item "
        f"({entry.get('edit_type')} edit). Single-factor intervention; descriptive observation only, "
        f"no deployment or causal-understanding claim."
    )


def build_failure_gallery_v2(tasks_path: str, preds_path: str, scores_path: str, out_dir: str, overrides_path: str | None = None) -> dict:
    tasks = {str(t.get("item_id")): t for t in read_jsonl(tasks_path)} if Path(tasks_path).exists() else {}
    preds = read_jsonl(preds_path) if Path(preds_path).exists() else []
    scores = read_jsonl(scores_path) if Path(scores_path).exists() else []
    overrides = _load_overrides(overrides_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    pred_map: dict[tuple[str, str], dict] = {}
    for p in preds:
        pred_map[(str(p.get("item_id")), str(p.get("image_variant")))] = p

    gallery: list[dict] = []
    for score in scores:
        item_id = str(score.get("item_id"))
        task = tasks.get(item_id, {})
        edit_type = task.get("edit_type") or (task.get("edit", {}) or {}).get("edit_type", "")
        po = pred_map.get((item_id, "original"))
        pe = pred_map.get((item_id, "edited"))
        cls = classify_failure(score, po, pe, edit_type=edit_type, overrides=overrides)
        if not cls.get("is_failure"):
            continue
        entry = {
            "item_id": item_id,
            "primary": cls["primary"],
            "applicable": cls["applicable"],
            "task_family": score.get("task_family"),
            "domain": score.get("domain"),
            "edit_type": edit_type,
            "required_change": score.get("required_change"),
            "original_image_path": task.get("original_image_path"),
            "edited_image_path": task.get("edited_image_path"),
            "original_prompt": (po or {}).get("prompt"),
            "edited_prompt": (pe or {}).get("prompt"),
            "original_raw_output": (po or {}).get("raw_output"),
            "edited_raw_output": (pe or {}).get("raw_output"),
            "parsed_original": cls.get("parsed_original"),
            "parsed_edited": cls.get("parsed_edited"),
            "release_mode": task.get("release_mode") or (task.get("metadata", {}) or {}).get("release_mode", "recipe_only"),
            "license_category": (task.get("source", {}) or {}).get("license_category") or task.get("license_category", "unknown"),
            "claim_eligibility": "non_evidence_qualitative_example",
            "pixels_copied": False,
            "paper_caption": "",
        }
        entry["paper_caption"] = _safe_caption(entry)
        gallery.append(entry)

    write_jsonl_local(out / "failure_gallery.jsonl", gallery)

    counts = Counter(e["primary"] for e in gallery)
    with (out / "failure_taxonomy_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["failure_type", "count"])
        for label, count in counts.most_common():
            writer.writerow([label, count])

    # paper candidates: prefer the headline failure types
    headline = {"missed_required_change", "answer_inertia", "spurious_flip_on_control"}
    candidates = [e for e in gallery if e["primary"] in headline]
    write_jsonl_local(out / "paper_candidate_failures.jsonl", candidates)

    (out / "failure_gallery.md").write_text(_render_md(gallery, counts), encoding="utf-8")
    (out / "local_gallery.html").write_text(_render_html(gallery, out), encoding="utf-8")

    summary = {
        "tasks": tasks_path,
        "n_scores": len(scores),
        "n_failures": len(gallery),
        "by_type": dict(counts),
        "paper_candidates": len(candidates),
        "pixels_copied": False,
        "evidence_status": "QUALITATIVE_NON_EVIDENCE",
    }
    (out / "failure_gallery_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def write_jsonl_local(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _render_md(gallery: list[dict], counts: Counter) -> str:
    lines = ["# Failure Gallery (V2)", "", "Qualitative, non-evidence. No deployment or causal-understanding claims.", "", "## Counts", ""]
    for label, count in counts.most_common():
        lines.append(f"- {label}: {count}")
    lines += ["", "## Examples", ""]
    for e in gallery[:50]:
        lines.append(f"- `{e['item_id']}` [{e['primary']}] {e['task_family']}/{e['edit_type']}: "
                     f"orig='{e.get('original_raw_output')}' edited='{e.get('edited_raw_output')}'")
    return "\n".join(lines) + "\n"


def _render_html(gallery: list[dict], out: Path) -> str:
    def rel(p):
        if not p:
            return ""
        try:
            return os.path.relpath(p, out)
        except ValueError:
            return p

    cards = []
    for e in gallery[:100]:
        cards.append(
            f"<div class='card'><h3>{html.escape(e['item_id'])} <small>[{html.escape(e['primary'])}]</small></h3>"
            f"<div class='imgs'><img src='{html.escape(rel(e.get('original_image_path')))}'><img src='{html.escape(rel(e.get('edited_image_path')))}'></div>"
            f"<p>orig: {html.escape(str(e.get('original_raw_output')))} | edited: {html.escape(str(e.get('edited_raw_output')))}</p>"
            f"<p class='cap'>{html.escape(e['paper_caption'])}</p></div>"
        )
    return ("<!doctype html><meta charset='utf-8'><title>CertVIC Failure Gallery</title>"
            "<style>.card{border:1px solid #ccc;margin:1rem;padding:1rem}.imgs img{max-width:240px;margin-right:8px}.cap{color:#555}</style>"
            "<h1>CertVIC Failure Gallery (non-evidence)</h1>" + "".join(cards))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC V2 failure gallery")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--preds", required=True)
    parser.add_argument("--scores", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--overrides")
    args = parser.parse_args(argv)
    print(json.dumps(build_failure_gallery_v2(args.tasks, args.preds, args.scores, args.out_dir, overrides_path=args.overrides), sort_keys=True))


if __name__ == "__main__":
    main()
