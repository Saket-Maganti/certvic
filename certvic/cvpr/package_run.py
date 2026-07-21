"""Validate, merge, manifest, and deterministically package completed CVPR VLM shards."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

from certvic.cvpr.contracts import OutputContract, validate_output_rows
from certvic.cvpr.runtime_preflight import hardware_report
from certvic.cvpr.transactional import promote_jsonl, read_jsonl
from certvic.cvpr.worker import _load_config, _run_contract, _tasks
from certvic.cvpr.t4x2 import derive_seed_manifest, write_seed_manifest


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_deterministic_zip(path: Path, package_paths: list[Path]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for member in sorted(package_paths, key=lambda value: value.name):
            info = zipfile.ZipInfo(member.name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, member.read_bytes())


def _validate_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ValueError("package archive is duplicate or corrupt")


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def package(
    config_path: str | Path,
    *,
    expected_shards: int,
    zip_writer: Callable[[Path, list[Path]], None] = _write_deterministic_zip,
    archive_validator: Callable[[Path], None] = _validate_zip,
    atomic_replace: Callable[[str | Path, str | Path], None] = os.replace,
) -> dict[str, object]:
    config = _load_config(config_path)
    tasks = _tasks(
        config["task_manifest"], bundle_root=config.get("task_bundle_root"),
        task_bundle_manifest=config.get("task_bundle_manifest"),
        task_bundle_hash=config.get("task_bundle_hash"),
    )
    run_contract = _run_contract(config, tasks)
    out = Path(config["output_dir"])
    assignment_path = out / "shard_assignment_manifest.json"
    if not assignment_path.is_file():
        raise ValueError("shard assignment manifest is missing")
    assignment = json.loads(assignment_path.read_text(encoding="utf-8"))
    if assignment.get("num_shards") != expected_shards:
        raise ValueError("packager expected_shards differs from the worker assignment manifest")
    shard_paths = [out / f"shard_{index}.complete.jsonl" for index in range(expected_shards)]
    missing = [path.name for path in shard_paths if not path.is_file()]
    if missing:
        raise ValueError(f"missing completed shards: {missing}")
    rows = [row for path in shard_paths for row in read_jsonl(path)]
    contract = OutputContract(
        provider=str(config["provider"]), run_tag=str(config["run_tag"]),
        model_commit=str(config["model_commit"]), processor_commit=str(config["processor_commit"]),
        item_ids=tuple(str(task["item_id"]) for task in tasks),
        bundle_sha256=str(config["code_bundle_hash"]),
        run_contract_hash=str(run_contract["run_contract_hash"]),
        prompt_template_hash=(str(config["prompt_template_hash"])
                              if config.get("prompt_template_hash") else None),
        strict_provenance=bool(config.get("strict_run_contract", False)),
    )
    errors = validate_output_rows(rows, contract)
    if errors:
        raise ValueError("; ".join(errors))
    merged = out / "merged_raw.jsonl"
    promotion = promote_jsonl(rows, merged, contract)
    merged_hash = hashlib.sha256(merged.read_bytes()).hexdigest()
    task_manifest_hash = str(run_contract["task_manifest_sha256"])
    event_payloads = [json.loads(path.read_text(encoding="utf-8"))
                      for path in sorted(out.glob("shard_*.runtime_events.json"))]
    events = [event for payload in event_payloads for event in payload.get("events", [])]
    peak_vram = max((float(event.get("peak_vram_gib", 0.0)) for event in events), default=0.0)
    oom_events = sum(event.get("event") == "CUDA_OOM" for event in events)
    model_release_passed = bool(event_payloads) and all(any(
        event.get("event") == "MODEL_RELEASED" and event.get("model_released") is True
        for event in payload.get("events", [])
    ) for payload in event_payloads)
    cuda_statuses = [
        str(event.get("status"))
        for payload in event_payloads
        for event in payload.get("events", [])
        if event.get("event") == "CUDA_CLEANUP"
    ]
    cuda_cleanup_status = (
        "PASS" if cuda_statuses and all(value == "PASS" for value in cuda_statuses)
        else "NOT_APPLICABLE" if cuda_statuses and all(value == "NOT_APPLICABLE" for value in cuda_statuses)
        else "FAIL"
    )
    unresolved_warnings = [
        event
        for payload in event_payloads
        for event in payload.get("events", [])
        if event.get("event") == "WARNING" and event.get("resolved") is not True
    ]
    cleanup_passed = model_release_passed and cuda_cleanup_status in {"PASS", "NOT_APPLICABLE"}
    runtime = {
        "schema": "certvic.cvpr.runtime_manifest.v2", "provider": config["provider"],
        "status": "COMPLETE",
        "runtime_class": config.get("runtime_class", "SCIENTIFIC_EXECUTION"),
        "synthetic_notebook_proof": config.get("synthetic_notebook_proof", False),
        "study": config.get("study", str(config["run_tag"]).removesuffix("_v1")),
        "run_tag": config["run_tag"], "model_id": config["model_id"],
        "model_commit": config["model_commit"], "processor_commit": config["processor_commit"],
        "code_bundle_hash": config["code_bundle_hash"],
        "model_snapshot_manifest_hash": config.get("model_snapshot_manifest_hash"),
        "processor_snapshot_manifest_hash": config.get(
            "processor_snapshot_manifest_hash", config.get("model_snapshot_manifest_hash")
        ),
        "snapshot_status": config.get("snapshot_status", "LEGACY_TEST_UNSPECIFIED"),
        "snapshot_contract": run_contract["snapshot_contract"],
        "environment_lock_hash": config.get("environment_lock_hash", "LEGACY_TEST_UNSPECIFIED"),
        "run_contract_hash": run_contract["run_contract_hash"],
        "task_manifest_sha256": task_manifest_hash, "merged_raw_sha256": merged_hash,
        "raw_prediction_sha256": merged_hash,
        "environment_hash": config.get("environment_lock_hash", "LEGACY_TEST_UNSPECIFIED"),
        "snapshot_manifest_hash": config.get("model_snapshot_manifest_hash"),
        "snapshot_root_hash": config.get("snapshot_root_hash"),
        "processor_model_contract": config.get("snapshot_contract"),
        "prompt_template_hash": config.get("prompt_template_hash"),
        "parser_version": config.get("parser_version", "certvic.parse.v2"),
        "peak_vram_gib": peak_vram,
        "peak_vram_status": ("SYNTHETIC_NOT_MEASURED" if config.get(
            "runtime_class"
        ) == "SYNTHETIC_END_TO_END_FIXTURE" and peak_vram == 0 else "MEASURED"),
        "oom_events": oom_events,
        "unresolved_warnings": unresolved_warnings,
        "cleanup_status": "PASS" if cleanup_passed else "FAIL",
        "model_release_status": "PASS" if model_release_passed else "FAIL",
        "cuda_cleanup_status": cuda_cleanup_status,
        "teardown_complete": cleanup_passed,
        "rows": len(rows),
        "output_schema": run_contract["output_schema"],
        "expected_shards": expected_shards, "paper_evidence": False,
        "produced_shards": len(shard_paths),
        "task_bundle_hash": config.get("task_bundle_hash"),
    }
    environment_path = out / "environment_manifest.json"
    environment = (
        json.loads(environment_path.read_text(encoding="utf-8"))
        if environment_path.is_file()
        else {
            "python": sys.version.split()[0], "platform": platform.platform(),
            "cuda_visible_devices": "recorded_in_shard_logs", "hardware": hardware_report(),
            "paper_evidence": False,
            "environment_hash": config.get("environment_lock_hash", "LEGACY_TEST_UNSPECIFIED"),
            "environment_lock_hash": config.get(
                "environment_lock_hash", "LEGACY_TEST_UNSPECIFIED"
            ),
        }
    )
    validation = {"passed": True, "rows": len(rows), "duplicates": 0,
                  "missing_keys": 0, "schema": "certvic.cvpr.output.v2",
                  "run_contract_hash": run_contract["run_contract_hash"],
                  "prompt_template_hash": config.get("prompt_template_hash"),
                  "validation_source": "RECOMPUTED_FROM_RETURNED_BYTES"}
    failures = {"failures": [], "count": 0, "silent_drops_allowed": False}
    cleanup = {"status": "PASS" if cleanup_passed else "FAIL",
               "model_released": cleanup_passed, "shards": expected_shards,
               "paper_evidence": False}
    _write(out / "runtime_manifest.json", runtime)
    _write(out / "environment_manifest.json", environment)
    _write(out / "validation_report.json", validation)
    _write(out / "failure_report.json", failures)
    _write(out / "cleanup_report.json", cleanup)
    _write(out / "run_contract.json", run_contract)
    seed_path = out / "seed_manifest.json"
    if not seed_path.is_file():
        seed = derive_seed_manifest(
            global_seed=int(config.get("seed", 12013)),
            study=str(config.get("study", config["run_tag"])),
            provider=str(config["provider"]),
            gpu_id=0,
            shard_id=0,
            task_ids=[str(task["item_id"]) for task in tasks],
            attempts=1,
        )
        write_seed_manifest(seed_path, seed)
    snapshot_package_path: Path | None = None
    snapshot_source = Path(str(config.get("snapshot_manifest_path", "")))
    if config.get("runtime_class") in {"NON_EVIDENCE_REAL_MODEL_SMOKE", "REAL_MODEL_SMOKE"} or config.get(
        "strict_smoke_fixture"
    ) is True:
        if not snapshot_source.is_file():
            raise ValueError("real-model smoke package requires its verified snapshot manifest")
        snapshot_package_path = out / "snapshot_manifest.json"
        if snapshot_source.resolve() != snapshot_package_path.resolve():
            shutil.copyfile(snapshot_source, snapshot_package_path)
    support_paths = [out / "shard_assignment_manifest.json", *sorted(out.glob("shard_*.runtime_events.json"))]
    package_paths = [*shard_paths, merged, out / "runtime_manifest.json",
                     out / "environment_manifest.json", out / "validation_report.json",
                     out / "failure_report.json", out / "cleanup_report.json",
                     out / "run_contract.json", seed_path,
                     *([snapshot_package_path] if snapshot_package_path is not None else []),
                     *[path for path in support_paths if path.is_file()]]
    runtime_class = str(config.get("runtime_class", "SCIENTIFIC_EXECUTION"))
    synthetic_notebook_proof = config.get("synthetic_notebook_proof") is True
    permission_source: Path | None = None
    events_source: Path | None = None
    if config.get("provider_permission_path"):
        from certvic.cvpr.reconcile_provider_permissions import build_authorization_proof

        permission_source = Path(str(config["provider_permission_path"]))
        events_source = Path(str(config["provider_permission_events_path"]))
        if not permission_source.is_file() or not events_source.is_file():
            raise ValueError("provider-local permission or event chain is missing")
        if runtime_class not in {"REAL_MODEL_SMOKE", "SYNTHETIC_SMOKE"}:
            from certvic.cvpr.reconcile_provider_permissions import (
                provider_state, read_provider_events, verify_provider_permission,
            )

            final_candidate = out / f"certvic_cvpr_{config['run_tag']}_{config['provider']}.zip"
            child = verify_provider_permission(permission_source)
            if provider_state(events_source, child) == "OUTPUT_PACKAGED" and final_candidate.is_file():
                archive_validator(final_candidate)
                final_hash = hashlib.sha256(final_candidate.read_bytes()).hexdigest()
                events = read_provider_events(events_source, child)
                if events[-1].get("detail", {}).get("zip_sha256") != final_hash:
                    raise ValueError("committed package hash differs from the existing final ZIP")
                return {
                    "status": "PACKAGED_IDEMPOTENT", "rows": len(rows),
                    "zip": str(final_candidate), "zip_sha256": final_hash,
                    "promotion": promotion,
                    "packaging_recovery": {
                        "retry_allowed": False,
                        "reason": "already-valid final ZIP and matching committed hash",
                    },
                }
        if runtime_class not in {"REAL_MODEL_SMOKE", "SYNTHETIC_SMOKE"}:
            output_hashes = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in package_paths
            }
            proof = build_authorization_proof(
                permission_source,
                events_source,
                output_hashes=output_hashes,
            )
            permission_path = out / "provider_permission.json"
            permission_path.write_text(
                json.dumps(json.loads(permission_source.read_text(encoding="utf-8")), indent=2,
                           sort_keys=True) + "\n",
                encoding="utf-8",
            )
            events_path = out / "permission_events.jsonl"
            shutil.copyfile(events_source, events_path)
            proof_path = out / "authorization_proof.json"
            _write(proof_path, proof)
            package_paths.extend([permission_path, events_path, proof_path])
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in package_paths}
    _write(out / "hash_manifest.json", hashes)
    package_paths.append(out / "hash_manifest.json")
    zip_path: Path | None = None
    recovery_report: dict[str, object] | None = None
    if runtime_class in {"REAL_MODEL_SMOKE", "SYNTHETIC_SMOKE"}:
        if runtime_class == "REAL_MODEL_SMOKE" and not synthetic_notebook_proof and (
            permission_source is None or events_source is None
        ):
            raise ValueError("REAL_MODEL_SMOKE canonical packaging requires provider permission inputs")
        from certvic.cvpr.smoke_artifacts import package_smoke

        canonical = package_smoke(
            out,
            provider=str(config["provider"]),
            task_bundle_manifest=str(config["task_bundle_manifest"]),
            destination=Path(str(config.get(
                "canonical_smoke_destination",
                out / f"00C2_{config['provider']}_real_model_smoke.zip",
            ))),
            synthetic=runtime_class == "SYNTHETIC_SMOKE" or synthetic_notebook_proof,
            provider_permission=permission_source,
            permission_events=events_source,
        )
        zip_path = Path(str(canonical["archive"]))
        recovery_report = canonical.get("packaging_recovery")  # type: ignore[assignment]
    elif not config.get("defer_canonical_smoke_package"):
        zip_path = out / f"certvic_cvpr_{config['run_tag']}_{config['provider']}.zip"
        shared_permission = config.get("strict_permission_binding") is True and permission_source is None
        if shared_permission and zip_path.is_file():
            from certvic.cvpr.permission_ledger import status as ledger_status

            current = ledger_status(config["permission_ledger_path"])
            slot = current["slots"][str(config["provider"])]
            if slot["state"] == "OUTPUT_PACKAGED":
                archive_validator(zip_path)
                zip_hash = hashlib.sha256(zip_path.read_bytes()).hexdigest()
                if current["events"][-1].get("detail", {}).get("zip_sha256") != zip_hash:
                    raise ValueError("committed package hash differs from the existing final ZIP")
                return {
                    "status": "PACKAGED_IDEMPOTENT", "rows": len(rows),
                    "zip": str(zip_path), "zip_sha256": zip_hash,
                    "promotion": promotion,
                    "packaging_recovery": {
                        "retry_allowed": False,
                        "reason": "already-valid final ZIP and matching committed hash",
                    },
                }
        temporary: Path | None = None
        try:
            if shared_permission:
                from certvic.cvpr.permission_ledger import transition
                for state in ("PACKAGING_STARTED", "PACKAGE_WRITTEN"):
                    transition(
                        config["permission_ledger_path"], provider=str(config["provider"]),
                        to_state=state, permission_id=str(config["execution_permission_id"]),
                        permission_signature=str(config["execution_permission_signature"]),
                        run_tag=str(config["run_tag"]), actor="certvic.cvpr.package_run",
                    )
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{zip_path.name}.", dir=out)
            os.close(descriptor)
            temporary = Path(temporary_name)
            zip_writer(temporary, package_paths)
            archive_validator(temporary)
            with temporary.open("rb") as handle:
                os.fsync(handle.fileno())
            atomic_replace(temporary, zip_path)
            temporary = None
            _fsync_directory(out)
            zip_hash = hashlib.sha256(zip_path.read_bytes()).hexdigest()
            if permission_source is not None and events_source is not None:
                from certvic.cvpr.reconcile_provider_permissions import transition_provider_permission
                transition_provider_permission(
                    permission_source, events_source, to_state="OUTPUT_PACKAGED",
                    actor="certvic.cvpr.package_run", detail={"zip_sha256": zip_hash},
                )
            elif shared_permission:
                transition(
                    config["permission_ledger_path"], provider=str(config["provider"]),
                    to_state="OUTPUT_PACKAGED", permission_id=str(config["execution_permission_id"]),
                    permission_signature=str(config["execution_permission_signature"]),
                    run_tag=str(config["run_tag"]), actor="certvic.cvpr.package_run",
                    detail={"zip_sha256": zip_hash},
                )
        except Exception as exc:
            if permission_source is not None and events_source is not None:
                from certvic.cvpr.reconcile_provider_permissions import (
                    provider_state, transition_provider_permission,
                )
                if provider_state(events_source, json.loads(permission_source.read_text())) in {
                    "PACKAGING_STARTED", "PACKAGE_WRITTEN"
                }:
                    transition_provider_permission(
                        permission_source, events_source, to_state="PACKAGING_FAILED",
                        actor="certvic.cvpr.package_run",
                        detail={"error_type": type(exc).__name__},
                    )
            elif shared_permission:
                from certvic.cvpr.permission_ledger import status as ledger_status

                slot_state = ledger_status(config["permission_ledger_path"])["slots"][
                    str(config["provider"])
                ]["state"]
                if slot_state in {"PACKAGING_STARTED", "PACKAGE_WRITTEN"}:
                    transition(
                        config["permission_ledger_path"], provider=str(config["provider"]),
                        to_state="PACKAGING_FAILED",
                        permission_id=str(config["execution_permission_id"]),
                        permission_signature=str(config["execution_permission_signature"]),
                        run_tag=str(config["run_tag"]), actor="certvic.cvpr.package_run",
                        detail={"error_type": type(exc).__name__},
                    )
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise
    return {"status": "PACKAGED", "rows": len(rows),
            "zip": str(zip_path) if zip_path is not None else None,
            "zip_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest()
            if zip_path is not None else None,
            "promotion": promotion, "packaging_recovery": recovery_report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Package validated CertVIC CVPR VLM shards")
    parser.add_argument("--frozen-runtime-config", required=True)
    parser.add_argument("--expected-shards", type=int, required=True)
    args = parser.parse_args(argv)
    result = package(args.frozen_runtime_config, expected_shards=args.expected_shards)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
