"""Build an absent-object perception control (CPU, ground-truth labels, no edits).

Disentangles "VLM sees but fails to update" from "VLM answers the question's
presupposition without looking". For each object used in the pilot (table/sofa/
chair/car) it samples ADE20K images that DO and DO NOT contain that object
(from the semantic annotations), and asks the same objective question
("Is there a clearly visible {obj}?") with ground-truth yes/no. If a model says
"yes" on absent images, it is presupposition-driven, not grounded.

Structured as no_change pairs (original == edited image) so it runs through the
existing VLM notebook unchanged; perception accuracy is read from the original
answer, split by present/absent. CPU-only, no evidence claims.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certvic.io import write_jsonl
from certvic.schema import TaskItem
from certvic.schema.edit import EditSpec
from certvic.schema.source import SourceImageRecord

OBJECTS = {16: "table", 24: "sofa", 20: "chair", 21: "car"}
# Extended set for the scaled control (verified ADE20K-150 ids): + bed/door/painting/plant.
OBJECTS_EXT = {**OBJECTS, 8: "bed", 15: "door", 23: "painting", 18: "plant"}
YES_NO = "Respond with exactly one token: yes or no."


def _task(item_id: str, img_rel: str, obj: str, present: bool, ade_split: str = "training") -> TaskItem:
    ans = "yes" if present else "no"
    q = f"Is there a clearly visible {obj} in the image? {YES_NO}"
    src = SourceImageRecord(source_id=item_id, source_name="ADE20K", license_category="pointer_only")
    edit = EditSpec(edit_id=item_id, source_id=item_id, edit_type="control_irrelevant",
                    task_family="occlusion_safety", domain="household",
                    expected_effect="absent-object perception control")
    return TaskItem(
        item_id=item_id, source=src, edit=edit,
        original_image_path=f"{img_rel}/orig/{item_id}.jpg",
        edited_image_path=f"{img_rel}/{item_id}.jpg",
        question_original=q, question_edited=q, answer_original=ans, answer_edited=ans,
        required_change="no_change", answer_format="yes_no",
        task_family="occlusion_safety", domain="household", split="train",
        metadata={"evidence_status": "HUMAN_REVIEWED_NON_EVIDENCE",
                  "control": "absent_object_perception", "present": present, "object": obj,
                  "ade_split": ade_split},
    )


def build(ade_root: str, out_dir: str, n_per: int = 15, area_thresh: float = 0.02,
          max_scan: int = 4000, jpeg_q: int = 90, seed: int = 0,
          split: str = "training", objects: dict[int, str] | None = None) -> dict:
    objects = objects or OBJECTS
    rng = random.Random(seed)
    img_dir = Path(ade_root) / "images" / split
    ann_dir = Path(ade_root) / "annotations" / split
    present: dict[int, list[Path]] = {lid: [] for lid in objects}
    absent: dict[int, list[Path]] = {lid: [] for lid in objects}
    need = n_per * 6  # collect a surplus, then sample
    for img in sorted(img_dir.glob("*.jpg"))[:max_scan]:
        ann = ann_dir / (img.stem + ".png")
        if not ann.exists():
            continue
        arr = np.asarray(Image.open(ann))
        labels = set(int(v) for v in np.unique(arr))
        for lid in objects:
            if lid in labels:
                if (arr == lid).sum() / arr.size >= area_thresh and len(present[lid]) < need:
                    present[lid].append(img)
            elif len(absent[lid]) < need:
                absent[lid].append(img)
        if all(len(present[k]) >= need and len(absent[k]) >= need for k in objects):
            break

    out = Path(out_dir)
    (out / "orig").mkdir(parents=True, exist_ok=True)
    tasks: list[TaskItem] = []
    used: set[str] = set()
    for lid, obj in objects.items():
        for pool, is_present in ((present[lid], True), (absent[lid], False)):
            picks = [p for p in pool if p.stem not in used]
            rng.shuffle(picks)
            for img in picks[:n_per]:
                used.add(img.stem)
                iid = f"ctrl_{obj}_{'pos' if is_present else 'neg'}_{img.stem}"
                im = Image.open(img).convert("RGB")
                im.save(out / f"{iid}.jpg", "JPEG", quality=jpeg_q, subsampling=2, optimize=True)
                im.save(out / "orig" / f"{iid}.jpg", "JPEG", quality=jpeg_q, subsampling=2, optimize=True)
                tasks.append(_task(iid, "__CTRL__", obj, is_present, ade_split=split))

    tasks_path = out / "pilot_eval_tasks_reviewed.jsonl"
    write_jsonl(str(tasks_path), [json.loads(t.model_dump_json()) for t in tasks])
    import collections
    return {
        "out_dir": out_dir,
        "split": split,
        "n_tasks": len(tasks),
        "by_object": dict(collections.Counter(t.metadata["object"] for t in tasks)),
        "present": sum(1 for t in tasks if t.metadata["present"]),
        "absent": sum(1 for t in tasks if not t.metadata["present"]),
        "tasks_path": str(tasks_path),
        "evidence_claims_made": False,
    }


def main(argv: list[str] | None = None) -> None:
    repo = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description="Build absent-object perception control")
    p.add_argument("--ade20k-root", default=str(repo / "ade20k_root/ADEChallengeData2016"))
    p.add_argument("--out-dir", default=str(repo / "data/edits/absent_object_control"))
    p.add_argument("--n-per", type=int, default=15)
    p.add_argument("--split", default="training", choices=["training", "validation"])
    p.add_argument("--objects", default="core", choices=["core", "ext"])
    args = p.parse_args(argv)
    objects = OBJECTS_EXT if args.objects == "ext" else OBJECTS
    print(json.dumps(build(args.ade20k_root, args.out_dir, n_per=args.n_per,
                           split=args.split, objects=objects), sort_keys=True))


if __name__ == "__main__":
    main()
