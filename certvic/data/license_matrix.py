"""Static dataset license matrix for V4 planning."""

from __future__ import annotations


def dataset_license_matrix() -> list[dict]:
    return [
        {
            "dataset": "ADE20K",
            "primary": True,
            "default_release_mode": "pointer_only",
            "figure_safe": False,
            "recommendation": "Use for experiments; do not redistribute pixels.",
            "legal_overclaim": False,
        },
        {
            "dataset": "Wikimedia CC0/PD subset",
            "primary": False,
            "default_release_mode": "redistributable_showcase",
            "figure_safe": True,
            "recommendation": "Prefer for paper/showcase figures after per-file license checks.",
            "legal_overclaim": False,
        },
        {
            "dataset": "Open Images",
            "primary": False,
            "default_release_mode": "pointer_only",
            "figure_safe": False,
            "recommendation": "Use only after per-image license review.",
            "legal_overclaim": False,
        },
    ]

