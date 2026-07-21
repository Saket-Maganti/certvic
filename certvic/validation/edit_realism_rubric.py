"""Formal edit realism rubric."""

from __future__ import annotations

RUBRIC_FIELDS = (
    "photorealism",
    "lighting_consistency",
    "boundary_artifacts",
    "shadow_consistency",
    "geometry_plausibility",
    "single_factor_preservation",
    "target_clarity",
    "required_change_clarity",
)


def rubric_template() -> list[dict]:
    return [
        {
            "field": field,
            "scale": "pass/uncertain/fail",
            "blocking": field in {"photorealism", "single_factor_preservation", "target_clarity"},
        }
        for field in RUBRIC_FIELDS
    ]

