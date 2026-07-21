"""Offline environment-lock and wheelhouse verification utilities."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes


WHEEL_RE = re.compile(r"^[A-Za-z0-9_.+-]+\.whl$")


def load_environment_lock(path: str | Path) -> dict[str, Any]:
    lock = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"schema", "python", "packages", "cuda_contract", "offline_install"}
    if not isinstance(lock, dict) or required - set(lock):
        raise ValueError("environment lock is not a complete mapping")
    if lock["offline_install"].get("allow_index") is not False:
        raise ValueError("environment lock must prohibit package indexes at runtime")
    packages = lock["packages"]
    if not isinstance(packages, dict) or not packages:
        raise ValueError("environment lock packages must be nonempty")
    for name, version in packages.items():
        if not re.fullmatch(r"[a-z0-9_.-]+", str(name)) or not re.fullmatch(
            r"[0-9]+(?:\.[0-9]+)*(?:[a-z0-9.+-]*)", str(version)
        ):
            raise ValueError(f"invalid exact package pin: {name}=={version}")
    return lock


def environment_lock_hash(path: str | Path) -> str:
    return sha256_bytes(canonical_json_bytes(load_environment_lock(path)))


def verify_current_environment(path: str | Path, *, require_cuda: bool) -> dict[str, Any]:
    lock = load_environment_lock(path)
    expected_python = str(lock["python"]["version"])
    observed_python = platform.python_version()
    mismatches: list[dict[str, str]] = []
    if not observed_python.startswith(expected_python + "."):
        mismatches.append({"component": "python", "expected": expected_python,
                           "observed": observed_python})
    observed_packages: dict[str, str | None] = {}
    for name, expected in sorted(lock["packages"].items()):
        try:
            observed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            observed = None
        observed_packages[name] = observed
        if observed != expected:
            mismatches.append({"component": name, "expected": expected,
                               "observed": observed or "NOT_INSTALLED"})
    cuda = {"required": require_cuda, "available": False, "devices": []}
    torch = sys.modules.get("torch")
    if require_cuda and torch is None:
        try:
            import torch as imported_torch
            torch = imported_torch
        except ImportError:
            pass
    if torch is not None:
        cuda["available"] = bool(torch.cuda.is_available())
        cuda["devices"] = [torch.cuda.get_device_name(index)
                           for index in range(torch.cuda.device_count())]
    if require_cuda and not cuda["available"]:
        mismatches.append({"component": "cuda", "expected": "AVAILABLE", "observed": "UNAVAILABLE"})
    return {
        "schema": "certvic.cvpr.environment_verification.v1",
        "passed": not mismatches,
        "mismatches": mismatches,
        "environment_lock_hash": environment_lock_hash(path),
        "python": observed_python,
        "packages": observed_packages,
        "cuda": cuda,
        "verification_scope": "CURRENT_ENVIRONMENT_ONLY",
        "paper_evidence": False,
    }


def verify_wheelhouse(wheelhouse: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    root = Path(wheelhouse)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("wheelhouse manifest files must be a nonempty mapping")
    observed = {path.name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "size": path.stat().st_size}
                for path in root.iterdir() if path.is_file() and WHEEL_RE.fullmatch(path.name)}
    missing = sorted(set(files) - set(observed))
    extra = sorted(set(observed) - set(files))
    mismatched: list[str] = []
    metadata_errors: list[str] = []
    required_metadata = {
        "filename", "package", "version", "python_tag", "platform_tag", "size", "sha256",
        "dependency_role",
    }
    for name in sorted(set(files) & set(observed)):
        record = files[name]
        if isinstance(record, str):
            if record != observed[name]["sha256"]:
                mismatched.append(name)
            metadata_errors.append(f"{name}: legacy hash-only record is not execution eligible")
            continue
        if not isinstance(record, dict) or required_metadata - set(record):
            metadata_errors.append(f"{name}: incomplete wheel metadata")
            continue
        if record["filename"] != name or record["sha256"] != observed[name]["sha256"]:
            mismatched.append(name)
        if int(record["size"]) != observed[name]["size"]:
            mismatched.append(name)
    return {
        "schema": "certvic.cvpr.wheelhouse_verification.v1",
        "passed": not (missing or extra or mismatched or metadata_errors),
        "missing": missing, "extra": extra, "mismatched": sorted(set(mismatched)),
        "metadata_errors": metadata_errors,
        "files_verified": len(observed),
        "manifest_sha256": hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
        "network_used": False, "paper_evidence": False,
    }


def offline_environment_flags() -> dict[str, str]:
    """Return the complete no-network environment required by notebooks and loaders."""
    return {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "DIFFUSERS_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    }


def prepare_offline_environment(
    lock_path: str | Path,
    *,
    wheelhouse: str | Path | None,
    wheelhouse_manifest: str | Path | None,
    allow_preinstalled: bool,
    require_exact: bool,
    require_cuda: bool,
    installer: Any = subprocess.run,
) -> dict[str, Any]:
    """Accept an exact environment or install a fully verified wheelhouse offline."""
    for key, value in offline_environment_flags().items():
        os.environ[key] = value
    before = verify_current_environment(lock_path, require_cuda=require_cuda)
    if before["passed"] and allow_preinstalled:
        before["status"] = "EXACT_PREINSTALLED_ENVIRONMENT_ACCEPTED"
        before["offline_flags"] = offline_environment_flags()
        before["environment_hash"] = sha256_bytes(canonical_json_bytes(before))
        return before
    if before["passed"] and not allow_preinstalled:
        raise ValueError("exact preinstalled environment exists but policy prohibits using it")
    if not require_exact:
        raise ValueError("non-exact environments are prohibited for CVPR runtime paths")
    if wheelhouse is None or wheelhouse_manifest is None:
        raise ValueError("exact environment mismatch requires an attached wheelhouse and manifest")
    verification = verify_wheelhouse(wheelhouse, wheelhouse_manifest)
    if not verification["passed"]:
        raise ValueError(f"wheelhouse verification failed: {verification}")
    lock = load_environment_lock(lock_path)
    requirements = [f"{name}=={version}" for name, version in sorted(lock["packages"].items())]
    command = [
        sys.executable, "-m", "pip", "install", "--no-index", "--find-links",
        str(Path(wheelhouse).resolve()), "--disable-pip-version-check", *requirements,
    ]
    completed = installer(command, check=False, capture_output=True, text=True,
                          env={**os.environ, **offline_environment_flags()})
    if int(completed.returncode) != 0:
        raise ValueError(f"offline wheelhouse installation failed: {completed.stderr}")
    after = verify_current_environment(lock_path, require_cuda=require_cuda)
    if not after["passed"]:
        raise ValueError(
            "offline installation completed but exact verification still fails; restart or re-exec "
            f"the kernel before continuing: {after['mismatches']}"
        )
    result = {
        **after,
        "status": "OFFLINE_WHEELHOUSE_INSTALLED_AND_VERIFIED",
        "wheelhouse_manifest_sha256": verification["manifest_sha256"],
        "install_command": command,
        "offline_flags": offline_environment_flags(),
        "restart_or_reexec_checked": True,
        "network_used": False,
    }
    result["environment_hash"] = sha256_bytes(canonical_json_bytes(result))
    return result
