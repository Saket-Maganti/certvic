#!/usr/bin/env python3
"""Build and audit the deterministic maximum-ceiling pre-run release."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "release/certvic_cvpr_pre_run_maximum.zip"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)

EXACT_FILES = (
    "README.md",
    "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md",
    "pyproject.toml",
)
TREE_RULES = (
    ("certvic", {".py", ".json", ".yaml", ".yml"}),
    ("configs", {".json", ".yaml", ".yml", ".toml"}),
    ("notebooks/kaggle/cvpr", {".ipynb", ".json"}),
    ("docs/execution", {".md"}),
    ("execution_pack", {".md"}),
    ("paper_cvpr", {".tex", ".bib", ".json", ".csv"}),
    ("reports/max_ceiling_upgrade", {".md", ".csv", ".json", ".dot"}),
    ("reports/repository_replacement", {".md", ".csv", ".json"}),
    ("reports/kaggle_execution_pack", {".md", ".csv", ".json"}),
    ("requirements", {".lock"}),
)
EXACT_SCRIPTS = (
    "scripts/build_maximum_ceiling_release.py",
    "scripts/validate_t4x2_notebooks.py",
    "scripts/build_kaggle_wheelhouse.py",
    "scripts/build_model_snapshot_bundle.py",
    "scripts/run_phase_b_cpu_workflows.py",
    "scripts/refresh_kaggle_release_lineage.py",
)
EXACT_TESTS = (
    "tests/test_cvpr_chaos.py",
    "tests/test_max_ceiling_upgrade.py",
    "tests/test_cvpr_smoke_authorization_order.py",
    "tests/test_kaggle_execution_pack.py",
)
FORBIDDEN_PARTS = {
    "__pycache__", ".pytest_cache", ".ruff_cache", ".git", "local_inputs",
    "incoming_archives", "provider_returns", "private", "tmp", "cache",
}
FORBIDDEN_SUFFIXES = {
    ".zip", ".tar", ".gz", ".7z", ".pt", ".pth", ".safetensors", ".ckpt",
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff",
    ".aux", ".log", ".out", ".DS_Store",
}
EXCLUDED_RELEASE_REPORTS = {"release_privacy_audit.md", "release_privacy_audit.json"}


class ReleaseError(ValueError):
    """The release candidate is unsafe, incomplete, or non-deterministic."""


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _members(root: Path) -> list[Path]:
    selected: set[Path] = set()
    for relative in (*EXACT_FILES, *EXACT_SCRIPTS, *EXACT_TESTS):
        path = root / relative
        if path.is_file():
            selected.add(path)
    for relative, suffixes in TREE_RULES:
        tree = root / relative
        if not tree.is_dir():
            continue
        for path in tree.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(root)
            if path.name in EXCLUDED_RELEASE_REPORTS:
                continue
            if FORBIDDEN_PARTS & set(rel.parts) or path.suffix in FORBIDDEN_SUFFIXES:
                continue
            if path.suffix.lower() in suffixes:
                selected.add(path)
    for relative in (
        "kaggle_uploads/CERTVIC_KAGGLE_UPLOAD_MANIFEST.csv",
        "kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md",
        "kaggle_uploads/00_code/certvic_code_bundle.zip",
        "kaggle_uploads/00_code/certvic_notebooks_bundle.zip",
        "kaggle_uploads/00_code/certvic_configs_bundle.zip",
        "kaggle_uploads/00_code/certvic_execution_tools_bundle.zip",
        "kaggle_uploads/00_code/certvic_synthetic_validation_bundle.zip",
    ):
        path = root / relative
        if path.is_file():
            selected.add(path)
    return sorted(selected, key=lambda path: path.relative_to(root).as_posix())


def _manifest(files: Iterable[Path], root: Path) -> dict[str, Any]:
    return {
        "schema": "certvic.cvpr.maximum_release_manifest.v1",
        "paper_evidence": False,
        "deterministic_zip_timestamp": "1980-01-01T00:00:00Z",
        "files": {
            path.relative_to(root).as_posix(): {
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in files
        },
        "excluded": [
            "weights", "datasets", "image bytes", "private review sheets", "incoming archives",
            "provider returns", "caches", "secrets", "temporary files", "host paths",
        ],
    }


def build_release(out: str | Path, *, root: str | Path = ROOT) -> dict[str, Any]:
    base = Path(root).resolve()
    destination = Path(out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = _members(base)
    required = {
        "certvic/cvpr/doctor.py",
        "certvic/cvpr/next_action.py",
        "certvic/cvpr/run_graph.py",
        "certvic/cvpr/artifact_registry.py",
        "certvic/cvpr/reproducibility_capsule.py",
        "certvic/cvpr/notebook_runner.py",
        "certvic/cvpr/chaos.py",
        "certvic/cvpr/runtime_planner.py",
        "certvic/data/license_registry.py",
        "configs/execution/certvic_run_graph.yaml",
        "configs/data/source_license_registry.yaml",
        "execution_pack/00_READ_ME_FIRST.md",
        "certvic/cvpr/kaggle_bundle.py",
        "certvic/cvpr/t4x2.py",
        "certvic/cvpr/notebook_bootstrap.py",
        "certvic/cvpr/build_all_kaggle_inputs.py",
        "kaggle_uploads/CERTVIC_KAGGLE_UPLOAD_MANIFEST.csv",
        "kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md",
        "reports/kaggle_execution_pack/CERTVIC_KAGGLE_READY_FOR_PHASE_B_HANDOFF.md",
        "reports/max_ceiling_upgrade/CERTVIC_MAX_CEILING_VALIDATION.md",
    }
    relative_files = {path.relative_to(base).as_posix() for path in files}
    missing = sorted(required - relative_files)
    if missing:
        raise ReleaseError(f"release dependency closure is incomplete: {missing}")
    manifest = _manifest(files, base)
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    with destination.open("wb") as raw:
        with zipfile.ZipFile(
            raw, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True
        ) as archive:
            for path in files:
                relative = path.relative_to(base).as_posix()
                info = zipfile.ZipInfo(relative, FIXED_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            info = zipfile.ZipInfo("RELEASE_FILE_MANIFEST.json", FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, manifest_bytes, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return {
        "path": destination.as_posix(),
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "size": destination.stat().st_size,
        "member_count": len(files) + 1,
        "paper_evidence": False,
    }


def audit_release(archive_path: str | Path, *, execute_clean: bool = False) -> dict[str, Any]:
    source = Path(archive_path)
    errors: list[str] = []
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)):
            errors.append("duplicate archive members")
        if archive.testzip() is not None:
            errors.append("archive CRC failure")
        for member in members:
            path = PurePosixPath(member.filename)
            if path.is_absolute() or ".." in path.parts:
                errors.append(f"unsafe archive member: {member.filename}")
            if member.date_time != FIXED_TIME:
                errors.append(f"non-deterministic timestamp: {member.filename}")
        try:
            manifest = json.loads(archive.read("RELEASE_FILE_MANIFEST.json"))
        except (KeyError, json.JSONDecodeError):
            manifest = {"files": {}}
            errors.append("release manifest missing or invalid")
        for name, declared in manifest.get("files", {}).items():
            try:
                payload = archive.read(name)
            except KeyError:
                errors.append(f"manifest member missing: {name}")
                continue
            if len(payload) != declared.get("size") or _sha_bytes(payload) != declared.get("sha256"):
                errors.append(f"manifest hash/size mismatch: {name}")
        extras = sorted(set(names) - set(manifest.get("files", {})) - {"RELEASE_FILE_MANIFEST.json"})
        if extras:
            errors.append(f"unmanifested members: {extras}")
        allowed_nested_zips = {
            f"kaggle_uploads/00_code/{name}" for name in (
                "certvic_code_bundle.zip", "certvic_notebooks_bundle.zip",
                "certvic_configs_bundle.zip", "certvic_execution_tools_bundle.zip",
                "certvic_synthetic_validation_bundle.zip",
            )
        }
        forbidden = [
            name for name in names
            if FORBIDDEN_PARTS & set(PurePosixPath(name).parts)
            or (
                PurePosixPath(name).suffix.lower() in FORBIDDEN_SUFFIXES
                and name not in allowed_nested_zips
            )
        ]
        if forbidden:
            errors.append(f"forbidden release members: {forbidden}")
        clean_results: list[dict[str, Any]] = []
        if execute_clean and not errors:
            with tempfile.TemporaryDirectory(prefix="certvic_release_audit_") as temporary:
                root = Path(temporary)
                archive.extractall(root)
                commands = (
                    [sys.executable, "-m", "compileall", "-q", "certvic", "scripts", "tests"],
                    [sys.executable, "-m", "certvic.cvpr.doctor", "--help"],
                    [sys.executable, "-m", "certvic.cvpr.next_action", "--help"],
                    [sys.executable, "-m", "certvic.cvpr.run_graph", "--help"],
                    [sys.executable, "-m", "certvic.cvpr.chaos", "--help"],
                )
                for command in commands:
                    completed = subprocess.run(
                        command, cwd=root, check=False, capture_output=True, text=True, timeout=120
                    )
                    clean_results.append({"command": command, "exit_code": completed.returncode})
                    if completed.returncode != 0:
                        errors.append(f"clean extraction command failed: {command}")
    return {
        "schema": "certvic.cvpr.maximum_release_audit.v1",
        "passed": not errors,
        "errors": errors,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "member_count": len(names),
        "clean_extraction_commands": clean_results,
        "paper_evidence": False,
    }


def deterministic_rebuild(out: str | Path, *, root: str | Path = ROOT) -> dict[str, Any]:
    destination = Path(out)
    first = build_release(destination, root=root)
    with tempfile.TemporaryDirectory(prefix="certvic_release_rebuild_") as temporary:
        second_path = Path(temporary) / destination.name
        second = build_release(second_path, root=root)
        identical = destination.read_bytes() == second_path.read_bytes()
    return {"passed": identical, "first": first, "second_sha256": second["sha256"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the deterministic CertVIC maximum release")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--clean-extraction", action="store_true")
    parser.add_argument("--deterministic-rebuild", action="store_true")
    args = parser.parse_args(argv)
    if args.audit_only:
        result: dict[str, Any] = audit_release(args.out, execute_clean=args.clean_extraction)
    elif args.deterministic_rebuild:
        rebuild = deterministic_rebuild(args.out)
        audit = audit_release(args.out, execute_clean=args.clean_extraction)
        result = {"passed": rebuild["passed"] and audit["passed"], "rebuild": rebuild, "audit": audit}
    else:
        build = build_release(args.out)
        audit = audit_release(args.out, execute_clean=args.clean_extraction)
        result = {"passed": audit["passed"], "build": build, "audit": audit}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
