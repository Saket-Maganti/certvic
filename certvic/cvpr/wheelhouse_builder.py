"""Build or verify a Linux/CPython-3.10 offline wheelhouse Kaggle input bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from certvic.cvpr.kaggle_bundle import build_bundle


MODES = {"LOCAL_VERIFY_ONLY", "LINUX_CONTAINER_BUILD", "KAGGLE_PROVISIONING_BUILD"}
LOCK_NAMES = (
    "kaggle_base.lock",
    "kaggle_qwen.lock",
    "kaggle_internvl.lock",
    "kaggle_llava.lock",
    "kaggle_generation.lock",
    "kaggle_analysis.lock",
)
PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s]+)$")


class WheelhouseBuilderError(ValueError):
    """Linux wheel bytes are absent, incompatible, or incomplete."""


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


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
        if name == "kaggle_base.lock":
            continue
        overlap = set(base) & set(pins)
        if overlap:
            raise WheelhouseBuilderError(f"{name} duplicates base pins: {sorted(overlap)}")
    return parsed


def all_pins(locks: dict[str, dict[str, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for pins in locks.values():
        for package, version in pins.items():
            if package in result and result[package] != version:
                raise WheelhouseBuilderError(f"cross-lock version conflict: {package}")
            result[package] = version
    return result


def _wheel_record(path: Path) -> dict[str, Any]:
    if not path.name.endswith(".whl"):
        raise WheelhouseBuilderError(f"unparseable wheel filename: {path.name}")
    parts = path.name[:-4].split("-")
    if len(parts) not in {5, 6}:
        raise WheelhouseBuilderError(f"unparseable wheel filename: {path.name}")
    if len(parts) == 5:
        distribution, version, python_tag, abi_tag, platform_tag = parts
    else:
        distribution, version, _build_tag, python_tag, abi_tag, platform_tag = parts
    lower = path.name.lower()
    if any(token in lower for token in ("macosx", "win32", "win_amd64")):
        raise WheelhouseBuilderError(f"non-Linux wheel prohibited: {path.name}")
    if platform_tag != "any" and not any(
        token in platform_tag for token in ("linux", "manylinux", "musllinux")
    ):
        raise WheelhouseBuilderError(f"wheel platform is not Linux/any: {path.name}")
    abi3_compatible = abi_tag == "abi3" and any(
        tag.startswith("cp") and tag[2:].isdigit() and int(tag[2:]) <= 310
        for tag in python_tag.split(".")
    )
    if (
        python_tag not in {"py3", "py2.py3", "cp310"}
        and "cp310" not in python_tag
        and not abi3_compatible
    ):
        raise WheelhouseBuilderError(f"wheel does not support CPython 3.10: {path.name}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "filename": path.name,
        "package": normalize(distribution),
        "version": version,
        "python_tag": python_tag,
        "platform_tag": platform_tag,
        "size": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "dependency_role": "DIRECT_OR_TRANSITIVE_OFFLINE_RUNTIME",
    }


def verify_wheel_root(
    wheel_root: str | Path,
    *,
    requirements_root: str | Path,
) -> dict[str, Any]:
    root = Path(wheel_root)
    locks = parse_locks(requirements_root)
    required = all_pins(locks)
    records = {
        path.name: _wheel_record(path)
        for path in sorted(root.glob("*.whl"))
        if path.is_file() and not path.is_symlink()
    } if root.is_dir() else {}
    coverage: dict[str, list[str]] = {name: [] for name in required}
    for filename, record in records.items():
        package = record["package"]
        if package in coverage and (
            record["version"] == required[package]
            or record["version"].startswith(required[package] + "+")
        ):
            coverage[package].append(filename)
    missing = sorted(name for name, filenames in coverage.items() if not filenames)
    return {
        "schema": "certvic.kaggle.wheelhouse_compatibility.v1",
        "status": "PASS" if records and not missing else "BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES",
        "passed": bool(records) and not missing,
        "target": {"os": "linux", "architecture": "x86_64", "python": "CPython 3.10"},
        "required_packages": required,
        "missing_direct_packages": missing,
        "files": records,
        "network_used": False,
        "paper_evidence": False,
    }


def _install_script() -> bytes:
    return b'''#!/usr/bin/env bash
set -euo pipefail
WHEELHOUSE="${1:?usage: install_offline.sh WHEELHOUSE LOCK}"
LOCK="${2:?usage: install_offline.sh WHEELHOUSE LOCK}"
export PIP_NO_INDEX=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 DIFFUSERS_OFFLINE=1
python -m pip install --no-index --find-links "$WHEELHOUSE" -r "$LOCK"
'''


def _smoke_script() -> bytes:
    return b'''import importlib
MODULES = ["torch", "torchvision", "transformers", "accelerate", "tokenizers",
           "safetensors", "sentencepiece", "PIL", "numpy", "scipy", "pandas",
           "sklearn", "cv2", "diffusers", "certvic"]
failed = {}
for name in MODULES:
    try:
        importlib.import_module(name)
    except Exception as error:
        failed[name] = f"{type(error).__name__}: {error}"
if failed:
    raise SystemExit(f"offline import smoke failed: {failed}")
print({"status": "OFFLINE_IMPORT_SMOKE_PASSED", "modules": MODULES})
'''


def _download(
    mode: str,
    destination: Path,
    *,
    requirements_root: Path,
    runner: Any = subprocess.run,
) -> None:
    if mode not in MODES - {"LOCAL_VERIFY_ONLY"}:
        raise WheelhouseBuilderError(f"mode does not provision bytes: {mode}")
    destination.mkdir(parents=True, exist_ok=True)
    pins = all_pins(parse_locks(requirements_root))
    command = [sys.executable, "-m", "pip", "download", "--only-binary=:all:", "--dest", str(destination)]
    if mode in {"LINUX_CONTAINER_BUILD", "KAGGLE_PROVISIONING_BUILD"}:
        # Kaggle's glibc accepts both the current manylinux_2_24 wheels used by
        # bitsandbytes and older manylinux2014/2_17 wheels used by the remaining
        # lock.  Supplying only manylinux2014 incorrectly made the exact lock
        # appear unsatisfiable.
        command += [
            "--platform", "manylinux_2_24_x86_64",
            "--platform", "manylinux2014_x86_64",
            "--platform", "manylinux_2_17_x86_64",
            "--platform", "linux_x86_64",
            "--python-version", "310", "--implementation", "cp",
        ]
    command += [f"{name}=={version}" for name, version in sorted(pins.items())]
    completed = runner(command, check=False)
    if int(completed.returncode) != 0:
        raise WheelhouseBuilderError("wheel provisioning failed; preserve logs and use a Kaggle/Linux builder")


def build_wheelhouse(
    *,
    wheel_root: str | Path,
    output: str | Path,
    requirements_root: str | Path,
    mode: str = "LOCAL_VERIFY_ONLY",
    provision: bool = False,
) -> dict[str, Any]:
    root = Path(wheel_root)
    locks_root = Path(requirements_root)
    if mode not in MODES:
        raise WheelhouseBuilderError(f"unknown mode: {mode}")
    if provision:
        _download(mode, root, requirements_root=locks_root)
    compatibility = verify_wheel_root(root, requirements_root=locks_root)
    if not compatibility["passed"]:
        return compatibility
    files: dict[str, Path | bytes] = {
        f"wheels/{name}": root / name for name in compatibility["files"]
    }
    for name in LOCK_NAMES:
        files[f"requirements/{name}"] = locks_root / name
    package_manifest = {
        "schema": "certvic.cvpr.wheelhouse_manifest.v2",
        "files": compatibility["files"],
        "network_used": mode != "LOCAL_VERIFY_ONLY",
        "target": compatibility["target"],
        "paper_evidence": False,
    }
    files["wheelhouse_manifest.json"] = (
        json.dumps(package_manifest, indent=2, sort_keys=True) + "\n"
    ).encode()
    files["compatibility_report.json"] = (
        json.dumps(compatibility, indent=2, sort_keys=True) + "\n"
    ).encode()
    files["install_offline.sh"] = _install_script()
    files["smoke_imports.py"] = _smoke_script()
    return build_bundle(
        output,
        files,
        bundle_type="OFFLINE_LINUX_WHEELHOUSE",
        study="all",
        stage="environment",
        provider=None,
        required_notebook="00A_certvic_code_and_environment_smoke.ipynb",
        dataset_slug="certvic/certvic-offline-wheelhouse",
        mount_path="/kaggle/input/certvic-offline-wheelhouse",
        external_dependency_status="EXTERNAL_BYTES_VERIFIED",
        evidence_class="NON_EVIDENCE_RUNTIME_DEPENDENCY",
        builder_command=(
            "python3 -m certvic.cvpr.wheelhouse_builder --mode LOCAL_VERIFY_ONLY "
            "--requirements-root requirements --wheel-root local_inputs/wheelhouse/linux_cp310 "
            "--output kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip"
        ),
        validation_command=(
            "python3 -m certvic.cvpr.kaggle_bundle verify "
            "kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip"
        ),
        readme=(
            "# CertVIC offline Kaggle wheelhouse\n\n"
            "Built only from Linux/CPython-3.10 compatible wheels. Scientific notebooks set all "
            "offline flags and install with `--no-index --find-links`. Run `smoke_imports.py` after "
            "installation and before any model load."
        ),
        extra_manifest={"compatibility_report": "compatibility_report.json"},
    )


def status(requirements_root: str | Path, wheel_root: str | Path | None = None) -> dict[str, Any]:
    locks = parse_locks(requirements_root)
    if wheel_root is None:
        return {
            "status": "BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES",
            "required_packages": all_pins(locks),
            "builder_command": (
                "python3 scripts/build_kaggle_wheelhouse.py --mode LOCAL_VERIFY_ONLY "
                "--wheel-root <LINUX_CP310_WHEELS>"
            ),
            "output": "kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip",
            "expected_size": "8-18 GB (resolve and record actual bytes)",
            "paper_evidence": False,
        }
    return verify_wheel_root(wheel_root, requirements_root=requirements_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=sorted(MODES), default="LOCAL_VERIFY_ONLY")
    parser.add_argument("--wheel-root")
    parser.add_argument("--requirements-root", default="requirements")
    parser.add_argument(
        "--output", default="kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip"
    )
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--provision", action="store_true")
    args = parser.parse_args(argv)
    if args.status or not args.wheel_root:
        result = status(args.requirements_root, args.wheel_root)
    else:
        result = build_wheelhouse(
            wheel_root=args.wheel_root,
            output=args.output,
            requirements_root=args.requirements_root,
            mode=args.mode,
            provision=args.provision,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("passed") or result.get("status") == "BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES" else 2


if __name__ == "__main__":
    raise SystemExit(main())
