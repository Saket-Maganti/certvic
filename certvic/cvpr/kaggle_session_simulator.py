"""Non-evidence simulator for three isolated Kaggle provider sessions."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from certvic.cvpr.import_transaction import ImportTransactionError, transactional_import
from certvic.cvpr.reconcile_provider_permissions import (
    ProviderPermissionError,
    build_authorization_proof,
    create_matrix_authorization,
    derive_provider_permission,
    reconcile_provider_permissions,
    transition_provider_permission,
)


PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(members.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)


def simulate(root: str | Path) -> dict[str, Any]:
    """Exercise isolation, portable proofs, reconciliation, commit, recovery, and replay."""
    out = Path(root)
    out.mkdir(parents=True, exist_ok=False)
    hashes = {name: _sha(f"SIMULATOR:{name}".encode()) for name in (
        "task_bundle", "final_tasks", "task_universe", "edited_images", "review",
        "detectability", "environment", "model_registry", "code",
        "prompt_template",
    )}
    matrix_path = out / "matrix_authorization.json"
    matrix = create_matrix_authorization(
        study="synthetic_kaggle_session_simulator",
        task_bundle_hash=hashes["task_bundle"],
        final_task_manifest_hash=hashes["final_tasks"],
        task_universe_sha256=hashes["task_universe"],
        edited_image_hashes_hash=hashes["edited_images"],
        review_hash=hashes["review"],
        detectability_hash=hashes["detectability"],
        environment_hash=hashes["environment"],
        model_registry_hash=hashes["model_registry"],
        providers=list(PROVIDERS),
        code_hash=hashes["code"],
        prompt_template_hash=hashes["prompt_template"],
        output_schema="certvic.cvpr.output.v2",
        issued_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        validity_hours=24 * 3650,
        out=matrix_path,
    )
    archives: dict[str, Path] = {}
    session_roots: dict[str, str] = {}
    for index, provider in enumerate(PROVIDERS):
        session = out / "isolated_sessions" / provider
        session.mkdir(parents=True)
        session_roots[provider] = str(session)
        snapshot = _sha(f"SIMULATOR:snapshot:{provider}".encode())
        snapshot_root = _sha(f"SIMULATOR:snapshot-root:{provider}".encode())
        model_id = f"synthetic-simulator/{provider}"
        revision = f"{index + 1}" * 40
        run_contract_hash = _sha(f"SIMULATOR:run-contract:{provider}".encode())
        smoke = {
            "provider": provider,
            "runtime_class": "REAL_MODEL_SMOKE",
            "synthetic_fixture": False,
            "model_id": model_id,
            "model_revision": revision,
            "snapshot_manifest_hash": snapshot,
            "snapshot_root_hash": snapshot_root,
            "environment_manifest_hash": hashes["environment"],
            "code_hash": hashes["code"],
            "parser_version": "certvic.parse.v2",
            "processor_model_contract": "UNIFIED_SNAPSHOT",
            "run_contract_hash": run_contract_hash,
            "prompt_template_hash": hashes["prompt_template"],
        }
        permission_path = session / "provider_permission.json"
        permission = derive_provider_permission(
            matrix,
            provider=provider,
            model_id=model_id,
            model_revision=revision,
            snapshot_hash=snapshot,
            snapshot_root_hash=snapshot_root,
            environment_hash=hashes["environment"],
            task_bundle_hash=hashes["task_bundle"],
            run_tag="synthetic_kaggle_session_simulator_v1",
            code_hash=hashes["code"],
            parser_version="certvic.parse.v2",
            processor_model_contract="UNIFIED_SNAPSHOT",
            run_contract_hash=run_contract_hash,
            prompt_template_hash=hashes["prompt_template"],
            smoke_identity=smoke,
            active_input_hashes={
                role: _sha(f"SIMULATOR:active:{provider}:{role}".encode())
                for role in (
                    "task_bundle_manifest", "freeze_manifest", "final_review", "smoke_gate",
                    "environment_lock", "model_registry", "snapshot_manifest", "code_bundle",
                    "study_config",
                    "matrix_authorization",
                )
            },
            active_scalars={
                "schema_version": "certvic.cvpr.output.v2",
                "provider": provider,
                "run_tag": "synthetic_kaggle_session_simulator_v1",
            },
            nonce=_sha(f"SIMULATOR:nonce:{provider}".encode()),
            out=permission_path,
        )
        events = session / "permission_events.jsonl"
        transition_provider_permission(
            permission, events, to_state="CLAIMED", actor="simulated_notebook_preflight"
        )
        transition_provider_permission(
            permission, events, to_state="RUN_STARTED", actor="simulated_worker"
        )
        fixture_payload = _json_bytes(
            {
                "schema": "certvic.cvpr.kaggle_session_simulator_output.v1",
                "provider": provider,
                "synthetic_fixture": True,
                "paper_evidence": False,
                "contains_predictions": False,
            }
        )
        proof = build_authorization_proof(
            permission,
            events,
            output_hashes={"simulator_output.json": _sha(fixture_payload)},
        )
        members = {
            "simulator_output.json": fixture_payload,
            "provider_permission.json": _json_bytes(permission),
            "permission_events.jsonl": events.read_bytes(),
            "authorization_proof.json": _json_bytes(proof),
        }
        members["hash_manifest.json"] = _json_bytes(
            {name: _sha(payload) for name, payload in members.items()}
        )
        archive = out / f"{provider}_return.zip"
        _zip(archive, members)
        transition_provider_permission(
            permission, events, to_state="OUTPUT_PACKAGED",
            actor="simulated_packager", detail={"zip_sha256": _sha(archive.read_bytes())},
        )
        archives[provider] = archive
    reconciliation = reconcile_provider_permissions(matrix_path, archives)
    reconciliation_path = out / "provider_permission_reconciliation.json"
    reconciliation_path.write_text(
        json.dumps(reconciliation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    nonce_ledger = out / "consumed_nonces.json"
    imported = transactional_import(
        archives,
        matrix_authorization=matrix_path,
        destination=out / "canonical_import",
        nonce_ledger=nonce_ledger,
    )
    replay_rejected = False
    try:
        transactional_import(
            archives,
            matrix_authorization=matrix_path,
            destination=out / "replay_destination",
            nonce_ledger=nonce_ledger,
        )
    except (ImportTransactionError, ProviderPermissionError):
        replay_rejected = True
    result = {
        "schema": "certvic.cvpr.kaggle_session_simulator.v1",
        "status": "KAGGLE_MULTI_SESSION_SIMULATION_PASSED" if replay_rejected else "FAILED",
        "sessions": session_roots,
        "shared_writable_state_between_sessions": False,
        "returned_archives": {provider: str(path) for provider, path in archives.items()},
        "reconciliation_status": reconciliation["status"],
        "import_status": imported["status"],
        "replay_rejected": replay_rejected,
        "synthetic_fixture": True,
        "contains_predictions": False,
        "paper_evidence": False,
    }
    (out / "SIMULATION_RESULT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulate three isolated Kaggle sessions")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    try:
        result = simulate(args.out_dir)
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "KAGGLE_SESSION_SIMULATOR_BLOCKED", "reason": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "KAGGLE_MULTI_SESSION_SIMULATION_PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
