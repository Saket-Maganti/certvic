"""Deduplicate prediction rows with explicit conflict reporting."""

from __future__ import annotations

from collections import defaultdict


def prediction_key(row: dict) -> tuple[str, str, str, str]:
    return (
        str(row.get("run_id")),
        str(row.get("item_id")),
        str(row.get("image_variant")),
        str(row.get("provider_name")),
    )


def deduplicate_predictions(rows: list[dict]) -> dict:
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[prediction_key(row)].append(row)
    merged: list[dict] = []
    duplicates: list[dict] = []
    conflicts: list[dict] = []
    for key, bucket in sorted(grouped.items()):
        first = bucket[0]
        merged.append(first)
        if len(bucket) > 1:
            duplicates.append({"key": key, "n": len(bucket)})
            outputs = {(r.get("raw_output"), r.get("parsed_answer"), r.get("parse_ok")) for r in bucket}
            if len(outputs) > 1:
                conflicts.append({"key": key, "n_versions": len(outputs)})
    return {"merged": merged, "duplicates": duplicates, "conflicts": conflicts}

