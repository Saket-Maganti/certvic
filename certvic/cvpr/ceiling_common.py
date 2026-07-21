"""Small, dependency-light primitives shared by the maximum-ceiling tools."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def repository_root(start: str | Path | None = None) -> Path:
    """Find the checkout root without embedding a host-specific absolute path."""
    current = Path(start).resolve() if start else Path(__file__).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "certvic").is_dir():
            return candidate
    raise FileNotFoundError("could not locate the CertVIC repository root")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def atomic_json(path: str | Path, value: Any) -> None:
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative_to_root(path: str | Path, root: str | Path) -> str:
    source = Path(path).resolve()
    base = Path(root).resolve()
    try:
        return source.relative_to(base).as_posix()
    except ValueError as error:
        raise ValueError(f"artifact is outside the repository: {source}") from error

