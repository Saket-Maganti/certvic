"""Ingest a Kaggle diffusion-results zip and composite edits to true single-factor.

The Kaggle inpaint pipeline runs the whole image through the VAE (encode/resize/
decode), so generated edits change pixels OUTSIDE the target mask and fail the
single-factor quality gate (outside_mask_change ~0.45 vs limit 0.02). This script
rebuilds each edit locally by compositing the inpainted pixels INSIDE the object
mask onto the pristine original — recovering a clean single-factor edit with NO GPU
re-run — then recomputes the quality gate and writes a corrected generated-edits
manifest with local paths. CPU-only; no downloads; rows stay GENERATED_EDIT_ONLY.
"""

from __future__ import annotations

import argparse
import glob
import json
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

from PIL import Image

from certvic.edit.generate_edits import _load_mask_for_plan
from certvic.edit.quality_gates import evaluate_edit_quality
from certvic.hashing import sha256_file
from certvic.io import read_jsonl, write_json, write_jsonl

try:  # PIL>=9.1
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:  # older PIL
    RESAMPLE = Image.LANCZOS


def _extract(results_zip: str, workdir: Path) -> Path:
    with zipfile.ZipFile(results_zip) as z:
        z.extractall(workdir)
    for nested in glob.glob(f"{workdir}/**/diffusion_out.zip", recursive=True):
        with zipfile.ZipFile(nested) as z:
            z.extractall(workdir)
    hits = glob.glob(f"{workdir}/**/pilot_generated_edits.jsonl", recursive=True)
    if not hits:
        raise FileNotFoundError("pilot_generated_edits.jsonl not found inside the results zip")
    return Path(hits[0])


def _detect_baked_root(plans: list[dict]) -> str | None:
    for p in plans:
        ip = p.get("image_path")
        if ip and "/images/" in ip:
            return ip.split("/images/")[0]
    return None


def ingest(
    results_zip: str,
    ade20k_root: str,
    edit_plan_path: str,
    out_manifest: str,
    edits_dir: str,
    rejected_out: str,
    summary_out: str,
    jpeg_quality: int = 90,
    task_preview_path: str | None = None,
) -> dict:
    work = Path(tempfile.mkdtemp(prefix="cv_ingest_"))
    manifest_path = _extract(results_zip, work)
    manifest = read_jsonl(str(manifest_path))
    plans = {str(p.get("edit_id")): p for p in read_jsonl(edit_plan_path)}
    baked = _detect_baked_root(list(plans.values()))
    out_edits = Path(edits_dir)
    out_edits.mkdir(parents=True, exist_ok=True)

    corrected: list[dict] = []
    rejected: list[dict] = []
    for row in manifest:
        eid = str(row.get("edit_id"))
        plan = dict(plans.get(eid, {}))
        for k in ("image_path", "mask_path", "original_image_path", "annotation_path"):
            if plan.get(k) and baked:
                plan[k] = plan[k].replace(baked, ade20k_root)
        png = next(iter(glob.glob(f"{work}/**/{eid}.png", recursive=True)), None)
        try:
            if png is None:
                raise FileNotFoundError(f"edited png for {eid} not found in zip")
            orig_path = plan.get("image_path")
            if not orig_path or not Path(orig_path).exists():
                raise FileNotFoundError(f"original image not found: {orig_path}")
            orig = Image.open(orig_path).convert("RGB")
            edited = Image.open(png).convert("RGB")
            if edited.size != orig.size:
                edited = edited.resize(orig.size, RESAMPLE)
            mask, _info = _load_mask_for_plan(plan, orig.size)
            mask_img = Image.fromarray((mask.astype("uint8") * 255))  # 'L' inferred
            composite = Image.composite(edited, orig, mask_img)       # inside mask -> edited, else original
            # Re-encode BOTH arms through the identical JPEG pipeline. Outside the mask both
            # are the same encoder applied to the same pixels -> byte-identical (quality gate
            # passes), and file_size/compression no longer separates them (detectability clean).
            ext = Path(orig_path).suffix.lower()
            if ext in (".jpg", ".jpeg"):
                ref_dir = out_edits / "orig"
                ref_dir.mkdir(parents=True, exist_ok=True)
                ref_path = ref_dir / f"{eid}.jpg"
                orig.save(ref_path, format="JPEG", quality=jpeg_quality, subsampling=2, optimize=True)
                out_png = out_edits / f"{eid}.jpg"
                composite.save(out_png, format="JPEG", quality=jpeg_quality, subsampling=2, optimize=True)
                ref = str(ref_path)
            else:
                out_png = out_edits / f"{eid}.png"
                composite.save(out_png)
                ref = orig_path
            quality = evaluate_edit_quality(
                ref, str(out_png), mask,
                edit_type=str(row.get("edit_type")),
                planned_params=plan.get("planned_params") or {},
                actual_params=row.get("actual_params") or {},
            )
            new = dict(row)
            new.update({
                "original_image_path": ref,
                "edited_image_path": str(out_png),
                "edited_sha256": sha256_file(str(out_png)),
                "quality": quality,
                "quality_gate_status": quality["quality_gate_status"],
                "postprocess": "composited_single_factor",
                "generation_status": "generated",
                "evidence_status": "GENERATED_EDIT_ONLY",
            })
            corrected.append(new)
        except Exception as exc:
            rejected.append({"edit_id": eid, "rejection_reason": f"{type(exc).__name__}: {exc}",
                             "evidence_status": "GENERATED_EDIT_ONLY"})

    write_jsonl(out_manifest, corrected)
    write_jsonl(rejected_out, rejected)

    # Point the task preview's originals at the re-encoded copies so the eval / detectability
    # compare like-with-like (both arms identical JPEG pipeline).
    preview_updated = 0
    if task_preview_path and Path(task_preview_path).exists():
        ref_by_id = {str(r.get("edit_id")): r["original_image_path"] for r in corrected}
        preview = read_jsonl(task_preview_path)
        for row in preview:
            rid = str(row.get("edit_id"))
            if rid in ref_by_id and row.get("original_image_path") != ref_by_id[rid]:
                row["original_image_path"] = ref_by_id[rid]
                preview_updated += 1
        write_jsonl(task_preview_path, preview)

    summary = {
        "results_zip": results_zip,
        "ade20k_root": ade20k_root,
        "input_edits": len(manifest),
        "composited": len(corrected),
        "rejected": len(rejected),
        "quality_passed": sum(1 for r in corrected if r.get("quality_gate_status") == "pass"),
        "quality_failed": sum(1 for r in corrected if r.get("quality_gate_status") != "pass"),
        "by_edit_type_pass": dict(sorted(Counter(
            r.get("edit_type") for r in corrected if r.get("quality_gate_status") == "pass").items())),
        "by_edit_type_fail": dict(sorted(Counter(
            r.get("edit_type") for r in corrected if r.get("quality_gate_status") != "pass").items())),
        "out_manifest": out_manifest,
        "edits_dir": edits_dir,
        "task_preview_updated": preview_updated,
        "postprocess": "composited_single_factor",
        "evidence_status": "GENERATED_EDIT_ONLY",
        "evidence_claims_made": False,
    }
    write_json(summary_out, summary)
    return summary


def main(argv: list[str] | None = None) -> None:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Composite Kaggle diffusion edits to single-factor and recompute quality")
    parser.add_argument("--results-zip", required=True)
    parser.add_argument("--ade20k-root", default=str(repo / "ade20k_root" / "ADEChallengeData2016"))
    parser.add_argument("--edit-plan", default=str(repo / "data/results/main_real_200/pilot_edit_plan.jsonl"))
    parser.add_argument("--out-manifest", default=str(repo / "data/results/main_real_200/pilot_generated_edits.jsonl"))
    parser.add_argument("--edits-dir", default=str(repo / "data/edits/main_real_200"))
    parser.add_argument("--rejected-out", default=str(repo / "data/results/main_real_200/pilot_generated_rejected.jsonl"))
    parser.add_argument("--summary-out", default=str(repo / "data/results/main_real_200/ingest_summary.json"))
    parser.add_argument("--jpeg-quality", type=int, default=90)
    parser.add_argument("--task-preview", default=str(repo / "data/results/main_real_200/pilot_task_preview.jsonl"))
    args = parser.parse_args(argv)
    summary = ingest(args.results_zip, args.ade20k_root, args.edit_plan, args.out_manifest,
                     args.edits_dir, args.rejected_out, args.summary_out, jpeg_quality=args.jpeg_quality,
                     task_preview_path=args.task_preview)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
