"""Tested Kaggle/local setup primitives for code, snapshots, inputs, and GPUs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from certvic.cvpr.model_snapshot_manifest import verify_manifest


class PreflightError(ValueError):
    pass


OFFLINE_ENVIRONMENT = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "DIFFUSERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
    "TOKENIZERS_PARALLELISM": "false",
}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover_unique(roots: list[str | Path], pattern: str) -> Path:
    matches = sorted({path.resolve() for root in roots for path in Path(root).glob(pattern)})
    if len(matches) != 1:
        raise PreflightError(f"expected one match for {pattern!r}; discovered {matches}")
    return matches[0]


def _safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        names = [member.filename for member in handle.infolist()]
        if len(names) != len(set(names)):
            raise PreflightError("code archive contains duplicate members")
        if handle.testzip() is not None:
            raise PreflightError("code archive is corrupt")
        total = 0
        for member in handle.infolist():
            pure = PurePosixPath(member.filename)
            if pure.is_absolute() or ".." in pure.parts:
                raise PreflightError(f"unsafe archive member: {member.filename}")
            total += member.file_size
            if total > 2_000_000_000:
                raise PreflightError("uncompressed archive exceeds safety limit")
        handle.extractall(destination)


def _project_root(extracted: Path) -> Path:
    candidates = sorted({path.parent for path in extracted.rglob("pyproject.toml")
                         if (path.parent / "certvic/__init__.py").is_file()})
    if len(candidates) != 1:
        raise PreflightError(f"archive must contain exactly one CertVIC project; found {candidates}")
    return candidates[0]


def prepare_code_bundle(
    bundle: str | Path,
    destination: str | Path,
    expected_sha256: str,
    *,
    replace_existing: bool = False,
) -> dict[str, Any]:
    archive = Path(bundle)
    if not archive.is_file():
        raise PreflightError(f"code bundle is missing: {archive}")
    observed = sha256_file(archive)
    if observed != expected_sha256:
        raise PreflightError("code bundle hash mismatch")
    destination = Path(destination)
    if destination.exists():
        if not replace_existing:
            raise PreflightError(f"extraction destination already exists: {destination}")
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    try:
        _safe_extract(archive, destination)
        root = _project_root(destination)
        spec = importlib.util.spec_from_file_location("_certvic_preflight", root / "certvic/__init__.py")
        if spec is None or spec.loader is None:
            raise PreflightError("unable to load certvic package from extracted bundle")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source_hash = sha256_file(root / "certvic/__init__.py")
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    for key, value in OFFLINE_ENVIRONMENT.items():
        os.environ[key] = value
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return {
        "status": "CODE_BUNDLE_READY",
        "bundle_sha256": observed,
        "project_root": str(root),
        "package_source_sha256": source_hash,
        "offline_environment": dict(OFFLINE_ENVIRONMENT),
    }


def hardware_report(*, python_executable: str | Path | None = None) -> dict[str, Any]:
    """Inspect Torch/CUDA in a child process so planning imports remain lightweight."""
    disk = shutil.disk_usage(Path.cwd())
    script = r'''
import json
try:
    import torch
except ImportError:
    print(json.dumps({"torch_status": "NOT_INSTALLED", "cuda_available": False,
                      "gpu_count": 0, "gpus": []}))
    raise SystemExit
report = {"torch_version": torch.__version__, "cuda_available": bool(torch.cuda.is_available()),
          "gpu_count": int(torch.cuda.device_count()), "gpus": []}
for index in range(report["gpu_count"]):
    properties = torch.cuda.get_device_properties(index)
    major, minor = torch.cuda.get_device_capability(index)
    report["gpus"].append({"index": index, "name": properties.name,
        "vram_bytes": properties.total_memory, "compute_capability": f"{major}.{minor}",
        "float16_supported": major >= 5,
        "bfloat16_supported": bool(torch.cuda.is_bf16_supported())})
print(json.dumps(report))
'''
    executable = str(python_executable or sys.executable)
    result = subprocess.run([executable, "-c", script], text=True, capture_output=True, check=False)
    if result.returncode or not result.stdout.strip():
        hardware: dict[str, Any] = {
            "torch_status": "INSPECTION_FAILED",
            "torch_stderr": result.stderr[-1000:],
            "cuda_available": False,
            "gpu_count": 0,
            "gpus": [],
        }
    else:
        hardware = json.loads(result.stdout)
    return {"python_executable": executable, "disk_free_bytes": disk.free, **hardware}


def run_preflight(
    *,
    code_bundle: str | Path,
    code_bundle_hash: str,
    extract_to: str | Path,
    snapshots: list[dict[str, str]],
    input_hashes: dict[str, str],
    require_gpu: bool,
) -> dict[str, Any]:
    code = prepare_code_bundle(code_bundle, extract_to, code_bundle_hash, replace_existing=True)
    input_errors = [
        path for path, expected in sorted(input_hashes.items())
        if not Path(path).is_file() or sha256_file(path) != expected
    ]
    snapshot_results = [{**snapshot, "verification": verify_manifest(
        snapshot["path"],
        snapshot.get("manifest"),
        expected_model_id=snapshot.get("model_id"),
        expected_model_commit=snapshot.get("model_commit"),
        expected_processor_commit=snapshot.get("processor_commit"),
        expected_architecture=snapshot.get("architecture"),
    )} for snapshot in snapshots]
    hardware = hardware_report()
    errors = [f"input hash mismatch: {path}" for path in input_errors]
    errors.extend(
        f"snapshot verification failed: {snapshot['path']}: "
        + "; ".join(snapshot["verification"]["errors"])
        for snapshot in snapshot_results if not snapshot["verification"]["passed"]
    )
    if require_gpu and not hardware["cuda_available"]:
        errors.append("CUDA accelerator is required but unavailable")
    return {
        "schema": "certvic.cvpr.runtime_preflight.v1",
        "passed": not errors,
        "errors": errors,
        "code": code,
        "inputs_verified": len(input_hashes) - len(input_errors),
        "snapshots": snapshot_results,
        "hardware": hardware,
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CertVIC offline runtime preflight")
    parser.add_argument("--code-bundle", required=True)
    parser.add_argument("--code-bundle-hash", required=True)
    parser.add_argument("--extract-to", required=True)
    parser.add_argument("--snapshot-contracts", help="JSON list of snapshot contracts")
    parser.add_argument("--input-hashes", help="JSON mapping of paths to hashes")
    parser.add_argument("--require-gpu", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    result = run_preflight(
        code_bundle=args.code_bundle,
        code_bundle_hash=args.code_bundle_hash,
        extract_to=args.extract_to,
        snapshots=json.loads(args.snapshot_contracts) if args.snapshot_contracts else [],
        input_hashes=json.loads(args.input_hashes) if args.input_hashes else {},
        require_gpu=args.require_gpu,
    )
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"passed": result["passed"], "errors": result["errors"]}, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
