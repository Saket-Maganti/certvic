"""Provider-local one-run permissions and offline reconciliation.

Each Kaggle session receives one immutable child permission and writes its own
hash-chained event file.  Returned ZIPs therefore need no shared Kaggle state.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import secrets
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from certvic.cvpr.content_discovery import authenticate_content_path
from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes


MATRIX_SCHEMA = "certvic.cvpr.matrix_authorization.v1"
PERMISSION_SCHEMA = "certvic.cvpr.provider_permission.v1"
EVENT_SCHEMA = "certvic.cvpr.provider_permission_event.v1"
PROOF_SCHEMA = "certvic.cvpr.provider_authorization_proof.v1"
RECONCILIATION_SCHEMA = "certvic.cvpr.provider_permission_reconciliation.v1"
STATES = (
    "ISSUED", "CLAIMED", "RUN_STARTED", "PACKAGING_STARTED", "PACKAGE_WRITTEN",
    "PACKAGING_FAILED", "OUTPUT_PACKAGED", "CONSUMED",
)
TRANSITIONS = {
    "ISSUED": {"CLAIMED"},
    "CLAIMED": {"RUN_STARTED"},
    "RUN_STARTED": {"PACKAGING_STARTED"},
    "PACKAGING_STARTED": {"PACKAGE_WRITTEN", "PACKAGING_FAILED"},
    "PACKAGE_WRITTEN": {"OUTPUT_PACKAGED", "PACKAGING_FAILED"},
    "PACKAGING_FAILED": {"PACKAGING_STARTED"},
    "OUTPUT_PACKAGED": {"CONSUMED"},
    "CONSUMED": set(),
}


class ProviderPermissionError(ValueError):
    """A matrix, child permission, provider proof, or transition is invalid."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _signature(value: Mapping[str, Any], field: str = "content_signature_sha256") -> str:
    return sha256_bytes(canonical_json_bytes({key: item for key, item in value.items() if key != field}))


def _load(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return json.loads(Path(value).read_text(encoding="utf-8"))


def _write(path: str | Path, value: Any) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def create_matrix_authorization(
    *,
    study: str,
    task_bundle_hash: str,
    final_task_manifest_hash: str,
    task_universe_sha256: str,
    edited_image_hashes_hash: str,
    review_hash: str,
    detectability_hash: str,
    environment_hash: str,
    model_registry_hash: str,
    providers: list[str],
    code_hash: str,
    prompt_template_hash: str,
    output_schema: str,
    issued_at: datetime | None = None,
    validity_hours: int = 168,
    out: str | Path | None = None,
) -> dict[str, Any]:
    """Create the immutable parent authorization shared only as read-only input."""
    hashes = {
        "task_bundle_hash": task_bundle_hash,
        "final_task_manifest_hash": final_task_manifest_hash,
        "task_universe_sha256": task_universe_sha256,
        "edited_image_hashes_hash": edited_image_hashes_hash,
        "review_hash": review_hash,
        "detectability_hash": detectability_hash,
        "environment_hash": environment_hash,
        "model_registry_hash": model_registry_hash,
        "code_hash": code_hash,
        "prompt_template_hash": prompt_template_hash,
    }
    invalid = sorted(name for name, value in hashes.items() if not _valid_sha(value))
    unique = sorted(set(map(str, providers)))
    if invalid or not unique or len(unique) != len(providers):
        raise ProviderPermissionError(
            f"matrix authorization has invalid hashes/providers: hashes={invalid}, providers={providers}"
        )
    now = issued_at or _now()
    unsigned = {
        "schema": MATRIX_SCHEMA,
        "authorization_status": "AUTHORIZED",
        "study": study,
        **hashes,
        "providers": unique,
        "output_schema": output_schema,
        "issued_at_utc": _iso(now),
        "expires_at_utc": _iso(now + timedelta(hours=validity_hours)),
        "one_run_per_provider": True,
        "paper_evidence": False,
    }
    unsigned["matrix_authorization_id"] = sha256_bytes(canonical_json_bytes(unsigned))
    result = {**unsigned, "content_signature_sha256": _signature(unsigned)}
    if out is not None:
        _write(out, result)
    return result


def create_matrix_authorization_from_paths(
    *,
    study: str,
    task_bundle_manifest: str | Path,
    bundle_root: str | Path,
    final_task_manifest: str | Path,
    final_review: str | Path,
    detectability_gate: str | Path,
    environment_lock: str | Path,
    model_registry: str | Path,
    providers: list[str],
    code_bundle: str | Path,
    prompt_template: str | Path,
    output_schema: str,
    out: str | Path | None = None,
) -> dict[str, Any]:
    """Issue the parent from trusted files without manual hash transcription."""
    from certvic.cvpr.environment_lock import environment_lock_hash
    from certvic.cvpr.task_bundle import verify_bundle

    bundle = verify_bundle(bundle_root, task_bundle_manifest)
    if Path(bundle["tasks_path"]).resolve() != Path(final_task_manifest).resolve():
        raise ProviderPermissionError("matrix final tasks are not the verified bundle task matrix")
    detectability = json.loads(Path(detectability_gate).read_text(encoding="utf-8"))
    exact = detectability.get("exact_byte_binding")
    expected_gate_hash = sha256_bytes(canonical_json_bytes({
        key: value for key, value in detectability.items() if key != "gate_hash"
    }))
    if (
        detectability.get("status") != "DETECTABILITY_GATE_PASS"
        or detectability.get("execution_allowed") is not True
        or detectability.get("exact_byte_binding_verified") is not True
        or not isinstance(exact, dict)
        or detectability.get("gate_hash") != expected_gate_hash
        or exact.get("task_bundle_hash") != bundle["bundle_hash"]
        or exact.get("final_task_manifest_sha256")
        != hashlib.sha256(Path(final_task_manifest).read_bytes()).hexdigest()
    ):
        raise ProviderPermissionError("matrix detectability gate does not bind the current frozen bytes")
    return create_matrix_authorization(
        study=study,
        task_bundle_hash=bundle["bundle_hash"],
        final_task_manifest_hash=hashlib.sha256(Path(final_task_manifest).read_bytes()).hexdigest(),
        task_universe_sha256=str(detectability["task_universe_sha256"]),
        edited_image_hashes_hash=str(exact["edited_image_hashes_sha256"]),
        review_hash=hashlib.sha256(Path(final_review).read_bytes()).hexdigest(),
        detectability_hash=str(detectability["gate_hash"]),
        environment_hash=environment_lock_hash(environment_lock),
        model_registry_hash=hashlib.sha256(Path(model_registry).read_bytes()).hexdigest(),
        providers=providers,
        code_hash=authenticate_content_path(code_bundle, "CODE"),
        prompt_template_hash=hashlib.sha256(
            (Path(prompt_template).read_bytes() if Path(prompt_template).is_file()
             else str(prompt_template).encode("utf-8"))
        ).hexdigest(),
        output_schema=output_schema,
        out=out,
    )


def verify_matrix_authorization(
    matrix: str | Path | Mapping[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    value = _load(matrix)
    if value.get("schema") != MATRIX_SCHEMA or value.get("authorization_status") != "AUTHORIZED":
        raise ProviderPermissionError("matrix authorization schema/status mismatch")
    if value.get("content_signature_sha256") != _signature(value):
        raise ProviderPermissionError("matrix authorization signature mismatch")
    without_id = {
        key: item
        for key, item in value.items()
        if key not in {"matrix_authorization_id", "content_signature_sha256"}
    }
    if value.get("matrix_authorization_id") != sha256_bytes(canonical_json_bytes(without_id)):
        raise ProviderPermissionError("matrix authorization ID mismatch")
    if value.get("one_run_per_provider") is not True or not value.get("providers"):
        raise ProviderPermissionError("matrix authorization one-run provider policy mismatch")
    for field in (
        "task_bundle_hash",
        "final_task_manifest_hash",
        "task_universe_sha256",
        "edited_image_hashes_hash",
        "review_hash",
        "detectability_hash",
        "environment_hash",
        "model_registry_hash",
        "code_hash",
        "prompt_template_hash",
    ):
        if not _valid_sha(value.get(field)):
            raise ProviderPermissionError(f"matrix authorization has invalid {field}")
    current = now or _now()
    if current.astimezone(timezone.utc) > datetime.fromisoformat(value["expires_at_utc"]):
        raise ProviderPermissionError("matrix authorization has expired")
    return value


def _verify_smoke_identity(
    smoke: Mapping[str, Any], current: Mapping[str, Any], provider: str
) -> None:
    if smoke.get("provider") != provider:
        raise ProviderPermissionError("smoke identity provider mismatch")
    if smoke.get("runtime_class") != "REAL_MODEL_SMOKE" or smoke.get("synthetic_fixture") is not False:
        raise ProviderPermissionError("scientific permission requires a non-synthetic real-model smoke")
    equalities = {
        "model_id": "model_id",
        "model_revision": "model_revision",
        "snapshot_manifest_hash": "snapshot_hash",
        "snapshot_root_hash": "snapshot_root_hash",
        "environment_manifest_hash": "environment_hash",
        "code_hash": "code_hash",
        "parser_version": "parser_version",
        "processor_model_contract": "processor_model_contract",
        "prompt_template_hash": "prompt_template_hash",
    }
    for smoke_field, current_field in equalities.items():
        expected = current.get(current_field)
        if expected is None or smoke.get(smoke_field) != expected:
            raise ProviderPermissionError(
                f"smoke/scientific semantic identity mismatch: {smoke_field}"
            )


def derive_provider_permission(
    matrix: str | Path | Mapping[str, Any],
    *,
    provider: str,
    model_id: str,
    model_revision: str,
    snapshot_hash: str,
    snapshot_root_hash: str,
    environment_hash: str,
    task_bundle_hash: str,
    run_tag: str,
    code_hash: str,
    parser_version: str,
    processor_model_contract: str,
    active_input_hashes: Mapping[str, str],
    active_scalars: Mapping[str, str],
    smoke_identity: Mapping[str, Any] | None = None,
    runtime_class: str = "SCIENTIFIC_RUN",
    run_contract_hash: str | None = None,
    prompt_template_hash: str | None = None,
    nonce: str | None = None,
    out: str | Path | None = None,
) -> dict[str, Any]:
    """Derive one provider child only after exact smoke/current equality checks."""
    parent = verify_matrix_authorization(matrix)
    if provider not in parent["providers"]:
        raise ProviderPermissionError("provider is not authorized by the parent matrix")
    current = {
        "model_id": model_id,
        "model_revision": model_revision,
        "snapshot_hash": snapshot_hash,
        "snapshot_root_hash": snapshot_root_hash,
        "environment_hash": environment_hash,
        "task_bundle_hash": task_bundle_hash,
        "run_tag": run_tag,
        "code_hash": code_hash,
        "parser_version": parser_version,
        "processor_model_contract": processor_model_contract,
        "run_contract_hash": run_contract_hash or (
            smoke_identity.get("run_contract_hash") if smoke_identity else None
        ),
        "prompt_template_hash": prompt_template_hash or parent["prompt_template_hash"],
    }
    if runtime_class not in {"SCIENTIFIC_RUN", "REAL_MODEL_SMOKE"}:
        raise ProviderPermissionError("provider permission runtime class is not authorized")
    if runtime_class == "SCIENTIFIC_RUN":
        if smoke_identity is None:
            raise ProviderPermissionError("scientific permission requires trusted smoke identity")
        _verify_smoke_identity(smoke_identity, current, provider)
    for field in ("environment_hash", "task_bundle_hash", "code_hash", "prompt_template_hash"):
        if current[field] != parent[field]:
            raise ProviderPermissionError(f"provider permission {field} differs from parent matrix")
    for field in (
        "snapshot_hash", "snapshot_root_hash", "run_contract_hash", "prompt_template_hash",
    ):
        if not _valid_sha(current[field]):
            raise ProviderPermissionError(f"provider permission has invalid {field}")
    one_run_nonce = nonce or secrets.token_hex(32)
    if not _valid_sha(one_run_nonce):
        raise ProviderPermissionError("provider one-run nonce must be 64 lowercase hex characters")
    required_roles = {
        "task_bundle_manifest", "freeze_manifest", "final_review", "smoke_gate",
        "environment_lock", "model_registry", "snapshot_manifest", "code_bundle",
        "study_config",
        "matrix_authorization",
    }
    if set(active_input_hashes) != required_roles or any(
        not _valid_sha(value) for value in active_input_hashes.values()
    ):
        raise ProviderPermissionError("provider permission active input hash matrix is incomplete")
    expected_scalars = {
        "schema_version": parent["output_schema"],
        "provider": provider,
        "run_tag": run_tag,
    }
    if any(active_scalars.get(key) != value for key, value in expected_scalars.items()):
        raise ProviderPermissionError("provider permission active scalar matrix mismatch")
    payload = {
        "schema": PERMISSION_SCHEMA,
        "authorization_status": "AUTHORIZED",
        "parent_matrix_authorization_id": parent["matrix_authorization_id"],
        "parent_matrix_signature": parent["content_signature_sha256"],
        "study": parent["study"],
        "provider": provider,
        **current,
        "final_task_manifest_hash": parent["final_task_manifest_hash"],
        "task_universe_sha256": parent["task_universe_sha256"],
        "edited_image_hashes_hash": parent["edited_image_hashes_hash"],
        "review_hash": parent["review_hash"],
        "detectability_hash": parent["detectability_hash"],
        "model_registry_hash": parent["model_registry_hash"],
        "one_run_nonce": one_run_nonce,
        "expires_at_utc": parent["expires_at_utc"],
        "output_schema": parent["output_schema"],
        "initial_state": "ISSUED",
        "active_input_hashes": dict(sorted(active_input_hashes.items())),
        "active_scalars": dict(sorted(active_scalars.items())),
        "runtime_class": runtime_class,
        "synthetic_fixture": False,
        "paper_evidence": False,
    }
    payload["permission_id"] = sha256_bytes(canonical_json_bytes(payload))
    result = {**payload, "content_signature_sha256": _signature(payload)}
    if out is not None:
        _write(out, result)
    return result


def verify_provider_permission(
    permission: str | Path | Mapping[str, Any],
    *,
    matrix: str | Path | Mapping[str, Any] | None = None,
    expected_provider: str | None = None,
    expected_run_tag: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    value = _load(permission)
    if value.get("schema") != PERMISSION_SCHEMA or value.get("authorization_status") != "AUTHORIZED":
        raise ProviderPermissionError("provider permission schema/status mismatch")
    if value.get("content_signature_sha256") != _signature(value):
        raise ProviderPermissionError("provider permission signature mismatch")
    unsigned_id = {
        key: item
        for key, item in value.items()
        if key not in {"permission_id", "content_signature_sha256"}
    }
    if value.get("permission_id") != sha256_bytes(canonical_json_bytes(unsigned_id)):
        raise ProviderPermissionError("provider permission ID mismatch")
    if value.get("runtime_class") not in {"SCIENTIFIC_RUN", "REAL_MODEL_SMOKE"} or value.get(
        "synthetic_fixture"
    ) is not False:
        raise ProviderPermissionError("provider permission is not an authorized real runtime")
    if value.get("initial_state") != "ISSUED" or not _valid_sha(value.get("one_run_nonce")):
        raise ProviderPermissionError("provider permission one-run state/nonce mismatch")
    if not isinstance(value.get("active_input_hashes"), dict) or any(
        not _valid_sha(item) for item in value["active_input_hashes"].values()
    ):
        raise ProviderPermissionError("provider permission active input hashes are invalid")
    for field in ("run_contract_hash", "prompt_template_hash"):
        if not _valid_sha(value.get(field)):
            raise ProviderPermissionError(f"provider permission has invalid {field}")
    current = now or _now()
    if current.astimezone(timezone.utc) > datetime.fromisoformat(value["expires_at_utc"]):
        raise ProviderPermissionError("provider permission has expired")
    if expected_provider is not None and value.get("provider") != expected_provider:
        raise ProviderPermissionError("provider permission provider mismatch")
    if expected_run_tag is not None and value.get("run_tag") != expected_run_tag:
        raise ProviderPermissionError("provider permission run-tag mismatch")
    if matrix is not None:
        parent = verify_matrix_authorization(matrix, now=current)
        if (
            value.get("parent_matrix_authorization_id") != parent["matrix_authorization_id"]
            or value.get("parent_matrix_signature") != parent["content_signature_sha256"]
            or value.get("provider") not in parent["providers"]
        ):
            raise ProviderPermissionError("provider permission parent matrix mismatch")
        for field in (
            "study", "task_bundle_hash", "final_task_manifest_hash", "task_universe_sha256",
            "edited_image_hashes_hash", "review_hash", "detectability_hash",
            "environment_hash", "model_registry_hash", "code_hash",
            "prompt_template_hash", "output_schema",
        ):
            if value.get(field) != parent.get(field):
                raise ProviderPermissionError(f"provider permission parent field mismatch: {field}")
    return value


def read_provider_events(path: str | Path, permission: Mapping[str, Any]) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    rows: list[dict[str, Any]] = []
    previous = "0" * 64
    state = "ISSUED"
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            continue
        row = json.loads(line)
        expected_hash = _signature(row, field="event_hash")
        if (
            row.get("schema") != EVENT_SCHEMA
            or row.get("event_hash") != expected_hash
            or row.get("previous_event_hash") != previous
            or row.get("sequence") != line_number
            or row.get("from_state") != state
            or row.get("to_state") not in TRANSITIONS[state]
            or row.get("permission_id") != permission["permission_id"]
            or row.get("permission_signature") != permission["content_signature_sha256"]
            or row.get("provider") != permission["provider"]
            or row.get("one_run_nonce") != permission["one_run_nonce"]
        ):
            raise ProviderPermissionError(f"provider permission event chain mismatch at line {line_number}")
        previous = row["event_hash"]
        state = row["to_state"]
        rows.append(row)
    return rows


def provider_state(path: str | Path, permission: Mapping[str, Any]) -> str:
    rows = read_provider_events(path, permission)
    return rows[-1]["to_state"] if rows else "ISSUED"


def transition_provider_permission(
    permission: str | Path | Mapping[str, Any],
    events_path: str | Path,
    *,
    to_state: str,
    actor: str,
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one fsync'd provider-local transition under an exclusive lock."""
    child = verify_provider_permission(permission)
    path = Path(events_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        rows = read_provider_events(path, child)
        from_state = rows[-1]["to_state"] if rows else "ISSUED"
        if to_state not in TRANSITIONS[from_state]:
            raise ProviderPermissionError(f"invalid or replayed provider transition {from_state}->{to_state}")
        event = {
            "schema": EVENT_SCHEMA,
            "sequence": len(rows) + 1,
            "provider": child["provider"],
            "study": child["study"],
            "run_tag": child["run_tag"],
            "permission_id": child["permission_id"],
            "permission_signature": child["content_signature_sha256"],
            "parent_matrix_authorization_id": child["parent_matrix_authorization_id"],
            "one_run_nonce": child["one_run_nonce"],
            "from_state": from_state,
            "to_state": to_state,
            "actor": actor,
            "detail": dict(detail or {}),
            "timestamp_utc": _iso(_now()),
            "previous_event_hash": rows[-1]["event_hash"] if rows else "0" * 64,
        }
        event["event_hash"] = _signature(event, field="event_hash")
        descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as output:
            output.write(json.dumps(event, sort_keys=True) + "\n")
            output.flush()
            os.fsync(output.fileno())
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return event


def build_authorization_proof(
    permission: str | Path | Mapping[str, Any],
    events_path: str | Path,
    *,
    output_hashes: Mapping[str, str],
    transition_output_packaged: bool = True,
) -> dict[str, Any]:
    """Finalize OUTPUT_PACKAGED and bind the returned bytes into a portable proof."""
    child = verify_provider_permission(permission)
    if not output_hashes or any(not _valid_sha(value) for value in output_hashes.values()):
        raise ProviderPermissionError("authorization proof output hashes are incomplete")
    if transition_output_packaged:
        state = provider_state(events_path, child)
        if state in {"RUN_STARTED", "PACKAGING_FAILED"}:
            transition_provider_permission(
                child, events_path, to_state="PACKAGING_STARTED",
                actor="certvic.cvpr.package_run",
            )
            state = "PACKAGING_STARTED"
        if state == "PACKAGING_STARTED":
            transition_provider_permission(
                child, events_path, to_state="PACKAGE_WRITTEN",
                actor="certvic.cvpr.package_run",
                detail={"output_hashes": dict(sorted(output_hashes.items()))},
            )
    events = read_provider_events(events_path, child)
    if not events or events[-1]["to_state"] not in {"PACKAGE_WRITTEN", "OUTPUT_PACKAGED"}:
        raise ProviderPermissionError("provider proof requires a written package state")
    events_bytes = Path(events_path).read_bytes()
    payload = {
        "schema": PROOF_SCHEMA,
        "provider": child["provider"],
        "study": child["study"],
        "run_tag": child["run_tag"],
        "parent_matrix_authorization_id": child["parent_matrix_authorization_id"],
        "permission_id": child["permission_id"],
        "permission_signature": child["content_signature_sha256"],
        "provider_permission_sha256": sha256_bytes(
            json.dumps(child, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        ),
        "one_run_nonce": child["one_run_nonce"],
        "final_state": events[-1]["to_state"],
        "final_event_hash": events[-1]["event_hash"],
        "permission_events_sha256": hashlib.sha256(events_bytes).hexdigest(),
        "output_hashes": dict(sorted(output_hashes.items())),
        "runtime_class": child["runtime_class"],
        "run_contract_hash": child["run_contract_hash"],
        "prompt_template_hash": child["prompt_template_hash"],
        "synthetic_fixture": False,
        "paper_evidence": False,
    }
    return {**payload, "content_signature_sha256": _signature(payload)}


def _zip_members(path: str | Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ProviderPermissionError("returned provider ZIP is duplicate or corrupt")
        if any(
            PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts for name in names
        ):
            raise ProviderPermissionError("returned provider ZIP contains an unsafe member")
        return {name: archive.read(name) for name in names}


def verify_provider_archive_proof(
    archive: str | Path,
    *,
    matrix: str | Path | Mapping[str, Any],
) -> dict[str, Any]:
    members = _zip_members(archive)
    required = {"provider_permission.json", "permission_events.jsonl", "authorization_proof.json"}
    by_basename: dict[str, list[str]] = {
        name: [candidate for candidate in members if PurePosixPath(candidate).name == name]
        for name in required
    }
    if any(len(candidates) != 1 for candidates in by_basename.values()):
        raise ProviderPermissionError("provider ZIP must contain one permission, event chain, and proof")
    permission_name = by_basename["provider_permission.json"][0]
    events_name = by_basename["permission_events.jsonl"][0]
    proof_name = by_basename["authorization_proof.json"][0]
    child = json.loads(members[permission_name])
    child = verify_provider_permission(child, matrix=matrix)
    with tempfile.TemporaryDirectory(prefix="certvic_provider_proof_") as temporary:
        events_path = Path(temporary) / "permission_events.jsonl"
        events_path.write_bytes(members[events_name])
        events = read_provider_events(events_path, child)
    proof = json.loads(members[proof_name])
    if proof.get("schema") != PROOF_SCHEMA or proof.get("content_signature_sha256") != _signature(proof):
        raise ProviderPermissionError("provider authorization proof signature mismatch")
    child_bytes = json.dumps(child, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    expected = {
        "provider": child["provider"],
        "parent_matrix_authorization_id": child["parent_matrix_authorization_id"],
        "permission_id": child["permission_id"],
        "permission_signature": child["content_signature_sha256"],
        "provider_permission_sha256": hashlib.sha256(child_bytes).hexdigest(),
        "permission_events_sha256": hashlib.sha256(members[events_name]).hexdigest(),
        "one_run_nonce": child["one_run_nonce"],
        "final_state": events[-1]["to_state"] if events else None,
        "final_event_hash": events[-1]["event_hash"] if events else None,
        "runtime_class": child["runtime_class"],
        "run_contract_hash": child["run_contract_hash"],
        "prompt_template_hash": child["prompt_template_hash"],
        "synthetic_fixture": False,
    }
    mismatches = {key: (value, proof.get(key)) for key, value in expected.items() if proof.get(key) != value}
    if mismatches:
        raise ProviderPermissionError(f"provider authorization proof mismatch: {mismatches}")
    if expected["final_state"] not in {"PACKAGE_WRITTEN", "OUTPUT_PACKAGED"}:
        raise ProviderPermissionError("provider archive was not produced from a written package state")
    output_hashes = proof.get("output_hashes")
    if not isinstance(output_hashes, dict) or not output_hashes:
        raise ProviderPermissionError("provider authorization proof has no output byte bindings")
    basename_members: dict[str, list[str]] = {}
    for name in members:
        basename_members.setdefault(PurePosixPath(name).name, []).append(name)
    for name, expected_hash in output_hashes.items():
        candidates = basename_members.get(str(name), [])
        if len(candidates) != 1 or hashlib.sha256(members[candidates[0]]).hexdigest() != expected_hash:
            raise ProviderPermissionError(f"provider proof output hash mismatch: {name}")
    return {
        "provider": child["provider"],
        "permission_id": child["permission_id"],
        "one_run_nonce": child["one_run_nonce"],
        "run_contract_hash": child["run_contract_hash"],
        "prompt_template_hash": child["prompt_template_hash"],
        "archive_sha256": hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
        "final_event_hash": events[-1]["event_hash"],
        "proof_signature": proof["content_signature_sha256"],
        "permission": child,
        "proof": proof,
    }


def reconcile_provider_permissions(
    matrix: str | Path | Mapping[str, Any],
    archives: Mapping[str, str | Path],
    *,
    consumed_nonces: set[str] | None = None,
) -> dict[str, Any]:
    """Verify all provider ZIP proofs against one immutable parent authorization."""
    parent = verify_matrix_authorization(matrix)
    expected = set(parent["providers"])
    if set(archives) != expected:
        raise ProviderPermissionError("returned provider ZIP matrix is incomplete or unexpected")
    rows = [verify_provider_archive_proof(archives[provider], matrix=parent) for provider in sorted(expected)]
    if {row["provider"] for row in rows} != expected:
        raise ProviderPermissionError("returned provider identity differs from ZIP mapping")
    nonces = [row["one_run_nonce"] for row in rows]
    archive_hashes = [row["archive_sha256"] for row in rows]
    if len(set(nonces)) != len(nonces) or len(set(archive_hashes)) != len(archive_hashes):
        raise ProviderPermissionError("duplicated provider ZIP or one-run nonce")
    replayed = sorted(set(nonces) & set(consumed_nonces or set()))
    if replayed:
        raise ProviderPermissionError(f"provider nonce was already consumed: {replayed}")
    safe_rows = [{key: value for key, value in row.items() if key not in {"permission", "proof"}} for row in rows]
    result = {
        "schema": RECONCILIATION_SCHEMA,
        "status": "PROVIDER_PERMISSIONS_RECONCILED",
        "matrix_authorization_id": parent["matrix_authorization_id"],
        "study": parent["study"],
        "providers": safe_rows,
        "provider_nonces": sorted(nonces),
        "paper_evidence": False,
    }
    result["reconciliation_hash"] = sha256_bytes(canonical_json_bytes(result))
    return result


def proof_report(verified: Mapping[str, Any]) -> str:
    return (
        f"# Provider authorization proof: {verified['provider']}\n\n"
        f"- Permission: `{verified['permission_id']}`\n"
        f"- One-run nonce: `{verified['one_run_nonce']}`\n"
        f"- Returned ZIP SHA-256: `{verified['archive_sha256']}`\n"
        f"- Final provider-local state: `OUTPUT_PACKAGED`\n"
        f"- Final event: `{verified['final_event_hash']}`\n"
        "- Synthetic fixture: `false`\n"
        "- Paper evidence: `false`\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile provider-local CertVIC permissions")
    sub = parser.add_subparsers(dest="command", required=True)
    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--matrix", required=True)
    reconcile.add_argument("--provider-zip", action="append", required=True)
    reconcile.add_argument("--out", required=True)
    issue = sub.add_parser("issue-matrix")
    issue.add_argument("--inputs-json")
    issue.add_argument("--study")
    issue.add_argument("--task-bundle-manifest")
    issue.add_argument("--bundle-root")
    issue.add_argument("--final-task-manifest")
    issue.add_argument("--final-review")
    issue.add_argument("--detectability-gate")
    issue.add_argument("--environment-lock")
    issue.add_argument("--model-registry")
    issue.add_argument("--providers", nargs="+")
    issue.add_argument("--code-bundle")
    issue.add_argument("--prompt-template")
    issue.add_argument("--output-schema", default="certvic.cvpr.output.v2")
    issue.add_argument("--out", required=True)
    derive = sub.add_parser("derive-provider")
    derive.add_argument("--matrix", required=True)
    derive.add_argument("--provider-config", required=True)
    derive.add_argument("--smoke-gate", required=True)
    derive.add_argument("--out", required=True)
    view = sub.add_parser("view")
    view.add_argument("--matrix", required=True)
    view.add_argument("--archive", required=True)
    view.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        if args.command == "reconcile":
            archives = dict(value.split("=", 1) for value in args.provider_zip)
            result = reconcile_provider_permissions(args.matrix, archives)
            _write(args.out, result)
            output: Any = {"status": result["status"], "out": args.out}
        elif args.command == "issue-matrix":
            if args.inputs_json:
                inputs = json.loads(Path(args.inputs_json).read_text(encoding="utf-8"))
                result = create_matrix_authorization(**inputs, out=args.out)
            else:
                required = {
                    "study": args.study,
                    "task_bundle_manifest": args.task_bundle_manifest,
                    "bundle_root": args.bundle_root,
                    "final_task_manifest": args.final_task_manifest,
                    "final_review": args.final_review,
                    "detectability_gate": args.detectability_gate,
                    "environment_lock": args.environment_lock,
                    "model_registry": args.model_registry,
                    "providers": args.providers,
                    "code_bundle": args.code_bundle,
                    "prompt_template": args.prompt_template,
                }
                missing = [name for name, value in required.items() if not value]
                if missing:
                    raise ProviderPermissionError(f"issue-matrix path inputs are missing: {missing}")
                result = create_matrix_authorization_from_paths(
                    **required,
                    output_schema=args.output_schema,
                    out=args.out,
                )
            output = {
                "status": "MATRIX_AUTHORIZATION_ISSUED",
                "matrix_authorization_id": result["matrix_authorization_id"],
                "out": args.out,
            }
        elif args.command == "derive-provider":
            config = json.loads(Path(args.provider_config).read_text(encoding="utf-8"))
            if "active_input_paths" in config:
                config["active_input_hashes"] = {
                    role: (
                        authenticate_content_path(path, "CODE")
                        if role == "code_bundle"
                        else hashlib.sha256(Path(path).read_bytes()).hexdigest()
                    )
                    for role, path in config.pop("active_input_paths").items()
                }
            smoke_gate = json.loads(Path(args.smoke_gate).read_text(encoding="utf-8"))
            provider = str(config["provider"])
            matches = [row for row in smoke_gate.get("models", []) if row.get("model") == provider]
            if len(matches) != 1 or matches[0].get("status") != "PASS":
                raise ProviderPermissionError("provider does not have one PASS row in the smoke gate")
            result = derive_provider_permission(
                args.matrix, **config, smoke_identity=matches[0], out=args.out
            )
            output = {
                "status": "PROVIDER_PERMISSION_ISSUED",
                "provider": provider,
                "permission_id": result["permission_id"],
                "out": args.out,
            }
        else:
            result = verify_provider_archive_proof(args.archive, matrix=args.matrix)
            report = proof_report(result)
            if args.out:
                Path(args.out).write_text(report, encoding="utf-8")
            output = {"status": "PROVIDER_PROOF_VALID", "provider": result["provider"]}
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "PROVIDER_PERMISSION_RECONCILIATION_BLOCKED", "reason": str(exc)}))
        return 2
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
