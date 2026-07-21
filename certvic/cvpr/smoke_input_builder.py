"""Build the exact two-item, licensed, portable real-model smoke input bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from certvic.cvpr.kaggle_bundle import build_bundle


class SmokeInputBuilderError(ValueError):
    """The requested real smoke task set is unsafe, synthetic, overlapping, or incomplete."""


def _jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]
    if not all(isinstance(row, dict) for row in rows):
        raise SmokeInputBuilderError("smoke task manifest must contain JSON objects")
    return rows


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _historical_identities(paths: Iterable[str | Path]) -> set[str]:
    identities: set[str] = set()
    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                value = line.strip()
            if isinstance(value, dict):
                identities.update(str(value[key]) for key in ("item_id", "source_sha256", "edited_sha256") if value.get(key))
            elif value:
                identities.add(str(value))
    return identities


def build_smoke_bundle(
    task_manifest: str | Path,
    *,
    output: str | Path = "kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip",
    historical_manifests: Iterable[str | Path] = (),
    synthetic_fixture: bool = False,
) -> dict[str, Any]:
    rows = _jsonl(task_manifest)
    if len(rows) != 2 or len({str(row.get("item_id")) for row in rows}) != 2:
        raise SmokeInputBuilderError("real smoke input must contain exactly two unique items")
    historical = _historical_identities(historical_manifests)
    portable_rows: list[dict[str, Any]] = []
    files: dict[str, Path | bytes] = {}
    byte_identities: set[str] = set()
    for index, row in enumerate(rows):
        if not synthetic_fixture and (
            row.get("synthetic_fixture") is True
            or str(row.get("source_dataset", "")).upper().startswith("SYNTHETIC")
        ):
            raise SmokeInputBuilderError("synthetic fixtures are prohibited in real smoke mode")
        if row.get("license_eligible") is not True or not row.get("license_id"):
            raise SmokeInputBuilderError(f"item {index} lacks affirmative licensing metadata")
        item_id = str(row["item_id"])
        if item_id in historical:
            raise SmokeInputBuilderError(f"historical item overlap: {item_id}")
        portable = dict(row)
        for role in ("original_image_path", "edited_image_path", "mask_path"):
            raw_path = row.get(role)
            if role != "mask_path" and not raw_path:
                raise SmokeInputBuilderError(f"item {item_id} missing {role}")
            if not raw_path:
                continue
            source = Path(raw_path).resolve()
            if not source.is_file() or source.is_symlink():
                raise SmokeInputBuilderError(f"item asset missing or symlinked: {source}")
            digest = _sha(source)
            if digest in historical:
                raise SmokeInputBuilderError(f"historical byte overlap: {role} for {item_id}")
            if digest in byte_identities:
                raise SmokeInputBuilderError(f"duplicate asset bytes: {role} for {item_id}")
            byte_identities.add(digest)
            archive_name = f"assets/{item_id}/{role.removesuffix('_path')}{source.suffix.lower()}"
            files[archive_name] = source
            portable[role] = archive_name
            portable[role.removesuffix("_path") + "_sha256"] = digest
        portable["synthetic_fixture"] = bool(synthetic_fixture)
        portable["paper_evidence"] = False
        portable_rows.append(portable)
    portable_rows.sort(key=lambda row: str(row["item_id"]))
    task_bytes = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
        for row in portable_rows
    )
    files["task_manifest.jsonl"] = task_bytes
    prompt_hashes = sorted({str(row.get("prompt_template_hash")) for row in rows if row.get("prompt_template_hash")})
    run_hashes = sorted({str(row.get("run_contract_hash")) for row in rows if row.get("run_contract_hash")})
    parser_versions = sorted({str(row.get("parser_version")) for row in rows if row.get("parser_version")})
    if not prompt_hashes or not run_hashes or not parser_versions:
        raise SmokeInputBuilderError("prompt, parser, and run-contract identities are mandatory")
    task_bundle = {
        "schema": "certvic.kaggle.real_smoke_task_bundle.v1",
        "cardinality": 2,
        "task_manifest_sha256": hashlib.sha256(task_bytes).hexdigest(),
        "prompt_template_hashes": prompt_hashes,
        "run_contract_hashes": run_hashes,
        "parser_versions": parser_versions,
        "asset_sha256": sorted(byte_identities),
        "zero_historical_overlap": True,
        "synthetic_fixture": bool(synthetic_fixture),
        "paper_evidence": False,
    }
    task_bundle_bytes = (json.dumps(task_bundle, indent=2, sort_keys=True) + "\n").encode()
    task_bundle["task_bundle_sha256"] = hashlib.sha256(task_bundle_bytes).hexdigest()
    files["task_bundle_manifest.json"] = (
        json.dumps(task_bundle, indent=2, sort_keys=True) + "\n"
    ).encode()
    files["smoke_contract.json"] = (
        json.dumps({
            "schema": "certvic.kaggle.real_two_item_smoke_contract.v1",
            "cardinality": 2,
            "providers": ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"],
            "use_real_model": not synthetic_fixture,
            "zero_historical_overlap": True,
            "synthetic_fixture": bool(synthetic_fixture),
            "paper_evidence": False,
        }, indent=2, sort_keys=True) + "\n"
    ).encode()
    files["licensing_metadata.json"] = (
        json.dumps({
            "schema": "certvic.kaggle.smoke_licensing.v1",
            "items": [{
                "item_id": row["item_id"],
                "license_id": row["license_id"],
                "license_eligible": row["license_eligible"],
            } for row in portable_rows],
        }, indent=2, sort_keys=True) + "\n"
    ).encode()
    files["validation_report.json"] = (
        json.dumps({
            "schema": "certvic.kaggle.smoke_input_validation.v1",
            "passed": True,
            "cardinality": 2,
            "portable_assets": len(byte_identities),
            "zero_historical_overlap": True,
            "synthetic_fixture": bool(synthetic_fixture),
            "paper_evidence": False,
        }, indent=2, sort_keys=True) + "\n"
    ).encode()
    return build_bundle(
        output,
        files,
        bundle_type="REAL_TWO_ITEM_SMOKE_INPUT" if not synthetic_fixture else "SYNTHETIC_TWO_ITEM_SMOKE_PROOF",
        study="pre_smoke",
        stage="real_model_smoke",
        provider=None,
        required_notebook="00C2_certvic_real_model_two_item_smoke.ipynb",
        dataset_slug="certvic/certvic-real-two-item-smoke",
        mount_path="/kaggle/input/certvic-real-two-item-smoke",
        external_dependency_status="EXTERNAL_BYTES_VERIFIED" if not synthetic_fixture else "SYNTHETIC_PROOF_ONLY",
        evidence_class="REAL_MODEL_SMOKE_NON_EVIDENCE" if not synthetic_fixture else "SYNTHETIC_FIXTURE",
        builder_command=(
            "python3 -m certvic.cvpr.smoke_input_builder --task-manifest "
            "<TRUSTED_TWO_ITEM_TASKS_JSONL>"
        ),
        readme=(
            "# CertVIC two-item smoke input\n\nExactly two portable, hash-bound tasks. This bundle is "
            "non-evidence and exists only to prove each real model/runtime contract before scientific "
            "authorization."
        ),
        extra_manifest={"synthetic_fixture": bool(synthetic_fixture)},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-manifest")
    parser.add_argument("--historical-manifest", action="append", default=[])
    parser.add_argument("--output", default="kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    if args.status or not args.task_manifest:
        result = {
            "status": "BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES",
            "required_layout": {
                "tasks.jsonl": "exactly two real licensed rows with portable source/edit/mask paths",
                "assets": "real licensed image/mask bytes referenced by tasks.jsonl",
            },
            "builder_command": "python3 -m certvic.cvpr.smoke_input_builder --task-manifest <TASKS_JSONL>",
            "output": args.output,
            "expected_size": "1-50 MB (depends on the two licensed image pairs)",
            "paper_evidence": False,
        }
    else:
        result = build_smoke_bundle(
            args.task_manifest,
            output=args.output,
            historical_manifests=args.historical_manifest,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

