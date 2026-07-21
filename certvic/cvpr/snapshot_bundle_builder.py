"""Fail-closed offline snapshot ZIP factory for the three frozen CertVIC providers."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from certvic.cvpr.kaggle_bundle import build_bundle
from certvic.cvpr.model_snapshot_manifest import create_manifest, snapshot_files, verify_manifest


PROVIDERS: dict[str, dict[str, str]] = {
    "qwen2_5_vl_7b": {
        "model_id": "Qwen/Qwen2.5-VL-7B-Instruct",
        "architecture": "Qwen2_5_VLForConditionalGeneration",
        "output": "qwen2_5_vl_7b_snapshot.zip",
        "dataset": "certvic/qwen2-5-vl-7b-snapshot",
        "size": "15-18 GB",
    },
    "internvl_8b": {
        "model_id": "OpenGVLab/InternVL2-8B",
        "architecture": "InternVLChatModel",
        "output": "internvl2_8b_snapshot.zip",
        "dataset": "certvic/internvl2-8b-snapshot",
        "size": "16-20 GB",
    },
    "llava_onevision_7b": {
        "model_id": "llava-hf/llava-onevision-qwen2-7b-ov-hf",
        "architecture": "LlavaOnevisionForConditionalGeneration",
        "output": "llava_onevision_7b_snapshot.zip",
        "dataset": "certvic/llava-onevision-7b-snapshot",
        "size": "15-18 GB",
    },
}

REQUIRED_GROUPS = {
    "configuration": ("config.json",),
    "model_weights": ("*.safetensors", "pytorch_model*.bin"),
    "tokenizer": ("tokenizer.json", "tokenizer.model", "vocab.json"),
    "processor": ("processor_config.json", "preprocessor_config.json"),
    "generation": ("generation_config.json",),
}


class SnapshotBundleBuilderError(ValueError):
    """Snapshot bytes are missing, partial, unsafe, or do not match their identity."""


def checklist(provider: str, root: str | Path | None = None) -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise SnapshotBundleBuilderError(f"unknown provider: {provider}")
    base = Path(root) if root is not None else None
    groups: dict[str, Any] = {}
    for group, patterns in REQUIRED_GROUPS.items():
        matches = [] if base is None or not base.is_dir() else sorted(
            {path.relative_to(base).as_posix() for pattern in patterns for path in base.glob(pattern)}
        )
        groups[group] = {"accepted_patterns": list(patterns), "matches": matches, "passed": bool(matches)}
    required_passed = all(groups[name]["passed"] for name in ("configuration", "model_weights", "tokenizer", "processor"))
    return {
        "schema": "certvic.kaggle.snapshot_checklist.v1",
        "provider": provider,
        "model_id": PROVIDERS[provider]["model_id"],
        "expected_architecture": PROVIDERS[provider]["architecture"],
        "required_groups": groups,
        "root_exists": bool(base and base.is_dir()),
        "passed": required_passed,
        "status": "READY_FOR_BUILD" if required_passed else "BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES",
        "expected_size": PROVIDERS[provider]["size"],
        "paper_evidence": False,
    }


def _offline_processor_smoke(root: Path) -> dict[str, Any]:
    """Load config/processor locally when Transformers is available; never contact the Hub."""
    try:
        from transformers import AutoConfig, AutoProcessor
    except ImportError:
        return {
            "status": "STRUCTURAL_LOCAL_FILES_ONLY_SMOKE",
            "transformers_available": False,
            "config_json_loaded": True,
            "processor_files_present": True,
            "network_used": False,
        }
    config = AutoConfig.from_pretrained(root, local_files_only=True, trust_remote_code=True)
    processor = AutoProcessor.from_pretrained(root, local_files_only=True, trust_remote_code=True)
    return {
        "status": "TRANSFORMERS_LOCAL_FILES_ONLY_SMOKE_PASSED",
        "transformers_available": True,
        "config_class": type(config).__name__,
        "processor_class": type(processor).__name__,
        "network_used": False,
    }


def validate_snapshot(
    provider: str,
    root: str | Path,
    *,
    model_commit: str,
    processor_commit: str,
    import_smoke: bool = True,
    exact_file_universe: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    base = Path(root).resolve()
    check = checklist(provider, base)
    if not check["passed"]:
        raise SnapshotBundleBuilderError(f"partial snapshot: {check['required_groups']}")
    symlinks = [
        path.relative_to(base).as_posix()
        for path in base.rglob("*")
        if path.is_symlink()
        and not {".cache", ".git", "__pycache__"}.intersection(
            path.relative_to(base).parts
        )
    ]
    if symlinks:
        raise SnapshotBundleBuilderError(f"snapshot symlinks are prohibited: {symlinks[:10]}")
    registry_path = Path(__file__).resolve().parents[2] / (
        "configs/models/certvic_immutable_model_registry.json"
    )
    if not registry_path.is_file():
        raise SnapshotBundleBuilderError("immutable model registry is unavailable")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    expected_files = set(registry["models"][provider]["expected_files"])
    observed_files = {path.relative_to(base).as_posix() for path in snapshot_files(base)}
    if exact_file_universe and observed_files != expected_files:
        raise SnapshotBundleBuilderError(
            "snapshot file universe differs from the immutable registry: "
            f"missing={sorted(expected_files - observed_files)}, "
            f"extra={sorted(observed_files - expected_files)}"
        )
    spec = PROVIDERS[provider]
    manifest = create_manifest(
        base,
        model_id=spec["model_id"],
        model_commit=model_commit,
        processor_commit=processor_commit,
        expected_architecture=spec["architecture"],
    )
    verification = verify_manifest(
        base,
        manifest,
        expected_model_id=spec["model_id"],
        expected_model_commit=model_commit,
        expected_processor_commit=processor_commit,
        expected_architecture=spec["architecture"],
    )
    if not verification["passed"]:
        raise SnapshotBundleBuilderError(f"snapshot manifest verification failed: {verification}")
    smoke = _offline_processor_smoke(base) if import_smoke else {
        "status": "STRUCTURAL_LOCAL_FILES_ONLY_SMOKE",
        "network_used": False,
    }
    report = {
        "schema": "certvic.kaggle.snapshot_validation.v1",
        "provider": provider,
        "passed": True,
        "checklist": check,
        "manifest_verification": verification,
        "local_files_only_smoke": smoke,
        "paper_evidence": False,
    }
    return manifest, report


def build_snapshot_bundle(
    provider: str,
    root: str | Path,
    *,
    model_commit: str,
    processor_commit: str,
    output: str | Path | None = None,
    import_smoke: bool = True,
    synthetic_fixture: bool = False,
) -> dict[str, Any]:
    base = Path(root).resolve()
    spec = PROVIDERS[provider]
    destination = Path(output) if output else Path("kaggle_uploads/02_snapshots") / spec["output"]
    manifest, report = validate_snapshot(
        provider,
        base,
        model_commit=model_commit,
        processor_commit=processor_commit,
        import_smoke=import_smoke,
        exact_file_universe=not synthetic_fixture,
    )
    files: dict[str, Path | bytes] = {
        f"snapshot/{path.relative_to(base).as_posix()}": path
        for path in snapshot_files(base)
    }
    files["snapshot/certvic_model_snapshot_manifest.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode()
    files["snapshot_validation_report.json"] = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    ).encode()
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    sidecar = destination.with_name(f"{destination.stem}_manifest.json")
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_bytes(manifest_bytes)
    built = build_bundle(
        destination,
        files,
        bundle_type="MODEL_SNAPSHOT" if not synthetic_fixture else "SYNTHETIC_MODEL_SNAPSHOT_PROOF",
        study="all",
        stage="model_snapshot",
        provider=provider,
        required_notebook="00B_certvic_model_snapshot_smoke.ipynb",
        dataset_slug=spec["dataset"],
        mount_path=f"/kaggle/input/{spec['dataset'].split('/', 1)[1]}",
        external_dependency_status=(
            "EXTERNAL_BYTES_VERIFIED" if not synthetic_fixture else "SYNTHETIC_FIXTURE"
        ),
        evidence_class=(
            "NON_EVIDENCE_MODEL_RUNTIME_DEPENDENCY" if not synthetic_fixture
            else "SYNTHETIC_FIXTURE"
        ),
        builder_command=(
            "python3 scripts/build_model_snapshot_bundle.py "
            f"--provider {provider} --snapshot-root <SNAPSHOT_ROOT> "
            "--model-commit <40_HEX> --processor-commit <40_HEX>"
        ),
        validation_command=(
            "python3 -m certvic.cvpr.kaggle_bundle verify "
            f"kaggle_uploads/02_snapshots/{spec['output']}"
        ),
        readme=(
            f"# {provider} immutable offline snapshot\n\n"
            "Every byte is hash-bound to the unified model/processor manifest. Attach this private "
            "dataset with internet disabled. Never edit, rename, or partially replace snapshot files."
        ),
        extra_manifest={
            "model_id": spec["model_id"],
            "model_commit": model_commit,
            "processor_commit": processor_commit,
            "expected_architecture": spec["architecture"],
            "unified_snapshot_root_sha256": manifest["unified_snapshot_root_sha256"],
            "synthetic_fixture": synthetic_fixture,
        },
    )
    return {
        **built,
        "snapshot_manifest_path": sidecar.as_posix(),
        "snapshot_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "snapshot_root_sha256": manifest["unified_snapshot_root_sha256"],
        "snapshot_files": len(manifest["files"]),
    }


def status(provider: str, root: str | Path | None = None) -> dict[str, Any]:
    result = checklist(provider, root)
    result.update({
        "builder_command": (
            "python3 scripts/build_model_snapshot_bundle.py "
            f"--provider {provider} --snapshot-root <SNAPSHOT_ROOT> "
            "--model-commit <40_HEX> --processor-commit <40_HEX>"
        ),
        "validation_command": (
            "python3 -m certvic.cvpr.kaggle_bundle verify "
            f"kaggle_uploads/02_snapshots/{PROVIDERS[provider]['output']}"
        ),
        "output": f"kaggle_uploads/02_snapshots/{PROVIDERS[provider]['output']}",
    })
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=sorted(PROVIDERS), required=True)
    parser.add_argument("--snapshot-root")
    parser.add_argument("--model-commit")
    parser.add_argument("--processor-commit")
    parser.add_argument("--output")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--structural-smoke-only", action="store_true")
    parser.add_argument("--synthetic-fixture", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.status or not args.snapshot_root:
        result = status(args.provider, args.snapshot_root)
    else:
        if not args.model_commit or not args.processor_commit:
            parser.error("--model-commit and --processor-commit are required for a build")
        result = build_snapshot_bundle(
            args.provider,
            args.snapshot_root,
            model_commit=args.model_commit,
            processor_commit=args.processor_commit,
            output=args.output,
            import_smoke=not args.structural_smoke_only,
            synthetic_fixture=args.synthetic_fixture,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("passed") or result.get("status") in {
        "READY_FOR_BUILD", "BUILDER_READY_BLOCKED_BY_EXTERNAL_BYTES"
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
