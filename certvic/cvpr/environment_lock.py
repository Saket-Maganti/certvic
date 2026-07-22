"""Profile-aware offline environment and isolated-venv verification utilities."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from packaging.utils import canonicalize_name

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.runtime_profiles import (
    isolated_python,
    runtime_probe,
    select_runtime_profile,
    validate_wheelhouse,
)


WHEEL_RE = re.compile(r"^[A-Za-z0-9_.+-]+\.whl$")
REQUIRED_IMPORTS = (
    "torch", "torchvision", "transformers", "accelerate", "tokenizers",
    "safetensors", "PIL", "numpy", "scipy", "pandas", "diffusers",
    "sentencepiece", "sklearn", "cv2", "qwen_vl_utils", "timm",
    "matplotlib", "nbclient", "nbformat", "av",
)


def load_environment_lock(path: str | Path) -> dict[str, Any]:
    lock = json.loads(Path(path).read_text(encoding="utf-8"))
    # Historical synthetic artifacts retain their v1 bytes for evidence
    # separation.  They may be hashed/inspected but cannot enter profile
    # selection or the isolated scientific runtime path.
    if isinstance(lock, dict) and lock.get("schema") in {
        "certvic.cvpr.kaggle_environment_lock.v1", "certvic.cvpr.environment_lock.v1",
    }:
        legacy_required = {"schema", "python", "packages", "cuda_contract", "offline_install"}
        if legacy_required - set(lock) or lock["offline_install"].get("allow_index") is not False:
            raise ValueError("legacy environment lock is incomplete")
        return lock
    required = {
        "schema", "python", "runtime_profiles", "packages", "cuda_contract",
        "offline_install", "torch_cuda_distribution",
    }
    if not isinstance(lock, dict) or required - set(lock):
        raise ValueError("environment lock is not a complete v2 mapping")
    if lock["schema"] != "certvic.cvpr.kaggle_environment_lock.v2":
        raise ValueError("environment lock must use the runtime-profile v2 schema")
    if (
        lock["offline_install"].get("allow_index") is not False
        or lock["offline_install"].get("isolated_venv_required") is not True
        or lock["offline_install"].get("system_site_packages") is not False
    ):
        raise ValueError("environment lock must require an isolated no-index venv")
    packages = lock["packages"]
    if not isinstance(packages, dict) or not packages:
        raise ValueError("environment lock packages must be nonempty")
    for name, version in packages.items():
        if not re.fullmatch(r"[a-z0-9_.-]+", str(name)) or not re.fullmatch(
            r"[0-9]+(?:\.[0-9]+)*(?:[a-z0-9.+-]*)", str(version)
        ):
            raise ValueError(f"invalid exact package pin: {name}=={version}")
    profiles = lock["runtime_profiles"]
    if set(profiles) != {"kaggle_cp310_legacy", "kaggle_cp312_2026_07"}:
        raise ValueError("environment lock must preserve exactly the CP310 and CP312 profiles")
    profile_fields = {
        "implementation", "python_version", "python_abi", "system", "architecture",
        "libc", "glibc_minimum", "glibc_observed", "isolated_venv",
        "expected_wheelhouse_filename", "status",
    }
    for profile_id, profile in profiles.items():
        if not isinstance(profile, dict) or profile_fields - set(profile):
            raise ValueError(f"runtime profile is incomplete: {profile_id}")
        if not str(profile["python_abi"]).startswith("cp"):
            raise ValueError(f"runtime profile ABI is invalid: {profile_id}")
    return lock


def environment_lock_hash(path: str | Path) -> str:
    return sha256_bytes(canonical_json_bytes(load_environment_lock(path)))


def select_locked_runtime(
    path: str | Path, *, probe: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    return select_runtime_profile(load_environment_lock(path), probe or runtime_probe())


def _verify_script(packages: Mapping[str, str], *, require_cuda: bool) -> str:
    return (
        "import importlib.metadata,json,platform,sys\n"
        f"expected={json.dumps(dict(packages), sort_keys=True)}\n"
        "observed={}; mismatches=[]\n"
        "for name,version in sorted(expected.items()):\n"
        "  try: value=importlib.metadata.version(name)\n"
        "  except importlib.metadata.PackageNotFoundError: value=None\n"
        "  observed[name]=value\n"
        "  if value!=version and not (name in {'torch','torchvision'} and value and value.startswith(version+'+')): mismatches.append({'component':name,'expected':version,'observed':value or 'NOT_INSTALLED'})\n"
        "cuda={'required':" + repr(require_cuda) + ",'available':False,'devices':[],'torch_version':observed.get('torch')}\n"
        "try:\n"
        " import torch\n"
        " cuda['available']=bool(torch.cuda.is_available())\n"
        " cuda['devices']=[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]\n"
        " cuda['torch_cuda_version']=torch.version.cuda\n"
        "except Exception as error: cuda['error']=f'{type(error).__name__}: {error}'\n"
        "if cuda['required'] and not cuda['available']: mismatches.append({'component':'cuda','expected':'AVAILABLE','observed':'UNAVAILABLE'})\n"
        "print(json.dumps({'passed':not mismatches,'mismatches':mismatches,'python':platform.python_version(),'packages':observed,'cuda':cuda,'executable':sys.executable}))\n"
    )


def verify_current_environment(
    path: str | Path,
    *,
    require_cuda: bool,
    python_executable: str | Path | None = None,
    selected_profile: Mapping[str, Any] | None = None,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    lock = load_environment_lock(path)
    executable = str(python_executable or sys.executable)
    profile = selected_profile or select_locked_runtime(path, probe=runtime_probe(executable=executable))
    completed = runner(
        [executable, "-c", _verify_script(lock["packages"], require_cuda=require_cuda)],
        check=False, capture_output=True, text=True,
        env={**os.environ, **offline_environment_flags()},
    )
    if int(completed.returncode) != 0:
        value = {
            "passed": False,
            "mismatches": [{"component": "interpreter", "expected": "RUNNABLE", "observed": "FAILED"}],
            "python": None, "packages": {}, "cuda": {"required": require_cuda, "available": False},
            "executable": executable, "stderr": str(completed.stderr)[-2000:],
        }
    else:
        value = json.loads(completed.stdout.strip().splitlines()[-1])
    return {
        "schema": "certvic.cvpr.environment_verification.v2",
        **value,
        "environment_lock_hash": environment_lock_hash(path),
        "runtime_profile_id": profile["profile_id"],
        "runtime_profile_hash": profile["profile_hash"],
        "runtime_probe": profile["observed_runtime"],
        "verification_scope": "SELECTED_ISOLATED_INTERPRETER",
        "paper_evidence": False,
    }


def verify_wheelhouse(wheelhouse: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    """Byte-verify a rich wheelhouse manifest (legacy-compatible public API)."""
    root = Path(wheelhouse)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("wheelhouse manifest files must be a nonempty mapping")
    observed = {
        path.name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size": path.stat().st_size}
        for path in root.iterdir() if path.is_file() and WHEEL_RE.fullmatch(path.name)
    }
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
        "schema": "certvic.cvpr.wheelhouse_verification.v2",
        "passed": not (missing or extra or mismatched or metadata_errors),
        "missing": missing, "extra": extra, "mismatched": sorted(set(mismatched)),
        "metadata_errors": metadata_errors, "files_verified": len(observed),
        "manifest_sha256": hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
        "runtime_profile_id": manifest.get("runtime_profile_id"),
        "runtime_profile_hash": manifest.get("runtime_profile_hash"),
        "network_used": False, "paper_evidence": False,
    }


def offline_environment_flags() -> dict[str, str]:
    return {
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "DIFFUSERS_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
        "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    }


def _manifest_requirements(manifest_path: str | Path, lock: Mapping[str, Any]) -> dict[str, str]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    source = manifest.get("required_packages", lock["packages"])
    return {canonicalize_name(name): str(version) for name, version in source.items()}


def prepare_offline_environment(
    lock_path: str | Path,
    *,
    wheelhouse: str | Path | None,
    wheelhouse_manifest: str | Path | None,
    allow_preinstalled: bool,
    require_exact: bool,
    require_cuda: bool,
    selected_profile: Mapping[str, Any] | None = None,
    venv_root: str | Path | None = None,
    import_modules: tuple[str, ...] = REQUIRED_IMPORTS,
    content_identities: Mapping[str, str] | None = None,
    installer: Any = subprocess.run,
) -> dict[str, Any]:
    """Create, install, and verify one isolated offline runtime.

    ``allow_preinstalled`` remains accepted for source compatibility but a v2
    lock never accepts notebook-kernel packages as the execution environment.
    """
    del allow_preinstalled
    if not require_exact:
        raise ValueError("non-exact environments are prohibited for CVPR runtime paths")
    if wheelhouse is None or wheelhouse_manifest is None:
        raise ValueError("an authenticated wheelhouse and manifest are required")
    os.environ.update(offline_environment_flags())
    lock = load_environment_lock(lock_path)
    selected = selected_profile or select_locked_runtime(lock_path)
    requirements = _manifest_requirements(wheelhouse_manifest, lock)
    compatibility = validate_wheelhouse(
        wheelhouse, selected_profile=selected, required_packages=requirements,
        manifest_path=wheelhouse_manifest, content_identities=content_identities,
    )
    root = Path(venv_root or selected["profile"]["isolated_venv"])
    python = isolated_python(root)
    create_command = [str(selected["observed_runtime"]["executable"]), "-m", "venv", str(root)]
    if not python.is_file():
        completed = installer(create_command, check=False, capture_output=True, text=True)
        if int(completed.returncode) != 0:
            raise ValueError(f"isolated venv creation failed: {str(completed.stderr)[-2000:]}")
    pyvenv = root / "pyvenv.cfg"
    if not pyvenv.is_file() or "include-system-site-packages = false" not in pyvenv.read_text(
        encoding="utf-8"
    ).lower():
        raise ValueError("isolated venv must set include-system-site-packages = false")
    install_command = [
        str(python), "-m", "pip", "install", "--no-index", "--find-links",
        str(Path(wheelhouse).resolve()), "--only-binary=:all:", "--disable-pip-version-check",
        *[f"{name}=={version}" for name, version in sorted(requirements.items())],
    ]
    completed = installer(
        install_command, check=False, capture_output=True, text=True,
        env={**os.environ, **offline_environment_flags()},
    )
    if int(completed.returncode) != 0:
        raise ValueError(f"offline isolated-venv installation failed: {str(completed.stderr)[-4000:]}")
    after = verify_current_environment(
        lock_path, require_cuda=require_cuda, python_executable=python,
        selected_profile=selected, runner=installer,
    )
    if not after["passed"]:
        raise ValueError(f"isolated runtime exact verification failed: {after['mismatches']}")
    import_script = (
        "import importlib,json; modules=" + repr(list(import_modules)) + "; failed={}; versions={}\n"
        "for name in modules:\n"
        "  try:\n"
        "    module=importlib.import_module(name); versions[name]=str(getattr(module,'__version__','IMPORTED'))\n"
        "  except Exception as error: failed[name]=f'{type(error).__name__}: {error}'\n"
        "print(json.dumps({'failed':failed,'versions':versions}))\n"
        "raise SystemExit(1 if failed else 0)"
    )
    smoke = installer(
        [str(python), "-c", import_script], check=False, capture_output=True, text=True,
        env={**os.environ, **offline_environment_flags()},
    )
    if int(smoke.returncode) != 0:
        raise ValueError(f"isolated runtime import smoke failed: {str(smoke.stdout)[-4000:]}")
    result = {
        **after,
        "status": "ISOLATED_OFFLINE_VENV_INSTALLED_AND_VERIFIED",
        "python_executable": str(python), "venv_root": str(root),
        "venv_create_command": create_command, "install_command": install_command,
        "wheelhouse_manifest_sha256": compatibility.get("manifest_sha256") or hashlib.sha256(
            Path(wheelhouse_manifest).read_bytes()
        ).hexdigest(),
        "wheelhouse_validation": compatibility,
        "import_smoke": json.loads(smoke.stdout.strip().splitlines()[-1]),
        "offline_flags": offline_environment_flags(), "system_site_packages": False,
        "network_used": False, "restart_or_reexec_checked": True,
    }
    result["environment_hash"] = sha256_bytes(canonical_json_bytes({
        "environment_lock_hash": result["environment_lock_hash"],
        "runtime_profile_id": result["runtime_profile_id"],
        "runtime_profile_hash": result["runtime_profile_hash"],
        "wheelhouse_manifest_sha256": result["wheelhouse_manifest_sha256"],
        "python_executable": result["python_executable"],
    }))
    return result
