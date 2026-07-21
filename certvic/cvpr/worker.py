"""Contract-validating, batch-aware, resume-safe single-device CVPR worker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from certvic.cvpr.adapters import BaseAdapter, load_adapter
from certvic.cvpr.contracts import (
    COMMIT_RE,
    OUTPUT_FIELDS,
    OutputContract,
    canonical_json_bytes,
    sha256_bytes,
    validate_output_rows,
)
from certvic.cvpr.run_contract import build_run_contract
from certvic.cvpr.task_schema import require_task_matrix, resolve_task_path
from certvic.cvpr.environment_lock import environment_lock_hash
from certvic.cvpr.model_snapshot_manifest import verify_manifest
from certvic.cvpr.transactional import TransactionError, promote_jsonl, read_jsonl
from certvic.eval.parse import parse_answer_record


def _load_config(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("runtime config must be a JSON object")
    for field in (
        "provider", "model_id", "model_commit", "processor_commit", "run_tag",
        "task_manifest", "output_dir", "code_bundle_hash", "seed", "generation_parameters",
    ):
        if field not in value:
            raise ValueError(f"runtime config missing {field}")
    for field in ("model_commit", "processor_commit"):
        if not COMMIT_RE.fullmatch(str(value[field])):
            raise ValueError(f"{field} must be a 40-character immutable commit")
    if len(str(value["code_bundle_hash"])) != 64 or any(
        character not in "0123456789abcdef" for character in str(value["code_bundle_hash"])
    ):
        raise ValueError("code_bundle_hash must be SHA-256")
    if value.get("strict_run_contract") is True:
        strict_fields = {
            "study", "runtime_class", "processor_id", "model_path", "snapshot_manifest_path",
            "expected_architecture", "model_snapshot_manifest_hash",
                "processor_snapshot_manifest_hash", "snapshot_status",
            "environment_lock_path",
            "environment_lock_hash", "prompt_template_id", "prompt_template_hash",
            "prompt_template",
            "parser_version", "output_schema",
            "snapshot_contract",
            "task_bundle_root", "task_bundle_manifest",
            }
        if value.get("runtime_class") in {
            "REAL_MODEL_SMOKE", "SCIENTIFIC_RUN", "NON_EVIDENCE_REAL_MODEL_SMOKE",
        }:
            strict_fields |= {"snapshot_root_hash", "task_bundle_hash"}
        missing_strict = sorted(strict_fields - set(value))
        if missing_strict:
            raise ValueError(f"strict runtime config missing fields: {missing_strict}")
        if sha256_bytes(str(value["prompt_template"]).encode()) != value["prompt_template_hash"]:
            raise ValueError("prompt_template_hash does not match the exact active prompt template")
        if value["snapshot_status"] != "LOCAL_SNAPSHOT_BYTES_VERIFIED":
            raise ValueError("offline scientific worker requires LOCAL_SNAPSHOT_BYTES_VERIFIED")
        if value["snapshot_contract"] != "UNIFIED_SNAPSHOT":
            raise ValueError("offline scientific worker requires the unified snapshot contract")
        if value["model_snapshot_manifest_hash"] != value["processor_snapshot_manifest_hash"]:
            raise ValueError("unified model/processor snapshot hashes differ")
        snapshot_manifest = Path(str(value["snapshot_manifest_path"]))
        if not snapshot_manifest.is_file() or sha256_bytes(snapshot_manifest.read_bytes()) != value[
            "model_snapshot_manifest_hash"
        ]:
            raise ValueError("snapshot manifest file hash mismatch")
        snapshot = verify_manifest(
            value["model_path"], snapshot_manifest, expected_model_id=value["model_id"],
            expected_model_commit=value["model_commit"],
            expected_processor_commit=value["processor_commit"],
            expected_architecture=value["expected_architecture"],
        )
        if not snapshot["passed"]:
            raise ValueError("snapshot byte verification failed: " + "; ".join(snapshot["errors"]))
        if "snapshot_root_hash" in value:
            snapshot_value = json.loads(snapshot_manifest.read_text(encoding="utf-8"))
            if snapshot_value.get("unified_snapshot_root_sha256") != value["snapshot_root_hash"]:
                raise ValueError("snapshot root hash differs from the verified manifest")
        if environment_lock_hash(value["environment_lock_path"]) != value["environment_lock_hash"]:
            raise ValueError("environment lock content hash mismatch")
        if value.get("runtime_class") in {"SCIENTIFIC_EXECUTION", "SCIENTIFIC_RUN"}:
            for field in ("execution_permission_id", "execution_permission_signature"):
                if len(str(value.get(field, ""))) != 64:
                    raise ValueError(f"scientific runtime requires hash-bound {field}")
        if value.get("strict_permission_binding") is True:
            permission_fields = (
                {
                    "provider_permission_path",
                    "provider_permission_events_path",
                    "permission_binding",
                    "notebook_name",
                    "matrix_authorization",
                }
                if value.get("provider_permission_path")
                else {
                    "execution_permission_path", "permission_input_paths", "permission_ledger_path",
                    "task_bundle_root", "task_bundle_manifest", "notebook_name",
                }
            )
            missing_permission = sorted(permission_fields - set(value))
            if missing_permission:
                raise ValueError(f"strict permission runtime missing fields: {missing_permission}")
    return value


def _tasks(
    path: str | Path, *, bundle_root: str | Path | None = None,
    task_bundle_manifest: str | Path | None = None,
    task_bundle_hash: str | None = None,
) -> list[dict[str, Any]]:
    if task_bundle_manifest is not None:
        from certvic.cvpr.task_bundle import verify_bundle
        verified = verify_bundle(bundle_root or Path(task_bundle_manifest).parent, task_bundle_manifest)
        if task_bundle_hash is not None and verified["bundle_hash"] != task_bundle_hash:
            raise ValueError("runtime task bundle hash differs from verified task bundle")
        if Path(verified["tasks_path"]).resolve() != Path(path).resolve():
            raise ValueError("runtime task manifest differs from verified task bundle")
    rows = read_jsonl(path)
    ids = [str(row.get("item_id", "")) for row in rows]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("task manifest has blank or duplicate item IDs")
    if task_bundle_manifest is not None:
        require_task_matrix(rows, verify_files=True, bundle_root=bundle_root)
    return rows


def _prompt(
    task: dict[str, Any], variant: str, *, prompt_template: str | None = None
) -> str:
    prompts = task.get("prompts", {})
    prompt = prompts.get(variant) if isinstance(prompts, dict) else None
    prompt = prompt or task.get("prompt") or task.get("question")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"{task.get('item_id')}: missing prompt")
    template = prompt_template or "{prompt}"
    try:
        rendered = template.format(prompt=prompt, question=prompt, variant=variant)
    except (KeyError, ValueError) as exc:
        raise ValueError("prompt template cannot be rendered from the frozen fields") from exc
    if not rendered.strip():
        raise ValueError(f"{task.get('item_id')}: rendered prompt is empty")
    return rendered


def _image(
    task: dict[str, Any], variant: str, *, bundle_root: str | Path | None = None,
) -> str:
    key = "original_image_path" if variant == "original" else "edited_image_path"
    value = task.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{task.get('item_id')}: missing {key}")
    path = resolve_task_path(task, key, bundle_root=bundle_root)
    assert path is not None
    return str(path)


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _estimated_cost(task: dict[str, Any]) -> float:
    explicit = task.get("estimated_cost")
    if explicit is not None:
        return max(0.001, float(explicit))
    width = float(task.get("image_width", 1))
    height = float(task.get("image_height", 1))
    return max(1.0, width * height)


def assignment_manifest(tasks: list[dict[str, Any]], num_shards: int) -> dict[str, Any]:
    if num_shards < 1:
        raise ValueError("num_shards must be positive")
    loads = [0.0] * num_shards
    assignments: dict[str, int] = {}
    ordered = sorted(
        tasks,
        key=lambda task: (-_estimated_cost(task), hashlib.sha256(str(task["item_id"]).encode()).hexdigest()),
    )
    for task in ordered:
        shard = min(range(num_shards), key=lambda index: (loads[index], index))
        assignments[str(task["item_id"])] = shard
        loads[shard] += _estimated_cost(task)
    return {
        "schema": "certvic.cvpr.shard_assignment.v1",
        "num_shards": num_shards,
        "assignments": dict(sorted(assignments.items())),
        "estimated_loads": loads,
        "task_manifest_sha256": sha256_bytes(canonical_json_bytes(tasks)),
    }


def _contract(config: dict[str, Any], tasks: list[dict[str, Any]]) -> OutputContract:
    run_contract_hash = config.get("_resolved_run_contract_hash")
    if not run_contract_hash:
        run_contract_hash = _run_contract(config, tasks)["run_contract_hash"]
    return OutputContract(
        provider=str(config["provider"]),
        run_tag=str(config["run_tag"]),
        model_commit=str(config["model_commit"]),
        processor_commit=str(config["processor_commit"]),
        item_ids=tuple(str(task["item_id"]) for task in tasks),
        bundle_sha256=str(config["code_bundle_hash"]),
        run_contract_hash=str(run_contract_hash),
        prompt_template_hash=(str(config["prompt_template_hash"])
                              if config.get("prompt_template_hash") else None),
        strict_provenance=bool(config.get("strict_run_contract", False)),
    )


def _run_contract(config: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the exact contract used for rows and resume validation."""
    return build_run_contract(
        config,
        task_manifest_sha256=sha256_bytes(canonical_json_bytes(tasks)),
        strict=bool(config.get("strict_run_contract", False)),
    )


def _expected_values(
    task: dict[str, Any], variant: str, *, mock_runtime: bool,
    bundle_root: str | Path | None = None,
    prompt_template: str | None = None,
    prompt_template_hash: str | None = None,
) -> dict[str, str]:
    prompt = _prompt(task, variant, prompt_template=prompt_template)
    image_path = _image(task, variant, bundle_root=bundle_root)
    if mock_runtime:
        path = Path(image_path)
        image_hash = sha256_bytes(path.read_bytes()) if path.is_file() else sha256_bytes(image_path.encode())
    else:
        path = Path(image_path)
        if not path.is_file():
            raise ValueError(f"missing image: {path}")
        image_hash = sha256_bytes(path.read_bytes())
    return {
        "prompt_hash": sha256_bytes(prompt.encode()),
        "prompt_template_hash": str(prompt_template_hash or ""),
        "image_hash": image_hash,
        "task_hash": str(task.get("task_hash") or sha256_bytes(canonical_json_bytes(task))),
    }


def _validate_prior_rows(
    rows: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    mock_runtime: bool,
    require_complete: bool,
) -> list[str]:
    errors: list[str] = []
    task_map = {str(task["item_id"]): task for task in tasks}
    seen: set[tuple[str, str]] = set()
    contract = _contract(config, tasks)
    for index, row in enumerate(rows, start=1):
        required = OUTPUT_FIELDS | {"run_contract_hash"}
        missing = sorted(required - set(row))
        if missing:
            errors.append(f"row {index}: missing fields {missing}")
            continue
        key = str(row["item_id"]), str(row["variant"])
        if key in seen:
            errors.append(f"row {index}: duplicate key {key}")
        seen.add(key)
        if key not in contract.expected_keys:
            errors.append(f"row {index}: unexpected key {key}")
            continue
        if row["provider"] != contract.provider or row["run_tag"] != contract.run_tag:
            errors.append(f"row {index}: provider or run tag mismatch")
        if row["model_commit"] != contract.model_commit:
            errors.append(f"row {index}: model commit mismatch")
        if row["processor_commit"] != contract.processor_commit:
            errors.append(f"row {index}: processor commit mismatch")
        if row["code_bundle_hash"] != contract.bundle_sha256:
            errors.append(f"row {index}: code bundle hash mismatch")
        if row["run_contract_hash"] != contract.run_contract_hash:
            errors.append(f"row {index}: run contract hash mismatch")
        try:
            expected = _expected_values(
                task_map[key[0]], key[1], mock_runtime=mock_runtime,
                bundle_root=config.get("task_bundle_root"),
                prompt_template=config.get("prompt_template"),
                prompt_template_hash=config.get("prompt_template_hash"),
            )
        except (KeyError, ValueError) as exc:
            errors.append(f"row {index}: cannot reconstruct expected values: {exc}")
            continue
        for field, value in expected.items():
            if row[field] != value:
                errors.append(f"row {index}: {field} mismatch")
    if require_complete:
        errors.extend(validate_output_rows(rows, contract))
    return errors


def _quarantine(path: Path, errors: list[str], *, reason: str = "contract_mismatch") -> Path:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = path.parent / "quarantine" / reason / stamp / f"{path.name}.{digest}"
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(path, target)
    _atomic_json(target.with_suffix(target.suffix + ".errors.json"), {"errors": errors})
    # Backward-compatible, content-free pointer for older operational tooling.
    _atomic_json(path.with_name(f"{path.name}.quarantine.{digest}.pointer.json"), {
        "quarantined_path": str(target.relative_to(path.parent)), "reason": reason,
    })
    return target


def _is_oom(exc: BaseException) -> bool:
    return "out of memory" in str(exc).lower() or exc.__class__.__name__ == "OutOfMemoryError"


def _clear_cuda() -> str:
    torch = sys.modules.get("torch")
    if torch is None or not torch.cuda.is_available():
        return "NOT_APPLICABLE"
    try:
        torch.cuda.empty_cache()
    except Exception:
        return "FAIL"
    return "PASS"


def _peak_vram_gib() -> float:
    torch = sys.modules.get("torch")
    if torch is None or not torch.cuda.is_available():
        return 0.0
    return float(torch.cuda.max_memory_allocated() / (1024**3))


def _record(
    task: dict[str, Any],
    variant: str,
    raw: str,
    config: dict[str, Any],
    shard: int,
    *,
    mock_runtime: bool,
    run_contract: dict[str, Any],
) -> dict[str, Any]:
    parsed = parse_answer_record(raw, str(task.get("answer_format", "yes_no")))
    expected = _expected_values(
        task, variant, mock_runtime=mock_runtime, bundle_root=config.get("task_bundle_root"),
        prompt_template=config.get("prompt_template"),
        prompt_template_hash=config.get("prompt_template_hash"),
    )
    return {
        "item_id": task["item_id"],
        "variant": variant,
        "raw_response": raw,
        "parsed_response": parsed["parsed_response"],
        "parse_status": parsed["parse_status"],
        "provider": config["provider"],
        "model_id": config["model_id"],
        "processor_id": config.get("processor_id", config["model_id"]),
        "model_commit": config["model_commit"],
        "processor_commit": config["processor_commit"],
        **expected,
        "code_bundle_hash": config["code_bundle_hash"],
        "model_snapshot_manifest_hash": config.get("model_snapshot_manifest_hash"),
        "processor_snapshot_manifest_hash": config.get(
            "processor_snapshot_manifest_hash", config.get("model_snapshot_manifest_hash")
        ),
        "snapshot_status": config.get("snapshot_status", "LEGACY_TEST_UNSPECIFIED"),
        "snapshot_contract": run_contract["snapshot_contract"],
        "environment_lock_hash": config.get("environment_lock_hash", "LEGACY_TEST_UNSPECIFIED"),
        "output_schema": config.get("output_schema", "certvic.cvpr.output.v2"),
        "run_contract_hash": run_contract["run_contract_hash"],
        "seed": config["seed"],
        "generation_parameters": config["generation_parameters"],
        "shard": shard,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_tag": config["run_tag"],
        "parser_version": parsed["parser_version"],
        "task_bundle_hash": config.get("task_bundle_hash"),
    }


def run_shard(
    config_path: str | Path,
    *,
    shard: int,
    num_shards: int,
    mock_runtime: bool,
    resume: bool = True,
    batch_size: int = 1,
    oom_reduce_to_one: bool = True,
    fail_closed: bool = True,
    adapter_factory: Callable[[str, dict[str, Any]], BaseAdapter] = load_adapter,
) -> dict[str, Any]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    config = _load_config(config_path)
    all_tasks = _tasks(
        config["task_manifest"], bundle_root=config.get("task_bundle_root"),
        task_bundle_manifest=config.get("task_bundle_manifest"),
        task_bundle_hash=config.get("task_bundle_hash"),
    )
    if config.get("runtime_class") in {
        "SCIENTIFIC_EXECUTION", "NON_EVIDENCE_REAL_MODEL_SMOKE",
        "SYNTHETIC_END_TO_END_FIXTURE", "SCIENTIFIC_RUN", "REAL_MODEL_SMOKE",
        "SYNTHETIC_SMOKE",
    }:
        require_task_matrix(
            all_tasks, verify_files=not mock_runtime,
            bundle_root=config.get("task_bundle_root"),
        )
    run_contract = _run_contract(config, all_tasks)
    config["_resolved_run_contract_hash"] = run_contract["run_contract_hash"]
    if config.get("strict_permission_binding") is True:
        if config.get("provider_permission_path"):
            from certvic.cvpr.notebook_permission_binding import assert_runtime_binding
            from certvic.cvpr.reconcile_provider_permissions import (
                provider_state,
                transition_provider_permission,
                verify_provider_permission,
            )

            assert_runtime_binding(config["permission_binding"], config)
            child = verify_provider_permission(
                config["provider_permission_path"],
                matrix=config.get("matrix_authorization"),
                expected_provider=str(config["provider"]),
                expected_run_tag=str(config["run_tag"]),
            )
            if (
                child["permission_id"] != config.get("execution_permission_id")
                or child["content_signature_sha256"] != config.get(
                    "execution_permission_signature"
                )
                or child["task_bundle_hash"] != config.get("task_bundle_hash")
                or child["environment_hash"] != config.get("environment_lock_hash")
                or child["code_hash"] != config.get("code_bundle_hash")
                or child["prompt_template_hash"] != config.get("prompt_template_hash")
                or child["run_contract_hash"] != run_contract["run_contract_hash"]
                or child["active_input_hashes"] != config["permission_binding"]["input_hashes"]
                or child["active_scalars"] != config["permission_binding"]["scalars"]
            ):
                raise ValueError("provider permission identity differs from the active worker runtime")
            state = provider_state(config["provider_permission_events_path"], child)
            if state == "CLAIMED":
                transition_provider_permission(
                    child,
                    config["provider_permission_events_path"],
                    to_state="RUN_STARTED",
                    actor="certvic.cvpr.worker",
                    detail={"num_shards": num_shards},
                )
            elif state != "RUN_STARTED":
                raise ValueError(f"provider permission cannot start worker from {state}")
        else:
            from certvic.cvpr.execution_gate import verify_permission
            from certvic.cvpr.permission_ledger import (
                PermissionLedgerError, status as ledger_status, transition, verify_slot,
            )
            permission = verify_permission(
                config["execution_permission_path"], study=str(config["study"]),
                allow_synthetic=config.get("runtime_class") == "SYNTHETIC_END_TO_END_FIXTURE",
                input_paths={str(role): str(path) for role, path in config["permission_input_paths"].items()},
                expected_code_hash=str(config["code_bundle_hash"]),
                expected_provider=str(config["provider"]), expected_run_tag=str(config["run_tag"]),
                expected_output_schema=str(config["output_schema"]),
            )
            if permission["permission_id"] != config.get("execution_permission_id") or permission[
                "content_signature_sha256"
            ] != config.get("execution_permission_signature"):
                raise ValueError("runtime permission identity differs from current signed artifact")
            ledger = ledger_status(config["permission_ledger_path"])
            slot = ledger["slots"].get(str(config["provider"]), {})
            if slot.get("state") == "CLAIMED":
                try:
                    transition(
                        config["permission_ledger_path"], provider=str(config["provider"]),
                        to_state="RUN_STARTED", permission_id=permission["permission_id"],
                        permission_signature=permission["content_signature_sha256"],
                        run_tag=str(config["run_tag"]), actor="certvic.cvpr.worker",
                        detail={"num_shards": num_shards},
                    )
                except PermissionLedgerError:
                    verify_slot(
                        config["permission_ledger_path"], provider=str(config["provider"]),
                        required_state="RUN_STARTED", permission_id=permission["permission_id"],
                        permission_signature=permission["content_signature_sha256"],
                        run_tag=str(config["run_tag"]),
                    )
            else:
                verify_slot(
                    config["permission_ledger_path"], provider=str(config["provider"]),
                    required_state="RUN_STARTED", permission_id=permission["permission_id"],
                    permission_signature=permission["content_signature_sha256"],
                    run_tag=str(config["run_tag"]),
                )
    assignment = assignment_manifest(all_tasks, num_shards)
    out = Path(config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    assignment_path = out / "shard_assignment_manifest.json"
    if assignment_path.exists():
        if json.loads(assignment_path.read_text(encoding="utf-8")) != assignment:
            raise TransactionError("existing shard assignment conflicts with current task contract")
    else:
        _atomic_json(assignment_path, assignment)
    tasks = [task for task in all_tasks if assignment["assignments"][str(task["item_id"])] == shard]
    partial = out / f"shard_{shard}.partial.jsonl"
    completed = out / f"shard_{shard}.complete.jsonl"
    event_path = out / f"shard_{shard}.runtime_events.json"
    events: list[dict[str, Any]] = []
    if completed.exists():
        try:
            complete_rows = read_jsonl(completed)
            errors = _validate_prior_rows(
                complete_rows, tasks, config, mock_runtime=mock_runtime, require_complete=True
            )
        except TransactionError as exc:
            errors = [str(exc)]
            complete_rows = []
        if not errors:
            return {"status": "SHARD_ALREADY_COMPLETE", "shard": shard,
                    "rows": len(complete_rows), "prior_validation": "PASS"}
        if not resume:
            raise TransactionError("invalid completed shard exists and --resume was not enabled")
        quarantined = _quarantine(completed, errors)
        events.append({"event": "QUARANTINED_COMPLETE", "path": str(quarantined), "errors": errors})
    existing: list[dict[str, Any]] = []
    if partial.exists():
        if not resume:
            raise TransactionError("partial shard exists; enable --resume or move it explicitly")
        try:
            existing = read_jsonl(partial)
            errors = _validate_prior_rows(
                existing, tasks, config, mock_runtime=mock_runtime, require_complete=False
            )
        except TransactionError as exc:
            errors = [str(exc)]
        if errors:
            quarantined = _quarantine(partial, errors)
            events.append({"event": "QUARANTINED_PARTIAL", "path": str(quarantined),
                           "errors": errors})
            existing = []
    done = {(str(row["item_id"]), str(row["variant"])) for row in existing}
    pending = [(task, variant) for task in tasks for variant in ("original", "edited")
               if (str(task["item_id"]), variant) not in done]
    adapter = None if mock_runtime else adapter_factory(str(config["provider"]), config)
    if adapter is not None:
        events.append({"event": "ADAPTER_PREPARE", "capabilities": adapter.prepare()})
    effective_batch = min(batch_size, max(1, len(pending)))
    failures: list[dict[str, Any]] = []
    try:
        with partial.open("a", encoding="utf-8") as handle:
            index = 0
            while index < len(pending):
                chunk = pending[index:index + effective_batch]
                started = time.monotonic()
                try:
                    if mock_runtime:
                        raws = [str(task.get("mock_raw_response", "yes")) for task, _ in chunk]
                    else:
                        requests = [(_image(
                            task, variant, bundle_root=config.get("task_bundle_root")
                        ), _prompt(
                            task, variant, prompt_template=config.get("prompt_template")
                        ))
                                    for task, variant in chunk]
                        raws = adapter.generate_batch(requests)  # type: ignore[union-attr]
                    if len(raws) != len(chunk):
                        raise RuntimeError("adapter batch returned the wrong number of outputs")
                except Exception as exc:
                    if _is_oom(exc) and oom_reduce_to_one:
                        events.append({"event": "CUDA_OOM", "batch_size": effective_batch,
                                       "pending_index": index, "error": str(exc)})
                        _clear_cuda()
                        if adapter is not None:
                            adapter.release()
                        if effective_batch == 1:
                            raise RuntimeError("CUDA OOM persisted at batch size 1; shard is partial") from exc
                        effective_batch = max(1, effective_batch // 2)
                        if adapter is not None:
                            events.append({"event": "ADAPTER_RELOAD_AFTER_OOM",
                                           "capabilities": adapter.prepare()})
                        continue
                    failure = {"event": "BATCH_FAILURE", "pending_index": index,
                               "batch_size": effective_batch, "error": str(exc)}
                    events.append(failure)
                    failures.append(failure)
                    if fail_closed:
                        raise
                    index += len(chunk)
                    continue
                elapsed = time.monotonic() - started
                events.append({"event": "BATCH_COMPLETE", "requested_batch_size": batch_size,
                               "effective_batch_size": effective_batch,
                               "items": len(chunk), "duration_seconds": elapsed})
                for (task, variant), raw in zip(chunk, raws, strict=True):
                    record = _record(
                            task, variant, raw, config, shard, mock_runtime=mock_runtime,
                        run_contract=run_contract,
                    )
                    handle.write(json.dumps(record, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                    existing.append(record)
                index += len(chunk)
    except Exception as exc:
        if config.get("strict_permission_binding") is True and not config.get(
            "provider_permission_path"
        ):
            from certvic.cvpr.permission_ledger import transition
            transition(
                config["permission_ledger_path"], provider=str(config["provider"]),
                to_state="FAILED", permission_id=str(config["execution_permission_id"]),
                permission_signature=str(config["execution_permission_signature"]),
                run_tag=str(config["run_tag"]), actor="certvic.cvpr.worker",
                detail={"error_type": type(exc).__name__, "shard": shard},
            )
        raise
    finally:
        model_release_status = "PASS"
        if adapter is not None:
            try:
                adapter.release()
            except Exception:
                model_release_status = "FAIL"
        peak_vram_gib = _peak_vram_gib()
        cuda_cleanup_status = _clear_cuda()
        events.append({"event": "MODEL_RELEASED", "model_released": model_release_status == "PASS",
                       "status": model_release_status,
                       "peak_vram_gib": peak_vram_gib})
        events.append({"event": "CUDA_CLEANUP", "status": cuda_cleanup_status})
        _atomic_json(event_path, {
            "requested_batch_size": batch_size,
            "final_effective_batch_size": effective_batch,
            "resume": resume,
            "oom_reduce_to_one": oom_reduce_to_one,
            "fail_closed": fail_closed,
            "events": events,
            "failures": failures,
        })
    if failures:
        if config.get("strict_permission_binding") is True and not config.get(
            "provider_permission_path"
        ):
            from certvic.cvpr.permission_ledger import transition
            transition(
                config["permission_ledger_path"], provider=str(config["provider"]),
                to_state="FAILED", permission_id=str(config["execution_permission_id"]),
                permission_signature=str(config["execution_permission_signature"]),
                run_tag=str(config["run_tag"]), actor="certvic.cvpr.worker",
                detail={"recorded_failures": len(failures), "shard": shard},
            )
        return {"status": "SHARD_PARTIAL_WITH_RECORDED_FAILURES", "shard": shard,
                "rows": len(existing), "failures": len(failures)}
    promotion = promote_jsonl(existing, completed, _contract(config, tasks))
    return {
        "status": "SHARD_COMPLETE",
        "shard": shard,
        "rows": len(existing),
        "promotion": promotion,
        "mock_runtime": mock_runtime,
        "requested_batch_size": batch_size,
        "effective_batch_size": effective_batch,
        "oom_events": sum(event["event"] == "CUDA_OOM" for event in events),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CertVIC CVPR deterministic shard worker")
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--num-shards", type=int, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--oom-reduce-to-one", action="store_true")
    parser.add_argument("--fail-closed", action="store_true")
    parser.add_argument("--frozen-runtime-config", required=True)
    parser.add_argument("--mock-runtime", action="store_true")
    args = parser.parse_args(argv)
    if not 0 <= args.shard < args.num_shards:
        raise SystemExit("invalid shard index")
    result = run_shard(
        args.frozen_runtime_config,
        shard=args.shard,
        num_shards=args.num_shards,
        mock_runtime=args.mock_runtime,
        resume=args.resume,
        batch_size=args.batch_size,
        oom_reduce_to_one=args.oom_reduce_to_one,
        fail_closed=args.fail_closed,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {"SHARD_COMPLETE", "SHARD_ALREADY_COMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
