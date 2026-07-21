"""Import-safe ADE20K adapter, layout inspector, and mask-manifest builder.

No downloads are performed. The user must provide a local ADE20K root. V1.3 can
inspect common ADE20K-style layouts and convert semantic PNG annotations into
manifest-only mask records. It does not generate edited images, copy source
pixels into release artifacts, require GPU, or run model inference.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError

from certvic.hashing import sha256_file
from certvic.io import write_json, write_jsonl
from certvic.schema import LicenseCategory, MaskRecord, SourceImageRecord

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ANNOTATION_EXTENSIONS = {".png", ".mat", ".tif", ".tiff"}
SUPPORTED_ANNOTATION_EXTENSIONS = {".png"}
IMAGE_DIR_MARKERS = {"image", "images", "img", "imgs"}
ANNOTATION_DIR_MARKERS = {
    "annotation",
    "annotations",
    "annot",
    "ann",
    "mask",
    "masks",
    "seg",
    "segmentation",
    "semantic",
    "object",
    "objects",
}
TRAIN_MARKERS = {"train", "training"}
VAL_MARKERS = {"val", "valid", "validation"}
BACKGROUND_LABEL_IDS = {0}


class ADE20KLayoutError(ValueError):
    """Raised when a local ADE20K root cannot support inspection or manifests."""


def inspect_ade20k_layout(
    root: str | Path,
    max_examples: int = 10,
    max_items_for_stats: int = 500,
) -> dict[str, Any]:
    root_path = Path(root).expanduser()
    if not root_path.exists():
        raise ADE20KLayoutError(
            f"ADE20K root does not exist: {root_path}. Provide a local dataset root; "
            "CertVIC will not download ADE20K automatically."
        )
    if not root_path.is_dir():
        raise ADE20KLayoutError(f"ADE20K root is not a directory: {root_path}")

    image_dirs = _find_candidate_dirs(root_path, IMAGE_DIR_MARKERS)
    annotation_dirs = _find_candidate_dirs(root_path, ANNOTATION_DIR_MARKERS)
    image_files = _find_image_files(root_path, image_dirs)
    annotation_files = _find_annotation_files(root_path, annotation_dirs)
    supported_annotation_files = [
        path for path in annotation_files if path.suffix.lower() in SUPPORTED_ANNOTATION_EXTENSIONS
    ]

    if not image_files:
        raise ADE20KLayoutError(
            f"No candidate ADE20K image files found under {root_path}. Expected a local "
            "layout with image folders such as images/training and images/validation."
        )

    pairs = pair_images_and_annotations(root_path, image_files, supported_annotation_files)
    matched_pairs = [pair for pair in pairs if pair["annotation_path"] is not None]
    missing_annotation_pairs = [pair for pair in pairs if pair["annotation_path"] is None]
    mask_stats = summarize_annotation_masks(matched_pairs[:max_items_for_stats])

    warnings: list[str] = []
    if not image_dirs:
        warnings.append("No explicit image directory marker found; layout is unsupported until reorganized.")
    if not annotation_dirs:
        warnings.append("No likely annotation/mask directory was found.")
    if annotation_files and not supported_annotation_files:
        warnings.append("Annotation files were found, but no supported semantic PNG annotations were found.")
    if not annotation_files:
        warnings.append("No candidate annotation files found; mask manifests cannot be built.")
    if missing_annotation_pairs:
        warnings.append(
            f"{len(missing_annotation_pairs)} candidate image files do not have matching annotation PNG stems."
        )

    common_layout = _has_common_ade20k_layout(root_path, image_dirs, annotation_dirs)
    if common_layout and supported_annotation_files:
        layout_status = "supported_layout"
        mask_parser_status = "semantic_png_supported"
    elif annotation_files and not supported_annotation_files:
        layout_status = "parser_required"
        mask_parser_status = "parser_required_for_non_png_annotations"
    else:
        layout_status = "unsupported_layout"
        mask_parser_status = "unsupported_layout_missing_annotations"

    train_images = [path for path in image_files if _detect_split(path) == "train"]
    val_images = [path for path in image_files if _detect_split(path) == "val"]
    train_annotations = [path for path in annotation_files if _detect_split(path) == "train"]
    val_annotations = [path for path in annotation_files if _detect_split(path) == "val"]

    return {
        "root": str(root_path),
        "exists": True,
        "dry_run_only": True,
        "downloads_attempted": False,
        "pixels_copied": False,
        "edits_generated": False,
        "gpu_required": False,
        "layout_status": layout_status,
        "supported_for_source_manifest": bool(image_files),
        "supported_for_mask_manifest": layout_status == "supported_layout",
        "mask_parser_status": mask_parser_status,
        "candidate_image_count": len(image_files),
        "candidate_annotation_count": len(annotation_files),
        "supported_annotation_count": len(supported_annotation_files),
        "matched_pair_count": len(matched_pairs),
        "missing_annotation_count": len(missing_annotation_pairs),
        "candidate_mask_count": mask_stats["candidate_mask_count"],
        "train_image_count": len(train_images),
        "val_image_count": len(val_images),
        "train_annotation_count": len(train_annotations),
        "val_annotation_count": len(val_annotations),
        "unmatched_image_count": len(missing_annotation_pairs),
        "mask_area_statistics": mask_stats["mask_area_statistics"],
        "top_label_ids_by_frequency": mask_stats["top_label_ids_by_frequency"],
        "unsupported_annotations": mask_stats["unsupported_annotations"],
        "candidate_image_dirs": [_dir_summary(root_path, path, IMAGE_EXTENSIONS) for path in image_dirs],
        "candidate_annotation_dirs": [
            _dir_summary(root_path, path, ANNOTATION_EXTENSIONS) for path in annotation_dirs
        ],
        "example_images": [_rel(root_path, path) for path in image_files[:max_examples]],
        "example_annotations": [_rel(root_path, path) for path in annotation_files[:max_examples]],
        "example_missing_annotations": [
            _rel(root_path, pair["image_path"]) for pair in missing_annotation_pairs[:max_examples]
        ],
        "warnings": warnings,
        "actionable_next_steps": _next_steps(layout_status),
    }


def scan_ade20k_sources(root: str, max_items: int = 500) -> list[SourceImageRecord]:
    root_path = Path(root).expanduser()
    inspection = inspect_ade20k_layout(root_path, max_items_for_stats=max_items)
    image_paths = _find_image_files(
        root_path,
        [root_path / item["relative_path"] for item in inspection["candidate_image_dirs"]],
    )[:max_items]
    return [source_record_for_image(root_path, image_path) for image_path in image_paths]


def source_record_for_image(root: Path, image_path: Path) -> SourceImageRecord:
    source_id = source_id_for_image(root, image_path)
    return SourceImageRecord(
        source_id=source_id,
        source_name="ADE20K",
        source_url_or_pointer=str(image_path),
        local_path=str(image_path),
        sha256=None,
        license_category=LicenseCategory.POINTER_ONLY.value,
        license_text=None,
        redistribution_allowed=False,
        notes=(
            "User-supplied local ADE20K path; recipe-first pointer. "
            "Pixels are not rehostable by default."
        ),
    )


def source_id_for_image(root: Path, image_path: Path) -> str:
    split = _detect_split(image_path) or "unknown"
    rel = _rel(root, image_path.with_suffix(""))
    safe = re.sub(r"[^a-zA-Z0-9_]+", "_", rel).strip("_").lower()
    return f"ade20k_{split}_{safe}"


def build_ade20k_manifests(
    root: str,
    out_sources: str,
    out_masks: str,
    max_items: int = 500,
    export_binary_masks: bool = False,
    mask_out_dir: str | None = None,
) -> dict:
    root_path = Path(root).expanduser()
    inspection = inspect_ade20k_layout(root_path, max_items_for_stats=max_items)
    if inspection["layout_status"] != "supported_layout":
        raise ADE20KLayoutError(
            f"Cannot build ADE20K mask manifest for layout_status={inspection['layout_status']}. "
            "Expected images/{training,validation} and annotations/{training,validation} with semantic PNG annotations."
        )
    image_dirs = [root_path / item["relative_path"] for item in inspection["candidate_image_dirs"]]
    annotation_dirs = [root_path / item["relative_path"] for item in inspection["candidate_annotation_dirs"]]
    image_files = _find_image_files(root_path, image_dirs)[:max_items]
    annotation_files = [
        path for path in _find_annotation_files(root_path, annotation_dirs)
        if path.suffix.lower() in SUPPORTED_ANNOTATION_EXTENSIONS
    ]
    pairs = pair_images_and_annotations(root_path, image_files, annotation_files)
    matched_pairs = [pair for pair in pairs if pair["annotation_path"] is not None]

    sources = [source_record_for_image(root_path, pair["image_path"]) for pair in matched_pairs]
    source_by_image = {pair["image_path"]: source for pair, source in zip(matched_pairs, sources)}
    masks: list[MaskRecord] = []
    for pair in matched_pairs:
        masks.extend(
            mask_records_for_annotation(
                root_path,
                source_by_image[pair["image_path"]],
                pair["annotation_path"],
                export_binary_masks=export_binary_masks,
                mask_out_dir=mask_out_dir,
            )
        )

    write_jsonl(out_sources, sources)
    write_jsonl(out_masks, masks)
    return {
        "sources": len(sources),
        "masks": len(masks),
        "matched_pairs": len(matched_pairs),
        "missing_annotations": len([pair for pair in pairs if pair["annotation_path"] is None]),
        "release_mode_default": "recipe_only",
        "mask_status": "semantic_png_manifest",
        "binary_masks_exported": export_binary_masks,
        "mask_out_dir": mask_out_dir if export_binary_masks else None,
        "note": "ADE20K pixels are pointer-only until redistribution terms are explicitly verified.",
    }


def pair_images_and_annotations(
    root: str | Path,
    image_files: list[Path] | None = None,
    annotation_files: list[Path] | None = None,
) -> list[dict[str, Any]]:
    root_path = Path(root).expanduser()
    image_files = image_files if image_files is not None else _find_image_files(
        root_path,
        _find_candidate_dirs(root_path, IMAGE_DIR_MARKERS),
    )
    annotation_files = annotation_files if annotation_files is not None else [
        path for path in _find_annotation_files(root_path, _find_candidate_dirs(root_path, ANNOTATION_DIR_MARKERS))
        if path.suffix.lower() in SUPPORTED_ANNOTATION_EXTENSIONS
    ]
    annotations_by_key: dict[tuple[str | None, str], Path] = {}
    for annotation_path in annotation_files:
        annotations_by_key[(_detect_split(annotation_path), annotation_path.stem)] = annotation_path

    pairs: list[dict[str, Any]] = []
    for image_path in sorted(image_files, key=lambda p: str(p)):
        key = (_detect_split(image_path), image_path.stem)
        annotation_path = annotations_by_key.get(key) or annotations_by_key.get((None, image_path.stem))
        pairs.append(
            {
                "image_path": image_path,
                "annotation_path": annotation_path,
                "split": _detect_split(image_path),
                "stem": image_path.stem,
                "matched": annotation_path is not None,
            }
        )
    return pairs


def summarize_annotation_masks(pairs: list[dict[str, Any]]) -> dict:
    label_counter: Counter[int] = Counter()
    areas: list[float] = []
    unsupported: list[dict[str, str]] = []
    candidate_count = 0
    for pair in pairs:
        annotation_path = pair.get("annotation_path")
        if annotation_path is None:
            continue
        try:
            labels = _read_semantic_annotation(annotation_path)
        except ADE20KLayoutError as exc:
            unsupported.append({"annotation_path": str(annotation_path), "reason": str(exc)})
            continue
        total = labels.size
        for label_id in sorted(int(value) for value in np.unique(labels) if int(value) not in BACKGROUND_LABEL_IDS):
            mask = labels == label_id
            area = float(mask.sum() / total)
            if area <= 0:
                continue
            candidate_count += 1
            areas.append(area)
            label_counter[label_id] += 1

    return {
        "candidate_mask_count": candidate_count,
        "mask_area_statistics": _area_stats(areas),
        "top_label_ids_by_frequency": [
            {"label_id": label_id, "count": count}
            for label_id, count in label_counter.most_common(20)
        ],
        "unsupported_annotations": unsupported,
    }


def mask_records_for_annotation(
    root: Path,
    source: SourceImageRecord,
    annotation_path: Path,
    export_binary_masks: bool = False,
    mask_out_dir: str | None = None,
) -> list[MaskRecord]:
    labels = _read_semantic_annotation(annotation_path)
    total = labels.size
    records: list[MaskRecord] = []
    for label_id in sorted(int(value) for value in np.unique(labels) if int(value) not in BACKGROUND_LABEL_IDS):
        mask = labels == label_id
        bbox = _bbox_from_bool_mask(mask)
        if bbox is None:
            continue
        area_fraction = float(mask.sum() / total)
        binary_mask_path = None
        if export_binary_masks:
            if not mask_out_dir:
                raise ADE20KLayoutError("--mask-out-dir is required with --export-binary-masks.")
            binary_mask_path = _export_binary_mask(mask, mask_out_dir, source.source_id, label_id)
        mask_path = binary_mask_path or str(annotation_path)
        records.append(
            MaskRecord(
                mask_id=f"{source.source_id}_label_{label_id}",
                source_id=source.source_id,
                mask_path=mask_path,
                object_label=f"ade20k_label_{label_id}",
                bbox_xyxy=bbox,
                mask_sha256=sha256_file(mask_path) if binary_mask_path else None,
                method="ade20k_semantic_png",
                quality_notes="manifest_only; semantic label name unresolved",
                label_id=label_id,
                annotation_path=str(annotation_path),
                mask_area_fraction=area_fraction,
                metadata={
                    "annotation_relative_path": _rel(root, annotation_path),
                    "binary_mask_exported": bool(binary_mask_path),
                    "semantic_name_status": "unresolved",
                    "regeneration": {
                        "label_id": label_id,
                        "annotation_path": str(annotation_path),
                    },
                },
            )
        )
    return records


def _read_semantic_annotation(annotation_path: str | Path) -> np.ndarray:
    path = Path(annotation_path)
    try:
        image = Image.open(path)
        arr = np.asarray(image)
    except (OSError, UnidentifiedImageError) as exc:
        raise ADE20KLayoutError(f"Could not read annotation PNG {path}: {exc}") from exc
    if arr.ndim == 2:
        return arr.astype(np.int64)
    if arr.ndim == 3 and arr.shape[2] >= 3 and np.array_equal(arr[..., 0], arr[..., 1]) and np.array_equal(arr[..., 0], arr[..., 2]):
        return arr[..., 0].astype(np.int64)
    raise ADE20KLayoutError(
        f"Unsupported annotation encoding for {path}; expected indexed/grayscale semantic PNG."
    )


def _bbox_from_bool_mask(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]


def _export_binary_mask(mask: np.ndarray, mask_out_dir: str, source_id: str, label_id: int) -> str:
    out_dir = Path(mask_out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{source_id}_label_{label_id}.png"
    Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(out_path)
    return str(out_path)


def _find_candidate_dirs(root: Path, markers: set[str]) -> list[Path]:
    dirs: list[Path] = []
    for path in [root, *root.rglob("*")]:
        if not path.is_dir():
            continue
        parts = {_normalize(part) for part in path.relative_to(root).parts}
        name = _normalize(path.name)
        if name in markers or parts & markers:
            dirs.append(path)
    return sorted(set(dirs), key=lambda p: str(p))


def _find_image_files(root: Path, image_dirs: list[Path]) -> list[Path]:
    search_dirs = image_dirs or [root]
    files: list[Path] = []
    for directory in search_dirs:
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            if _looks_like_annotation_path(path):
                continue
            files.append(path)
    return sorted(set(files), key=lambda p: str(p))


def _find_annotation_files(root: Path, annotation_dirs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for directory in annotation_dirs:
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in ANNOTATION_EXTENSIONS:
                files.append(path)
    return sorted(set(files), key=lambda p: str(p))


def _has_common_ade20k_layout(root: Path, image_dirs: list[Path], annotation_dirs: list[Path]) -> bool:
    image_splits = {_detect_split(path) for path in image_dirs}
    annotation_splits = {_detect_split(path) for path in annotation_dirs}
    has_image_root = any(_normalize(path.name) in IMAGE_DIR_MARKERS for path in image_dirs)
    has_annotation_root = any(_normalize(path.name) in ANNOTATION_DIR_MARKERS for path in annotation_dirs)
    return (
        has_image_root
        and has_annotation_root
        and bool({"train", "val"} & image_splits)
        and bool({"train", "val"} & annotation_splits)
    )


def _looks_like_annotation_path(path: Path) -> bool:
    normalized_parts = {_normalize(part) for part in path.parts}
    return bool(normalized_parts & ANNOTATION_DIR_MARKERS)


def _detect_split(path: Path) -> str | None:
    parts = {_normalize(part) for part in path.parts}
    if parts & TRAIN_MARKERS:
        return "train"
    if parts & VAL_MARKERS:
        return "val"
    return None


def _dir_summary(root: Path, path: Path, extensions: set[str]) -> dict:
    return {
        "relative_path": _rel(root, path),
        "split": _detect_split(path),
        "file_count": sum(
            1 for child in path.rglob("*") if child.is_file() and child.suffix.lower() in extensions
        ),
    }


def _area_stats(areas: list[float]) -> dict:
    if not areas:
        return {"n": 0, "min": None, "max": None, "mean": None}
    return {
        "n": len(areas),
        "min": min(areas),
        "max": max(areas),
        "mean": mean(areas),
    }


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _normalize(value: str) -> str:
    return value.lower().replace("-", "_")


def _next_steps(layout_status: str) -> list[str]:
    if layout_status == "supported_layout":
        return [
            "Review dataset_inspection.json and confirm matched image/annotation counts.",
            "Build pointer-only source and mask manifests without exporting binary masks by default.",
            "Run pilot selection only after mask-area thresholds and source-link checks pass.",
        ]
    if layout_status == "parser_required":
        return [
            "A non-PNG annotation format was detected; implement a parser before mask manifests are ready.",
            "Do not generate edits or model predictions until mask manifests are valid.",
        ]
    return [
        "Provide a local ADE20K root with images/{training,validation} and annotations/{training,validation}.",
        "Rerun the dry-run inspection; no downloads are attempted by CertVIC.",
    ]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ade20k-root", required=True)
    parser.add_argument("--out-sources")
    parser.add_argument("--out-masks")
    parser.add_argument("--max-items", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--inspection-out")
    parser.add_argument("--export-binary-masks", action="store_true")
    parser.add_argument("--mask-out-dir")
    parser.add_argument("--write-manifests-in-dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.dry_run:
            inspection = inspect_ade20k_layout(args.ade20k_root, max_items_for_stats=args.max_items)
            if args.inspection_out:
                write_json(args.inspection_out, inspection)
            if args.write_manifests_in_dry_run:
                if not args.out_sources or not args.out_masks:
                    raise ADE20KLayoutError(
                        "--out-sources and --out-masks are required with --write-manifests-in-dry-run."
                    )
                summary = build_ade20k_manifests(
                    args.ade20k_root,
                    args.out_sources,
                    args.out_masks,
                    max_items=args.max_items,
                    export_binary_masks=args.export_binary_masks,
                    mask_out_dir=args.mask_out_dir,
                )
                inspection["dry_run_manifest_summary"] = summary
            print(json.dumps(inspection, sort_keys=True))
            return

        if not args.out_sources or not args.out_masks:
            raise ADE20KLayoutError("--out-sources and --out-masks are required outside --dry-run.")
        summary = build_ade20k_manifests(
            args.ade20k_root,
            args.out_sources,
            args.out_masks,
            max_items=args.max_items,
            export_binary_masks=args.export_binary_masks,
            mask_out_dir=args.mask_out_dir,
        )
        if args.inspection_out:
            write_json(args.inspection_out, inspect_ade20k_layout(args.ade20k_root, max_items_for_stats=args.max_items))
        print(json.dumps(summary, sort_keys=True))
    except ADE20KLayoutError as exc:
        raise SystemExit(f"ADE20K layout inspection failed: {exc}") from None


if __name__ == "__main__":
    main()
