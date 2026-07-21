"""Dataset and insertion-asset license eligibility registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


REQUIRED_FIELDS = {
    "dataset",
    "split",
    "origin",
    "local_root",
    "redistribution",
    "paper_use",
    "image_level_license",
    "insertion_asset_license",
    "reviewer_visibility",
    "release_inclusion",
    "verification_status",
}


class LicenseRegistryError(ValueError):
    """Source or asset license eligibility is unresolved."""


def load_registry(path: str | Path) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != "certvic.data.license_registry.v1":
        raise LicenseRegistryError("source license registry schema mismatch")
    sources = value.get("sources")
    if not isinstance(sources, list):
        raise LicenseRegistryError("source license registry must contain a sources list")
    errors = [
        f"row {index}: missing {sorted(REQUIRED_FIELDS - set(row))}"
        for index, row in enumerate(sources)
        if not isinstance(row, dict) or REQUIRED_FIELDS - set(row)
    ]
    keys = [
        (str(row.get("dataset")), str(row.get("split")))
        for row in sources
        if isinstance(row, dict)
    ]
    if len(keys) != len(set(keys)):
        errors.append("duplicate dataset/split rows")
    if errors:
        raise LicenseRegistryError("; ".join(errors))
    return value


def validate_tasks(
    tasks: list[dict[str, Any]],
    registry: dict[str, Any],
    *,
    for_release: bool = False,
) -> dict[str, Any]:
    by_key = {
        (str(row["dataset"]), str(row["split"])): row for row in registry["sources"]
    }
    errors: list[dict[str, str]] = []
    for index, task in enumerate(tasks, start=1):
        dataset = str(task.get("source_dataset", task.get("dataset", "")))
        split = str(task.get("source_split", task.get("split", "")))
        row = by_key.get((dataset, split)) or by_key.get((dataset, "*"))
        item_id = str(task.get("task_id", task.get("item_id", index)))
        if row is None:
            errors.append({"item_id": item_id, "error_code": "LICENSE_SOURCE_UNREGISTERED"})
            continue
        if row["verification_status"] != "VERIFIED":
            errors.append({"item_id": item_id, "error_code": "LICENSE_SOURCE_UNVERIFIED"})
        if task.get("license_eligible") is not True and task.get("license_status") not in {
            "VERIFIED", "VERIFIED_ELIGIBLE"
        }:
            errors.append({"item_id": item_id, "error_code": "LICENSE_TASK_NOT_ELIGIBLE"})
        insertion = task.get("insertion_asset_license", "NOT_APPLICABLE")
        if task.get("insertion_asset_path") and insertion in {None, "", "UNRESOLVED"}:
            errors.append({"item_id": item_id, "error_code": "LICENSE_INSERTION_ASSET_UNRESOLVED"})
        if for_release and row["release_inclusion"] != "ALLOW_BYTES":
            errors.append({"item_id": item_id, "error_code": "LICENSE_RELEASE_BYTES_FORBIDDEN"})
    return {
        "schema": "certvic.data.task_license_validation.v1",
        "passed": not errors,
        "task_count": len(tasks),
        "for_release": for_release,
        "errors": errors,
        "paper_evidence": False,
    }


def assert_task_licenses(
    tasks: list[dict[str, Any]], registry_path: str | Path, *, for_release: bool = False
) -> None:
    result = validate_tasks(tasks, load_registry(registry_path), for_release=for_release)
    if not result["passed"]:
        raise LicenseRegistryError(f"task license validation failed: {result['errors']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate CertVIC task source licenses")
    parser.add_argument(
        "--registry", default="configs/data/source_license_registry.yaml"
    )
    parser.add_argument("--tasks")
    parser.add_argument("--for-release", action="store_true")
    args = parser.parse_args(argv)
    registry = load_registry(args.registry)
    if args.tasks:
        tasks = [
            json.loads(line) for line in Path(args.tasks).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        result = validate_tasks(tasks, registry, for_release=args.for_release)
    else:
        result = {
            "schema": "certvic.data.license_registry_validation.v1",
            "passed": True,
            "source_count": len(registry["sources"]),
            "verified_count": sum(
                row["verification_status"] == "VERIFIED" for row in registry["sources"]
            ),
            "paper_evidence": False,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

