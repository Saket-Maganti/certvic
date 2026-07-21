"""Source manifest records with release policy metadata."""

from __future__ import annotations

from pathlib import Path

from certvic.data.license_policy import release_mode_for_source, validate_license_for_split
from certvic.hashing import sha256_file
from certvic.schema import SourceImageRecord


def enrich_source_record(record: SourceImageRecord, split: str) -> dict:
    data = record.model_dump(mode="json")
    if record.local_path and Path(record.local_path).exists():
        data["sha256"] = sha256_file(record.local_path)
    normalized = SourceImageRecord.model_validate(data)
    data["release_mode"] = release_mode_for_source(normalized)
    data["license_warnings"] = validate_license_for_split(normalized, split)
    return data


def summarize_sources(records: list[dict]) -> dict:
    summary = {"n": len(records), "by_license": {}, "by_release_mode": {}}
    for row in records:
        license_category = row.get("license_category", "unknown")
        release_mode = row.get("release_mode", "unknown")
        summary["by_license"][license_category] = summary["by_license"].get(license_category, 0) + 1
        summary["by_release_mode"][release_mode] = summary["by_release_mode"].get(release_mode, 0) + 1
    return summary
