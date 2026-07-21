"""Figure manifest placeholders."""

from __future__ import annotations


def figure_manifest(summary: dict) -> dict:
    return {
        "status": "placeholder",
        "note": "Figures require real pilot/main outputs; smoke mode does not generate paper figures.",
        "n": summary.get("n", 0),
    }
