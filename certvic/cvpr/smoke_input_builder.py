"""Build the exact two-item, licensed, portable real-model smoke input bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Iterable

from certvic.cvpr.kaggle_bundle import build_bundle
from certvic.cvpr.task_bundle import create_bundle
from certvic.cvpr.task_schema import TASK_SCHEMA, convert_legacy_task, require_task_matrix


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
    canonical_rows: list[dict[str, Any]] = []
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
        prepared = dict(row)
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
            prepared[role.removesuffix("_path") + "_sha256"] = digest
        prepared.setdefault("source_image_path", prepared["original_image_path"])
        prepared.setdefault("source_image_hash", prepared["original_image_sha256"])
        prepared.setdefault("source_dataset", "USER_OWNED_REAL_SMOKE")
        prepared.setdefault("source_split", "operator_smoke")
        prepared.setdefault("source_image_id", item_id)
        prepared.setdefault("question", "Is the main visible content coherent? Answer yes or no.")
        prepared.setdefault("original_expected_answer", "yes")
        prepared.setdefault("edited_expected_answer", "yes")
        prepared.setdefault("required_change", False)
        prepared.setdefault("control_edit_family", "user_owned_smoke_edit")
        prepared.setdefault("target_bbox", [0, 0, 1, 1])
        prepared.setdefault("selected_engine", "user_supplied_edit")
        prepared.setdefault("review_status", "HUMAN_REVIEW_PENDING")
        prepared.setdefault("qa_status", "REAL_SMOKE_INTAKE_VERIFIED")
        prepared.setdefault("license_status", "VERIFIED_ELIGIBLE")
        prepared["synthetic_fixture"] = bool(synthetic_fixture)
        prepared["paper_evidence"] = False
        if prepared.get("task_schema_version") != TASK_SCHEMA:
            prepared = convert_legacy_task(prepared, study="specificity_confirmatory_cvpr")
        canonical_rows.append(prepared)
    canonical_rows.sort(key=lambda row: str(row["task_id"]))
    require_task_matrix(canonical_rows, verify_files=True)
    prompt_hashes = sorted({str(row.get("prompt_template_hash")) for row in rows if row.get("prompt_template_hash")})
    run_hashes = sorted({str(row.get("run_contract_hash")) for row in rows if row.get("run_contract_hash")})
    parser_versions = sorted({str(row.get("parser_version")) for row in rows if row.get("parser_version")})
    if not prompt_hashes or not run_hashes or not parser_versions:
        raise SmokeInputBuilderError("prompt, parser, and run-contract identities are mandatory")
    contract_bytes = (
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
    licensing_bytes = (
        json.dumps({
            "schema": "certvic.kaggle.smoke_licensing.v1",
            "items": [{
                "item_id": row["item_id"],
                "license_id": row["license_id"],
                "license_eligible": row["license_eligible"],
            } for row in canonical_rows],
        }, indent=2, sort_keys=True) + "\n"
    ).encode()
    validation_bytes = (
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
    with tempfile.TemporaryDirectory(prefix="certvic_real_smoke_bundle_") as temporary:
        bundle_root = Path(temporary) / "task_bundle"
        create_bundle(canonical_rows, bundle_root)
        files: dict[str, Path | bytes] = {
            f"task_bundle/{path.relative_to(bundle_root).as_posix()}": path
            for path in bundle_root.rglob("*")
            if path.is_file()
        }
        files.update({
            "metadata/smoke_contract.json": contract_bytes,
            "metadata/licensing_metadata.json": licensing_bytes,
            "metadata/validation_report.json": validation_bytes,
        })
        return build_bundle(
            output,
            files,
            bundle_type=(
                "REAL_TWO_ITEM_SMOKE_INPUT"
                if not synthetic_fixture
                else "SYNTHETIC_TWO_ITEM_SMOKE_PROOF"
            ),
            study="pre_smoke",
            stage="real_model_smoke",
            provider=None,
            required_notebook="ALL_3_PROVIDER_SPECIFIC_00C2_NOTEBOOKS",
            dataset_slug="certvic/certvic-real-two-item-smoke",
            mount_path="/kaggle/input/certvic-real-two-item-smoke",
            external_dependency_status=(
                "EXTERNAL_BYTES_VERIFIED" if not synthetic_fixture else "SYNTHETIC_PROOF_ONLY"
            ),
            evidence_class=(
                "REAL_MODEL_SMOKE_NON_EVIDENCE" if not synthetic_fixture else "SYNTHETIC_FIXTURE"
            ),
            builder_command=(
                "python3 -m certvic.cvpr.smoke_input_builder --task-manifest "
                "<TRUSTED_TWO_ITEM_TASKS_JSONL>"
            ),
            readme=(
                "# CertVIC two-item smoke input\n\nExactly two portable, hash-bound tasks. This "
                "bundle is non-evidence and exists only to prove each real model/runtime "
                "contract before scientific authorization."
            ),
            extra_manifest={
                "synthetic_fixture": bool(synthetic_fixture),
                "task_bundle_schema": "certvic.cvpr.task_bundle.v1",
                "provider_run_contracts": "DERIVED_EXACTLY_AT_PERMISSION_ISSUE",
            },
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
