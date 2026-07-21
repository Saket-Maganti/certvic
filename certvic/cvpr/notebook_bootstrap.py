"""Shared offline bootstrap used by every CertVIC Kaggle runbook."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import os
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
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
    "EXTRACT": "KAGGLE_BOOTSTRAP_09_UNSAFE_EXTRACTION",
    "DISCOVERY": "KAGGLE_BOOTSTRAP_10_AMBIGUOUS_CONTENT",
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


def verify_attached_bundle(
    path: str | Path,
    *,
    expected_type: str | None = None,
    expected_slug: str | None = None,
) -> dict[str, Any]:
    result = verify_bundle(path)
    if not result["passed"]:
        raise NotebookBootstrapError(f"{ERRORS['BUNDLE']}: {result['errors']}")
    observed_type = result["bundle_manifest"].get("bundle_type")
    if expected_type is not None and observed_type != expected_type:
        raise NotebookBootstrapError(
            f"{ERRORS['BUNDLE']}: expected type {expected_type}, observed {observed_type}"
        )
    observed_slug = result["bundle_manifest"].get("expected_kaggle_dataset_slug")
    if expected_slug is not None and observed_slug != expected_slug:
        raise NotebookBootstrapError(
            f"{ERRORS['BUNDLE']}: expected slug {expected_slug}, observed {observed_slug}"
        )
    return result


def _safe_member(info: zipfile.ZipInfo) -> str:
    name = info.filename
    normalized = name.replace("\\", "/")
    member = PurePosixPath(normalized)
    mode = (info.external_attr >> 16) & 0xFFFF
    if (
        not normalized
        or normalized != name
        or normalized.endswith("/")
        or member.is_absolute()
        or ".." in member.parts
        or "." in member.parts
        or normalized.startswith("~")
        or "\x00" in normalized
        or info.is_dir()
        or stat.S_ISLNK(mode)
        or (mode and not stat.S_ISREG(mode))
    ):
        raise NotebookBootstrapError(f"{ERRORS['EXTRACT']}: unsafe member {name!r}")
    return member.as_posix()


def _verify_extracted_files(target: Path, verification: Mapping[str, Any]) -> dict[str, str]:
    def digest(path: Path) -> str:
        value = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                value.update(block)
        return value.hexdigest()

    with zipfile.ZipFile(verification["path"]) as archive:
        hash_manifest = json.loads(archive.read("hash_manifest.json"))
    expected = dict(hash_manifest.get("files", {}))
    expected["hash_manifest.json"] = {
        "sha256": digest(target / "hash_manifest.json"),
        "size": (target / "hash_manifest.json").stat().st_size,
    }
    observed_paths = {
        path.relative_to(target).as_posix(): path
        for path in target.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    if set(observed_paths) != set(expected):
        raise NotebookBootstrapError(
            f"{ERRORS['EXTRACT']}: extracted file universe mismatch"
        )
    hashes: dict[str, str] = {}
    for name, record in sorted(expected.items()):
        path = observed_paths[name]
        observed_digest = digest(path)
        hashes[name] = observed_digest
        if path.stat().st_size != int(record["size"]) or observed_digest != record["sha256"]:
            raise NotebookBootstrapError(
                f"{ERRORS['EXTRACT']}: extracted byte mismatch {name}"
            )
    return hashes


def extract_verified_bundle(
    path: str | Path,
    destination: str | Path,
    *,
    expected_type: str | None = None,
    expected_slug: str | None = None,
) -> Path:
    """Verify and safely extract a canonical bundle to one deterministic directory."""
    verification = verify_attached_bundle(
        path, expected_type=expected_type, expected_slug=expected_slug
    )
    target = Path(destination).resolve()
    if target.exists():
        if target.is_symlink() or not target.is_dir():
            raise NotebookBootstrapError(
                f"{ERRORS['EXTRACT']}: destination is not a regular directory: {target}"
            )
        shutil.rmtree(target)
    target.mkdir(parents=True)
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [_safe_member(info) for info in infos]
            if len(names) != len(set(names)):
                raise NotebookBootstrapError(
                    f"{ERRORS['EXTRACT']}: duplicate archive members"
                )
            if archive.testzip() is not None:
                raise NotebookBootstrapError(f"{ERRORS['EXTRACT']}: corrupt archive member")
            for info, name in zip(infos, names, strict=True):
                output = (target / name).resolve()
                try:
                    output.relative_to(target)
                except ValueError as error:
                    raise NotebookBootstrapError(
                        f"{ERRORS['EXTRACT']}: traversal member {name!r}"
                    ) from error
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, output.open("xb") as sink:
                    shutil.copyfileobj(source, sink, length=1024 * 1024)
        _verify_extracted_files(target, verification)
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise
    return target


def discover_unique_file(root: str | Path, filename: str) -> Path:
    """Return exactly one regular, non-symlink file with the requested basename."""
    base = Path(root).resolve()
    matches = sorted(
        path.resolve() for path in base.rglob(filename)
        if path.is_file() and not path.is_symlink()
    ) if base.is_dir() else []
    if len(matches) != 1:
        raise NotebookBootstrapError(
            f"{ERRORS['DISCOVERY']}: filename={filename} matches={[str(path) for path in matches]}"
        )
    return matches[0]


def discover_unique_root(
    root: str | Path,
    marker: str,
    *,
    required_relative: Iterable[str] = (),
) -> Path:
    """Discover one root from a marker and required files below the marker's parent."""
    base = Path(root).resolve()
    candidates = []
    for path in base.rglob(marker) if base.is_dir() else []:
        candidate = path.parent.resolve()
        if path.is_file() and not path.is_symlink() and all(
            (candidate / relative).is_file() for relative in required_relative
        ):
            candidates.append(candidate)
    candidates = sorted(set(candidates))
    if len(candidates) != 1:
        raise NotebookBootstrapError(
            f"{ERRORS['DISCOVERY']}: marker={marker} roots={[str(path) for path in candidates]}"
        )
    return candidates[0]


def materialize_dataset(
    *,
    slug: str,
    filename: str,
    destination: str | Path,
    expected_type: str,
    input_root: str | Path = "/kaggle/input",
) -> dict[str, Any]:
    """Locate, authenticate, safely extract, and describe one attached dataset archive."""
    archive = locate_dataset(
        slug=slug, expected_filename=filename, input_root=input_root
    )
    verification = verify_attached_bundle(
        archive, expected_type=expected_type, expected_slug=slug
    )
    extracted = extract_verified_bundle(
        archive,
        destination,
        expected_type=expected_type,
        expected_slug=slug,
    )
    return {
        "schema": "certvic.kaggle.materialized_dataset.v1",
        "slug": slug,
        "filename": filename,
        "archive": str(archive.resolve()),
        "archive_sha256": verification["sha256"],
        "archive_size": verification["size"],
        "bundle_manifest": verification["bundle_manifest"],
        "root": str(extracted),
        "paper_evidence": False,
    }


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
