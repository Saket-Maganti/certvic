#!/usr/bin/env python3
"""Mechanically refresh changed Kaggle prompt/capsule/release rows in the artifact registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certvic.cvpr.ceiling_common import atomic_json, canonical_json_bytes  # noqa: E402


REGISTRY = ROOT / "reports/max_ceiling_upgrade/artifact_registry.json"
CAPSULES = (
    ROOT / "reports/max_ceiling_upgrade/pre_run_reproducibility_capsule.json",
    ROOT / "reports/max_ceiling_upgrade/pre_run_reproducibility_capsule_final.json",
    ROOT / "reports/max_ceiling_upgrade/pre_run_reproducibility_capsule_sealed.json",
)
KAGGLE_BUNDLES = tuple(
    ROOT / "kaggle_uploads/00_code" / name
    for name in (
        "certvic_code_bundle.zip",
        "certvic_notebooks_bundle.zip",
        "certvic_configs_bundle.zip",
        "certvic_execution_tools_bundle.zip",
        "certvic_synthetic_validation_bundle.zip",
    )
)
PHASE_C_LOCKS = (
    ROOT / "configs/studies/specificity_confirmatory_cvpr.yaml",
    ROOT / "configs/models/certvic_cvpr_model_registry.yaml",
)


def _identity(row: dict[str, Any], source: Path) -> tuple[str, str, int]:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    artifact_id = hashlib.sha256(canonical_json_bytes({
        "role": row["role"], "sha256": digest, "study": row["study"],
        "schema": row["schema"],
    })).hexdigest()[:24]
    return artifact_id, digest, source.stat().st_size


def refresh(*, include_release: bool = False) -> dict[str, Any]:
    registry = json.loads(REGISTRY.read_text())
    rows = registry["artifacts"]
    refresh_locations = {
        "certvic/cvpr/notebook_builder.py",
        *(path.relative_to(ROOT).as_posix() for path in PHASE_C_LOCKS),
    }
    if include_release:
        refresh_locations.add("release/certvic_cvpr_pre_run_maximum.zip")
        refresh_locations.update(
            path.relative_to(ROOT).as_posix() for path in KAGGLE_BUNDLES
        )
    id_map: dict[str, str] = {}
    for row in rows:
        location = str(row["immutable_location"])
        source = ROOT / location
        if location not in refresh_locations or not source.is_file():
            continue
        old_id = str(row["artifact_id"])
        artifact_id, digest, size = _identity(row, source)
        row.update(artifact_id=artifact_id, sha256=digest, size=size)
        id_map[old_id] = artifact_id

    # Capsules bind registry identities. Refresh every changed binding before
    # recomputing the capsules' own content-addressed registry rows.
    changed_capsules: list[str] = []
    by_id = {str(row["artifact_id"]): row for row in rows}
    capsule_locations = {path.relative_to(ROOT).as_posix() for path in CAPSULES}
    for path in CAPSULES:
        capsule = json.loads(path.read_text())
        for binding in capsule.get("artifact_bindings", {}).values():
            old_binding_id = str(binding.get("artifact_id", ""))
            new_binding_id = id_map.get(old_binding_id, old_binding_id)
            target = by_id.get(new_binding_id)
            if target is not None:
                binding["artifact_id"] = new_binding_id
                binding["sha256"] = target["sha256"]
        capsule["capsule_hash"] = hashlib.sha256(canonical_json_bytes({
            key: value for key, value in capsule.items() if key != "capsule_hash"
        })).hexdigest()
        atomic_json(path, capsule)
        changed_capsules.append(path.relative_to(ROOT).as_posix())

    for row in rows:
        location = str(row["immutable_location"])
        if location not in capsule_locations:
            continue
        source = ROOT / location
        if not source.is_file():
            continue
        old_id = str(row["artifact_id"])
        artifact_id, digest, size = _identity(row, source)
        row.update(artifact_id=artifact_id, sha256=digest, size=size)
        id_map[old_id] = artifact_id

    def current_id(value: str) -> str:
        seen: set[str] = set()
        while value in id_map and value not in seen:
            seen.add(value)
            value = id_map[value]
        return value

    for row in rows:
        row["parent_artifacts"] = sorted(
            current_id(str(parent)) for parent in row.get("parent_artifacts", [])
        )
    rows.sort(key=lambda row: str(row["artifact_id"]))
    registry["registry_hash"] = hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
    atomic_json(REGISTRY, registry)
    return {
        "schema": "certvic.kaggle.release_lineage_refresh.v1",
        "prompt_artifact_id": next(
            row["artifact_id"]
            for row in rows
            if row["immutable_location"] == "certvic/cvpr/notebook_builder.py"
        ),
        "capsules": changed_capsules,
        "release_refreshed": include_release,
        "registry_hash": registry["registry_hash"],
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-release", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(refresh(include_release=args.include_release), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
