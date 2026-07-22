"""Fail-closed Kaggle runtime-profile and wheel compatibility selection.

This module deliberately runs before any package installation.  It binds the
observed interpreter ABI to one lock profile, authenticates the matching
wheelhouse content identity, and rejects every wheel that pip could not load in
that interpreter.  It never treats a source distribution as an offline runtime
artifact.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

from packaging.tags import Tag, compatible_tags, cpython_tags, sys_tags
from packaging.utils import InvalidWheelFilename, canonicalize_name, parse_wheel_filename

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes


PYTHON_PROFILE_NOT_SUPPORTED = "CERTVIC_RUNTIME_01_PYTHON_PROFILE_NOT_SUPPORTED"
WHEELHOUSE_ABI_MISMATCH = "CERTVIC_RUNTIME_02_WHEELHOUSE_ABI_MISMATCH"
REQUIRED_WHEEL_MISSING = "CERTVIC_RUNTIME_03_REQUIRED_WHEEL_MISSING"
MULTIPLE_PROFILES_AMBIGUOUS = "CERTVIC_RUNTIME_04_MULTIPLE_RUNTIME_PROFILES_AMBIGUOUS"
RUNTIME_SCHEMA = "certvic.cvpr.runtime_probe.v2"
REPORT_SCHEMA = "certvic.cvpr.runtime_failure_report.v2"


class RuntimeProfileError(RuntimeError):
    """A stable runtime-profile failure with a machine-readable report."""

    def __init__(self, code: str, report: Mapping[str, Any]):
        self.code = code
        self.report = {"schema": REPORT_SCHEMA, "status": code, **dict(report)}
        super().__init__(f"{code}: {json.dumps(self.report, sort_keys=True)}")


def _version_tuple(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.split(".") if part != "")
    except ValueError:
        return ()


def runtime_probe(
    *,
    executable: str | Path | None = None,
    implementation: str | None = None,
    python_version: str | None = None,
    architecture: str | None = None,
    system: str | None = None,
    libc_name: str | None = None,
    libc_version: str | None = None,
    supported_tags: Iterable[str | Tag] | None = None,
) -> dict[str, Any]:
    """Return the live interpreter identity and ordered supported wheel tags.

    Explicit fields are test/provisioning inputs; omitted fields are probed from
    the current process.  A different executable is probed in a subprocess so
    notebook-kernel and worker-interpreter drift remains visible.
    """
    selected = str(executable or sys.executable)
    if (
        executable is not None
        and implementation is None
        and python_version is None
        and architecture is None
        and system is None
        and libc_name is None
        and libc_version is None
        and supported_tags is None
        and Path(selected).resolve() != Path(sys.executable).resolve()
    ):
        script = (
            "import json,platform,sys; from packaging.tags import sys_tags; "
            "print(json.dumps({'executable':sys.executable,'implementation':platform.python_implementation(),"
            "'python_version':platform.python_version(),'architecture':platform.machine(),"
            "'system':platform.system(),'libc':platform.libc_ver(),"
            "'supported_tags':[str(x) for x in sys_tags()]}))"
        )
        completed = subprocess.run(
            [selected, "-c", script], check=False, capture_output=True, text=True
        )
        if completed.returncode != 0:
            raise RuntimeProfileError(PYTHON_PROFILE_NOT_SUPPORTED, {
                "observed_runtime": {"executable": selected},
                "supported_tags": [], "selected_profile": None,
                "selected_wheelhouse": None, "missing_packages": [],
                "incompatible_wheels": [], "content_identities": {},
                "remediation": "Use an interpreter that can import packaging and emit sys_tags().",
                "probe_stderr": completed.stderr[-2000:],
            })
        value = json.loads(completed.stdout)
        observed_libc = value.get("libc", ["", ""])
        return runtime_probe(
            executable=value["executable"], implementation=value["implementation"],
            python_version=value["python_version"], architecture=value["architecture"],
            system=value["system"], libc_name=observed_libc[0], libc_version=observed_libc[1],
            supported_tags=value["supported_tags"],
        )
    observed_libc_name, observed_libc_version = platform.libc_ver()
    tags = [str(value) for value in (supported_tags if supported_tags is not None else sys_tags())]
    return {
        "schema": RUNTIME_SCHEMA,
        "executable": selected,
        "implementation": implementation or platform.python_implementation(),
        "python_version": python_version or platform.python_version(),
        "python_major_minor": ".".join((python_version or platform.python_version()).split(".")[:2]),
        "architecture": (architecture or platform.machine()).lower(),
        "system": system or platform.system(),
        "libc": {
            "name": libc_name if libc_name is not None else observed_libc_name,
            "version": libc_version if libc_version is not None else observed_libc_version,
        },
        "supported_tags": tags,
        "supported_tags_sha256": sha256_bytes(canonical_json_bytes(tags)),
        "paper_evidence": False,
    }


def profile_hash(profile_id: str, profile: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes({"profile_id": profile_id, "profile": profile}))


def _profile_matches(profile: Mapping[str, Any], probe: Mapping[str, Any]) -> bool:
    libc = probe.get("libc", {})
    return (
        probe.get("implementation") == profile.get("implementation")
        and probe.get("python_major_minor") == profile.get("python_version")
        and str(probe.get("architecture", "")).lower() == str(profile.get("architecture", "")).lower()
        and str(probe.get("system", "")).lower() == str(profile.get("system", "")).lower()
        and str(libc.get("name", "")).lower() == str(profile.get("libc", "")).lower()
        and _version_tuple(str(libc.get("version", ""))) >= _version_tuple(
            str(profile.get("glibc_minimum", ""))
        )
    )


def select_runtime_profile(lock: Mapping[str, Any], probe: Mapping[str, Any]) -> dict[str, Any]:
    profiles = lock.get("runtime_profiles")
    if not isinstance(profiles, Mapping) or not profiles:
        raise ValueError("environment lock has no runtime_profiles mapping")
    matches = [name for name, value in profiles.items() if _profile_matches(value, probe)]
    common = {
        "observed_runtime": dict(probe),
        "supported_tags": list(probe.get("supported_tags", [])),
        "selected_wheelhouse": None,
        "missing_packages": [], "incompatible_wheels": [], "content_identities": {},
    }
    if not matches:
        raise RuntimeProfileError(PYTHON_PROFILE_NOT_SUPPORTED, {
            **common, "selected_profile": None,
            "available_profiles": sorted(profiles),
            "remediation": "Use a supported CPython/Linux/x86_64 runtime or add a reviewed lock profile.",
        })
    if len(matches) != 1:
        raise RuntimeProfileError(MULTIPLE_PROFILES_AMBIGUOUS, {
            **common, "selected_profile": None, "matching_profiles": sorted(matches),
            "remediation": "Make runtime profile predicates mutually exclusive.",
        })
    name = matches[0]
    profile = dict(profiles[name])
    return {
        "schema": "certvic.cvpr.selected_runtime_profile.v2",
        "profile_id": name,
        "profile_hash": profile_hash(name, profile),
        "profile": profile,
        "observed_runtime": dict(probe),
        "paper_evidence": False,
    }


def target_tags(profile: Mapping[str, Any]) -> list[str]:
    """Generate the accepted tag universe for a locked Linux/glibc profile."""
    major, minor = (int(value) for value in str(profile["python_version"]).split("."))
    abi = str(profile["python_abi"])
    architecture = str(profile["architecture"])
    observed = _version_tuple(str(profile.get("glibc_observed", profile["glibc_minimum"])))
    minimum = _version_tuple(str(profile["glibc_minimum"]))
    upper_minor = observed[1] if len(observed) > 1 else 17
    lower_minor = minimum[1] if len(minimum) > 1 else 17
    platforms = [f"manylinux_2_{value}_{architecture}" for value in range(upper_minor, lower_minor - 1, -1)]
    if lower_minor <= 17:
        platforms.append(f"manylinux2014_{architecture}")
    platforms.append(f"linux_{architecture}")
    tags = list(cpython_tags((major, minor), abis=[abi], platforms=platforms))
    tags += list(compatible_tags((major, minor), interpreter=abi, platforms=platforms))
    return list(dict.fromkeys(str(value) for value in tags))


def wheel_record(path: str | Path, *, supported_tags: Iterable[str | Tag]) -> dict[str, Any]:
    source = Path(path)
    try:
        distribution, version, build, wheel_tags = parse_wheel_filename(source.name)
    except InvalidWheelFilename as error:
        raise RuntimeProfileError(WHEELHOUSE_ABI_MISMATCH, {
            "observed_runtime": {}, "supported_tags": [str(tag) for tag in supported_tags],
            "selected_profile": None, "selected_wheelhouse": str(source.parent),
            "missing_packages": [], "incompatible_wheels": [source.name],
            "content_identities": {}, "remediation": "Provision only valid binary .whl files.",
        }) from error
    supported = {str(tag) for tag in supported_tags}
    declared = sorted(str(tag) for tag in wheel_tags)
    compatible = sorted(supported & set(declared))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    return {
        "filename": source.name,
        "package": canonicalize_name(distribution),
        "version": str(version),
        "build_tag": list(build) if build else [],
        "python_tag": ".".join(sorted({tag.interpreter for tag in wheel_tags})),
        "abi_tag": ".".join(sorted({tag.abi for tag in wheel_tags})),
        "platform_tag": ".".join(sorted({tag.platform for tag in wheel_tags})),
        "wheel_tags": declared,
        "compatible_tags": compatible,
        "compatible": bool(compatible),
        "size": source.stat().st_size,
        "sha256": digest,
        "dependency_role": "DIRECT_OR_TRANSITIVE_OFFLINE_RUNTIME",
    }


def validate_wheelhouse(
    wheel_root: str | Path,
    *,
    selected_profile: Mapping[str, Any],
    required_packages: Mapping[str, str],
    manifest_path: str | Path | None = None,
    content_identities: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    root = Path(wheel_root)
    observed = selected_profile["observed_runtime"]
    supported = list(observed.get("supported_tags", [])) or target_tags(selected_profile["profile"])
    wheels = sorted(path for path in root.iterdir() if path.is_file() and path.suffix == ".whl") if root.is_dir() else []
    sdists = sorted(
        path.name for path in root.iterdir()
        if path.is_file() and path.suffix != ".whl" and path.name not in {"wheelhouse_manifest.json"}
    ) if root.is_dir() else []
    records = {path.name: wheel_record(path, supported_tags=supported) for path in wheels}
    incompatible = sorted(name for name, record in records.items() if not record["compatible"])
    coverage: dict[str, list[str]] = {canonicalize_name(name): [] for name in required_packages}
    for filename, record in records.items():
        package = record["package"]
        expected = required_packages.get(package)
        if expected is not None and (
            record["version"] == expected or record["version"].startswith(expected + "+")
        ) and record["compatible"]:
            coverage[package].append(filename)
    missing = sorted(name for name, names in coverage.items() if not names)
    manifest_errors: list[str] = []
    manifest: dict[str, Any] = {}
    if manifest_path is not None:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        if manifest.get("runtime_profile_id") != selected_profile["profile_id"]:
            manifest_errors.append("runtime profile ID mismatch")
        if manifest.get("runtime_profile_hash") != selected_profile["profile_hash"]:
            manifest_errors.append("runtime profile hash mismatch")
        declared = manifest.get("files", {})
        if set(declared) != set(records):
            manifest_errors.append("wheel file universe mismatch")
        for name in set(declared) & set(records):
            if declared[name].get("sha256") != records[name]["sha256"]:
                manifest_errors.append(f"wheel hash mismatch: {name}")
    base_report = {
        "observed_runtime": dict(observed), "supported_tags": supported,
        "selected_profile": selected_profile["profile_id"],
        "selected_profile_hash": selected_profile["profile_hash"],
        "selected_wheelhouse": str(root), "missing_packages": missing,
        "incompatible_wheels": incompatible, "source_distributions": sdists,
        "manifest_errors": manifest_errors,
        "content_identities": dict(content_identities or {}),
    }
    if incompatible or sdists or manifest_errors:
        raise RuntimeProfileError(WHEELHOUSE_ABI_MISMATCH, {
            **base_report,
            "remediation": "Attach the wheelhouse built for the selected profile; remove sdists and foreign ABI/platform wheels.",
        })
    if missing:
        raise RuntimeProfileError(REQUIRED_WHEEL_MISSING, {
            **base_report,
            "remediation": "Re-run the profile provisioning notebook with Internet on and upload its complete ZIP.",
        })
    return {
        "schema": "certvic.cvpr.wheelhouse_runtime_validation.v2",
        "status": "COMPATIBLE_WHEELHOUSE_SELECTED",
        "passed": True, **base_report, "files": records,
        "wheel_count": len(records), "network_used": False, "paper_evidence": False,
    }


def discover_runtime_wheelhouse(
    selected_profile: Mapping[str, Any],
    *,
    roots: Iterable[str | Path] | str | Path | None,
    materialization_root: str | Path,
    expected_content_identity: str | None = None,
) -> dict[str, Any]:
    """Discover exactly one authenticated wheelhouse compatible with the profile."""
    from certvic.cvpr.content_discovery import ContentDiscoveryError, discover_authenticated_input

    expected: str | Mapping[str, Any] = (
        expected_content_identity
        if expected_content_identity
        else {"runtime_profile_id": selected_profile["profile_id"]}
    )
    try:
        return discover_authenticated_input(
            "OFFLINE_LINUX_WHEELHOUSE", roots=roots, expected_identity=expected,
            materialization_root=materialization_root,
        )
    except ContentDiscoveryError as error:
        text = str(error)
        code = (
            MULTIPLE_PROFILES_AMBIGUOUS
            if "CERTVIC_DISCOVERY_02_AMBIGUOUS_DISTINCT_CONTENT" in text
            else WHEELHOUSE_ABI_MISMATCH
        )
        raise RuntimeProfileError(code, {
            "observed_runtime": selected_profile["observed_runtime"],
            "supported_tags": selected_profile["observed_runtime"].get("supported_tags", []),
            "selected_profile": selected_profile["profile_id"],
            "selected_wheelhouse": None, "missing_packages": [],
            "incompatible_wheels": [], "content_identities": {},
            "remediation": (
                "Set the expected wheelhouse content identity when more than one compatible identity is attached."
                if code == MULTIPLE_PROFILES_AMBIGUOUS
                else "Attach the authenticated wheelhouse built for this runtime profile."
            ),
            "discovery_failure": text,
        }) from error


def isolated_python(venv_root: str | Path) -> Path:
    root = Path(venv_root)
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
