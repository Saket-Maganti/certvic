"""ADE20K mask manifest capability status."""

from __future__ import annotations


def ade20k_masks_available(root: str) -> bool:
    return True


def ade20k_mask_parser_status(root: str) -> dict:
    return {
        "available": True,
        "status": "semantic_png_manifest_supported",
        "root": root,
        "note": (
            "V1.3 can decode ADE20K-style semantic PNG annotations into "
            "manifest-only MaskRecord rows. It does not generate edited images."
        ),
    }
