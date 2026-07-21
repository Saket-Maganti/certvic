"""Validated, atomic, conflict-refusing JSONL promotion."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from certvic.cvpr.contracts import OutputContract, canonical_json_bytes, validate_output_rows


class TransactionError(ValueError):
    pass


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            suffix = "corrupt final line" if index == len(lines) else "corrupt JSONL line"
            raise TransactionError(f"{path}: {suffix} {index}: {exc}") from exc
        if not isinstance(row, dict):
            raise TransactionError(f"{path}: line {index} is not an object")
        rows.append(row)
    return rows


def canonical_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) for row in rows)


def promote_jsonl(
    rows: list[dict[str, Any]],
    destination: str | Path,
    contract: OutputContract,
) -> dict[str, Any]:
    errors = validate_output_rows(rows, contract)
    if errors:
        raise TransactionError("; ".join(errors))
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_jsonl(sorted(rows, key=lambda r: (r["item_id"], r["variant"])))
    if destination.exists():
        if destination.read_bytes() == payload:
            return {"status": "IDEMPOTENT", "path": str(destination), "rows": len(rows)}
        raise TransactionError(f"refusing to overwrite conflicting completed output: {destination}")
    handle, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, destination)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return {"status": "PROMOTED", "path": str(destination), "rows": len(rows)}


def shard_resume_state(
    paths: Iterable[str | Path],
    contract: OutputContract,
) -> dict[str, Any]:
    valid_rows: list[dict[str, Any]] = []
    corrupt: list[str] = []
    for path in paths:
        try:
            valid_rows.extend(read_jsonl(path))
        except TransactionError as exc:
            corrupt.append(str(exc))
    seen = {(str(row.get("item_id")), str(row.get("variant"))) for row in valid_rows}
    return {
        "completed": sorted([list(key) for key in seen & contract.expected_keys]),
        "missing": sorted([list(key) for key in contract.expected_keys - seen]),
        "corrupt": corrupt,
    }
