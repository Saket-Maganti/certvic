"""Shared deterministic helpers for the operator-only CVPR 2027 analyses."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping


REPO = Path(__file__).resolve().parents[1]
REPORT_ROOT = REPO / "reports" / "cvpr2027_max_ceiling"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _finite(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _finite(value: Any) -> Any:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(key): _finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite(item) for item in value]
    return value


def write_json(path: str | Path, value: Any) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_finite(value), indent=2, sort_keys=True) + "\n"
    file_descriptor, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(destination)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    return destination


def write_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> Path:
    destination = Path(path)
    payload = b"".join(canonical_json_bytes(dict(row)) + b"\n" for row in rows)
    return write_bytes(destination, payload)


def write_text(path: str | Path, value: str) -> Path:
    return write_bytes(path, value.encode("utf-8"))


def write_bytes(path: str | Path, value: bytes) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(destination)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    return destination


def write_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, Any]],
    fieldnames: Iterable[str] | None = None,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    materialized = [dict(row) for row in rows]
    if fieldnames is None:
        ordered: list[str] = []
        for row in materialized:
            for key in row:
                if key not in ordered:
                    ordered.append(key)
        fieldnames = ordered
    fields = list(fieldnames)
    file_descriptor, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n"
            )
            writer.writeheader()
            for row in materialized:
                writer.writerow({key: _csv_value(row.get(key)) for key in fields})
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(destination)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
    return destination


def _csv_value(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_finite(value), sort_keys=True, separators=(",", ":"))
    if value is None:
        return ""
    return value


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def resolve_repository_path(value: str | Path | None, *, base: Path | None = None) -> Path | None:
    """Resolve old absolute paths without depending on the original username/root."""
    if value is None or not str(value):
        return None
    raw = str(value)
    if raw.startswith("__CTRL__/") and base is not None:
        return (base / raw.removeprefix("__CTRL__/")).resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (base or REPO) / candidate
    marker = "/data/"
    normalized = raw.replace("\\", "/")
    if marker in normalized:
        portable = REPO / "data" / normalized.split(marker, maxsplit=1)[1]
        if portable.exists():
            return portable.resolve()
    if candidate.exists():
        return candidate.resolve()
    return candidate.resolve()


def artifact_manifest(paths: Iterable[str | Path], *, root: Path = REPO) -> dict[str, Any]:
    rows = []
    for value in sorted({Path(path).resolve() for path in paths}, key=lambda item: item.as_posix()):
        relative = value.relative_to(root).as_posix() if value.is_relative_to(root) else value.name
        rows.append(
            {
                "path": relative,
                "sha256": sha256_file(value),
                "size_bytes": value.stat().st_size,
            }
        )
    identity = hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
    return {
        "schema": "certvic.cvpr2027.artifact_manifest.v1",
        "identity_sha256": identity,
        "files": rows,
        "paper_evidence": False,
    }
