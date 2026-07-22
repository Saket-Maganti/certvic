"""Build deterministic profile-specific Linux offline wheelhouse bundles."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

from packaging.utils import canonicalize_name

from certvic.cvpr.environment_lock import environment_lock_hash, load_environment_lock
from certvic.cvpr.kaggle_bundle import build_bundle
from certvic.cvpr.runtime_profiles import (
    RuntimeProfileError,
    profile_hash,
    target_tags,
    validate_wheelhouse,
    wheel_record,
)


MODES = {"LOCAL_VERIFY_ONLY", "LINUX_CONTAINER_BUILD", "KAGGLE_PROVISIONING_BUILD"}
LOCK_NAMES = (
    "kaggle_base.lock", "kaggle_qwen.lock", "kaggle_internvl.lock",
    "kaggle_llava.lock", "kaggle_generation.lock", "kaggle_analysis.lock",
)
PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s]+)$")
DEFAULT_PROFILE = "kaggle_cp312_2026_07"


class WheelhouseBuilderError(ValueError):
    """Linux wheel bytes are absent, incompatible, or incomplete."""


def normalize(name: str) -> str:
    return canonicalize_name(name)


def parse_locks(requirements_root: str | Path) -> dict[str, dict[str, str]]:
    root = Path(requirements_root)
    parsed: dict[str, dict[str, str]] = {}
    for name in LOCK_NAMES:
        path = root / name
        if not path.is_file():
            raise WheelhouseBuilderError(f"missing requirements lock: {path}")
        pins: dict[str, str] = {}
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("-r "):
                continue
            match = PIN.fullmatch(line)
            if match is None:
                raise WheelhouseBuilderError(f"lock is not exact: {path.name}: {line}")
            package, version = match.groups()
            key = normalize(package)
            if key in pins and pins[key] != version:
                raise WheelhouseBuilderError(f"conflicting pin for {package}")
            pins[key] = version
        parsed[name] = pins
    base = parsed["kaggle_base.lock"]
    for name, pins in parsed.items():
        if name != "kaggle_base.lock" and set(base) & set(pins):
            raise WheelhouseBuilderError(f"{name} duplicates base pins: {sorted(set(base) & set(pins))}")
    return parsed


def all_pins(locks: Mapping[str, Mapping[str, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for pins in locks.values():
        for package, version in pins.items():
            if package in result and result[package] != version:
                raise WheelhouseBuilderError(f"cross-lock version conflict: {package}")
            result[package] = version
    return result


def _lock_path(requirements_root: str | Path, environment_lock: str | Path | None) -> Path:
    return Path(environment_lock or Path(requirements_root).parent / "configs/runtime/kaggle_t4x2_environment.lock.json")


def _selected_target(
    profile_id: str, *, requirements_root: str | Path, environment_lock: str | Path | None = None
) -> dict[str, Any]:
    path = _lock_path(requirements_root, environment_lock)
    lock = load_environment_lock(path)
    if profile_id not in lock["runtime_profiles"]:
        raise WheelhouseBuilderError(f"unknown runtime profile: {profile_id}")
    profile = lock["runtime_profiles"][profile_id]
    return {
        "schema": "certvic.cvpr.selected_runtime_profile.v2",
        "profile_id": profile_id,
        "profile_hash": profile_hash(profile_id, profile),
        "profile": profile,
        "observed_runtime": {
            "schema": "certvic.cvpr.runtime_probe.v2",
            "executable": sys.executable,
            "implementation": profile["implementation"],
            "python_version": profile["python_version"] + ".0",
            "python_major_minor": profile["python_version"],
            "architecture": profile["architecture"], "system": profile["system"],
            "libc": {"name": profile["libc"], "version": profile["glibc_observed"]},
            "supported_tags": target_tags(profile), "paper_evidence": False,
        },
    }


def _wheel_record(path: Path, profile: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return rich wheel metadata; default retains the legacy CP310 unit-test API."""
    if profile is None:
        profile = {
            "python_version": "3.10", "python_abi": "cp310", "architecture": "x86_64",
            "glibc_minimum": "2.17", "glibc_observed": "2.35",
        }
    try:
        record = wheel_record(path, supported_tags=target_tags(profile))
    except RuntimeProfileError as error:
        raise WheelhouseBuilderError(str(error)) from error
    if not record["compatible"]:
        if any(
            token in record["platform_tag"]
            for token in ("macosx", "win32", "win_amd64")
        ):
            raise WheelhouseBuilderError(f"non-Linux wheel prohibited: {path.name}")
        raise WheelhouseBuilderError(
            f"wheel is incompatible with {profile['python_abi']}/Linux x86_64: {path.name}"
        )
    return record


def verify_wheel_root(
    wheel_root: str | Path,
    *,
    requirements_root: str | Path,
    profile_id: str = DEFAULT_PROFILE,
    environment_lock: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(wheel_root)
    locks = parse_locks(requirements_root)
    required = all_pins(locks)
    selected = _selected_target(
        profile_id, requirements_root=requirements_root, environment_lock=environment_lock
    )
    if not root.is_dir() or not any(root.glob("*.whl")):
        return {
            "schema": "certvic.kaggle.wheelhouse_compatibility.v2",
            "status": "BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES", "passed": False,
            "runtime_profile_id": profile_id, "runtime_profile_hash": selected["profile_hash"],
            "target": selected["profile"], "required_packages": required,
            "missing_direct_packages": sorted(required), "files": {},
            "network_used": False, "paper_evidence": False,
        }
    try:
        checked = validate_wheelhouse(
            root, selected_profile=selected, required_packages=required
        )
    except RuntimeProfileError as error:
        return {
            "schema": "certvic.kaggle.wheelhouse_compatibility.v2",
            "status": error.code, "passed": False,
            "runtime_profile_id": profile_id, "runtime_profile_hash": selected["profile_hash"],
            "target": selected["profile"], "required_packages": required,
            "missing_direct_packages": error.report.get("missing_packages", []),
            "incompatible_wheels": error.report.get("incompatible_wheels", []),
            "source_distributions": error.report.get("source_distributions", []),
            "files": {}, "failure_report": error.report,
            "network_used": False, "paper_evidence": False,
        }
    return {
        "schema": "certvic.kaggle.wheelhouse_compatibility.v2",
        "status": "PASS", "passed": True,
        "runtime_profile_id": profile_id, "runtime_profile_hash": selected["profile_hash"],
        "target": selected["profile"], "required_packages": required,
        "missing_direct_packages": [], "files": checked["files"],
        "supported_tags": checked["supported_tags"],
        "wheel_count": checked["wheel_count"], "network_used": False,
        "paper_evidence": False,
    }


def _install_script() -> bytes:
    return b'''#!/usr/bin/env bash
set -euo pipefail
PYTHON="${1:?usage: install_offline.sh ISOLATED_PYTHON WHEELHOUSE LOCK}"
WHEELHOUSE="${2:?usage: install_offline.sh ISOLATED_PYTHON WHEELHOUSE LOCK}"
LOCK="${3:?usage: install_offline.sh ISOLATED_PYTHON WHEELHOUSE LOCK}"
export PIP_NO_INDEX=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 DIFFUSERS_OFFLINE=1
"$PYTHON" -m pip install --no-index --find-links "$WHEELHOUSE" --only-binary=:all: -r "$LOCK"
'''


def _smoke_script() -> bytes:
    return b'''import importlib, json, platform, sys
from packaging.tags import sys_tags
MODULES = ["torch", "torchvision", "transformers", "accelerate", "tokenizers",
           "safetensors", "sentencepiece", "PIL", "numpy", "scipy", "pandas",
           "sklearn", "cv2", "diffusers"]
failed, versions = {}, {}
for name in MODULES:
    try:
        module = importlib.import_module(name)
        versions[name] = str(getattr(module, "__version__", "IMPORTED"))
    except Exception as error:
        failed[name] = f"{type(error).__name__}: {error}"
report = {"python": platform.python_version(), "executable": sys.executable,
          "supported_tags": [str(tag) for tag in sys_tags()], "versions": versions,
          "failed": failed, "network_used": False, "paper_evidence": False}
print(json.dumps(report, sort_keys=True))
if failed: raise SystemExit(1)
'''


def _download(
    mode: str,
    destination: Path,
    *,
    requirements_root: Path,
    profile_id: str,
    environment_lock: str | Path | None = None,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    if mode not in MODES - {"LOCAL_VERIFY_ONLY"}:
        raise WheelhouseBuilderError(f"mode does not provision bytes: {mode}")
    destination.mkdir(parents=True, exist_ok=True)
    pins = all_pins(parse_locks(requirements_root))
    selected = _selected_target(
        profile_id, requirements_root=requirements_root, environment_lock=environment_lock
    )
    profile = selected["profile"]
    lock = load_environment_lock(_lock_path(requirements_root, environment_lock))
    platforms = list(dict.fromkeys(
        tag.split("-", 2)[2] for tag in target_tags(profile)
        if tag.split("-", 2)[2] != "any"
    ))
    command = [
        sys.executable, "-m", "pip", "download", "--only-binary=:all:",
        "--dest", str(destination), "--python-version", profile["python_version"].replace(".", ""),
        "--implementation", "cp", "--abi", profile["python_abi"],
    ]
    for value in platforms:
        command += ["--platform", value]
    command += ["--extra-index-url", lock["torch_cuda_distribution"]["index_url"]]
    command += [f"{name}=={version}" for name, version in sorted(pins.items())]
    completed = runner(command, check=False, capture_output=True, text=True)
    if int(completed.returncode) != 0:
        raise WheelhouseBuilderError(
            "wheel provisioning failed; preserve resolver logs: " + str(completed.stderr)[-4000:]
        )
    return {
        "command": command,
        "stdout_tail": str(completed.stdout)[-4000:],
        "stderr_tail": str(completed.stderr)[-4000:],
        "official_sources": ["https://pypi.org/simple", lock["torch_cuda_distribution"]["index_url"]],
    }


def build_wheelhouse(
    *,
    wheel_root: str | Path,
    output: str | Path,
    requirements_root: str | Path,
    mode: str = "LOCAL_VERIFY_ONLY",
    provision: bool = False,
    profile_id: str = DEFAULT_PROFILE,
    environment_lock: str | Path | None = None,
    provisioning_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(wheel_root)
    locks_root = Path(requirements_root)
    if mode not in MODES:
        raise WheelhouseBuilderError(f"unknown mode: {mode}")
    provisioning: dict[str, Any] | None = dict(provisioning_report or {}) or None
    if provision:
        provisioning = _download(
            mode, root, requirements_root=locks_root, profile_id=profile_id,
            environment_lock=environment_lock,
        )
    compatibility = verify_wheel_root(
        root, requirements_root=locks_root, profile_id=profile_id,
        environment_lock=environment_lock,
    )
    if not compatibility["passed"]:
        return compatibility
    lock_path = _lock_path(locks_root, environment_lock)
    files: dict[str, Path | bytes] = {
        f"wheels/{name}": root / name for name in compatibility["files"]
    }
    for name in LOCK_NAMES:
        files[f"requirements/{name}"] = locks_root / name
    package_manifest = {
        "schema": "certvic.cvpr.wheelhouse_manifest.v3",
        "environment_lock_hash": environment_lock_hash(lock_path),
        "runtime_profile_id": profile_id,
        "runtime_profile_hash": compatibility["runtime_profile_hash"],
        "files": compatibility["files"],
        "required_packages": compatibility["required_packages"],
        "supported_tags": compatibility["supported_tags"],
        "network_used": mode != "LOCAL_VERIFY_ONLY",
        "official_sources": (
            (provisioning or {}).get("official_sources")
            or (["https://pypi.org/simple", load_environment_lock(lock_path)[
                "torch_cuda_distribution"
            ]["index_url"]] if mode != "LOCAL_VERIFY_ONLY" else [])
        ),
        "target": compatibility["target"], "paper_evidence": False,
    }
    files["wheelhouse_manifest.json"] = (
        json.dumps(package_manifest, indent=2, sort_keys=True) + "\n"
    ).encode()
    files["compatibility_report.json"] = (
        json.dumps(compatibility, indent=2, sort_keys=True) + "\n"
    ).encode()
    if provisioning is not None:
        files["provisioning_report.json"] = (
            json.dumps(provisioning, indent=2, sort_keys=True) + "\n"
        ).encode()
    files["install_offline.sh"] = _install_script()
    files["smoke_imports.py"] = _smoke_script()
    expected_filename = compatibility["target"]["expected_wheelhouse_filename"]
    bundle = build_bundle(
        output, files, bundle_type="OFFLINE_LINUX_WHEELHOUSE", study="all",
        stage="environment", provider=None,
        required_notebook="00A_certvic_code_and_environment_smoke.ipynb",
        dataset_slug=f"certvic/{Path(expected_filename).stem.replace('_', '-')}",
        mount_path=f"/kaggle/input/{Path(expected_filename).stem.replace('_', '-')}",
        external_dependency_status="EXTERNAL_BYTES_VERIFIED",
        evidence_class="NON_EVIDENCE_RUNTIME_DEPENDENCY",
        builder_command=(
            "python3 -m certvic.cvpr.wheelhouse_builder --mode LOCAL_VERIFY_ONLY "
            f"--profile {profile_id} --requirements-root requirements --wheel-root <WHEELS> "
            f"--output kaggle_uploads/01_wheelhouse/{expected_filename}"
        ),
        validation_command=f"python3 -m certvic.cvpr.kaggle_bundle verify {output}",
        readme=(
            "# CertVIC offline Kaggle wheelhouse\n\n"
            f"Runtime profile: `{profile_id}`. Binary wheels only; every wheel is checked against "
            "the target packaging tag set before this deterministic bundle is emitted."
        ),
        extra_manifest={
            "compatibility_report": "compatibility_report.json",
            "runtime_profile_id": profile_id,
            "runtime_profile_hash": compatibility["runtime_profile_hash"],
        },
    )
    return {
        **bundle,
        "runtime_profile_id": profile_id,
        "runtime_profile_hash": compatibility["runtime_profile_hash"],
        "wheel_count": compatibility["wheel_count"],
        "required_package_count": len(compatibility["required_packages"]),
        "compatibility_status": compatibility["status"],
    }


def deterministic_provision(
    *,
    wheel_root: str | Path,
    output: str | Path,
    requirements_root: str | Path,
    profile_id: str = DEFAULT_PROFILE,
    environment_lock: str | Path | None = None,
) -> dict[str, Any]:
    """Provision once, build twice, and require byte-identical bundle output."""
    root = Path(wheel_root)
    if root.exists() and any(root.iterdir()):
        raise WheelhouseBuilderError(
            "deterministic provisioning requires an empty wheel root; start a fresh builder session"
        )
    provisioning = _download(
        "KAGGLE_PROVISIONING_BUILD", root, requirements_root=Path(requirements_root),
        profile_id=profile_id, environment_lock=environment_lock,
    )
    destination = Path(output)
    first = build_wheelhouse(
        wheel_root=root, output=destination, requirements_root=requirements_root,
        mode="KAGGLE_PROVISIONING_BUILD", profile_id=profile_id,
        environment_lock=environment_lock, provisioning_report=provisioning,
    )
    if not first.get("passed", False):
        return first
    with tempfile.TemporaryDirectory(prefix="certvic_wheelhouse_rebuild_") as temporary:
        second_path = Path(temporary) / destination.name
        second = build_wheelhouse(
            wheel_root=root, output=second_path, requirements_root=requirements_root,
            mode="KAGGLE_PROVISIONING_BUILD", profile_id=profile_id,
            environment_lock=environment_lock, provisioning_report=provisioning,
        )
        identical = destination.read_bytes() == second_path.read_bytes()
    if not identical:
        raise WheelhouseBuilderError("deterministic wheelhouse rebuild was not byte-identical")
    return {
        **first, "resolver_result": provisioning, "deterministic_rebuild": {
            "result": "PASS", "byte_identical": True,
            "first_sha256": first["sha256"], "second_sha256": second["sha256"],
        },
    }


def status(
    requirements_root: str | Path,
    wheel_root: str | Path | None = None,
    *,
    profile_id: str = DEFAULT_PROFILE,
    environment_lock: str | Path | None = None,
) -> dict[str, Any]:
    selected = _selected_target(
        profile_id, requirements_root=requirements_root, environment_lock=environment_lock
    )
    if wheel_root is not None:
        return verify_wheel_root(
            wheel_root, requirements_root=requirements_root, profile_id=profile_id,
            environment_lock=environment_lock,
        )
    output = selected["profile"]["expected_wheelhouse_filename"]
    return {
        "status": "CP312_WHEELHOUSE_BUILDER_READY" if profile_id == DEFAULT_PROFILE else "LEGACY_CP310_PROFILE_PRESERVED",
        "passed": False, "runtime_profile_id": profile_id,
        "runtime_profile_hash": selected["profile_hash"],
        "required_packages": all_pins(parse_locks(requirements_root)),
        "builder_command": (
            "python3 scripts/build_kaggle_wheelhouse.py --mode KAGGLE_PROVISIONING_BUILD "
            f"--profile {profile_id} --deterministic-provision "
            "--wheel-root /kaggle/working/wheels"
        ),
        "output": f"kaggle_uploads/01_wheelhouse/{output}",
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=sorted(MODES), default="LOCAL_VERIFY_ONLY")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--wheel-root")
    parser.add_argument("--requirements-root", default="requirements")
    parser.add_argument("--environment-lock", default="configs/runtime/kaggle_t4x2_environment.lock.json")
    parser.add_argument("--output")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--provision", action="store_true")
    parser.add_argument("--deterministic-provision", action="store_true")
    args = parser.parse_args(argv)
    selected = _selected_target(
        args.profile, requirements_root=args.requirements_root,
        environment_lock=args.environment_lock,
    )
    output = args.output or str(
        Path("kaggle_uploads/01_wheelhouse") /
        selected["profile"]["expected_wheelhouse_filename"]
    )
    if args.status or not args.wheel_root:
        result = status(
            args.requirements_root, args.wheel_root, profile_id=args.profile,
            environment_lock=args.environment_lock,
        )
    elif args.deterministic_provision:
        result = deterministic_provision(
            wheel_root=args.wheel_root, output=output,
            requirements_root=args.requirements_root, profile_id=args.profile,
            environment_lock=args.environment_lock,
        )
    else:
        result = build_wheelhouse(
            wheel_root=args.wheel_root, output=output,
            requirements_root=args.requirements_root, mode=args.mode,
            provision=args.provision, profile_id=args.profile,
            environment_lock=args.environment_lock,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("passed") or "READY" in str(result.get("status")) or "PRESERVED" in str(result.get("status")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
