"""Canonical CVPR output-schema contract and mixed-version rejection."""

from __future__ import annotations

from typing import Any, Iterable


OUTPUT_SCHEMA = "certvic.cvpr.output.v2"


def validate_schema_matrix(
    rows: Iterable[dict[str, Any]], *, expected: str = OUTPUT_SCHEMA
) -> dict[str, Any]:
    """Validate that every runtime row uses the one frozen output schema."""
    values = [str(row.get("output_schema", "")) for row in rows]
    observed = sorted(set(values))
    errors: list[str] = []
    if not values:
        errors.append("output matrix is empty")
    if "" in observed:
        errors.append("one or more rows omit output_schema")
    if any(value != expected for value in values):
        errors.append(f"output schema must be exactly {expected}; observed={observed}")
    return {
        "schema": "certvic.cvpr.schema_validation.v1",
        "passed": not errors,
        "expected_output_schema": expected,
        "observed_output_schemas": observed,
        "rows": len(values),
        "errors": errors,
        "paper_evidence": False,
    }


def require_schema_matrix(
    rows: Iterable[dict[str, Any]], *, expected: str = OUTPUT_SCHEMA
) -> dict[str, Any]:
    result = validate_schema_matrix(rows, expected=expected)
    if not result["passed"]:
        raise ValueError("; ".join(result["errors"]))
    return result
