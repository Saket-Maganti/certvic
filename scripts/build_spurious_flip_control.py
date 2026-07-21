"""Build a spurious-flip (specificity) control: CPU, mask-aware, no diffusion.

The intervention result says VLMs fail to update when a *meaningful* edit removes the
queried object. A reviewer will ask the dual question: do they flip their answer under
ANY edit? This control answers it. For images that clearly contain the object
(answer = "yes"), it makes an **irrelevant** local edit -- a gentle blur+jitter patch
placed in an OBJECT-FREE region (the object's mask pixels are left untouched) -- so the
correct answer is still "yes". A model that flips yes->no here is reacting to irrelevant
pixels; a model that stays "yes" shows the certified gap is specific to object-removing
edits. Feeds the existing `spurious_flip_rate <= 0.10` certification gate
(`certvic/metrics/certification_policy.py`).

Structured as no_change pairs (orig != edited pixels, but same gold answer) so it runs
through the existing VLM notebooks unchanged. Both arms re-encoded through the same JPEG
pipeline (no file-size detectability cue). CPU-only, ground-truth labels, no evidence claims.
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certvic.io import write_jsonl
from certvic.schema import TaskItem
from certvic.schema.edit import EditSpec
from certvic.schema.source import SourceImageRecord

# ADE20K-150 label ids (verified against the annotation PNGs), same objects as the intervention.
OBJECTS = {16: "table", 24: "sofa", 20: "chair", 21: "car"}
YES_NO = "Respond with exactly one token: yes or no."


def _task(item_id: str, obj: str) -> TaskItem:
    q = f"Is there a clearly visible {obj} in the image? {YES_NO}"
    src = SourceImageRecord(source_id=item_id, source_name="ADE20K", license_category="pointer_only")
    edit = EditSpec(edit_id=item_id, source_id=item_id, edit_type="control_irrelevant",
                    task_family="occlusion_safety", domain="household",
                    expected_effect="irrelevant edit in object-free region; answer must NOT change")
    return TaskItem(
        item_id=item_id, source=src, edit=edit,
        original_image_path=f"__CTRL__/orig/{item_id}.jpg",
        edited_image_path=f"__CTRL__/{item_id}.jpg",
        question_original=q, question_edited=q, answer_original="yes", answer_edited="yes",
        required_change="no_change", answer_format="yes_no",
        task_family="occlusion_safety", domain="household", split="train",
        metadata={"evidence_status": "HUMAN_REVIEW_PENDING",
                  "visual_review_status": "pending",
                  "control": "spurious_flip", "object": obj, "present": True},
    )


def _place_patch(mask: np.ndarray, rng: random.Random, frac: float = 0.09, tries: int = 60):
    """Find a box covering ~frac of the image area with minimal object overlap."""
    h, w = mask.shape
    ph, pw = max(16, int((h * w * frac) ** 0.5)), max(16, int((h * w * frac) ** 0.5))
    ph, pw = min(ph, h), min(pw, w)
    best, best_ov = None, 2.0
    for _ in range(tries):
        y = rng.randint(0, h - ph)
        x = rng.randint(0, w - pw)
        ov = float(mask[y:y + ph, x:x + pw].mean())
        if ov < best_ov:
            best, best_ov = (y, x, ph, pw), ov
        if ov == 0.0:
            break
    return best, best_ov


def _perturb(im: Image.Image, box, rng: random.Random) -> Image.Image:
    """Irrelevant edit inside `box` only: blur + mild brightness + light noise. Object untouched."""
    y, x, ph, pw = box
    arr = np.asarray(im).astype(np.float32).copy()
    patch = im.crop((x, y, x + pw, y + ph)).filter(ImageFilter.GaussianBlur(radius=5))
    p = np.asarray(patch).astype(np.float32)
    p *= rng.uniform(0.85, 1.15)                              # mild local brightness
    p += np.random.default_rng(rng.randint(0, 1 << 30)).normal(0, 10, p.shape)  # light non-semantic noise
    arr[y:y + ph, x:x + pw] = np.clip(p, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def build(ade_root: str, out_dir: str, split: str = "training", n_per: int = 24,
          area_thresh: float = 0.03, max_scan: int = 6000, jpeg_q: int = 90, seed: int = 0) -> dict:
    rng = random.Random(seed)
    img_dir = Path(ade_root) / "images" / split
    ann_dir = Path(ade_root) / "annotations" / split
    pools: dict[int, list[Path]] = {lid: [] for lid in OBJECTS}
    need = n_per * 4
    for img in sorted(img_dir.glob("*.jpg"))[:max_scan]:
        ann = ann_dir / (img.stem + ".png")
        if not ann.exists():
            continue
        arr = np.asarray(Image.open(ann))
        for lid in OBJECTS:
            if lid in arr and (arr == lid).sum() / arr.size >= area_thresh and len(pools[lid]) < need:
                pools[lid].append((img, ann))
        if all(len(pools[k]) >= need for k in OBJECTS):
            break

    out = Path(out_dir)
    (out / "orig").mkdir(parents=True, exist_ok=True)
    tasks: list[TaskItem] = []
    verify = {"obj_diff": [], "patch_diff": [], "obj_overlap": []}
    used: set[str] = set()
    for lid, obj in OBJECTS.items():
        picks = [pa for pa in pools[lid] if pa[0].stem not in used]
        rng.shuffle(picks)
        for img, ann in picks[:n_per]:
            used.add(img.stem)
            im = Image.open(img).convert("RGB")
            mask = (np.asarray(Image.open(ann)) == lid)
            if mask.shape != np.asarray(im).shape[:2]:
                im = im.resize((mask.shape[1], mask.shape[0]))
            box, ov = _place_patch(mask, rng)
            if box is None or ov > 0.02:        # need a genuinely object-free patch
                continue
            edited = _perturb(im, box, rng)
            iid = f"sflip_{obj}_{img.stem}"
            # re-encode BOTH arms identically (no file-size detectability cue)
            im.save(out / "orig" / f"{iid}.jpg", "JPEG", quality=jpeg_q, subsampling=2, optimize=True)
            edited.save(out / f"{iid}.jpg", "JPEG", quality=jpeg_q, subsampling=2, optimize=True)
            tasks.append(_task(iid, obj))
            o, e = np.asarray(im).astype(int), np.asarray(edited).astype(int)
            y, x, ph, pw = box
            verify["obj_diff"].append(float(np.abs(o - e)[mask].mean()) if mask.any() else 0.0)
            verify["patch_diff"].append(float(np.abs(o - e)[y:y + ph, x:x + pw].mean()))
            verify["obj_overlap"].append(ov)

    write_jsonl(str(out / "pilot_eval_tasks_reviewed.jsonl"),
                [json.loads(t.model_dump_json()) for t in tasks])
    n = len(tasks)
    return {
        "out_dir": out_dir, "split": split, "n_tasks": n,
        "by_object": dict(collections.Counter(t.metadata["object"] for t in tasks)),
        "mean_object_region_diff": round(float(np.mean(verify["obj_diff"])), 3) if n else None,
        "mean_patch_region_diff": round(float(np.mean(verify["patch_diff"])), 3) if n else None,
        "max_object_overlap": round(float(np.max(verify["obj_overlap"])), 4) if n else None,
        "tasks_path": str(out / "pilot_eval_tasks_reviewed.jsonl"),
        "evidence_claims_made": False,
    }


def main(argv: list[str] | None = None) -> None:
    repo = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description="Build spurious-flip (specificity) control")
    p.add_argument("--ade20k-root", default=str(repo / "ade20k_root/ADEChallengeData2016"))
    p.add_argument("--out-dir", default=str(repo / "data/edits/spurious_flip_control"))
    p.add_argument("--split", default="training", choices=["training", "validation"])
    p.add_argument("--n-per", type=int, default=24)
    args = p.parse_args(argv)
    print(json.dumps(build(args.ade20k_root, args.out_dir, split=args.split, n_per=args.n_per), sort_keys=True))


if __name__ == "__main__":
    main()
