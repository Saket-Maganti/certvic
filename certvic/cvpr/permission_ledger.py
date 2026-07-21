"""Atomic one-run permission ledger with independent provider slots.

The immutable ledger is an authorization input.  State changes are appended to
an fsync'd hash-chained sidecar under an exclusive file lock, so the input hash
bound by the permission never changes while replay remains detectable.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes


LEDGER_SCHEMA = "certvic.cvpr.permission_ledger.v1"
EVENT_SCHEMA = "certvic.cvpr.permission_event.v1"
STATES = {
    "ISSUED",
    "CLAIMED",
    "RUN_STARTED",
    "PACKAGING_STARTED",
    "PACKAGE_WRITTEN",
    "PACKAGING_FAILED",
    "OUTPUT_PACKAGED",
    "IMPORTED",
    "CONSUMED",
    "REVOKED",
    "EXPIRED",
    "FAILED",
}
TRANSITIONS = {
    "ISSUED": {"CLAIMED", "REVOKED", "EXPIRED"},
    "CLAIMED": {"RUN_STARTED", "FAILED", "REVOKED", "EXPIRED"},
    # OUTPUT_PACKAGED remains accepted for historical ledgers; package_run itself always
    # uses the retry-safe intermediate states below.
    "RUN_STARTED": {"PACKAGING_STARTED", "OUTPUT_PACKAGED", "FAILED", "REVOKED", "EXPIRED"},
    "PACKAGING_STARTED": {"PACKAGE_WRITTEN", "PACKAGING_FAILED", "FAILED", "REVOKED", "EXPIRED"},
    "PACKAGE_WRITTEN": {"OUTPUT_PACKAGED", "PACKAGING_FAILED", "FAILED", "REVOKED", "EXPIRED"},
    "PACKAGING_FAILED": {"PACKAGING_STARTED", "FAILED", "REVOKED", "EXPIRED"},
    "OUTPUT_PACKAGED": {"IMPORTED", "FAILED", "REVOKED", "EXPIRED"},
    "IMPORTED": {"CONSUMED", "FAILED", "REVOKED"},
    "CONSUMED": set(),
    "REVOKED": set(),
    "EXPIRED": set(),
    "FAILED": set(),
}


class PermissionLedgerError(ValueError):
    """A permission slot transition is invalid or replayed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events_path(ledger_path: str | Path) -> Path:
    path = Path(ledger_path)
    return path.with_name(path.name + ".events.jsonl")


def _lock_path(ledger_path: str | Path) -> Path:
    path = Path(ledger_path)
    return path.with_name(path.name + ".lock")


def initialize(
    out: str | Path,
    *,
    study: str,
    providers: list[str],
    run_tags: dict[str, str] | str,
    task_universe_sha256: str,
    output_schema: str,
    authorization_nonce: str,
) -> dict[str, Any]:
    path = Path(out)
    if path.exists() or events_path(path).exists():
        raise PermissionLedgerError("permission ledger already exists; retry requires a new ledger")
    unique = sorted(set(map(str, providers)))
    if not unique or len(unique) != len(providers):
        raise PermissionLedgerError("provider matrix must be nonempty and unique")
    tags = (
        {provider: str(run_tags) for provider in unique}
        if isinstance(run_tags, str)
        else {str(key): str(value) for key, value in run_tags.items()}
    )
    if set(tags) != set(unique) or any(not value for value in tags.values()):
        raise PermissionLedgerError("run-tag matrix must exactly match providers")
    if len(task_universe_sha256) != 64 or len(authorization_nonce) != 64:
        raise PermissionLedgerError("task universe and authorization nonce must be SHA-256")
    payload = {
        "schema": LEDGER_SCHEMA,
        "study": study,
        "providers": unique,
        "run_tags": tags,
        "task_universe_sha256": task_universe_sha256,
        "output_schema": output_schema,
        "authorization_nonce": authorization_nonce,
        "initial_states": {provider: "ISSUED" for provider in unique},
        "issued_at_utc": _now(),
        "one_run_policy": True,
        "paper_evidence": False,
    }
    payload["ledger_hash"] = sha256_bytes(canonical_json_bytes(payload))
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return payload


def load_ledger(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise PermissionLedgerError("permission ledger is missing")
    ledger = json.loads(source.read_text(encoding="utf-8"))
    if ledger.get("schema") != LEDGER_SCHEMA or ledger.get("one_run_policy") is not True:
        raise PermissionLedgerError("permission ledger schema/policy mismatch")
    observed = ledger.get("ledger_hash")
    expected = sha256_bytes(
        canonical_json_bytes({key: value for key, value in ledger.items() if key != "ledger_hash"})
    )
    if observed != expected:
        raise PermissionLedgerError("permission ledger hash mismatch")
    if set(ledger.get("providers", [])) != set(ledger.get("initial_states", {})):
        raise PermissionLedgerError("permission ledger provider slots mismatch")
    return ledger


def _events(path: str | Path) -> list[dict[str, Any]]:
    source = events_path(path)
    if not source.exists():
        return []
    rows: list[dict[str, Any]] = []
    previous = "0" * 64
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            continue
        row = json.loads(line)
        if row.get("schema") != EVENT_SCHEMA or row.get("previous_event_hash") != previous:
            raise PermissionLedgerError(f"permission event chain mismatch at line {line_number}")
        expected = sha256_bytes(
            canonical_json_bytes({key: value for key, value in row.items() if key != "event_hash"})
        )
        if row.get("event_hash") != expected:
            raise PermissionLedgerError(f"permission event hash mismatch at line {line_number}")
        previous = expected
        rows.append(row)
    return rows


def status(path: str | Path) -> dict[str, Any]:
    ledger = load_ledger(path)
    rows = _events(path)
    slots = {provider: {"state": "ISSUED", "event_count": 0} for provider in ledger["providers"]}
    for row in rows:
        provider = str(row.get("provider"))
        if provider not in slots or row.get("from_state") != slots[provider]["state"]:
            raise PermissionLedgerError("permission event transition history is inconsistent")
        slots[provider] = {
            "state": row["to_state"],
            "event_count": slots[provider]["event_count"] + 1,
            "permission_id": row.get("permission_id"),
            "permission_signature": row.get("permission_signature"),
            "run_tag": row.get("run_tag"),
            "notebook": row.get("notebook"),
            "last_event_hash": row["event_hash"],
            "updated_at_utc": row["timestamp_utc"],
        }
    return {
        "schema": "certvic.cvpr.permission_ledger_status.v1",
        "ledger_hash": ledger["ledger_hash"],
        "study": ledger["study"],
        "task_universe_sha256": ledger["task_universe_sha256"],
        "output_schema": ledger["output_schema"],
        "slots": slots,
        "events": rows,
        "paper_evidence": False,
    }


def _mutate(
    path: str | Path, operation: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
) -> dict[str, Any]:
    lock = _lock_path(path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        ledger = load_ledger(path)
        current = status(path)
        event = operation(ledger, current)
        rows = current["events"]
        event = {
            "schema": EVENT_SCHEMA,
            **event,
            "timestamp_utc": _now(),
            "sequence": len(rows) + 1,
            "previous_event_hash": rows[-1]["event_hash"] if rows else "0" * 64,
        }
        event["event_hash"] = sha256_bytes(canonical_json_bytes(event))
        target = events_path(path)
        descriptor = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as output:
            output.write(json.dumps(event, sort_keys=True) + "\n")
            output.flush()
            os.fsync(output.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return event


def claim(
    path: str | Path,
    *,
    study: str,
    provider: str,
    run_tag: str,
    notebook: str,
    task_universe_sha256: str,
    permission_id: str,
    permission_signature: str,
) -> dict[str, Any]:
    def operation(ledger: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        if ledger["study"] != study or provider not in ledger["providers"]:
            raise PermissionLedgerError("wrong study or provider for permission ledger")
        if ledger["run_tags"][provider] != run_tag:
            raise PermissionLedgerError("wrong run tag for permission ledger slot")
        if ledger["task_universe_sha256"] != task_universe_sha256:
            raise PermissionLedgerError("wrong task universe for permission ledger")
        state = current["slots"][provider]["state"]
        if state != "ISSUED":
            raise PermissionLedgerError(f"permission slot cannot be claimed from {state}")
        return {
            "event": "CLAIM",
            "provider": provider,
            "from_state": state,
            "to_state": "CLAIMED",
            "study": study,
            "run_tag": run_tag,
            "notebook": notebook,
            "task_universe_sha256": task_universe_sha256,
            "permission_id": permission_id,
            "permission_signature": permission_signature,
        }

    return _mutate(path, operation)


def transition(
    path: str | Path,
    *,
    provider: str,
    to_state: str,
    permission_id: str,
    permission_signature: str,
    run_tag: str,
    actor: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if to_state not in STATES or to_state == "ISSUED":
        raise PermissionLedgerError(f"invalid destination state: {to_state}")

    def operation(ledger: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        if provider not in ledger["providers"] or ledger["run_tags"].get(provider) != run_tag:
            raise PermissionLedgerError("wrong provider or run tag for permission transition")
        slot = current["slots"][provider]
        from_state = slot["state"]
        if to_state not in TRANSITIONS[from_state]:
            raise PermissionLedgerError(f"invalid/replayed transition {from_state}->{to_state}")
        if from_state != "ISSUED" and (
            slot.get("permission_id") != permission_id
            or slot.get("permission_signature") != permission_signature
        ):
            raise PermissionLedgerError("permission identity differs from claimed slot")
        return {
            "event": "TRANSITION",
            "provider": provider,
            "from_state": from_state,
            "to_state": to_state,
            "study": ledger["study"],
            "run_tag": run_tag,
            "notebook": slot.get("notebook"),
            "task_universe_sha256": ledger["task_universe_sha256"],
            "permission_id": permission_id,
            "permission_signature": permission_signature,
            "actor": actor,
            "detail": detail or {},
        }

    return _mutate(path, operation)


def verify_slot(
    path: str | Path,
    *,
    provider: str,
    required_state: str,
    permission_id: str,
    permission_signature: str,
    run_tag: str,
) -> dict[str, Any]:
    current = status(path)
    slot = current["slots"].get(provider)
    if not slot or slot.get("state") != required_state:
        raise PermissionLedgerError(f"permission slot is not {required_state}")
    if (slot.get("permission_id"), slot.get("permission_signature"), slot.get("run_tag")) != (
        permission_id,
        permission_signature,
        run_tag,
    ):
        raise PermissionLedgerError("permission slot identity mismatch")
    return slot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage one-run CertVIC permission slots")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--out", required=True)
    init.add_argument("--study", required=True)
    init.add_argument("--providers", nargs="+", required=True)
    init.add_argument("--run-tag", required=True)
    init.add_argument("--task-universe-sha256", required=True)
    init.add_argument("--output-schema", required=True)
    init.add_argument("--authorization-nonce", required=True)
    show = sub.add_parser("status")
    show.add_argument("--ledger", required=True)
    claim_parser = sub.add_parser("claim")
    for flag in (
        "ledger",
        "study",
        "provider",
        "run-tag",
        "notebook",
        "task-universe-sha256",
        "permission-id",
        "permission-signature",
    ):
        claim_parser.add_argument("--" + flag, required=True)
    change = sub.add_parser("transition")
    for flag in (
        "ledger",
        "provider",
        "to-state",
        "permission-id",
        "permission-signature",
        "run-tag",
        "actor",
    ):
        change.add_argument("--" + flag, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = initialize(
                args.out,
                study=args.study,
                providers=args.providers,
                run_tags=args.run_tag,
                task_universe_sha256=args.task_universe_sha256,
                output_schema=args.output_schema,
                authorization_nonce=args.authorization_nonce,
            )
        elif args.command == "status":
            result = status(args.ledger)
        elif args.command == "claim":
            result = claim(
                args.ledger,
                study=args.study,
                provider=args.provider,
                run_tag=args.run_tag,
                notebook=args.notebook,
                task_universe_sha256=args.task_universe_sha256,
                permission_id=args.permission_id,
                permission_signature=args.permission_signature,
            )
        else:
            result = transition(
                args.ledger,
                provider=args.provider,
                to_state=args.to_state,
                permission_id=args.permission_id,
                permission_signature=args.permission_signature,
                run_tag=args.run_tag,
                actor=args.actor,
            )
    except (PermissionLedgerError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "status": "PERMISSION_LEDGER_BLOCKED",
                    "reason": str(exc),
                    "paper_evidence": False,
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
