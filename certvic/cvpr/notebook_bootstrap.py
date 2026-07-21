"""Shared offline bootstrap used by every CertVIC Kaggle runbook."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from certvic.cvpr.kaggle_bundle import verify_bundle
from certvic.cvpr.t4x2 import AcceleratorPlan, detect_topology


ERRORS = {
    "DATASET": "KAGGLE_BOOTSTRAP_01_DATASET_NOT_FOUND",
    "AMBIGUOUS": "KAGGLE_BOOTSTRAP_02_AMBIGUOUS_DATASET",
    "BUNDLE": "KAGGLE_BOOTSTRAP_03_BUNDLE_INVALID",
    "WHEELHOUSE": "KAGGLE_BOOTSTRAP_04_WHEELHOUSE_INVALID",
    "INSTALL": "KAGGLE_BOOTSTRAP_05_OFFLINE_INSTALL_FAILED",
    "IMPORT": "KAGGLE_BOOTSTRAP_06_IMPORT_SMOKE_FAILED",
    "GPU": "KAGGLE_BOOTSTRAP_07_GPU_CONTRACT_FAILED",
    "IDENTITY": "KAGGLE_BOOTSTRAP_08_RUN_IDENTITY_INCOMPLETE",
}

OFFLINE_ENVIRONMENT = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "DIFFUSERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "PIP_NO_INDEX": "1",
    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
}


class NotebookBootstrapError(RuntimeError):
    """A stable, actionable Kaggle bootstrap failure."""


def configure_offline_environment() -> dict[str, str]:
    os.environ.update(OFFLINE_ENVIRONMENT)
    return dict(OFFLINE_ENVIRONMENT)


def _slug_directory(slug: str) -> str:
    if "/" not in slug:
        raise NotebookBootstrapError(f"{ERRORS['DATASET']}: invalid slug {slug!r}")
    return slug.split("/", 1)[1].lower().replace("_", "-")


def locate_dataset(
    *,
    slug: str,
    expected_filename: str | None = None,
    input_root: str | Path = "/kaggle/input",
) -> Path:
    """Locate one attached private dataset without asking the user to rename anything."""
    root = Path(input_root)
    dataset_name = _slug_directory(slug)
    candidate_roots = [
        child for child in root.iterdir() if child.is_dir()
        and child.name.lower().replace("_", "-") == dataset_name
    ] if root.is_dir() else []
    if expected_filename:
        exact = [path for base in candidate_roots for path in base.rglob(expected_filename)]
        if not exact and root.is_dir():
            exact = list(root.glob(f"*/{expected_filename}"))
        candidates = exact
    else:
        candidates = candidate_roots
    candidates = sorted({path.resolve() for path in candidates})
    if not candidates:
        raise NotebookBootstrapError(
            f"{ERRORS['DATASET']}: slug={slug} filename={expected_filename}"
        )
    if len(candidates) != 1:
        raise NotebookBootstrapError(
            f"{ERRORS['AMBIGUOUS']}: slug={slug} candidates={[str(path) for path in candidates]}"
        )
    return candidates[0]


def verify_attached_bundle(path: str | Path, *, expected_type: str | None = None) -> dict[str, Any]:
    result = verify_bundle(path)
    if not result["passed"]:
        raise NotebookBootstrapError(f"{ERRORS['BUNDLE']}: {result['errors']}")
    observed_type = result["bundle_manifest"].get("bundle_type")
    if expected_type is not None and observed_type != expected_type:
        raise NotebookBootstrapError(
            f"{ERRORS['BUNDLE']}: expected type {expected_type}, observed {observed_type}"
        )
    return result


def extract_verified_bundle(path: str | Path, destination: str | Path) -> Path:
    verify_attached_bundle(path)
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        archive.extractall(target)
    return target


def offline_install_command(
    wheelhouse: str | Path,
    lock: str | Path,
    *,
    require_hashes: bool = False,
) -> list[str]:
    command = [
        sys.executable, "-m", "pip", "install", "--no-index", "--find-links",
        str(Path(wheelhouse)), "-r", str(Path(lock)),
    ]
    if require_hashes:
        command.insert(-2, "--require-hashes")
    return command


def install_offline(
    wheelhouse: str | Path,
    lock: str | Path,
    *,
    require_hashes: bool = False,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    configure_offline_environment()
    wheels = list(Path(wheelhouse).glob("*.whl"))
    if not wheels or not Path(lock).is_file():
        raise NotebookBootstrapError(f"{ERRORS['WHEELHOUSE']}: missing wheels or lock")
    command = offline_install_command(wheelhouse, lock, require_hashes=require_hashes)
    completed = runner(command, check=False, capture_output=True, text=True, env=dict(os.environ))
    if int(completed.returncode) != 0:
        raise NotebookBootstrapError(
            f"{ERRORS['INSTALL']}: {str(completed.stderr)[-2000:]}"
        )
    return {"command": command, "exit_code": 0, "network_used": False}


def import_smoke(modules: Iterable[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    failures: dict[str, str] = {}
    for name in modules:
        try:
            module = importlib.import_module(name)
            package_name = name.split(".", 1)[0]
            try:
                version = importlib.metadata.version(package_name)
            except importlib.metadata.PackageNotFoundError:
                version = str(getattr(module, "__version__", "PROJECT_OR_STDLIB"))
            versions[name] = version
        except Exception as error:  # import-time native failures must be reported too
            failures[name] = f"{type(error).__name__}: {error}"
    if failures:
        raise NotebookBootstrapError(f"{ERRORS['IMPORT']}: {failures}")
    return versions


def validate_run_identity(identity: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "notebook", "study", "stage", "provider", "run_tag", "code_bundle_sha256",
        "prompt_sha256", "run_contract_sha256",
    }
    missing = sorted(required - set(identity))
    placeholders = sorted(
        key for key, value in identity.items()
        if isinstance(value, str) and (not value or value == "REQUIRED_USER_FILL")
    )
    for key in ("code_bundle_sha256", "prompt_sha256", "run_contract_sha256"):
        value = str(identity.get(key, ""))
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            placeholders.append(key)
    if missing or placeholders:
        raise NotebookBootstrapError(
            f"{ERRORS['IDENTITY']}: missing={missing} invalid={sorted(set(placeholders))}"
        )
    payload = dict(identity)
    payload["identity_sha256"] = hashlib.sha256(
        (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    return payload


def bootstrap(
    identity: Mapping[str, Any],
    *,
    required_datasets: Mapping[str, str],
    input_root: str | Path = "/kaggle/input",
    require_gpu: bool,
    device_names: list[str] | None = None,
) -> dict[str, Any]:
    """Perform the non-installing common preflight; installation remains an explicit notebook cell."""
    configure_offline_environment()
    validated_identity = validate_run_identity(identity)
    attached = {
        slug: str(locate_dataset(slug=slug, expected_filename=filename, input_root=input_root))
        for slug, filename in sorted(required_datasets.items())
    }
    topology: AcceleratorPlan | None = None
    if require_gpu:
        try:
            topology = detect_topology(device_names=device_names)
        except Exception as error:
            raise NotebookBootstrapError(f"{ERRORS['GPU']}: {error}") from error
    return {
        "schema": "certvic.kaggle.notebook_bootstrap.v1",
        "identity": validated_identity,
        "attached_datasets": attached,
        "topology": topology.as_dict() if topology else None,
        "offline_environment": dict(OFFLINE_ENVIRONMENT),
        "paper_evidence": False,
    }
