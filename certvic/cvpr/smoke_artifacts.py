"""Canonical, deterministic artifacts for the real Kaggle smoke handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes


ARTIFACT_SCHEMA = "certvic.cvpr.smoke_artifact.v1"
HASH_SCHEMA = "certvic.cvpr.smoke_hash_manifest.v1"
PROOF_SCHEMA = "certvic.cvpr.smoke_authorization_proof.v1"
RUNTIME_CLASSES = {"SYNTHETIC_SMOKE", "REAL_MODEL_SMOKE", "SCIENTIFIC_RUN"}
SMOKE_MEMBERS = (
    "predictions.jsonl",
    "runtime_manifest.json",
    "environment_manifest.json",
    "snapshot_manifest.json",
    "task_bundle_manifest.json",
    "seed_manifest.json",
    "validation_report.json",
    "hash_manifest.json",
    "authorization_proof.json",
    "provider_permission.json",
    "permission_events.jsonl",
)


class SmokeArtifactError(ValueError):
    """A canonical smoke artifact is incomplete, unsafe, or byte-inconsistent."""


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _deterministic_zip(
    path: Path,
    members: Mapping[str, bytes],
    *,
    archive_validator: Callable[[Path], None] | None = None,
    atomic_replace: Callable[[str | Path, str | Path], None] = os.replace,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name, payload in sorted(members.items()):
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, payload)
        if archive_validator is not None:
            archive_validator(Path(temporary))
        else:
            with zipfile.ZipFile(temporary) as archive:
                if archive.testzip() is not None:
                    raise SmokeArtifactError("temporary smoke ZIP failed CRC validation")
        with Path(temporary).open("rb") as handle:
            os.fsync(handle.fileno())
        atomic_replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _signed(payload: dict[str, Any], field: str = "content_signature_sha256") -> dict[str, Any]:
    result = dict(payload)
    result[field] = sha256_bytes(canonical_json_bytes(result))
    return result


def environment_names() -> tuple[str, str, str]:
    return (
        "00A_environment.json",
        "00A_environment_validation.json",
        "00A_environment_bundle.zip",
    )


def snapshot_names(provider: str) -> tuple[str, str, str]:
    if not provider or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789_" for character in provider):
        raise SmokeArtifactError("provider must be a lowercase filesystem-safe identifier")
    return (
        f"00B_{provider}_snapshot.json",
        f"00B_{provider}_snapshot_validation.json",
        f"00B_{provider}_snapshot_bundle.zip",
    )


def smoke_name(provider: str) -> str:
    snapshot_names(provider)
    return f"00C2_{provider}_real_model_smoke.zip"


def _small_bundle(
    out_dir: str | Path,
    *,
    primary_name: str,
    validation_name: str,
    bundle_name: str,
    primary: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    root = Path(out_dir)
    primary_payload = _json_bytes(primary)
    validation_payload = _json_bytes(validation)
    members = {
        primary_name: primary_payload,
        validation_name: validation_payload,
    }
    from certvic.cvpr.t4x2 import derive_seed_manifest

    members["seed_manifest.json"] = _json_bytes(derive_seed_manifest(
        global_seed=12013,
        study=str(primary.get("stage", primary.get("provider", "environment_smoke"))),
        provider=str(primary.get("provider", "all")),
        gpu_id=0,
        shard_id=0,
        task_ids=[],
        attempts=1,
    ))
    hash_payload = _json_bytes(
        {
            "schema": HASH_SCHEMA,
            "files": {name: hashlib.sha256(data).hexdigest() for name, data in members.items()},
        }
    )
    members["hash_manifest.json"] = hash_payload
    _atomic_write(root / primary_name, primary_payload)
    _atomic_write(root / validation_name, validation_payload)
    _deterministic_zip(root / bundle_name, members)
    return {
        "schema": ARTIFACT_SCHEMA,
        "status": "CANONICAL_ARTIFACTS_WRITTEN",
        "files": [primary_name, validation_name, bundle_name],
        "bundle_sha256": _sha(root / bundle_name),
        "paper_evidence": False,
    }


def write_environment_artifacts(
    out_dir: str | Path,
    environment: dict[str, Any],
    *,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write the exact three 00A return artifacts."""
    primary_name, validation_name, bundle_name = environment_names()
    if environment.get("passed") is not True:
        raise SmokeArtifactError("00A environment must be a successful exact-environment result")
    environment = {"schema": ARTIFACT_SCHEMA, **environment, "paper_evidence": False}
    validation = {
        "schema": ARTIFACT_SCHEMA,
        "stage": "00A",
        "passed": True,
        "validation_source": "RECOMPUTED_NOTEBOOK_PREFLIGHT",
        "environment_sha256": sha256_bytes(_json_bytes(environment)),
        "paper_evidence": False,
        **(validation or {}),
    }
    return _small_bundle(
        out_dir,
        primary_name=primary_name,
        validation_name=validation_name,
        bundle_name=bundle_name,
        primary=environment,
        validation=validation,
    )


def write_snapshot_artifacts(
    out_dir: str | Path,
    provider: str,
    snapshot: dict[str, Any],
    *,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write the exact three provider-specific 00B return artifacts."""
    primary_name, validation_name, bundle_name = snapshot_names(provider)
    if snapshot.get("passed") is not True:
        raise SmokeArtifactError("00B snapshot must be a successful byte-verification result")
    snapshot = {
        "schema": ARTIFACT_SCHEMA,
        "provider": provider,
        **snapshot,
        "paper_evidence": False,
    }
    validation = {
        "schema": ARTIFACT_SCHEMA,
        "stage": "00B",
        "provider": provider,
        "passed": True,
        "validation_source": "RECOMPUTED_NOTEBOOK_PREFLIGHT",
        "snapshot_sha256": sha256_bytes(_json_bytes(snapshot)),
        "paper_evidence": False,
        **(validation or {}),
    }
    return _small_bundle(
        out_dir,
        primary_name=primary_name,
        validation_name=validation_name,
        bundle_name=bundle_name,
        primary=snapshot,
        validation=validation,
    )


def _proof(runtime: dict[str, Any], bundle: dict[str, Any], *, synthetic: bool) -> dict[str, Any]:
    runtime_class = "SYNTHETIC_SMOKE" if synthetic else "REAL_MODEL_SMOKE"
    payload = {
        "schema": PROOF_SCHEMA,
        "artifact_schema": ARTIFACT_SCHEMA,
        "runtime_class": runtime_class,
        "synthetic_fixture": synthetic,
        "provider": runtime.get("provider"),
        "model_id": runtime.get("model_id"),
        "model_revision": runtime.get("model_revision", runtime.get("model_commit")),
        "processor_revision": runtime.get("processor_revision", runtime.get("processor_commit")),
        "snapshot_manifest_hash": runtime.get(
            "snapshot_manifest_hash", runtime.get("model_snapshot_manifest_hash")
        ),
        "snapshot_root_hash": runtime.get("snapshot_root_hash"),
        "environment_manifest_hash": runtime.get(
            "environment_manifest_hash", runtime.get("environment_hash", runtime.get("environment_lock_hash"))
        ),
        "code_hash": runtime.get("code_hash", runtime.get("code_bundle_hash")),
        "processor_model_contract": runtime.get("processor_model_contract", runtime.get("snapshot_contract")),
        "parser_version": runtime.get("parser_version"),
        "prompt_hash": runtime.get("prompt_hash", runtime.get("prompt_template_hash")),
        "task_bundle_hash": runtime.get("task_bundle_hash"),
        "smoke_fixture_hash": runtime.get("smoke_fixture_hash", runtime.get("task_manifest_sha256")),
        "run_contract_hash": runtime.get("run_contract_hash"),
        "prompt_template_hash": runtime.get("prompt_template_hash"),
        "runtime_profile_id": runtime.get("runtime_profile_id"),
        "runtime_profile_hash": runtime.get("runtime_profile_hash"),
        "wheelhouse_content_identity_sha256": runtime.get(
            "wheelhouse_content_identity_sha256"
        ),
        "bundle_manifest_hash": bundle.get("bundle_hash"),
        "paper_evidence": False,
    }
    missing = [
        field
        for field in (
            "provider",
            "model_id",
            "model_revision",
            "snapshot_manifest_hash",
            "environment_manifest_hash",
            "code_hash",
            "parser_version",
            "prompt_hash",
            "task_bundle_hash",
            "smoke_fixture_hash",
            "run_contract_hash",
            "prompt_template_hash",
        )
        if not payload.get(field)
    ]
    if missing:
        raise SmokeArtifactError(f"smoke authorization proof is missing identity fields: {missing}")
    if payload["task_bundle_hash"] != bundle.get("bundle_hash"):
        raise SmokeArtifactError("runtime and packaged task bundle hashes differ")
    if (payload["runtime_profile_id"] is None) != (payload["runtime_profile_hash"] is None):
        raise SmokeArtifactError("runtime profile ID/hash binding is incomplete")
    return _signed(payload)


def package_smoke(
    output_root: str | Path,
    *,
    provider: str,
    task_bundle_manifest: str | Path,
    destination: str | Path | None = None,
    synthetic: bool = False,
    authorization_proof: dict[str, Any] | None = None,
    provider_permission: str | Path | Mapping[str, Any] | None = None,
    permission_events: str | Path | None = None,
    archive_validator: Callable[[Path], None] | None = None,
    atomic_replace: Callable[[str | Path, str | Path], None] = os.replace,
) -> dict[str, Any]:
    """Package the canonical 00C2 artifact and commit permission only after promotion."""
    root = Path(output_root)
    sources = {
        "predictions.jsonl": root / "predictions.jsonl",
        "runtime_manifest.json": root / "runtime_manifest.json",
        "environment_manifest.json": root / "environment_manifest.json",
        "snapshot_manifest.json": root / "snapshot_manifest.json",
        "validation_report.json": root / "validation_report.json",
        "task_bundle_manifest.json": Path(task_bundle_manifest),
    }
    if not sources["predictions.jsonl"].is_file() and (root / "merged_raw.jsonl").is_file():
        sources["predictions.jsonl"] = root / "merged_raw.jsonl"
    seed_path = root / "seed_manifest.json"
    if not seed_path.is_file() and sources["predictions.jsonl"].is_file():
        from certvic.cvpr.t4x2 import derive_seed_manifest, write_seed_manifest

        provisional_runtime = json.loads(sources["runtime_manifest.json"].read_text())
        prediction_rows = [
            json.loads(line)
            for line in sources["predictions.jsonl"].read_text().splitlines()
            if line
        ]
        write_seed_manifest(seed_path, derive_seed_manifest(
            global_seed=int(provisional_runtime.get("seed", 12013)),
            study=str(provisional_runtime.get("study", "pre_smoke")),
            provider=str(provisional_runtime.get("provider", provider)),
            gpu_id=0,
            shard_id=0,
            task_ids=[str(row["item_id"]) for row in prediction_rows],
            attempts=1,
        ))
    sources["seed_manifest.json"] = seed_path
    missing = [name for name, path in sources.items() if not path.is_file()]
    if missing:
        raise SmokeArtifactError(f"cannot package smoke; missing canonical sources: {missing}")
    runtime = json.loads(sources["runtime_manifest.json"].read_text(encoding="utf-8"))
    bundle = json.loads(sources["task_bundle_manifest.json"].read_text(encoding="utf-8"))
    expected_class = "SYNTHETIC_SMOKE" if synthetic else "REAL_MODEL_SMOKE"
    observed_class = runtime.get("runtime_class")
    compatible = {
        "SYNTHETIC_SMOKE": {
            "SYNTHETIC_SMOKE", "SYNTHETIC_END_TO_END_FIXTURE", "REAL_MODEL_SMOKE",
        },
        "REAL_MODEL_SMOKE": {"REAL_MODEL_SMOKE", "NON_EVIDENCE_REAL_MODEL_SMOKE"},
    }
    if observed_class not in compatible[expected_class]:
        raise SmokeArtifactError(f"runtime class {observed_class!r} is not {expected_class}")
    if synthetic and observed_class == "REAL_MODEL_SMOKE" and runtime.get(
        "synthetic_notebook_proof"
    ) is not True:
        raise SmokeArtifactError("REAL_MODEL_SMOKE may be synthetic only in the explicit notebook proof")
    if not synthetic and runtime.get("synthetic_notebook_proof") is True:
        raise SmokeArtifactError("synthetic notebook proof cannot be promoted as real-model smoke")
    if runtime.get("provider") != provider:
        raise SmokeArtifactError("smoke runtime provider differs from canonical filename provider")
    run_contract_hash = runtime.get("run_contract_hash")
    prompt_template_hash = runtime.get("prompt_template_hash")
    if not all(isinstance(value, str) and len(value) == 64 for value in (
        run_contract_hash, prompt_template_hash
    )):
        raise SmokeArtifactError("runtime is missing run-contract or prompt-template identity")
    archive = Path(destination) if destination is not None else root / smoke_name(provider)
    child: dict[str, Any] | None = None
    events_path: Path | None = None
    recovery: dict[str, Any] = {
        "retry_allowed": False,
        "reason": "first packaging attempt",
        "prior_state": None,
    }
    if synthetic:
        synthetic_permission = {
            "schema": "certvic.cvpr.synthetic_smoke_permission.v1",
            "provider": provider,
            "runtime_class": "SYNTHETIC_SMOKE",
            "synthetic_fixture": True,
            "run_contract_hash": run_contract_hash,
            "prompt_template_hash": prompt_template_hash,
            "parent_matrix_authorization_id": hashlib.sha256(
                f"SYNTHETIC_NOTEBOOK_PROOF:{provider}".encode("utf-8")
            ).hexdigest(),
            "paper_evidence": False,
        }
        synthetic_permission["content_signature_sha256"] = sha256_bytes(
            canonical_json_bytes(synthetic_permission)
        )
        permission_payload = _json_bytes(synthetic_permission)
        events_payload = _json_bytes({
            "schema": "certvic.cvpr.synthetic_smoke_permission_event.v1",
            "provider": provider,
            "to_state": "PACKAGE_WRITTEN",
            "synthetic_fixture": True,
            "paper_evidence": False,
        })
    else:
        if provider_permission is None or permission_events is None:
            raise SmokeArtifactError(
                "real-model smoke requires its provider permission and local event chain"
            )
        from certvic.cvpr.reconcile_provider_permissions import (
            provider_state,
            transition_provider_permission,
            verify_provider_permission,
        )

        child = verify_provider_permission(
            provider_permission, expected_provider=provider,
        )
        if child.get("runtime_class") != "REAL_MODEL_SMOKE":
            raise SmokeArtifactError("00C2 requires a REAL_MODEL_SMOKE child permission")
        if child.get("run_contract_hash") != run_contract_hash or child.get(
            "prompt_template_hash"
        ) != prompt_template_hash:
            raise SmokeArtifactError("provider permission differs from active smoke identities")
        events_path = Path(permission_events)
        state = provider_state(events_path, child)
        recovery["prior_state"] = state
        if state == "OUTPUT_PACKAGED" and archive.is_file():
            read_smoke_archive(archive)
            final_hash = _sha(archive)
            recovery.update({
                "retry_allowed": False,
                "reason": "already-valid final ZIP exists with a committed permission",
                "idempotent": True,
            })
            return {
                "schema": ARTIFACT_SCHEMA,
                "status": "CANONICAL_REAL_MODEL_SMOKE_ALREADY_PACKAGED",
                "provider": provider,
                "runtime_class": expected_class,
                "synthetic_fixture": False,
                "archive": str(archive),
                "archive_sha256": final_hash,
                "members": list(SMOKE_MEMBERS),
                "packaging_recovery": recovery,
                "paper_evidence": False,
            }
        if archive.exists():
            raise SmokeArtifactError("final smoke ZIP exists without a matching committed permission")
        if state not in {"RUN_STARTED", "PACKAGING_FAILED"}:
            raise SmokeArtifactError(f"provider permission cannot package from {state}")
        if state == "PACKAGING_FAILED":
            recovery.update({
                "retry_allowed": True,
                "reason": "prior packaging failed, final ZIP is absent, runtime outputs remain bound",
            })
        transition_provider_permission(
            child, events_path, to_state="PACKAGING_STARTED",
            actor="certvic.cvpr.smoke_artifacts",
            detail={"recovery": recovery},
        )
        transition_provider_permission(
            child, events_path, to_state="PACKAGE_WRITTEN",
            actor="certvic.cvpr.smoke_artifacts",
            detail={"canonical_member_sources_validated": True},
        )
        permission_payload = _json_bytes(child)
        events_payload = events_path.read_bytes()
    proof = authorization_proof or _proof(runtime, bundle, synthetic=synthetic)
    if proof.get("runtime_class") != expected_class or proof.get("synthetic_fixture") is not synthetic:
        raise SmokeArtifactError("authorization proof runtime class is inconsistent")
    members = {name: path.read_bytes() for name, path in sources.items()}
    if child is not None:
        proof = {
            **proof,
            "parent_matrix_authorization_id": child["parent_matrix_authorization_id"],
            "permission_id": child["permission_id"],
            "permission_signature": child["content_signature_sha256"],
            "permission_events_sha256": hashlib.sha256(events_payload).hexdigest(),
        }
        proof.pop("content_signature_sha256", None)
        proof = _signed(proof)
    elif synthetic:
        proof = {
            **proof,
            "parent_matrix_authorization_id": synthetic_permission[
                "parent_matrix_authorization_id"
            ],
        }
        proof.pop("content_signature_sha256", None)
        proof = _signed(proof)
    members["authorization_proof.json"] = _json_bytes(proof)
    members["provider_permission.json"] = permission_payload
    members["permission_events.jsonl"] = events_payload
    members["hash_manifest.json"] = _json_bytes(
        {
            "schema": HASH_SCHEMA,
            "artifact_schema": ARTIFACT_SCHEMA,
            "files": {name: hashlib.sha256(data).hexdigest() for name, data in members.items()},
        }
    )
    if set(members) != set(SMOKE_MEMBERS):
        raise AssertionError("canonical smoke member contract drifted")
    try:
        _deterministic_zip(
            archive, members, archive_validator=archive_validator,
            atomic_replace=atomic_replace,
        )
        # Re-open the promoted bytes before committing the one-run permission.
        read_smoke_archive(archive)
        if child is not None and events_path is not None:
            from certvic.cvpr.reconcile_provider_permissions import transition_provider_permission

            transition_provider_permission(
                child, events_path, to_state="OUTPUT_PACKAGED",
                actor="certvic.cvpr.smoke_artifacts",
                detail={"zip_sha256": _sha(archive), "atomic_promotion": "PASS"},
            )
    except Exception as exc:
        if child is not None and events_path is not None:
            from certvic.cvpr.reconcile_provider_permissions import (
                provider_state, transition_provider_permission,
            )

            if provider_state(events_path, child) in {"PACKAGING_STARTED", "PACKAGE_WRITTEN"}:
                transition_provider_permission(
                    child, events_path, to_state="PACKAGING_FAILED",
                    actor="certvic.cvpr.smoke_artifacts",
                    detail={"error_type": type(exc).__name__},
                )
        if child is not None and archive.is_file():
            archive.unlink()
        raise
    return {
        "schema": ARTIFACT_SCHEMA,
        "status": "CANONICAL_REAL_MODEL_SMOKE_PACKAGED",
        "provider": provider,
        "runtime_class": expected_class,
        "synthetic_fixture": synthetic,
        "archive": str(archive),
        "archive_sha256": _sha(archive),
        "members": list(SMOKE_MEMBERS),
        "packaging_recovery": recovery,
        "paper_evidence": False,
    }


def read_smoke_archive(path: str | Path) -> dict[str, Any]:
    """Read and byte-verify one canonical smoke ZIP without trusting its paths."""
    archive_path = Path(path)
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or set(names) != set(SMOKE_MEMBERS):
            raise SmokeArtifactError("smoke ZIP does not contain exactly the canonical member set")
        if archive.testzip() is not None or any(
            PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts for name in names
        ):
            raise SmokeArtifactError("smoke ZIP is corrupt or contains an unsafe member")
        payloads = {name: archive.read(name) for name in names}
    hashes = json.loads(payloads["hash_manifest.json"])
    if hashes.get("schema") != HASH_SCHEMA or hashes.get("artifact_schema") != ARTIFACT_SCHEMA:
        raise SmokeArtifactError("smoke hash manifest schema mismatch")
    expected = hashes.get("files")
    observed = {
        name: hashlib.sha256(payload).hexdigest()
        for name, payload in payloads.items()
        if name != "hash_manifest.json"
    }
    if expected != observed:
        raise SmokeArtifactError("smoke ZIP member hashes differ from hash_manifest.json")
    proof = json.loads(payloads["authorization_proof.json"])
    signature = proof.get("content_signature_sha256")
    unsigned = {key: value for key, value in proof.items() if key != "content_signature_sha256"}
    if proof.get("schema") != PROOF_SCHEMA or signature != sha256_bytes(canonical_json_bytes(unsigned)):
        raise SmokeArtifactError("smoke authorization proof signature mismatch")
    runtime_class = proof.get("runtime_class")
    if runtime_class not in {"SYNTHETIC_SMOKE", "REAL_MODEL_SMOKE"}:
        raise SmokeArtifactError("smoke authorization proof has an invalid runtime class")
    rows = [json.loads(line) for line in payloads["predictions.jsonl"].splitlines() if line]
    runtime = json.loads(payloads["runtime_manifest.json"])
    validation = json.loads(payloads["validation_report.json"])
    run_hash = runtime.get("run_contract_hash")
    prompt_hash = runtime.get("prompt_template_hash")
    if not all(isinstance(value, str) and len(value) == 64 for value in (run_hash, prompt_hash)):
        raise SmokeArtifactError("smoke runtime identity hashes are missing")
    snapshot_hash = hashlib.sha256(payloads["snapshot_manifest.json"]).hexdigest()
    declared_snapshot_hash = runtime.get(
        "snapshot_manifest_hash", runtime.get("model_snapshot_manifest_hash")
    )
    if snapshot_hash != declared_snapshot_hash or proof.get("snapshot_manifest_hash") != snapshot_hash:
        raise SmokeArtifactError("smoke snapshot manifest identity mismatch")
    identity_values = {
        "authorization_proof.run_contract_hash": proof.get("run_contract_hash"),
        "authorization_proof.prompt_template_hash": proof.get("prompt_template_hash"),
        "validation_report.run_contract_hash": validation.get("run_contract_hash"),
        "validation_report.prompt_template_hash": validation.get("prompt_template_hash"),
    }
    expected_values = {
        "authorization_proof.run_contract_hash": run_hash,
        "authorization_proof.prompt_template_hash": prompt_hash,
        "validation_report.run_contract_hash": run_hash,
        "validation_report.prompt_template_hash": prompt_hash,
    }
    mismatches = {
        field: {"expected": expected_values[field], "observed": observed}
        for field, observed in identity_values.items()
        if observed != expected_values[field]
    }
    for index, row in enumerate(rows, start=1):
        if row.get("run_contract_hash") != run_hash:
            mismatches[f"predictions[{index}].run_contract_hash"] = {
                "expected": run_hash, "observed": row.get("run_contract_hash")
            }
        if row.get("prompt_template_hash") != prompt_hash:
            mismatches[f"predictions[{index}].prompt_template_hash"] = {
                "expected": prompt_hash, "observed": row.get("prompt_template_hash")
            }
    permission = json.loads(payloads["provider_permission.json"])
    if runtime_class == "REAL_MODEL_SMOKE":
        from certvic.cvpr.reconcile_provider_permissions import (
            read_provider_events, verify_provider_permission,
        )

        child = verify_provider_permission(permission, expected_provider=str(runtime.get("provider")))
        if child.get("run_contract_hash") != run_hash:
            mismatches["provider_permission.run_contract_hash"] = {
                "expected": run_hash, "observed": child.get("run_contract_hash")
            }
        if child.get("prompt_template_hash") != prompt_hash:
            mismatches["provider_permission.prompt_template_hash"] = {
                "expected": prompt_hash, "observed": child.get("prompt_template_hash")
            }
        with tempfile.TemporaryDirectory(prefix="certvic_smoke_events_") as temporary:
            event_path = Path(temporary) / "permission_events.jsonl"
            event_path.write_bytes(payloads["permission_events.jsonl"])
            events = read_provider_events(event_path, child)
        if not events or events[-1].get("to_state") != "PACKAGE_WRITTEN":
            raise SmokeArtifactError("portable smoke permission chain is not PACKAGE_WRITTEN")
        if proof.get("permission_id") != child.get("permission_id"):
            mismatches["authorization_proof.permission_id"] = {
                "expected": child.get("permission_id"), "observed": proof.get("permission_id")
            }
        if proof.get("parent_matrix_authorization_id") != child.get(
            "parent_matrix_authorization_id"
        ):
            mismatches["authorization_proof.parent_matrix_authorization_id"] = {
                "expected": child.get("parent_matrix_authorization_id"),
                "observed": proof.get("parent_matrix_authorization_id"),
            }
        expected_events_hash = hashlib.sha256(payloads["permission_events.jsonl"]).hexdigest()
        if proof.get("permission_events_sha256") != expected_events_hash:
            mismatches["authorization_proof.permission_events_sha256"] = {
                "expected": expected_events_hash,
                "observed": proof.get("permission_events_sha256"),
            }
    else:
        observed_permission_signature = permission.get("content_signature_sha256")
        unsigned_permission = {
            key: value for key, value in permission.items() if key != "content_signature_sha256"
        }
        if (
            permission.get("schema") != "certvic.cvpr.synthetic_smoke_permission.v1"
            or observed_permission_signature != sha256_bytes(canonical_json_bytes(unsigned_permission))
            or permission.get("run_contract_hash") != run_hash
            or permission.get("prompt_template_hash") != prompt_hash
            or permission.get("parent_matrix_authorization_id")
            != proof.get("parent_matrix_authorization_id")
        ):
            raise SmokeArtifactError("synthetic smoke permission identity mismatch")
    if mismatches:
        raise SmokeArtifactError(f"smoke identity mismatch: {mismatches}")
    return {
        "archive": archive_path,
        "archive_sha256": _sha(archive_path),
        "rows": rows,
        "runtime": runtime,
        "environment": json.loads(payloads["environment_manifest.json"]),
        "snapshot": json.loads(payloads["snapshot_manifest.json"]),
        "task_bundle": json.loads(payloads["task_bundle_manifest.json"]),
        "validation": validation,
        "provider_permission": permission,
        "authorization_proof": proof,
        "member_hashes": observed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build canonical CertVIC smoke artifacts")
    sub = parser.add_subparsers(dest="command", required=True)
    smoke = sub.add_parser("smoke")
    smoke.add_argument("--output-root", required=True)
    smoke.add_argument("--provider", required=True)
    smoke.add_argument("--task-bundle-manifest", required=True)
    smoke.add_argument("--out")
    smoke.add_argument("--synthetic", action="store_true")
    verify = sub.add_parser("verify-smoke")
    verify.add_argument("--archive", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "smoke":
            result = package_smoke(
                args.output_root,
                provider=args.provider,
                task_bundle_manifest=args.task_bundle_manifest,
                destination=args.out,
                synthetic=args.synthetic,
            )
        else:
            loaded = read_smoke_archive(args.archive)
            result = {
                "schema": ARTIFACT_SCHEMA,
                "status": "CANONICAL_SMOKE_VALID",
                "archive_sha256": loaded["archive_sha256"],
                "provider": loaded["authorization_proof"]["provider"],
                "runtime_class": loaded["authorization_proof"]["runtime_class"],
                "paper_evidence": False,
            }
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "SMOKE_ARTIFACT_BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
