"""Build deterministic profile-specific Linux offline wheelhouse bundles."""

from __future__ import annotations

import argparse
import email.parser
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from certvic.cvpr.environment_lock import environment_lock_hash, load_environment_lock
from certvic.cvpr.kaggle_bundle import build_bundle
from certvic.cvpr.runtime_profiles import (
    PYTHON_PROFILE_NOT_SUPPORTED,
    WHEELHOUSE_ABI_MISMATCH,
    RuntimeProfileError,
    profile_hash,
    runtime_probe,
    select_runtime_profile,
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
RESOLVER_FAILED = "CERTVIC_RUNTIME_05_WHEEL_RESOLVER_FAILED"
DEPENDENCY_CLOSURE_INCOMPLETE = "CERTVIC_RUNTIME_06_DEPENDENCY_CLOSURE_INCOMPLETE"
CUDA_FAMILY_MISMATCH = "CERTVIC_RUNTIME_07_PYTORCH_CUDA_FAMILY_MISMATCH"
FAILURE_REPORT_SCHEMA = "certvic.cvpr.cp312_wheelhouse_failure_report.v1"
PYPI_INDEX = "https://pypi.org/simple"


class WheelhouseBuilderError(ValueError):
    """Linux wheel bytes are absent, incompatible, or incomplete."""

    def __init__(
        self,
        message: str,
        *,
        status: str = RESOLVER_FAILED,
        report: Mapping[str, Any] | None = None,
    ) -> None:
        self.status = status
        self.report = dict(report or {})
        super().__init__(message)


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
    profile_id: str,
    *,
    requirements_root: str | Path,
    environment_lock: str | Path | None = None,
    live_runtime: bool = False,
) -> dict[str, Any]:
    path = _lock_path(requirements_root, environment_lock)
    lock = load_environment_lock(path)
    if profile_id not in lock["runtime_profiles"]:
        raise WheelhouseBuilderError(f"unknown runtime profile: {profile_id}")
    if live_runtime:
        probe = runtime_probe()
        try:
            selected = select_runtime_profile(lock, probe)
        except RuntimeProfileError as error:
            raise WheelhouseBuilderError(
                f"{error.code}: live interpreter does not match the provisioning profile",
                status=error.code,
                report=error.report,
            ) from error
        if selected["profile_id"] != profile_id:
            raise WheelhouseBuilderError(
                f"{PYTHON_PROFILE_NOT_SUPPORTED}: selected {selected['profile_id']}, "
                f"required {profile_id}",
                status=PYTHON_PROFILE_NOT_SUPPORTED,
                report={
                    "observed_runtime": probe,
                    "supported_tags": probe.get("supported_tags", []),
                    "selected_profile": selected["profile_id"],
                    "required_profile": profile_id,
                    "remediation": "Run this provisioner in Kaggle CPython 3.12 Linux x86_64.",
                    "paper_evidence": False,
                },
            )
        return selected
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


def _wheel_requirements(path: Path) -> list[str]:
    """Read ``Requires-Dist`` entries from one authenticated wheel container."""
    try:
        with zipfile.ZipFile(path) as archive:
            metadata_names = sorted(
                name for name in archive.namelist()
                if name.endswith(".dist-info/METADATA") and name.count("/") == 1
            )
            if len(metadata_names) != 1:
                raise WheelhouseBuilderError(
                    f"wheel has {len(metadata_names)} METADATA records: {path.name}",
                    status=DEPENDENCY_CLOSURE_INCOMPLETE,
                )
            message = email.parser.BytesParser().parsebytes(archive.read(metadata_names[0]))
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        raise WheelhouseBuilderError(
            f"wheel metadata is unreadable: {path.name}: {error}",
            status=DEPENDENCY_CLOSURE_INCOMPLETE,
        ) from error
    return [str(value) for value in message.get_all("Requires-Dist", [])]


def _target_marker_environment(selected: Mapping[str, Any]) -> dict[str, str]:
    observed = selected["observed_runtime"]
    profile = selected["profile"]
    environment = default_environment()
    environment.update({
        "implementation_name": "cpython",
        "platform_machine": str(profile["architecture"]),
        "platform_python_implementation": str(profile["implementation"]),
        "platform_system": str(profile["system"]),
        "python_version": str(profile["python_version"]),
        "python_full_version": str(observed.get("python_version", profile["python_version"])),
        "sys_platform": "linux",
        "extra": "",
    })
    return environment


def prune_redundant_incompatible_wheels(
    wheel_root: str | Path,
    *,
    supported_tags: list[str],
    remove: bool = True,
) -> dict[str, Any]:
    """Remove only foreign wheels with an exact compatible package/version mirror.

    A foreign wheel without that replacement is reported and retained.  The
    caller must still run the full dependency-closure validator after pruning.
    """
    root = Path(wheel_root)
    paths = sorted(root.glob("*.whl")) if root.is_dir() else []
    records = {path.name: wheel_record(path, supported_tags=supported_tags) for path in paths}
    compatible_keys = {
        (record["package"], record["version"])
        for record in records.values() if record["compatible"]
    }
    redundant = [
        record for record in records.values()
        if not record["compatible"]
        and (record["package"], record["version"]) in compatible_keys
    ]
    nonredundant = [
        record for record in records.values()
        if not record["compatible"]
        and (record["package"], record["version"]) not in compatible_keys
    ]
    if remove:
        for record in redundant:
            (root / record["filename"]).unlink()
    return {
        "schema": "certvic.cvpr.foreign_wheel_pruning.v1",
        "passed": not nonredundant,
        "removed_redundant_incompatible_wheels": (
            sorted(redundant, key=lambda row: row["filename"])
            if remove else []
        ),
        "retained_nonredundant_incompatible_wheels": sorted(
            nonredundant, key=lambda row: row["filename"]
        ),
        "paper_evidence": False,
    }


def _dependency_closure(
    root: Path,
    records: dict[str, dict[str, Any]],
    *,
    selected: Mapping[str, Any],
) -> dict[str, Any]:
    environment = _target_marker_environment(selected)
    by_package: dict[str, list[dict[str, Any]]] = {}
    invalid_requirements: list[dict[str, str]] = []
    for filename, record in records.items():
        requirements = _wheel_requirements(root / filename)
        record["requires_dist"] = requirements
        by_package.setdefault(str(record["package"]), []).append(record)
    duplicate_conflicts = [
        {"package": package, "versions": sorted({row["version"] for row in rows})}
        for package, rows in sorted(by_package.items())
        if len({row["version"] for row in rows}) > 1
    ]
    missing: list[dict[str, str]] = []
    for filename, record in sorted(records.items()):
        for raw in record["requires_dist"]:
            try:
                requirement = Requirement(raw)
            except InvalidRequirement:
                invalid_requirements.append({"wheel": filename, "requirement": raw})
                continue
            if requirement.marker is not None and not requirement.marker.evaluate(environment):
                continue
            package = canonicalize_name(requirement.name)
            candidates = by_package.get(package, [])
            compatible = []
            for candidate in candidates:
                try:
                    version = Version(str(candidate["version"]))
                except InvalidVersion:
                    continue
                if not requirement.specifier or requirement.specifier.contains(
                    version, prereleases=True
                ):
                    compatible.append(candidate)
            if not compatible:
                missing.append({
                    "required_by": filename,
                    "package": package,
                    "specifier": str(requirement.specifier) or "ANY",
                    "requirement": raw,
                })
    unique_missing = [
        dict(items)
        for items in sorted({tuple(sorted(row.items())) for row in missing})
    ]
    return {
        "schema": "certvic.cvpr.wheelhouse_dependency_closure.v1",
        "passed": not (unique_missing or duplicate_conflicts or invalid_requirements),
        "missing_dependencies": unique_missing,
        "duplicate_conflicts": duplicate_conflicts,
        "invalid_requirements": invalid_requirements,
        "resolved_packages": {
            package: sorted({row["version"] for row in rows})
            for package, rows in sorted(by_package.items())
        },
        "paper_evidence": False,
    }


def _cuda_contract(
    records: Mapping[str, Mapping[str, Any]], lock: Mapping[str, Any]
) -> dict[str, Any]:
    contract = lock["torch_cuda_distribution"]
    family = str(contract["cuda_family"])
    expected = {
        "torch": f"{contract['torch']}+{family}",
        "torchvision": f"{contract['torchvision']}+{family}",
    }
    observed: dict[str, list[str]] = {name: [] for name in expected}
    for record in records.values():
        package = str(record["package"])
        if package in observed:
            observed[package].append(str(record["version"]))
    errors = [
        f"{package}: expected only {version}, observed {sorted(set(observed[package]))}"
        for package, version in expected.items()
        if set(observed[package]) != {version}
    ]
    return {
        "schema": "certvic.cvpr.pytorch_cuda_wheel_contract.v1",
        "passed": not errors,
        "cuda_family": family,
        "expected": expected,
        "observed": {name: sorted(set(values)) for name, values in observed.items()},
        "errors": errors,
        "paper_evidence": False,
    }


def provisioning_failure_report(
    status: str,
    *,
    selected: Mapping[str, Any],
    required_packages: Mapping[str, str],
    provisioning: Mapping[str, Any] | None = None,
    downloaded_wheels: list[Mapping[str, Any]] | None = None,
    incompatible_wheels: list[Mapping[str, Any] | str] | None = None,
    source_distributions: list[str] | None = None,
    missing_packages: list[Any] | None = None,
    duplicate_conflicts: list[Any] | None = None,
    remediation: str,
) -> dict[str, Any]:
    resolver = dict(provisioning or {})
    return {
        "schema": FAILURE_REPORT_SCHEMA,
        "status": status,
        "observed_runtime": dict(selected.get("observed_runtime", {})),
        "supported_tags": list(selected.get("observed_runtime", {}).get("supported_tags", [])),
        "resolver_command": resolver.get("commands", resolver.get("command", [])),
        "resolver_stdout_tail": resolver.get("stdout_tail", ""),
        "resolver_stderr_tail": resolver.get("stderr_tail", ""),
        "required_packages": dict(required_packages),
        "downloaded_wheels": list(downloaded_wheels or []),
        "incompatible_wheels": list(incompatible_wheels or []),
        "source_distributions": list(source_distributions or []),
        "missing_packages": list(missing_packages or []),
        "duplicate_conflicts": list(duplicate_conflicts or []),
        "selected_indexes": resolver.get("selected_indexes", []),
        "remediation": remediation,
        "paper_evidence": False,
    }


def persist_failure_report(path: str | Path, report: Mapping[str, Any]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(report), indent=2, sort_keys=True) + "\n")
    os.replace(temporary, destination)
    return destination


def verify_wheel_root(
    wheel_root: str | Path,
    *,
    requirements_root: str | Path,
    profile_id: str = DEFAULT_PROFILE,
    environment_lock: str | Path | None = None,
    selected_target: Mapping[str, Any] | None = None,
    source_provenance: Mapping[str, Mapping[str, Any]] | None = None,
    removed_redundant: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(wheel_root)
    locks = parse_locks(requirements_root)
    required = all_pins(locks)
    selected = dict(selected_target or _selected_target(
        profile_id, requirements_root=requirements_root, environment_lock=environment_lock
    ))
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
    records = checked["files"]
    provenance = dict(source_provenance or {})
    for filename, record in records.items():
        source = dict(provenance.get(filename, {}))
        record["source_url"] = source.get("source_url")
        record["source_index"] = source.get("source_index", "PREEXISTING_AUTHENTICATED_BYTES")
    closure = _dependency_closure(root, records, selected=selected)
    cuda = _cuda_contract(
        records,
        load_environment_lock(_lock_path(requirements_root, environment_lock)),
    )
    if not closure["passed"]:
        return {
            "schema": "certvic.kaggle.wheelhouse_compatibility.v3",
            "status": DEPENDENCY_CLOSURE_INCOMPLETE,
            "passed": False,
            "runtime_profile_id": profile_id,
            "runtime_profile_hash": selected["profile_hash"],
            "target": selected["profile"],
            "observed_runtime": selected["observed_runtime"],
            "required_packages": required,
            "missing_direct_packages": [],
            "missing_packages": closure["missing_dependencies"],
            "duplicate_conflicts": closure["duplicate_conflicts"],
            "invalid_requirements": closure["invalid_requirements"],
            "files": records,
            "dependency_closure": closure,
            "pytorch_cuda_contract": cuda,
            "removed_redundant_incompatible_wheels": list(removed_redundant or []),
            "network_used": False,
            "paper_evidence": False,
        }
    if not cuda["passed"]:
        return {
            "schema": "certvic.kaggle.wheelhouse_compatibility.v3",
            "status": CUDA_FAMILY_MISMATCH,
            "passed": False,
            "runtime_profile_id": profile_id,
            "runtime_profile_hash": selected["profile_hash"],
            "target": selected["profile"],
            "observed_runtime": selected["observed_runtime"],
            "required_packages": required,
            "missing_direct_packages": [],
            "missing_packages": [],
            "duplicate_conflicts": [],
            "files": records,
            "dependency_closure": closure,
            "pytorch_cuda_contract": cuda,
            "removed_redundant_incompatible_wheels": list(removed_redundant or []),
            "network_used": False,
            "paper_evidence": False,
        }
    return {
        "schema": "certvic.kaggle.wheelhouse_compatibility.v2",
        "status": "PASS", "passed": True,
        "runtime_profile_id": profile_id, "runtime_profile_hash": selected["profile_hash"],
        "target": selected["profile"], "observed_runtime": selected["observed_runtime"],
        "required_packages": required,
        "missing_direct_packages": [], "files": records,
        "supported_tags": checked["supported_tags"],
        "wheel_count": checked["wheel_count"], "network_used": False,
        "dependency_closure": closure,
        "pytorch_cuda_contract": cuda,
        "removed_redundant_incompatible_wheels": list(removed_redundant or []),
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


def _resolver_provenance(output: str) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for raw in re.findall(r"https?://[^\s'\"<>]+", output):
        url = raw.rstrip("),.;")
        filename = unquote(Path(urlparse(url).path).name)
        if filename.endswith(".metadata"):
            filename = filename.removesuffix(".metadata")
        if not filename.endswith(".whl"):
            continue
        host = urlparse(url).netloc.lower()
        records[filename] = {
            "source_url": url,
            "source_index": (
                "PYTORCH_CU121" if "download.pytorch.org" in host else "PYPI"
            ),
        }
    return records


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
    pins = all_pins(parse_locks(requirements_root))
    selected = _selected_target(
        profile_id,
        requirements_root=requirements_root,
        environment_lock=environment_lock,
        live_runtime=mode == "KAGGLE_PROVISIONING_BUILD",
    )
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        report = provisioning_failure_report(
            RESOLVER_FAILED,
            selected=selected,
            required_packages=pins,
            remediation=(
                "Start a fresh Kaggle session or clear only the failed resolver directory; "
                "resolution requires a clean destination."
            ),
        )
        raise WheelhouseBuilderError(
            f"{RESOLVER_FAILED}: wheel resolution requires a clean destination directory",
            status=RESOLVER_FAILED,
            report=report,
        )
    profile = selected["profile"]
    lock = load_environment_lock(_lock_path(requirements_root, environment_lock))
    torch = lock["torch_cuda_distribution"]
    family = str(torch["cuda_family"])
    torch_requirements = [
        f"torch=={torch['torch']}+{family}",
        f"torchvision=={torch['torchvision']}+{family}",
    ]
    cross_target: list[str] = []
    if mode == "LINUX_CONTAINER_BUILD":
        platforms = list(dict.fromkeys(
            tag.split("-", 2)[2] for tag in target_tags(profile)
            if tag.split("-", 2)[2] != "any"
        ))
        cross_target = [
            "--python-version", profile["python_version"].replace(".", ""),
            "--implementation", "cp", "--abi", profile["python_abi"],
        ]
        for value in platforms:
            cross_target += ["--platform", value]
    common = [
        sys.executable, "-m", "pip", "download", "--only-binary=:all:",
        "--disable-pip-version-check", "--no-cache-dir", "--verbose",
        "--dest", str(destination), *cross_target,
    ]
    with tempfile.TemporaryDirectory(prefix="certvic_clean_resolver_") as temporary:
        constraints = Path(temporary) / "torch_cuda_constraints.txt"
        resolver_constraints = [
            *torch_requirements,
            *[
                f"{name}=={version}"
                for name, version in sorted(pins.items())
                if name not in {"torch", "torchvision"}
            ],
        ]
        constraints.write_text(
            "\n".join(resolver_constraints) + "\n", encoding="utf-8"
        )
        commands = [
            [
                *common,
                "--index-url", str(torch["index_url"]),
                "--extra-index-url", PYPI_INDEX,
                "--constraint", str(constraints),
                *torch_requirements,
            ],
            [
                *common,
                "--index-url", PYPI_INDEX,
                "--find-links", str(destination),
                "--constraint", str(constraints),
                *[
                    f"{name}=={version}"
                    for name, version in sorted(pins.items())
                    if name not in {"torch", "torchvision"}
                ],
            ],
        ]
        completed_steps = []
        for command in commands:
            completed = runner(command, check=False, capture_output=True, text=True)
            completed_steps.append(completed)
            if int(completed.returncode) != 0:
                break
        display_commands = [
            [str(value).replace(temporary, "<CLEAN_RESOLVER_ENV>") for value in command]
            for command in commands
        ]
    stdout = "\n".join(str(step.stdout) for step in completed_steps)
    stderr = "\n".join(str(step.stderr) for step in completed_steps)
    selected_indexes = [str(torch["index_url"]), PYPI_INDEX]
    provenance = _resolver_provenance(stdout + "\n" + stderr)
    for path in sorted(destination.glob("*.whl")):
        if path.name not in provenance:
            record = wheel_record(
                path, supported_tags=selected["observed_runtime"]["supported_tags"]
            )
            provenance[path.name] = {
                "source_url": "RESOLVER_LOG_URL_NOT_EMITTED",
                "source_index": (
                    "PYTORCH_CU121" if record["package"] in {"torch", "torchvision"}
                    else "OFFICIAL_PYPI_OR_PYTORCH_TRANSITIVE"
                ),
            }
    report = {
        "commands": display_commands,
        "stdout_tail": stdout[-8000:],
        "stderr_tail": stderr[-8000:],
        "selected_indexes": selected_indexes,
        "official_sources": selected_indexes,
        "source_provenance": provenance,
        "selected_runtime": selected,
        "resolution_strategy": (
            "LIVE_PACKAGING_SYS_TAGS" if mode == "KAGGLE_PROVISIONING_BUILD"
            else "EXPLICIT_REVIEWED_CONTAINER_CROSS_TARGET"
        ),
    }
    if len(completed_steps) != len(commands) or any(
        int(step.returncode) != 0 for step in completed_steps
    ):
        downloaded = []
        for path in sorted(destination.glob("*.whl")):
            try:
                downloaded.append(wheel_record(
                    path, supported_tags=selected["observed_runtime"]["supported_tags"]
                ))
            except RuntimeProfileError:
                continue
        failure = provisioning_failure_report(
            RESOLVER_FAILED,
            selected=selected,
            required_packages=pins,
            provisioning=report,
            downloaded_wheels=downloaded,
            source_distributions=sorted(
                path.name for path in destination.iterdir() if path.suffix != ".whl"
            ),
            remediation=(
                "Retry in a fresh Kaggle CPython 3.12 session. If the named package remains "
                "unavailable, update the reviewed lock instead of accepting an sdist or CPU Torch."
            ),
        )
        raise WheelhouseBuilderError(
            f"{RESOLVER_FAILED}: official-index binary resolution failed",
            status=RESOLVER_FAILED,
            report=failure,
        )
    return {
        **report,
        "required_packages": pins,
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
    selected_target: Mapping[str, Any] | None = None,
    removed_redundant: list[Mapping[str, Any]] | None = None,
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
        selected_target = provisioning.get("selected_runtime")
    compatibility = verify_wheel_root(
        root, requirements_root=locks_root, profile_id=profile_id,
        environment_lock=environment_lock,
        selected_target=selected_target,
        source_provenance=(provisioning or {}).get("source_provenance", {}),
        removed_redundant=removed_redundant,
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
        "dependency_closure": compatibility["dependency_closure"],
        "pytorch_cuda_contract": compatibility["pytorch_cuda_contract"],
        "removed_redundant_incompatible_wheels": compatibility[
            "removed_redundant_incompatible_wheels"
        ],
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
        validation_command=(
            "python3 -m certvic.cvpr.kaggle_bundle verify "
            f"/kaggle/working/{expected_filename}"
        ),
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
    failure_report_path: str | Path = (
        "/kaggle/working/certvic_cp312_wheelhouse_failure_report.json"
    ),
) -> dict[str, Any]:
    """Resolve with live tags, prune only redundant foreign wheels, and build twice."""
    root = Path(wheel_root)
    destination = Path(output)
    failure_path = Path(failure_report_path)
    required = all_pins(parse_locks(requirements_root))
    if root.exists() and any(root.iterdir()):
        raise WheelhouseBuilderError(
            "deterministic provisioning requires an empty wheel root; start a fresh builder session"
        )
    try:
        provisioning = _download(
            "KAGGLE_PROVISIONING_BUILD", root, requirements_root=Path(requirements_root),
            profile_id=profile_id, environment_lock=environment_lock,
        )
    except WheelhouseBuilderError as error:
        fallback = _selected_target(
            profile_id,
            requirements_root=requirements_root,
            environment_lock=environment_lock,
        )
        if error.report.get("observed_runtime"):
            fallback["observed_runtime"] = dict(error.report["observed_runtime"])
        if error.report.get("supported_tags"):
            fallback["observed_runtime"]["supported_tags"] = list(
                error.report["supported_tags"]
            )
        report = dict(error.report)
        if report.get("schema") != FAILURE_REPORT_SCHEMA:
            report = provisioning_failure_report(
                error.status,
                selected=fallback,
                required_packages=required,
                provisioning=error.report,
                remediation=str(error.report.get(
                    "remediation",
                    "Retry in a fresh Kaggle CPython 3.12 Linux x86_64 session.",
                )),
            )
        persist_failure_report(failure_path, report)
        destination.unlink(missing_ok=True)
        raise WheelhouseBuilderError(
            f"{report['status']}: resolver failed; report={failure_path}",
            status=str(report["status"]),
            report=report,
        ) from error
    selected = provisioning["selected_runtime"]
    pruning = prune_redundant_incompatible_wheels(
        root,
        supported_tags=list(selected["observed_runtime"]["supported_tags"]),
        remove=True,
    )
    if not pruning["passed"]:
        records = [
            wheel_record(path, supported_tags=selected["observed_runtime"]["supported_tags"])
            for path in sorted(root.glob("*.whl"))
        ]
        report = provisioning_failure_report(
            WHEELHOUSE_ABI_MISMATCH,
            selected=selected,
            required_packages=required,
            provisioning=provisioning,
            downloaded_wheels=records,
            incompatible_wheels=pruning["retained_nonredundant_incompatible_wheels"],
            remediation=(
                "The named foreign wheel is the only candidate for its package/version. "
                "Correct the reviewed pin or official-index availability; do not delete it silently."
            ),
        )
        persist_failure_report(failure_path, report)
        destination.unlink(missing_ok=True)
        return {**report, "passed": False, "failure_report_path": str(failure_path)}
    first = build_wheelhouse(
        wheel_root=root, output=destination, requirements_root=requirements_root,
        mode="KAGGLE_PROVISIONING_BUILD", profile_id=profile_id,
        environment_lock=environment_lock, provisioning_report=provisioning,
        selected_target=selected,
        removed_redundant=pruning["removed_redundant_incompatible_wheels"],
    )
    if not first.get("passed", False):
        report = provisioning_failure_report(
            str(first.get("status", DEPENDENCY_CLOSURE_INCOMPLETE)),
            selected=selected,
            required_packages=required,
            provisioning=provisioning,
            downloaded_wheels=list(first.get("files", {}).values()),
            incompatible_wheels=list(first.get("incompatible_wheels", [])),
            source_distributions=list(first.get("source_distributions", [])),
            missing_packages=list(first.get("missing_packages", [])),
            duplicate_conflicts=list(first.get("duplicate_conflicts", [])),
            remediation=(
                "Resolve every named direct/transitive dependency from the official indexes "
                "and preserve torch/torchvision cu121; never substitute an sdist or CPU wheel."
            ),
        )
        persist_failure_report(failure_path, report)
        destination.unlink(missing_ok=True)
        return {**report, "passed": False, "failure_report_path": str(failure_path)}
    with tempfile.TemporaryDirectory(prefix="certvic_wheelhouse_rebuild_") as temporary:
        second_path = Path(temporary) / destination.name
        second = build_wheelhouse(
            wheel_root=root, output=second_path, requirements_root=requirements_root,
            mode="KAGGLE_PROVISIONING_BUILD", profile_id=profile_id,
            environment_lock=environment_lock, provisioning_report=provisioning,
            selected_target=selected,
            removed_redundant=pruning["removed_redundant_incompatible_wheels"],
        )
        identical = destination.read_bytes() == second_path.read_bytes()
    if not identical:
        report = provisioning_failure_report(
            "CERTVIC_RUNTIME_08_NONDETERMINISTIC_WHEELHOUSE",
            selected=selected,
            required_packages=required,
            provisioning=provisioning,
            downloaded_wheels=list(first.get("files", {}).values()),
            remediation="Compare the two bundle manifests and remove nondeterministic metadata.",
        )
        persist_failure_report(failure_path, report)
        destination.unlink(missing_ok=True)
        raise WheelhouseBuilderError(
            f"{report['status']}: deterministic rebuild differed; report={failure_path}",
            status=str(report["status"]),
            report=report,
        )
    failure_path.unlink(missing_ok=True)
    return {
        **first,
        "resolver_result": provisioning,
        "foreign_wheel_pruning": pruning,
        "failure_report_path": None,
        "deterministic_rebuild": {
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
