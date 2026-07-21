"""All-providers-or-none validation and atomic import for a frozen CVPR study."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from certvic.cvpr.contracts import OutputContract, canonical_json_bytes, validate_output_rows
from certvic.cvpr.run_contract import validate_run_contract
from certvic.cvpr.transactional import canonical_jsonl, read_jsonl
from certvic.cvpr.task_schema import require_task_matrix, resolve_task_path


class StudyImportError(ValueError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        members = handle.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)):
            raise StudyImportError(f"{archive.name}: duplicate ZIP members")
        if handle.testzip() is not None:
            raise StudyImportError(f"{archive.name}: corrupt ZIP")
        total = 0
        for member in members:
            pure = PurePosixPath(member.filename)
            if pure.is_absolute() or ".." in pure.parts:
                raise StudyImportError(f"{archive.name}: unsafe member {member.filename}")
            total += member.file_size
            if total > 4_000_000_000:
                raise StudyImportError(f"{archive.name}: extracted content exceeds safety limit")
        handle.extractall(destination)


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise StudyImportError(f"expected one {name}; found {len(matches)}")
    return matches[0]


def _verify_member_hashes(root: Path) -> dict[str, str]:
    path = _single(root, "hash_manifest.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    hashes = value.get("files", value) if isinstance(value, dict) else None
    if not isinstance(hashes, dict) or not hashes:
        raise StudyImportError("hash_manifest.json is not a nonempty mapping")
    observed = {
        file.relative_to(path.parent).as_posix(): _sha(file)
        for file in path.parent.rglob("*") if file.is_file() and file != path
    }
    missing = sorted(set(hashes) - set(observed))
    mismatched = sorted(name for name in set(hashes) & set(observed) if hashes[name] != observed[name])
    unmanifested = sorted(set(observed) - set(hashes))
    if missing or mismatched or unmanifested:
        raise StudyImportError(
            f"member hash contract failed: missing={missing[:5]}, mismatched={mismatched[:5]}, "
            f"unmanifested={unmanifested[:5]}"
        )
    return observed


def _task_prompt(task: dict[str, Any], variant: str) -> str:
    prompts = task.get("prompts", {})
    value = prompts.get(variant) if isinstance(prompts, dict) else None
    prompt = value or task.get("prompt") or task.get("question")
    if not isinstance(prompt, str) or not prompt:
        raise StudyImportError(f"task {task.get('item_id')} has no prompt")
    return prompt


def _expected_image_hash(
    task: dict[str, Any], variant: str, *, bundle_root: str | Path | None = None,
) -> str:
    key = "original_image_path" if variant == "original" else "edited_image_path"
    path = resolve_task_path(task, key, bundle_root=bundle_root)
    if path is None:
        raise StudyImportError(f"task {task.get('item_id')} has no image path")
    if not path.is_file():
        raise StudyImportError(f"task {task.get('item_id')} has missing image {path}")
    return _sha(path)


def verify_returned_archive(
    archive: str | Path,
    *,
    study: str,
    run_tag: str,
    provider: str,
    model_contract: dict[str, Any],
    tasks: list[dict[str, Any]],
    expected_code_bundle_hash: str,
    expected_snapshot_manifest_hash: str,
    expected_run_contract_hash: str | None = None,
    expected_permission_id: str | None = None,
    expected_permission_signature: str | None = None,
    bundle_root: str | Path | None = None,
    destination: str | Path,
) -> dict[str, Any]:
    archive = Path(archive)
    destination = Path(destination)
    tasks = require_task_matrix(tasks, verify_files=True, bundle_root=bundle_root)
    destination.mkdir(parents=True, exist_ok=True)
    _safe_extract(archive, destination)
    member_hashes = _verify_member_hashes(destination)
    runtime = json.loads(_single(destination, "runtime_manifest.json").read_text(encoding="utf-8"))
    environment = json.loads(
        _single(destination, "environment_manifest.json").read_text(encoding="utf-8")
    )
    validation = json.loads(_single(destination, "validation_report.json").read_text(encoding="utf-8"))
    run_contract_paths = list(destination.rglob("run_contract.json"))
    if len(run_contract_paths) > 1:
        raise StudyImportError("returned archive contains multiple run contracts")
    returned_run_contract: dict[str, Any] | None = None
    effective_run_contract_hash = expected_run_contract_hash
    if run_contract_paths:
        returned_run_contract = json.loads(run_contract_paths[0].read_text(encoding="utf-8"))
        contract_errors = validate_run_contract(returned_run_contract, expected_run_contract_hash)
        if contract_errors:
            raise StudyImportError("run contract validation failed: " + "; ".join(contract_errors))
        effective_run_contract_hash = str(returned_run_contract["run_contract_hash"])
        if expected_permission_id is not None and returned_run_contract.get(
            "execution_permission_id"
        ) != expected_permission_id:
            raise StudyImportError("run contract execution permission ID mismatch")
        if expected_permission_signature is not None and returned_run_contract.get(
            "execution_permission_signature"
        ) != expected_permission_signature:
            raise StudyImportError("run contract execution permission signature mismatch")
    required = {
        "schema": "certvic.cvpr.runtime_manifest.v2",
        "study": study,
        "run_tag": run_tag,
        "provider": provider,
        "model_id": model_contract["model_id"],
        "model_commit": model_contract["model_commit"],
        "processor_commit": model_contract["processor_commit"],
        "code_bundle_hash": expected_code_bundle_hash,
        "model_snapshot_manifest_hash": expected_snapshot_manifest_hash,
    }
    if effective_run_contract_hash is not None:
        required["run_contract_hash"] = effective_run_contract_hash
    mismatches = {field: {"expected": expected, "observed": runtime.get(field)}
                  for field, expected in required.items() if runtime.get(field) != expected}
    if mismatches:
        raise StudyImportError(f"runtime manifest mismatch: {mismatches}")
    if not isinstance(environment, dict) or validation.get("passed") is not True:
        raise StudyImportError("environment or validation report is not successful")
    merged = _single(destination, "merged_raw.jsonl")
    if runtime.get("merged_raw_sha256") != _sha(merged):
        raise StudyImportError("merged output hash differs from runtime manifest")
    rows = read_jsonl(merged)
    item_ids = tuple(str(task["item_id"]) for task in tasks)
    contract = OutputContract(
        provider=provider,
        run_tag=run_tag,
        model_commit=str(model_contract["model_commit"]),
        processor_commit=str(model_contract["processor_commit"]),
        item_ids=item_ids,
        bundle_sha256=expected_code_bundle_hash,
        run_contract_hash=effective_run_contract_hash,
        strict_provenance=effective_run_contract_hash is not None,
    )
    errors = validate_output_rows(rows, contract)
    task_map = {str(task["item_id"]): task for task in tasks}
    for index, row in enumerate(rows, start=1):
        item_id, variant = str(row.get("item_id")), str(row.get("variant"))
        task = task_map.get(item_id)
        if task is None or variant not in {"original", "edited"}:
            continue
        expected = {
            "prompt_hash": hashlib.sha256(_task_prompt(task, variant).encode()).hexdigest(),
            "image_hash": _expected_image_hash(task, variant, bundle_root=bundle_root),
            "task_hash": str(task.get("task_hash") or hashlib.sha256(
                canonical_json_bytes(task)
            ).hexdigest()),
            "provider": provider,
            "model_id": model_contract["model_id"],
            "model_commit": model_contract["model_commit"],
            "processor_commit": model_contract["processor_commit"],
            "parser_version": "certvic.parse.v2",
            "code_bundle_hash": expected_code_bundle_hash,
            "model_snapshot_manifest_hash": expected_snapshot_manifest_hash,
        }
        if effective_run_contract_hash is not None:
            expected["run_contract_hash"] = effective_run_contract_hash
        for field, value in expected.items():
            if row.get(field) != value:
                errors.append(f"row {index}: expected-value mismatch for {field}")
    if errors:
        raise StudyImportError("; ".join(errors[:20]))
    expected_rows = 2 * len(tasks)
    if runtime.get("rows") != expected_rows or len(rows) != expected_rows:
        raise StudyImportError("returned archive has an unexpected row count")
    canonical = canonical_jsonl(sorted(rows, key=lambda row: (row["item_id"], row["variant"])))
    return {
        "provider": provider,
        "archive_sha256": _sha(archive),
        "merged_raw_sha256": _sha(merged),
        "canonical_normalized_sha256": hashlib.sha256(canonical).hexdigest(),
        "member_hashes": member_hashes,
        "task_identity_sha256": hashlib.sha256(canonical_json_bytes([
            {"item_id": row["item_id"], "variant": row["variant"], "task_hash": row["task_hash"],
             "prompt_hash": row["prompt_hash"], "image_hash": row["image_hash"]}
            for row in sorted(rows, key=lambda row: (row["item_id"], row["variant"]))
        ])).hexdigest(),
        "canonical_bytes": canonical,
        "runtime": runtime,
        "run_contract": returned_run_contract,
    }


def atomic_import_matrix(
    archives: dict[str, str | Path],
    *,
    study: str,
    run_tag: str,
    model_contracts: dict[str, dict[str, Any]],
    tasks: list[dict[str, Any]],
    expected_code_bundle_hash: str,
    expected_snapshot_hashes: dict[str, str],
    expected_run_contract_hashes: dict[str, str] | None = None,
    expected_permission_id: str | None = None,
    expected_permission_signature: str | None = None,
    permission_ledger_path: str | Path | None = None,
    bundle_root: str | Path | None = None,
    destination_root: str | Path,
) -> dict[str, Any]:
    expected = set(model_contracts)
    tasks = require_task_matrix(tasks, verify_files=True, bundle_root=bundle_root)
    if set(archives) != expected or set(expected_snapshot_hashes) != expected:
        raise StudyImportError("provider matrix is incomplete or contains unexpected providers")
    if expected_run_contract_hashes is not None and set(expected_run_contract_hashes) != expected:
        raise StudyImportError("run-contract provider matrix is incomplete or unexpected")
    if permission_ledger_path is not None:
        if expected_permission_id is None or expected_permission_signature is None:
            raise StudyImportError("ledger-bound import requires permission ID and signature")
        from certvic.cvpr.permission_ledger import verify_slot
        for provider in sorted(expected):
            try:
                verify_slot(
                    permission_ledger_path, provider=provider, required_state="OUTPUT_PACKAGED",
                    permission_id=expected_permission_id,
                    permission_signature=expected_permission_signature, run_tag=run_tag,
                )
            except ValueError as exc:
                raise StudyImportError(f"permission replay/state check failed for {provider}: {exc}") from exc
    root = Path(destination_root)
    root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="certvic_study_stage_", dir=root.parent) as temporary:
        stage = Path(temporary)
        verified: dict[str, dict[str, Any]] = {}
        for provider in sorted(expected):
            verified[provider] = verify_returned_archive(
                archives[provider],
                study=study,
                run_tag=run_tag,
                provider=provider,
                model_contract=model_contracts[provider],
                tasks=tasks,
                expected_code_bundle_hash=expected_code_bundle_hash,
                expected_snapshot_manifest_hash=expected_snapshot_hashes[provider],
                expected_run_contract_hash=(expected_run_contract_hashes or {}).get(provider),
                expected_permission_id=expected_permission_id,
                expected_permission_signature=expected_permission_signature,
                bundle_root=bundle_root,
                destination=stage / "unpacked" / provider,
            )
        task_identities = {value["task_identity_sha256"] for value in verified.values()}
        if len(task_identities) != 1:
            raise StudyImportError("cross-provider task identity mismatch")
        audit_safe = {
            provider: {key: value for key, value in payload.items() if key != "canonical_bytes"}
            for provider, payload in verified.items()
        }
        matrix_hash = hashlib.sha256(canonical_json_bytes(audit_safe)).hexdigest()
        if root.exists():
            audit_path = root / "study_import_audit.json"
            if audit_path.is_file() and json.loads(audit_path.read_text()).get("matrix_sha256") == matrix_hash:
                return {"status": "IDEMPOTENT", "matrix_sha256": matrix_hash,
                        "providers": sorted(expected), "paper_evidence": False}
            quarantine = root.with_name(f"{root.name}.conflict.{matrix_hash[:12]}")
            quarantine.mkdir(exist_ok=True)
            raise StudyImportError(f"conflicting study import refused; quarantine marker: {quarantine}")
        promotion = stage / "promotion"
        canonical_dir = promotion / "canonical"
        raw_dir = promotion / "immutable_raw"
        canonical_dir.mkdir(parents=True)
        raw_dir.mkdir()
        for provider, payload in verified.items():
            canonical_path = canonical_dir / f"{provider}.jsonl"
            canonical_path.write_bytes(payload["canonical_bytes"])
            shutil.copyfile(archives[provider], raw_dir / f"{provider}_{payload['archive_sha256']}.zip")
        audit = {
            "schema": "certvic.cvpr.atomic_study_import.v1",
            "status": "ATOMIC_MATRIX_PROMOTED",
            "study": study,
            "run_tag": run_tag,
            "matrix_sha256": matrix_hash,
            "task_identity_sha256": next(iter(task_identities)),
            "providers": audit_safe,
            "human_review_status": "HUMAN_REVIEW_PENDING",
            "paper_evidence": False,
        }
        (promotion / "study_import_audit.json").write_text(
            json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        evidence = []
        for provider, payload in sorted(verified.items()):
            raw_artifact = f"immutable_raw/{provider}_{payload['archive_sha256']}.zip"
            canonical_artifact = f"canonical/{provider}.jsonl"
            evidence.extend([
                {
                    "artifact": raw_artifact,
                    "evidence_class": "REAL_OBSERVED_EVIDENCE",
                    "sha256": payload["archive_sha256"],
                    "content_role": "IMMUTABLE_RETURNED_ARCHIVE",
                    "merged_raw_sha256": payload["merged_raw_sha256"],
                    "human_review_status": "HUMAN_REVIEW_PENDING",
                    "paper_evidence": False,
                },
                {
                    "artifact": canonical_artifact,
                    "evidence_class": "DERIVED_FROM_REAL_EVIDENCE",
                    "sha256": payload["canonical_normalized_sha256"],
                    "upstream_sha256": payload["archive_sha256"],
                    "normalization": "canonical_jsonl_sorted_by_item_and_variant",
                    "validation_status": "PASS",
                    "human_review_status": "HUMAN_REVIEW_PENDING",
                    "paper_evidence": False,
                },
            ])
        (promotion / "import_evidence_ledger.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(promotion, root)
    if permission_ledger_path is not None:
        from certvic.cvpr.permission_ledger import transition
        for provider in sorted(expected):
            transition(
                permission_ledger_path, provider=provider, to_state="IMPORTED",
                permission_id=str(expected_permission_id),
                permission_signature=str(expected_permission_signature), run_tag=run_tag,
                actor="certvic.cvpr.whole_study_import",
                detail={"matrix_sha256": matrix_hash},
            )
            transition(
                permission_ledger_path, provider=provider, to_state="CONSUMED",
                permission_id=str(expected_permission_id),
                permission_signature=str(expected_permission_signature), run_tag=run_tag,
                actor="certvic.cvpr.whole_study_import",
                detail={"matrix_sha256": matrix_hash},
            )
    return {"status": "ATOMIC_MATRIX_PROMOTED", "matrix_sha256": matrix_hash,
            "providers": sorted(expected), "human_review_status": "HUMAN_REVIEW_PENDING",
            "paper_evidence": False}
