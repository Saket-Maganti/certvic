"""Pointer-only Wikimedia/Commons fallback adapter stub."""

from __future__ import annotations


def adapter_summary() -> dict:
    return {
        "dataset": "Wikimedia Commons",
        "status": "adapter_stub",
        "primary": False,
        "pointer_only": True,
        "downloads_attempted": False,
        "license_risks": [
            "licenses vary by file",
            "attribution and share-alike requirements may affect releases",
            "CC0/public-domain rows are preferred for paper figures",
        ],
    }

