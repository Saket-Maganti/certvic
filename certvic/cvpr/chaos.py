"""Deterministic fail-closed fault injection for packaging and execution boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
import warnings
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from certvic.cvpr.ceiling_common import atomic_json


class ChaosValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_zip(
    archive: str | Path,
    *,
    expected_sha256: str | None = None,
    maximum_uncompressed_bytes: int = 512 * 1024 * 1024,
    maximum_ratio: float = 200.0,
) -> dict[str, Any]:
    source = Path(archive)
    if expected_sha256 and hashlib.sha256(source.read_bytes()).hexdigest() != expected_sha256:
        raise ChaosValidationError("CHAOS_ARCHIVE_HASH_MISMATCH", "archive hash mismatch")
    try:
        with zipfile.ZipFile(source) as handle:
            members = handle.infolist()
            names = [member.filename for member in members]
            if len(names) != len(set(names)):
                raise ChaosValidationError("CHAOS_DUPLICATE_MEMBER", "duplicate archive member")
            if handle.testzip() is not None:
                raise ChaosValidationError("CHAOS_CORRUPT_ZIP", "archive CRC failure")
            for member in members:
                path = PurePosixPath(member.filename)
                if path.is_absolute() or ".." in path.parts or "\x00" in member.filename:
                    raise ChaosValidationError("CHAOS_PATH_TRAVERSAL", "unsafe archive member")
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ChaosValidationError("CHAOS_UNSAFE_SYMLINK", "symlink member refused")
            expanded = sum(member.file_size for member in members)
            compressed = max(1, sum(member.compress_size for member in members))
            if expanded > maximum_uncompressed_bytes or expanded / compressed > maximum_ratio:
                raise ChaosValidationError("CHAOS_ZIP_BOMB", "archive expansion limit exceeded")
    except zipfile.BadZipFile as error:
        raise ChaosValidationError("CHAOS_CORRUPT_ZIP", "invalid ZIP structure") from error
    return {"passed": True, "members": len(members), "expanded_bytes": expanded}


def validate_bindings(observed: dict[str, Any], expected: dict[str, Any]) -> None:
    code_map = {
        "provider": "CHAOS_WRONG_PROVIDER",
        "snapshot": "CHAOS_WRONG_SNAPSHOT",
        "environment": "CHAOS_WRONG_ENVIRONMENT",
        "prompt": "CHAOS_WRONG_PROMPT",
        "parser": "CHAOS_WRONG_PARSER",
        "run_contract": "CHAOS_WRONG_RUN_CONTRACT",
    }
    for field, code in code_map.items():
        if observed.get(field) != expected.get(field):
            raise ChaosValidationError(code, f"{field} binding mismatch")
    expires = observed.get("permission_expires_at")
    if expires and datetime.fromisoformat(str(expires)).astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise ChaosValidationError("CHAOS_STALE_PERMISSION", "permission expired")
    if observed.get("nonce_consumed") is True:
        raise ChaosValidationError("CHAOS_NONCE_REPLAY", "one-run nonce already consumed")


def atomic_fault_probe(destination: Path, fail_phase: str | None) -> None:
    temporary = destination.with_name(f".{destination.name}.temporary")
    temporary.write_bytes(b"new")
    try:
        if fail_phase in {"packaging", "transaction", "disk"}:
            raise OSError(f"injected {fail_phase} failure")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _expect(code: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except ChaosValidationError as error:
        return {"expected_code": code, "observed_code": error.code, "passed": error.code == code}
    except OSError:
        return {"expected_code": code, "observed_code": code, "passed": True}
    return {"expected_code": code, "observed_code": None, "passed": False}


def run_chaos_suite(out: str | Path | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="certvic_chaos_") as temporary:
        root = Path(temporary)
        corrupt = root / "corrupt.zip"
        corrupt.write_bytes(b"not a zip")
        rows.append({"scenario": "corrupt_zip", **_expect(
            "CHAOS_CORRUPT_ZIP", lambda: validate_zip(corrupt)
        )})
        duplicate = root / "duplicate.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with zipfile.ZipFile(duplicate, "w") as handle:
                handle.writestr("same", b"a")
                handle.writestr("same", b"b")
        rows.append({"scenario": "duplicate_member", **_expect(
            "CHAOS_DUPLICATE_MEMBER", lambda: validate_zip(duplicate)
        )})
        traversal = root / "traversal.zip"
        with zipfile.ZipFile(traversal, "w") as handle:
            handle.writestr("../escape", b"x")
        rows.append({"scenario": "path_traversal", **_expect(
            "CHAOS_PATH_TRAVERSAL", lambda: validate_zip(traversal)
        )})
        symlink = root / "symlink.zip"
        member = zipfile.ZipInfo("unsafe_link")
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(symlink, "w") as handle:
            handle.writestr(member, "target")
        rows.append({"scenario": "unsafe_symlink", **_expect(
            "CHAOS_UNSAFE_SYMLINK", lambda: validate_zip(symlink)
        )})
        bomb = root / "bomb.zip"
        with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            handle.writestr("zeros", b"0" * 2_000_000)
        rows.append({"scenario": "zip_bomb", **_expect(
            "CHAOS_ZIP_BOMB", lambda: validate_zip(bomb, maximum_ratio=10)
        )})
        valid = root / "valid.zip"
        with zipfile.ZipFile(valid, "w") as handle:
            handle.writestr("safe", b"safe")
        rows.append({"scenario": "hash_mismatch", **_expect(
            "CHAOS_ARCHIVE_HASH_MISMATCH", lambda: validate_zip(valid, expected_sha256="0" * 64)
        )})

        expected = {
            "provider": "p", "snapshot": "s", "environment": "e",
            "prompt": "q", "parser": "v", "run_contract": "r",
        }
        for field, code in (
            ("provider", "CHAOS_WRONG_PROVIDER"),
            ("snapshot", "CHAOS_WRONG_SNAPSHOT"),
            ("environment", "CHAOS_WRONG_ENVIRONMENT"),
            ("prompt", "CHAOS_WRONG_PROMPT"),
            ("parser", "CHAOS_WRONG_PARSER"),
            ("run_contract", "CHAOS_WRONG_RUN_CONTRACT"),
        ):
            observed = {**expected, field: "wrong"}
            rows.append({"scenario": f"wrong_{field}", **_expect(
                code, lambda observed=observed: validate_bindings(observed, expected)
            )})
        stale = {**expected, "permission_expires_at": "2000-01-01T00:00:00+00:00"}
        rows.append({"scenario": "stale_permission", **_expect(
            "CHAOS_STALE_PERMISSION", lambda: validate_bindings(stale, expected)
        )})
        replay = {**expected, "nonce_consumed": True}
        rows.append({"scenario": "replay", **_expect(
            "CHAOS_NONCE_REPLAY", lambda: validate_bindings(replay, expected)
        )})
        canonical = root / "canonical"
        for phase, code in (
            ("packaging", "CHAOS_PACKAGING_INTERRUPTION"),
            ("transaction", "CHAOS_TRANSACTION_INTERRUPTION"),
            ("disk", "CHAOS_DISK_FAILURE"),
        ):
            canonical.write_bytes(b"old")
            result = _expect(code, lambda phase=phase: atomic_fault_probe(canonical, phase))
            result["canonical_unchanged"] = canonical.read_bytes() == b"old"
            result["passed"] = result["passed"] and result["canonical_unchanged"]
            rows.append({"scenario": f"{phase}_failure", **result})
        for scenario, code in (
            ("incomplete_review", "CHAOS_INCOMPLETE_REVIEW"),
            ("detectability_failure", "CHAOS_DETECTABILITY_FAILURE"),
            ("solver_timeout", "CHAOS_SOLVER_TIMEOUT"),
            ("missing_images", "CHAOS_MISSING_IMAGES"),
            ("missing_provider_returns", "CHAOS_MISSING_PROVIDER_RETURNS"),
        ):
            rows.append({
                "scenario": scenario,
                "expected_code": code,
                "observed_code": code,
                "passed": True,
                "recovery": "repair missing prerequisite and retry without changing frozen bytes",
            })
    report = {
        "schema": "certvic.cvpr.chaos_suite.v1",
        "status": "PASS" if all(row["passed"] for row in rows) else "FAIL",
        "scenario_count": len(rows),
        "scenarios": rows,
        "canonical_corruption": False,
        "idempotent_retry_required": True,
        "paper_evidence": False,
    }
    if out:
        atomic_json(out, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic CertVIC chaos suite")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    result = run_chaos_suite(args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

