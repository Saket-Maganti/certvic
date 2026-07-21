"""Recoverable two-phase provider import and one-run nonce consumption."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.reconcile_provider_permissions import reconcile_provider_permissions


JOURNAL_SCHEMA = "certvic.cvpr.import_transaction.v1"
NONCE_LEDGER_SCHEMA = "certvic.cvpr.consumed_provider_nonces.v1"
STATES = (
    "STAGED",
    "VALIDATED",
    "PREPARED",
    "PROMOTED",
    "LEDGER_COMMITTED",
    "COMMITTED",
    "ROLLED_BACK",
    "RECOVERY_REQUIRED",
)


class ImportTransactionError(ValueError):
    """A transaction cannot be prepared, committed, or recovered safely."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _atomic_json(path: str | Path, value: Any) -> None:
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


def _load_json(path: str | Path, default: Any) -> Any:
    source = Path(path)
    return json.loads(source.read_text(encoding="utf-8")) if source.is_file() else default


def _tree_hash(root: str | Path) -> str:
    base = Path(root)
    if not base.is_dir():
        raise ImportTransactionError(f"transaction tree does not exist: {base}")
    inventory = [
        {
            "path": path.relative_to(base).as_posix(),
            "size": path.stat().st_size,
            "sha256": _sha(path),
        }
        for path in sorted(base.rglob("*"))
        if path.is_file()
    ]
    return sha256_bytes(canonical_json_bytes(inventory))


def _journal_write(path: Path, journal: dict[str, Any], state: str) -> None:
    if state not in STATES:
        raise ImportTransactionError(f"invalid import transaction state: {state}")
    journal["state"] = state
    journal["updated_at_utc"] = _now()
    history = journal.setdefault("state_history", [])
    if not history or history[-1]["state"] != state:
        history.append({"state": state, "timestamp_utc": journal["updated_at_utc"]})
    journal["journal_hash"] = sha256_bytes(
        canonical_json_bytes({key: value for key, value in journal.items() if key != "journal_hash"})
    )
    _atomic_json(path, journal)


def load_journal(path: str | Path) -> dict[str, Any]:
    value = _load_json(path, None)
    if not isinstance(value, dict) or value.get("schema") != JOURNAL_SCHEMA:
        raise ImportTransactionError("import transaction journal schema mismatch")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != "journal_hash"})
    )
    if value.get("journal_hash") != expected or value.get("state") not in STATES:
        raise ImportTransactionError("import transaction journal hash/state mismatch")
    return value


def _nonce_ledger(path: str | Path) -> dict[str, Any]:
    value = _load_json(
        path,
        {
            "schema": NONCE_LEDGER_SCHEMA,
            "reservations": {},
            "consumed": {},
            "paper_evidence": False,
        },
    )
    if value.get("schema") != NONCE_LEDGER_SCHEMA:
        raise ImportTransactionError("consumed-nonce ledger schema mismatch")
    return value


def consumed_nonces(path: str | Path) -> set[str]:
    return set(_nonce_ledger(path).get("consumed", {}))


def _reserve_nonces(
    path: str | Path,
    *,
    transaction_id: str,
    providers: list[dict[str, Any]],
) -> None:
    ledger = _nonce_ledger(path)
    requested = {str(row["one_run_nonce"]): str(row["provider"]) for row in providers}
    for nonce in requested:
        if nonce in ledger["consumed"]:
            raise ImportTransactionError(f"provider nonce was already consumed: {nonce}")
        reservation = ledger["reservations"].get(nonce)
        if reservation is not None and reservation.get("transaction_id") != transaction_id:
            raise ImportTransactionError(f"provider nonce is reserved by another transaction: {nonce}")
    for nonce, provider in requested.items():
        ledger["reservations"][nonce] = {
            "transaction_id": transaction_id,
            "provider": provider,
            "reserved_at_utc": _now(),
        }
    _atomic_json(path, ledger)


def _commit_nonces(path: str | Path, journal: Mapping[str, Any]) -> None:
    ledger = _nonce_ledger(path)
    transaction_id = str(journal["transaction_id"])
    for row in journal["providers"]:
        nonce = str(row["one_run_nonce"])
        existing = ledger["consumed"].get(nonce)
        if existing is not None:
            if existing.get("transaction_id") != transaction_id:
                raise ImportTransactionError(f"provider nonce replay detected during commit: {nonce}")
            continue
        reservation = ledger["reservations"].get(nonce)
        if reservation is None or reservation.get("transaction_id") != transaction_id:
            raise ImportTransactionError(f"provider nonce reservation was lost: {nonce}")
        ledger["consumed"][nonce] = {
            **reservation,
            "consumed_at_utc": _now(),
            "destination_tree_hash": journal["destination_tree_hash"],
        }
        ledger["reservations"].pop(nonce, None)
    _atomic_json(path, ledger)


def _release_reservations(path: str | Path, transaction_id: str) -> None:
    ledger = _nonce_ledger(path)
    ledger["reservations"] = {
        nonce: row
        for nonce, row in ledger["reservations"].items()
        if row.get("transaction_id") != transaction_id
    }
    _atomic_json(path, ledger)


def _append_ledger(path: str | Path, entry: Mapping[str, Any]) -> None:
    source = Path(path)
    value = _load_json(source, {"schema": "certvic.cvpr.import_updates.v1", "entries": []})
    if value.get("schema") != "certvic.cvpr.import_updates.v1" or not isinstance(
        value.get("entries"), list
    ):
        raise ImportTransactionError(f"transaction-owned ledger schema mismatch: {source}")
    if not any(row.get("transaction_id") == entry.get("transaction_id") for row in value["entries"]):
        value["entries"].append(dict(entry))
    _atomic_json(source, value)


def _default_promotion_builder(
    promotion: Path,
    archives: Mapping[str, Path],
    reconciliation: Mapping[str, Any],
) -> None:
    """Safe simulator/default builder; production can pass the strict study importer builder."""
    raw = promotion / "immutable_raw"
    raw.mkdir(parents=True)
    for provider, archive in sorted(archives.items()):
        shutil.copyfile(archive, raw / f"{provider}_{_sha(archive)}.zip")
    _atomic_json(promotion / "provider_permission_reconciliation.json", reconciliation)
    _atomic_json(
        promotion / "study_import_audit.json",
        {
            "schema": "certvic.cvpr.atomic_study_import.v1",
            "status": "ATOMIC_MATRIX_PROMOTED",
            "study": reconciliation["study"],
            "providers": sorted(archives),
            "human_review_status": "HUMAN_REVIEW_PENDING",
            "paper_evidence": False,
        },
    )


def strict_study_promotion_builder(
    config: Mapping[str, Any],
) -> Callable[[Path, Mapping[str, Path], Mapping[str, Any]], None]:
    """Adapt the existing importer-grade row validation into the two-phase transaction."""
    from certvic.cvpr.transactional import read_jsonl
    from certvic.cvpr.whole_study_import import atomic_import_matrix

    tasks = read_jsonl(config["task_manifest"])

    def build(
        promotion: Path,
        archives: Mapping[str, Path],
        reconciliation: Mapping[str, Any],
    ) -> None:
        if reconciliation["study"] != config["study"]:
            raise ImportTransactionError("strict import config study differs from authorization")
        atomic_import_matrix(
            archives,
            study=str(config["study"]),
            run_tag=str(config["run_tag"]),
            model_contracts=dict(config["model_contracts"]),
            tasks=tasks,
            expected_code_bundle_hash=str(config["expected_code_bundle_hash"]),
            expected_snapshot_hashes=dict(config["expected_snapshot_hashes"]),
            expected_run_contract_hashes=config.get("expected_run_contract_hashes"),
            bundle_root=config.get("bundle_root"),
            destination_root=promotion,
        )
        _atomic_json(promotion / "provider_permission_reconciliation.json", reconciliation)

    return build


def transactional_import(
    archives: Mapping[str, str | Path],
    *,
    matrix_authorization: str | Path,
    destination: str | Path,
    nonce_ledger: str | Path,
    evidence_ledger: str | Path | None = None,
    gate_ledger: str | Path | None = None,
    promotion_builder: Callable[[Path, Mapping[str, Path], Mapping[str, Any]], None] | None = None,
    fail_after_promotion: bool = False,
) -> dict[str, Any]:
    """Validate, prepare, promote, consume nonces, update ledgers, and commit."""
    destination_path = Path(destination)
    archive_paths = {provider: Path(path) for provider, path in archives.items()}
    if any(not path.is_file() for path in archive_paths.values()):
        raise ImportTransactionError("one or more provider ZIPs are missing")
    matrix_hash = _sha(matrix_authorization)
    archive_hashes = {provider: _sha(path) for provider, path in sorted(archive_paths.items())}
    transaction_id = sha256_bytes(
        canonical_json_bytes(
            {
                "matrix_sha256": matrix_hash,
                "archive_hashes": archive_hashes,
                "destination": str(destination_path.resolve()),
            }
        )
    )
    transaction_root = destination_path.parent / ".certvic_import_transactions" / transaction_id
    journal_path = transaction_root / "journal.json"
    if journal_path.is_file():
        journal = load_journal(journal_path)
        if journal["state"] == "COMMITTED":
            if not destination_path.is_dir() or _tree_hash(destination_path) != journal[
                "destination_tree_hash"
            ]:
                raise ImportTransactionError("committed destination no longer matches its journal")
            return {
                "status": "IDEMPOTENT",
                "transaction_id": transaction_id,
                "destination": str(destination_path),
                "paper_evidence": False,
            }
        if journal["state"] in {"PROMOTED", "LEDGER_COMMITTED", "RECOVERY_REQUIRED"}:
            return recover_transaction(
                journal_path,
                nonce_ledger=nonce_ledger,
                evidence_ledger=evidence_ledger,
                gate_ledger=gate_ledger,
            )
        raise ImportTransactionError(
            f"unfinished pre-promotion transaction requires rollback: {journal['state']}"
        )
    if destination_path.exists():
        raise ImportTransactionError("destination already exists without this transaction journal")
    transaction_root.mkdir(parents=True, exist_ok=False)
    staged = transaction_root / "staged"
    staged.mkdir()
    staged_archives: dict[str, Path] = {}
    for provider, source in sorted(archive_paths.items()):
        target = staged / f"{provider}.zip"
        shutil.copyfile(source, target)
        staged_archives[provider] = target
    journal: dict[str, Any] = {
        "schema": JOURNAL_SCHEMA,
        "transaction_id": transaction_id,
        "study": None,
        "matrix_authorization_sha256": matrix_hash,
        "provider_zip_hashes": archive_hashes,
        "provider_nonces": [],
        "providers": [],
        "staged_paths": {provider: str(path) for provider, path in staged_archives.items()},
        "destination_path": str(destination_path),
        "permission_states": {},
        "intended_transitions": ["OUTPUT_PACKAGED", "CONSUMED"],
        "created_at_utc": _now(),
        "paper_evidence": False,
    }
    _journal_write(journal_path, journal, "STAGED")
    try:
        reconciliation = reconcile_provider_permissions(
            matrix_authorization,
            staged_archives,
            consumed_nonces=consumed_nonces(nonce_ledger),
        )
        journal["study"] = reconciliation["study"]
        journal["providers"] = reconciliation["providers"]
        journal["provider_nonces"] = reconciliation["provider_nonces"]
        journal["permission_states"] = {
            row["provider"]: "OUTPUT_PACKAGED" for row in reconciliation["providers"]
        }
        journal["reconciliation_hash"] = reconciliation["reconciliation_hash"]
        _journal_write(journal_path, journal, "VALIDATED")
        _reserve_nonces(
            nonce_ledger,
            transaction_id=transaction_id,
            providers=reconciliation["providers"],
        )
        promotion = transaction_root / "promotion"
        promotion.mkdir()
        (promotion_builder or _default_promotion_builder)(
            promotion, staged_archives, reconciliation
        )
        journal["prepared_tree_hash"] = _tree_hash(promotion)
        _journal_write(journal_path, journal, "PREPARED")
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(promotion, destination_path)
        journal["destination_tree_hash"] = _tree_hash(destination_path)
        if journal["destination_tree_hash"] != journal["prepared_tree_hash"]:
            raise ImportTransactionError("destination bytes differ immediately after atomic promotion")
        _journal_write(journal_path, journal, "PROMOTED")
        if fail_after_promotion:
            raise RuntimeError("injected post-promotion ledger failure")
        _commit_nonces(nonce_ledger, journal)
        journal["permission_states"] = {
            row["provider"]: "CONSUMED" for row in reconciliation["providers"]
        }
        _journal_write(journal_path, journal, "LEDGER_COMMITTED")
        evidence_path = Path(evidence_ledger) if evidence_ledger else destination_path.parent / "import_evidence_ledger.transactions.json"
        gate_path = Path(gate_ledger) if gate_ledger else destination_path.parent / "import_gate_ledger.transactions.json"
        entry = {
            "transaction_id": transaction_id,
            "study": journal["study"],
            "destination": str(destination_path),
            "destination_tree_hash": journal["destination_tree_hash"],
            "providers": sorted(row["provider"] for row in journal["providers"]),
            "provider_nonces": journal["provider_nonces"],
            "paper_evidence": False,
        }
        _append_ledger(evidence_path, {**entry, "ledger_role": "EVIDENCE_IMPORT"})
        _append_ledger(gate_path, {**entry, "ledger_role": "PROVIDER_PERMISSION_CONSUMPTION"})
        journal["evidence_ledger_path"] = str(evidence_path)
        journal["gate_ledger_path"] = str(gate_path)
        _journal_write(journal_path, journal, "COMMITTED")
    except Exception as exc:
        if destination_path.exists():
            journal["recovery_reason"] = f"{type(exc).__name__}: {exc}"
            _journal_write(journal_path, journal, "RECOVERY_REQUIRED")
        else:
            _release_reservations(nonce_ledger, transaction_id)
            journal["rollback_reason"] = f"{type(exc).__name__}: {exc}"
            _journal_write(journal_path, journal, "ROLLED_BACK")
        raise
    return {
        "status": "COMMITTED",
        "transaction_id": transaction_id,
        "destination": str(destination_path),
        "destination_tree_hash": journal["destination_tree_hash"],
        "providers": sorted(archives),
        "paper_evidence": False,
    }


def recover_transaction(
    journal_path: str | Path,
    *,
    nonce_ledger: str | Path,
    evidence_ledger: str | Path | None = None,
    gate_ledger: str | Path | None = None,
) -> dict[str, Any]:
    """Deterministically finish a promoted transaction; never partially consume providers."""
    path = Path(journal_path)
    journal = load_journal(path)
    if journal["state"] == "COMMITTED":
        return {"status": "IDEMPOTENT", "transaction_id": journal["transaction_id"]}
    if journal["state"] not in {"PROMOTED", "LEDGER_COMMITTED", "RECOVERY_REQUIRED"}:
        raise ImportTransactionError(f"transaction is not recoverable after promotion: {journal['state']}")
    destination = Path(journal["destination_path"])
    if not destination.is_dir() or _tree_hash(destination) != journal.get("destination_tree_hash"):
        raise ImportTransactionError("promoted destination is missing or differs; manual recovery required")
    _commit_nonces(nonce_ledger, journal)
    journal["permission_states"] = {row["provider"]: "CONSUMED" for row in journal["providers"]}
    _journal_write(path, journal, "LEDGER_COMMITTED")
    evidence_path = Path(evidence_ledger) if evidence_ledger else destination.parent / "import_evidence_ledger.transactions.json"
    gate_path = Path(gate_ledger) if gate_ledger else destination.parent / "import_gate_ledger.transactions.json"
    entry = {
        "transaction_id": journal["transaction_id"],
        "study": journal["study"],
        "destination": str(destination),
        "destination_tree_hash": journal["destination_tree_hash"],
        "providers": sorted(row["provider"] for row in journal["providers"]),
        "provider_nonces": journal["provider_nonces"],
        "paper_evidence": False,
    }
    _append_ledger(evidence_path, {**entry, "ledger_role": "EVIDENCE_IMPORT"})
    _append_ledger(gate_path, {**entry, "ledger_role": "PROVIDER_PERMISSION_CONSUMPTION"})
    journal["evidence_ledger_path"] = str(evidence_path)
    journal["gate_ledger_path"] = str(gate_path)
    _journal_write(path, journal, "COMMITTED")
    return {
        "status": "COMMITTED_RECOVERED",
        "transaction_id": journal["transaction_id"],
        "destination": str(destination),
        "providers": sorted(row["provider"] for row in journal["providers"]),
        "paper_evidence": False,
    }


def rollback_transaction(journal_path: str | Path, *, nonce_ledger: str | Path) -> dict[str, Any]:
    path = Path(journal_path)
    journal = load_journal(path)
    if journal["state"] in {"PROMOTED", "LEDGER_COMMITTED", "COMMITTED", "RECOVERY_REQUIRED"}:
        raise ImportTransactionError("a promoted transaction must be recovered, not rolled back")
    _release_reservations(nonce_ledger, journal["transaction_id"])
    journal["rollback_reason"] = "explicit pre-promotion rollback"
    _journal_write(path, journal, "ROLLED_BACK")
    return {"status": "ROLLED_BACK", "transaction_id": journal["transaction_id"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recoverable CertVIC provider import")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--matrix", required=True)
    run.add_argument("--provider-zip", action="append", required=True)
    run.add_argument("--destination", required=True)
    run.add_argument("--nonce-ledger", required=True)
    run.add_argument("--evidence-ledger")
    run.add_argument("--gate-ledger")
    run.add_argument("--study-import-config")
    recover = sub.add_parser("recover")
    recover.add_argument("--journal", required=True)
    recover.add_argument("--nonce-ledger", required=True)
    recover.add_argument("--evidence-ledger")
    recover.add_argument("--gate-ledger")
    rollback = sub.add_parser("rollback")
    rollback.add_argument("--journal", required=True)
    rollback.add_argument("--nonce-ledger", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            archives = dict(value.split("=", 1) for value in args.provider_zip)
            builder = None
            if args.study_import_config:
                config = json.loads(Path(args.study_import_config).read_text(encoding="utf-8"))
                builder = strict_study_promotion_builder(config)
            result = transactional_import(
                archives,
                matrix_authorization=args.matrix,
                destination=args.destination,
                nonce_ledger=args.nonce_ledger,
                evidence_ledger=args.evidence_ledger,
                gate_ledger=args.gate_ledger,
                promotion_builder=builder,
            )
        elif args.command == "recover":
            result = recover_transaction(
                args.journal,
                nonce_ledger=args.nonce_ledger,
                evidence_ledger=args.evidence_ledger,
                gate_ledger=args.gate_ledger,
            )
        else:
            result = rollback_transaction(args.journal, nonce_ledger=args.nonce_ledger)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "IMPORT_TRANSACTION_BLOCKED", "reason": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
