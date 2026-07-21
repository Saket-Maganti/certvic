"""Fail-closed validation of the sole prospective confirmatory protocol authority."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


class ProtocolAuthorityError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_authority(root: str | Path = ".") -> dict[str, Any]:
    base = Path(root).resolve()
    authority_path = base / "configs/studies/certvic_confirmatory_authority.json"
    errors: list[str] = []
    try:
        authority = json.loads(authority_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProtocolAuthorityError(f"authority manifest is missing or invalid: {exc}") from exc
    if authority.get("status") != "AUTHORITATIVE_AND_FROZEN":
        errors.append("authority status is not frozen")
    protocol_path = base / str(authority.get("authoritative_config_path", ""))
    analysis_path = base / str(authority.get("analysis_lock_path", ""))
    if not protocol_path.is_file():
        errors.append("authoritative protocol is missing")
        protocol = {}
    else:
        protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8")) or {}
        if protocol.get("schema") != authority.get("authoritative_schema_version"):
            errors.append("authoritative protocol schema mismatch")
        if protocol.get("protocol_authority") != authority_path.relative_to(base).as_posix():
            errors.append("authoritative protocol does not point back to authority manifest")
        if _sha256(protocol_path) != authority.get("protocol_sha256"):
            errors.append("authoritative protocol hash mismatch")
    if not analysis_path.is_file() or _sha256(analysis_path) != authority.get("analysis_lock_sha256"):
        errors.append("primary analysis lock is missing or hash-mismatched")
    superseded = authority.get("superseded_config_paths")
    if not isinstance(superseded, list) or not superseded:
        errors.append("superseded protocol inventory is empty")
        superseded = []
    for relative in superseded:
        path = base / str(relative)
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except OSError:
            errors.append(f"superseded protocol is missing: {relative}")
            continue
        if payload.get("status") != "DEPRECATED_NOT_FOR_EXECUTION":
            errors.append(f"superseded protocol is executable or ambiguously labeled: {relative}")
        if payload.get("execution_allowed") is not False:
            errors.append(f"superseded protocol does not fail closed: {relative}")
    prospective = []
    for path in sorted((base / "configs").rglob("*.yaml")):
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        if payload.get("prospective") is True and payload.get("status") != "DEPRECATED_NOT_FOR_EXECUTION":
            prospective.append(path.relative_to(base).as_posix())
    expected = [protocol_path.relative_to(base).as_posix()] if protocol_path.is_file() else []
    if prospective != expected:
        errors.append(f"expected exactly one live prospective protocol; found {prospective}")
    return {
        "schema": "certvic.confirmatory.protocol_authority_validation.v1",
        "passed": not errors,
        "errors": errors,
        "authority_manifest": authority_path.relative_to(base).as_posix(),
        "authoritative_protocol": expected[0] if expected else None,
        "live_prospective_protocols": prospective,
        "protocol_sha256": _sha256(protocol_path) if protocol_path.is_file() else None,
        "analysis_lock_sha256": _sha256(analysis_path) if analysis_path.is_file() else None,
        "paper_evidence": False,
    }


def require_authority(root: str | Path = ".") -> dict[str, Any]:
    result = validate_authority(root)
    if not result["passed"]:
        raise ProtocolAuthorityError("; ".join(result["errors"]))
    return result
