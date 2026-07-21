#!/usr/bin/env python3
"""Build and verify the deterministic, claim-safe Phase C pre-human release."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
ROOTS = (
    "certvic", "configs", "requirements", "notebooks/kaggle/cvpr",
    "notebooks/kaggle/provisioning", "scripts", "tests", "paper_cvpr/sections",
    "paper_cvpr/figures", "docs", "execution_pack", "reports/non_human_closure",
)
TOP = (
    "README.md", "LICENSE_STATUS.md", "pyproject.toml", "pytest.ini",
    "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", "PROJECT_RESTORE_HISTORICAL_OUTPUTS.md",
    "paper_cvpr/main.tex",
)
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _files() -> list[Path]:
    paths: set[Path] = set()
    for relative in ROOTS:
        base = ROOT / relative
        if not base.exists():
            continue
        for path in ([base] if base.is_file() else base.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(ROOT)
            if set(rel.parts) & EXCLUDED_PARTS or path.suffix.lower() in EXCLUDED_SUFFIXES:
                continue
            paths.add(path)
    for relative in TOP:
        path = ROOT / relative
        if path.is_file():
            paths.add(path)
    return sorted(paths, key=lambda path: path.relative_to(ROOT).as_posix())


def build(output: Path) -> dict:
    files = _files()
    records = {
        path.relative_to(ROOT).as_posix(): {"size": path.stat().st_size, "sha256": _sha(path)}
        for path in files
    }
    manifest = {
        "schema": "certvic.phase_c.pre_human_release.v1",
        "status": "PRE_HUMAN_EXTERNAL_EXECUTION_PENDING",
        "deterministic_timestamp": "1980-01-01T00:00:00Z",
        "files": records,
        "exclusions": [
            "model weights and snapshot archives", "wheelhouse bytes", "private source data",
            "unredacted or completed human sheets", "secrets and caches", "incoming archives",
            "historical kaggleoutputs bytes",
        ],
        "paper_evidence": False,
        "genuine_human_reviewed_true_count": 0,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in [(path.relative_to(ROOT).as_posix(), path) for path in files]:
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        info = zipfile.ZipInfo("RELEASE_FILE_MANIFEST.json", FIXED_TIME)
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, manifest_bytes, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return verify(output)


def verify(path: Path) -> dict:
    errors: list[str] = []
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            errors.append("duplicate member")
        for info in infos:
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts:
                errors.append(f"unsafe member: {info.filename}")
            if info.date_time != FIXED_TIME:
                errors.append(f"non-deterministic timestamp: {info.filename}")
        manifest = json.loads(archive.read("RELEASE_FILE_MANIFEST.json"))
        if set(manifest["files"]) != set(names) - {"RELEASE_FILE_MANIFEST.json"}:
            errors.append("manifest universe mismatch")
        for name, record in manifest["files"].items():
            payload = archive.read(name)
            if len(payload) != record["size"] or hashlib.sha256(payload).hexdigest() != record["sha256"]:
                errors.append(f"hash mismatch: {name}")
        with tempfile.TemporaryDirectory(prefix="certvic_phase_c_release_") as temp:
            archive.extractall(temp)
            for name, record in manifest["files"].items():
                extracted = Path(temp) / name
                if not extracted.is_file() or _sha(extracted) != record["sha256"]:
                    errors.append(f"clean extraction mismatch: {name}")
    return {
        "schema": "certvic.phase_c.release_validation.v1",
        "passed": not errors,
        "errors": errors,
        "path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
        "size": path.stat().st_size,
        "sha256": _sha(path),
        "members": len(names),
        "paper_evidence": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="release/certvic_phase_c_pre_human_release.zip")
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    result = build(output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
