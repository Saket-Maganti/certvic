"""Canonical offline COCO 2017 feasibility adapter.

The implementation supports local COCO instance JSON, polygon masks, deterministic
task construction, explicit licensing gates, and pointer-only manifests. It never
downloads or redistributes pixels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.task_schema import convert_legacy_task, require_task_matrix, with_task_hash


class COCOAdapterNotReady(RuntimeError):
    """Raised when required local COCO bytes are absent or unsupported."""


COCO_TO_CERTVIC_VOCAB = {
    "chair": "chair",
    "couch": "sofa",
    "car": "car",
    "dining table": "table",
}


def adapter_summary() -> dict[str, Any]:
    return {
        "dataset": "COCO 2017 instances val2017",
        "status": "FULL_OFFLINE_FEASIBILITY_ADAPTER",
        "primary": False,
        "recommended_second_domain": True,
        "pointer_only": True,
        "downloads_attempted": False,
        "overlapping_classes": sorted(COCO_TO_CERTVIC_VOCAB),
        "supported_segmentation": ["polygon", "uncompressed_rle"],
        "license_risks": [
            "annotations are CC-BY 4.0; image pixels retain varied Flickr licenses",
            "image license eligibility must be verified per row before final selection",
            "never place COCO pixels in the release package",
        ],
    }


def coco_category_overlap() -> dict[str, str]:
    return dict(COCO_TO_CERTVIC_VOCAB)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_coco_instances(root: str | Path) -> dict[str, Any]:
    """Load and validate local COCO val2017 annotations without network access."""
    root = Path(root)
    annotation_path = root / "annotations" / "instances_val2017.json"
    image_root = root / "val2017"
    if not annotation_path.is_file():
        raise COCOAdapterNotReady(
            f"COCO instances not found at {annotation_path}; this adapter will not download. "
            "Provide a local COCO 2017 val2017 tree."
        )
    if not image_root.is_dir():
        raise COCOAdapterNotReady(
            f"COCO val2017 images not found at {image_root}; this adapter will not download."
        )
    payload = json.loads(annotation_path.read_text(encoding="utf-8"))
    for key in ("images", "annotations", "categories"):
        if not isinstance(payload.get(key), list):
            raise COCOAdapterNotReady(f"COCO annotation JSON has no {key} list")
    images = {int(row["id"]): row for row in payload["images"]}
    categories = {int(row["id"]): row for row in payload["categories"]}
    annotations_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for annotation in payload["annotations"]:
        image_id, category_id = int(annotation["image_id"]), int(annotation["category_id"])
        if image_id not in images or category_id not in categories:
            raise COCOAdapterNotReady("COCO annotations reference unknown image/category IDs")
        annotations_by_image[image_id].append(annotation)
    licenses = {int(row["id"]): row for row in payload.get("licenses", [])}
    return {
        "root": str(root),
        "annotation_path": str(annotation_path),
        "annotation_sha256": _sha(annotation_path),
        "image_root": str(image_root),
        "images": images,
        "categories": categories,
        "annotations_by_image": dict(annotations_by_image),
        "licenses": licenses,
        "downloads_attempted": False,
    }


def _decode_uncompressed_rle(counts: list[int], size: list[int]) -> Image.Image:
    height, width = int(size[0]), int(size[1])
    flat: list[int] = []
    value = 0
    for run in counts:
        flat.extend([value] * int(run))
        value = 1 - value
    if len(flat) != width * height:
        raise COCOAdapterNotReady("invalid uncompressed COCO RLE length")
    # COCO RLE is column major.
    mask = Image.new("L", (width, height), 0)
    pixels = mask.load()
    for index, bit in enumerate(flat):
        if bit:
            y, x = divmod(index, height)
            pixels[y, x] = 255
    return mask


def annotation_mask(annotation: dict[str, Any], size: tuple[int, int]) -> Image.Image:
    segmentation = annotation.get("segmentation")
    if isinstance(segmentation, list):
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        for polygon in segmentation:
            if not isinstance(polygon, list) or len(polygon) < 6 or len(polygon) % 2:
                raise COCOAdapterNotReady("invalid polygon segmentation")
            draw.polygon(list(zip(polygon[0::2], polygon[1::2], strict=True)), fill=255)
        return mask
    if isinstance(segmentation, dict) and isinstance(segmentation.get("counts"), list):
        mask = _decode_uncompressed_rle(segmentation["counts"], segmentation["size"])
        if mask.size != size:
            raise COCOAdapterNotReady("RLE size differs from image metadata")
        return mask
    raise COCOAdapterNotReady(
        "compressed COCO RLE requires an explicitly locked pycocotools environment"
    )


def _stable(seed: int, *parts: Any) -> str:
    return hashlib.sha256(":".join([str(seed), *(str(part) for part in parts)]).encode()).hexdigest()


def _insertion_box(
    width: int, height: int, annotations: list[dict[str, Any]], *, seed: int, image_id: int,
) -> list[int]:
    side = max(48, int(min(width, height) * 0.18))
    margin = max(8, side // 3)
    proposals = [
        [margin, margin, margin + side, margin + side],
        [width - margin - side, margin, width - margin, margin + side],
        [margin, height - margin - side, margin + side, height - margin],
        [width - margin - side, height - margin - side, width - margin, height - margin],
        [(width - side) // 2, (height - side) // 2,
         (width + side) // 2, (height + side) // 2],
    ]
    boxes = []
    for annotation in annotations:
        x, y, box_width, box_height = [float(value) for value in annotation.get("bbox", [0, 0, 0, 0])]
        boxes.append([x, y, x + box_width, y + box_height])

    def overlap(candidate: list[int]) -> float:
        value = 0.0
        for box in boxes:
            dx = max(0.0, min(candidate[2], box[2]) - max(candidate[0], box[0]))
            dy = max(0.0, min(candidate[3], box[3]) - max(candidate[1], box[1]))
            value += dx * dy
        return value

    return min(proposals, key=lambda box: (overlap(box), _stable(seed, image_id, *box)))


def attach_insertion_assets(
    rows: list[dict[str, Any]], asset_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    assets = asset_manifest.get("categories")
    if not isinstance(assets, dict):
        raise COCOAdapterNotReady("insertion asset manifest must map categories")
    result = []
    for row in rows:
        if row["semantic_edit_family"] != "object_insertion":
            result.append(row)
            continue
        asset = assets.get(row["category"])
        if not isinstance(asset, dict):
            raise COCOAdapterNotReady(f"missing insertion asset for {row['category']}")
        path = Path(str(asset.get("path", "")))
        expected_hash = str(asset.get("sha256", ""))
        if (not path.is_file() or _sha(path) != expected_hash
                or asset.get("license_eligible") is not True):
            raise COCOAdapterNotReady(
                f"insertion asset bytes/license are not verified for {row['category']}"
            )
        result.append({**row, "insertion_asset_path": str(path),
                       "insertion_asset_sha256": expected_hash,
                       "insertion_asset_license": asset.get("license"),
                       "insertion_asset_status": "HASH_AND_LICENSE_VERIFIED"})
    return result


def build_feasibility_tasks(
    root: str | Path,
    *,
    out_dir: str | Path,
    items: int = 60,
    seed: int = 17011,
    minimum_short_side: int = 384,
    insertion_asset_manifest: str | Path | None = None,
) -> dict[str, Any]:
    """Build a balanced 60-item removal/insertion feasibility manifest.

    License and semantic validity remain pending.  The manifest is therefore a
    candidate/review input, never scientific evidence.
    """
    if items < 2 or items % 2:
        raise COCOAdapterNotReady("feasibility item count must be positive and even")
    data = load_coco_instances(root)
    categories = {identifier: str(row["name"]) for identifier, row in data["categories"].items()}
    overlap_ids = {identifier for identifier, name in categories.items()
                   if name in COCO_TO_CERTVIC_VOCAB}
    if not overlap_ids:
        raise COCOAdapterNotReady("COCO JSON has none of the frozen overlapping categories")
    out = Path(out_dir)
    mask_dir = out / "masks"
    mask_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[dict[str, Any]] = []
    for image_id, image_meta in sorted(data["images"].items()):
        image_path = Path(data["image_root"]) / str(image_meta["file_name"])
        if not image_path.is_file():
            continue
        width, height = int(image_meta["width"]), int(image_meta["height"])
        if min(width, height) < minimum_short_side:
            continue
        annotations = [row for row in data["annotations_by_image"].get(image_id, [])
                       if int(row["category_id"]) in overlap_ids and int(row.get("iscrowd", 0)) == 0]
        present_ids = {int(row["category_id"]) for row in annotations}
        license_id = int(image_meta.get("license", -1))
        license_record = data["licenses"].get(license_id, {})
        for annotation in annotations:
            category_id = int(annotation["category_id"])
            category = categories[category_id]
            x, y, box_width, box_height = [float(value) for value in annotation["bbox"]]
            mask = annotation_mask(annotation, (width, height))
            mask_path = mask_dir / f"coco_{image_id}_{annotation['id']}.png"
            mask.save(mask_path, format="PNG", compress_level=9)
            candidates.append({
                "item_id": f"coco17-removal-{image_id}-{annotation['id']}",
                "source_id": f"coco17:{image_id}", "source_image_id": str(image_id),
                "source_image_path": str(image_path), "original_image_path": str(image_path),
                "target_mask_path": str(mask_path),
                "target_mask_hash": _sha(mask_path),
                "target_bbox": [x, y, x + box_width, y + box_height],
                "category": COCO_TO_CERTVIC_VOCAB[category], "coco_category": category,
                "question": f"Is there a {COCO_TO_CERTVIC_VOCAB[category]} in the image?",
                "original_expected_answer": "yes", "edited_expected_answer": "no",
                "expected_answer": "yes", "required_change": True,
                "semantic_edit_family": "object_removal", "split": "val2017",
                "width": width, "height": height, "mode": "RGB",
                "annotation_id": int(annotation["id"]), "annotation_area": float(annotation["area"]),
                "license_id": license_id, "license_url": license_record.get("url"),
                "license_name": license_record.get("name"),
                "license_eligible": False, "license_status": "REQUIRES_PER_IMAGE_VERIFICATION",
                "source_sha256": _sha(image_path), "paper_evidence": False,
            })
        for category_id in sorted(overlap_ids - present_ids):
            category = categories[category_id]
            candidates.append({
                "item_id": f"coco17-insertion-{image_id}-{category_id}",
                "source_id": f"coco17:{image_id}", "source_image_id": str(image_id),
                "source_image_path": str(image_path), "original_image_path": str(image_path),
                "target_bbox": _insertion_box(
                    width, height, data["annotations_by_image"].get(image_id, []),
                    seed=seed, image_id=image_id,
                ),
                "category": COCO_TO_CERTVIC_VOCAB[category], "coco_category": category,
                "question": f"Is there a {COCO_TO_CERTVIC_VOCAB[category]} in the image?",
                "original_expected_answer": "no", "edited_expected_answer": "yes",
                "expected_answer": "no", "required_change": True,
                "semantic_edit_family": "object_insertion", "split": "val2017",
                "width": width, "height": height, "mode": "RGB",
                "license_id": license_id, "license_url": license_record.get("url"),
                "license_name": license_record.get("name"),
                "license_eligible": False, "license_status": "REQUIRES_PER_IMAGE_VERIFICATION",
                "insertion_asset_status": "REQUIRES_HASH_LOCKED_CATEGORY_ASSET",
                "source_sha256": _sha(image_path), "paper_evidence": False,
            })
    candidates.sort(key=lambda row: _stable(seed, row["semantic_edit_family"], row["category"],
                                             row["source_id"], row["item_id"]))
    selected: list[dict[str, Any]] = []
    max_per_source = 1
    used_sources: Counter[str] = Counter()
    family_target = {"object_removal": items // 2, "object_insertion": items // 2}
    family_counts: Counter[str] = Counter()
    category_cap = max(1, (items + len(COCO_TO_CERTVIC_VOCAB) - 1) // len(COCO_TO_CERTVIC_VOCAB))
    category_counts: Counter[str] = Counter()
    for required_family in ("object_removal", "object_insertion"):
        for row in candidates:
            family, category, source = row["semantic_edit_family"], row["category"], row["source_id"]
            if family != required_family or family_counts[family] >= family_target[family]:
                continue
            if category_counts[category] >= category_cap or used_sources[source] >= max_per_source:
                continue
            selected.append(row)
            family_counts[family] += 1
            category_counts[category] += 1
            used_sources[source] += 1
    shortage = items - len(selected)
    status = "FEASIBILITY_CANDIDATES_READY_FOR_LICENSE_AND_EDIT_REVIEW" if shortage == 0 else "BLOCKED_SHORTAGE"
    if insertion_asset_manifest is not None:
        selected = attach_insertion_assets(
            selected, json.loads(Path(insertion_asset_manifest).read_text(encoding="utf-8"))
        )
    canonical: list[dict[str, Any]] = []
    for row in selected:
        engine = (
            "hash_locked_asset_composite_v1"
            if row["semantic_edit_family"] == "object_insertion"
            and row.get("insertion_asset_status") == "HASH_AND_LICENSE_VERIFIED"
            else "manifest_verified_offline_inpainting_v1"
        )
        canonical.append(convert_legacy_task({
            **row, "source_dataset": "COCO_2017", "source_split": "val2017",
            "selected_engine": engine, "edit_engine_policy": "certvic.semantic_engine_policy.v1",
            "qa_status": "QA_PENDING", "review_status": "HUMAN_REVIEW_PENDING",
        }, study="second_domain_cvpr"))
    selected = require_task_matrix([with_task_hash(row) for row in canonical], verify_files=True) \
        if canonical else []
    task_path = out / "coco_feasibility_candidates.jsonl"
    task_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in selected),
                         encoding="utf-8")
    manifest = {
        "schema": "certvic.cvpr.coco_feasibility.v1", "status": status,
        "requested_items": items, "selected_items": len(selected), "shortage": shortage,
        "family_counts": dict(family_counts), "category_counts": dict(category_counts),
        "annotation_sha256": data["annotation_sha256"],
        "candidate_manifest_sha256": sha256_bytes(canonical_json_bytes(selected)),
        "license_status": "REQUIRES_PER_IMAGE_VERIFICATION",
        "insertion_asset_status": ("HASH_AND_LICENSE_VERIFIED" if insertion_asset_manifest
                                   else "REQUIRES_HASH_LOCKED_CATEGORY_ASSETS"),
        "human_review_status": "HUMAN_REVIEW_PENDING", "paper_evidence": False,
    }
    (out / "coco_feasibility_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build offline COCO 2017 feasibility candidates")
    parser.add_argument("--coco-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--items", type=int, default=60)
    parser.add_argument("--seed", type=int, default=17011)
    parser.add_argument("--insertion-asset-manifest")
    args = parser.parse_args(argv)
    result = build_feasibility_tasks(args.coco_root, out_dir=args.out_dir,
                                     items=args.items, seed=args.seed,
                                     insertion_asset_manifest=args.insertion_asset_manifest)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"].startswith("FEASIBILITY_CANDIDATES_READY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
