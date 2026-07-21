"""Deterministic hashing helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_record_hash(obj: Any) -> str:
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump(mode="json")
    return sha256_bytes(stable_json_dumps(obj).encode("utf-8"))


def stable_int_hash(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
