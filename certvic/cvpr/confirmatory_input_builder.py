"""Package licensed, unseen confirmatory source bytes for deterministic Kaggle generation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from certvic.cvpr.kaggle_bundle import build_bundle


REQUIRED_CONTROL_FILES = (
    "source_manifest", "exclusion_inventory", "generation_config", "licenses",
    "engine_policy", "seed_plan", "shard_plan", "resume_ledger",
)


class ConfirmatoryInputBuilderError(ValueError):
    """Confirmatory input is not licensed, unseen, portable, or complete."""


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line]
    value = json.loads(path.read_text())
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get("items"), list):
        return value["items"]
    raise ConfirmatoryInputBuilderError("source manifest must be JSONL or a JSON item list")


def build_confirmatory_input(
    control_files: Mapping[str, str | Path],
    *,
    output: str | Path = "kaggle_uploads/05_confirmatory/certvic_confirmatory_generation_input.zip",
    synthetic_fixture: bool = False,
) -> dict[str, Any]:
    missing = sorted(set(REQUIRED_CONTROL_FILES) - set(control_files))
    if missing:
        raise ConfirmatoryInputBuilderError(f"missing confirmatory controls: {missing}")
    controls = {role: Path(value).resolve() for role, value in control_files.items()}
    absent = sorted(role for role, path in controls.items() if not path.is_file() or path.is_symlink())
    if absent:
        raise ConfirmatoryInputBuilderError(f"missing or symlinked confirmatory files: {absent}")
    rows = _load_rows(controls["source_manifest"])
    if not rows:
        raise ConfirmatoryInputBuilderError("confirmatory source manifest is empty")
    identities: set[str] = set()
    portable_rows: list[dict[str, Any]] = []
    files: dict[str, Path | bytes] = {}
    for row in rows:
        item_id = str(row.get("item_id") or row.get("source_image_id") or "")
        if not item_id or item_id in identities:
            raise ConfirmatoryInputBuilderError("source identifiers must be present and unique")
        identities.add(item_id)
        if row.get("license_eligible") is not True or not row.get("license_id"):
            raise ConfirmatoryInputBuilderError(f"source {item_id} lacks verified license")
        if row.get("zero_v1_overlap") is not True:
            raise ConfirmatoryInputBuilderError(f"source {item_id} lacks explicit zero-V1-overlap proof")
        if not synthetic_fixture and row.get("synthetic_fixture") is True:
            raise ConfirmatoryInputBuilderError("synthetic source prohibited in real confirmatory mode")
        portable = dict(row)
        for role in ("source_image_path", "insertion_asset_path", "mask_path"):
            raw = row.get(role)
            if not raw:
                if role == "source_image_path":
                    raise ConfirmatoryInputBuilderError(f"source {item_id} missing source image")
                continue
            source = Path(raw).resolve()
            if not source.is_file() or source.is_symlink():
                raise ConfirmatoryInputBuilderError(f"asset missing or symlinked: {source}")
            archive_name = f"assets/{item_id}/{role.removesuffix('_path')}{source.suffix.lower()}"
            files[archive_name] = source
            portable[role] = archive_name
            portable[role.removesuffix("_path") + "_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        portable["synthetic_fixture"] = bool(synthetic_fixture)
        portable["paper_evidence"] = False
        portable_rows.append(portable)
    portable_rows.sort(key=lambda row: str(row.get("item_id") or row.get("source_image_id")))
    files["controls/source_manifest.jsonl"] = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
        for row in portable_rows
    )
    for role, path in sorted(controls.items()):
        if role != "source_manifest":
            files[f"controls/{role}{path.suffix.lower()}"] = path
    files["validation_report.json"] = (
        json.dumps({
            "schema": "certvic.kaggle.confirmatory_input_validation.v1",
            "passed": True,
            "source_count": len(portable_rows),
            "all_license_eligible": True,
            "zero_v1_overlap": True,
            "synthetic_fixture": bool(synthetic_fixture),
            "paper_evidence": False,
        }, indent=2, sort_keys=True) + "\n"
    ).encode()
    return build_bundle(
        output,
        files,
        bundle_type="CONFIRMATORY_GENERATION_INPUT" if not synthetic_fixture else "SYNTHETIC_CONFIRMATORY_GENERATION_PROOF",
        study="specificity_confirmatory_cvpr",
        stage="generation",
        provider="controls",
        required_notebook="01_specificity_confirmatory_generation_T4x2.ipynb",
        dataset_slug="certvic/certvic-confirmatory-generation-input",
        mount_path="/kaggle/input/certvic-confirmatory-generation-input",
        external_dependency_status="EXTERNAL_BYTES_VERIFIED" if not synthetic_fixture else "SYNTHETIC_PROOF_ONLY",
        evidence_class="PROSPECTIVE_CONFIRMATORY_INPUT" if not synthetic_fixture else "SYNTHETIC_FIXTURE",
        builder_command="python3 -m certvic.cvpr.confirmatory_input_builder --config <INPUT_CONFIG_JSON>",
        readme=(
            "# CertVIC confirmatory generation input\n\nThe source universe is prospectively frozen, "
            "license-verified, and explicitly zero-overlap with frozen V1. Missing source or license "
            "bytes fail closed."
        ),
        extra_manifest={"synthetic_fixture": bool(synthetic_fixture)},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--output", default="kaggle_uploads/05_confirmatory/certvic_confirmatory_generation_input.zip")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    if args.status or not args.config:
        result = {
            "status": "BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES",
            "required_roles": list(REQUIRED_CONTROL_FILES),
            "required_layout": "licensed source manifest plus referenced images/assets/masks and prospective controls",
            "builder_command": "python3 -m certvic.cvpr.confirmatory_input_builder --config <INPUT_CONFIG_JSON>",
            "output": args.output,
            "expected_size": "1-20 GB depending on the prospectively frozen pool",
            "paper_evidence": False,
        }
    else:
        config = json.loads(Path(args.config).read_text())
        result = build_confirmatory_input(config["control_files"], output=args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

