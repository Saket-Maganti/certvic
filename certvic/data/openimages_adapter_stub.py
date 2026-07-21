"""Pointer-only Open Images fallback adapter stub."""

from __future__ import annotations


def adapter_summary() -> dict:
    return {
        "dataset": "Open Images",
        "status": "adapter_stub",
        "primary": False,
        "pointer_only": True,
        "downloads_attempted": False,
        "license_risks": [
            "image licenses vary by source",
            "redistribution must be checked per image",
            "ADE20K remains primary unless access blocks",
        ],
    }

