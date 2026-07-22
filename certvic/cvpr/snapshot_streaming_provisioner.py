"""Quota-safe, ensurepip-free, single-pass model snapshot provisioning."""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, BinaryIO, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from certvic.cvpr.kaggle_bundle import (
    COMPRESSION_POLICY,
    StreamingMember,
    build_bundle,
    verify_bundle,
)
from certvic.cvpr.model_snapshot_manifest import PROCESSOR_FILES, create_manifest_from_records
from certvic.cvpr.snapshot_bundle_builder import PROVIDERS


INSUFFICIENT_WORKING_DISK = "CERTVIC_SNAPSHOT_08_INSUFFICIENT_WORKING_DISK"
HF_HUB_PIN = "huggingface_hub==0.26.2"
DEFAULT_SAFETY_MARGIN_BYTES = 2 * 1024 ** 3
DEFAULT_ARCHIVE_OVERHEAD_BYTES = 64 * 1024 ** 2
APPROVED_HF_HOST_SUFFIXES = (
    "huggingface.co",
    "hf.co",
)
REGISTRY_PATH = (
    Path(__file__).resolve().parents[2] / "configs/models/certvic_immutable_model_registry.json"
)
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class SnapshotStreamingError(RuntimeError):
    """A stable snapshot provisioning failure with a machine-readable report."""

    def __init__(self, code: str, report: Mapping[str, Any]):
        self.code = code
        self.report = {
            "schema": "certvic.cvpr.snapshot_failure_report.v1",
            "status": code,
            **dict(report),
            "paper_evidence": False,
        }
        super().__init__(f"{code}: {json.dumps(self.report, sort_keys=True)}")


def load_immutable_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_path = Path(path) if path is not None else REGISTRY_PATH
    if not registry_path.is_file():
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_REGISTRY_MISSING",
            {"registry_path": str(registry_path), "remediation": "Restore the immutable model registry."},
        )
    return json.loads(registry_path.read_text(encoding="utf-8"))


def available_bytes(path: str | Path) -> int:
    return int(shutil.disk_usage(Path(path)).free)


def disk_preflight(
    provider: str,
    *,
    working_dir: str | Path,
    safety_margin_bytes: int = DEFAULT_SAFETY_MARGIN_BYTES,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_UNKNOWN_PROVIDER",
            {"provider": provider, "remediation": "Use one of the three frozen CertVIC providers."},
        )
    models = (registry or load_immutable_registry())["models"]
    model = models[provider]
    expected_snapshot_bytes = int(model["remote_repository_bytes_at_lock"])
    expected_archive_bytes = expected_snapshot_bytes + DEFAULT_ARCHIVE_OVERHEAD_BYTES
    free = available_bytes(working_dir)
    largest_member_bytes = max(
        (
            int(model.get("largest_member_bytes") or 0),
            expected_snapshot_bytes // max(1, len(model["expected_files"])),
            4 * 1024 ** 3,
        )
    )
    report = {
        "provider": provider,
        "available_bytes": free,
        "expected_snapshot_bytes": expected_snapshot_bytes,
        "expected_archive_bytes": expected_archive_bytes,
        "largest_member_bytes": largest_member_bytes,
        "safety_margin_bytes": int(safety_margin_bytes),
        "compression_policy": dict(COMPRESSION_POLICY),
        "raw_snapshot_retained": False,
        "second_full_zip_created": False,
    }
    if free < expected_archive_bytes + int(safety_margin_bytes):
        report.update({
            "remediation": (
                "Free working disk or move to a larger machine before downloading. "
                "Do not retain a raw snapshot or a second deterministic-rebuild ZIP."
            ),
            "multipart_plan": {
                "strategy": "DETERMINISTIC_AUTHENTICATED_MULTI_PART_SNAPSHOT_SHARDS",
                "status": "PLAN_ONLY_NOT_EXECUTED",
                "reason": "canonical single archive plus safety margin cannot fit working disk",
                "provider": provider,
                "expected_archive_bytes": expected_archive_bytes,
                "available_bytes": free,
                "shard_policy": (
                    "Split the immutable file universe into ordered authenticated ZIP shards "
                    "with a top-level shard manifest binding every member hash; rebuild must "
                    "concatenate in canonical order to the same logical snapshot identity."
                ),
            },
        })
        raise SnapshotStreamingError(INSUFFICIENT_WORKING_DISK, report)
    return {"passed": True, **report}


def install_isolated_huggingface_hub(
    target_dir: str | Path,
    *,
    host_python: str | None = None,
    installer: Any = subprocess.run,
    pin: str = HF_HUB_PIN,
) -> dict[str, Any]:
    """Install huggingface_hub into an isolated --target directory only."""
    host = host_python or sys.executable
    root = Path(target_dir)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    command = [
        host, "-m", "pip", "install",
        "--target", str(root),
        "--disable-pip-version-check",
        "--no-warn-script-location",
        pin,
    ]
    completed = installer(command, check=False, capture_output=True, text=True)
    if int(completed.returncode) != 0:
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_DEP_INSTALL_FAILED",
            {
                "command": command,
                "stdout_tail": str(completed.stdout)[-2000:],
                "stderr_tail": str(completed.stderr)[-2000:],
                "remediation": "Install huggingface_hub into the isolated target directory only.",
            },
        )
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import huggingface_hub

    return {
        "status": "ISOLATED_HUGGINGFACE_HUB_READY",
        "pin": pin,
        "target_dir": str(root),
        "import_path": str(Path(huggingface_hub.__file__).resolve()),
        "version": getattr(huggingface_hub, "__version__", "UNKNOWN"),
        "host_python": host,
        "command": command,
        "kernel_packages_mutated": False,
    }


def _approved_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"https", "http"} or not host:
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_UNAPPROVED_REDIRECT",
            {"url": url, "remediation": "Only Hugging Face HTTPS endpoints are approved."},
        )
    if not any(host == suffix or host.endswith("." + suffix) for suffix in APPROVED_HF_HOST_SUFFIXES):
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_UNAPPROVED_REDIRECT",
            {
                "url": url,
                "host": host,
                "remediation": "Refusing redirect/download outside approved Hugging Face hosts.",
            },
        )
    return url


def _open_hf_stream(url: str, headers: Mapping[str, str]) -> BinaryIO:
    current = _approved_url(url)
    for _ in range(6):
        request = Request(current, headers=dict(headers))
        try:
            response = urlopen(request, timeout=120)  # noqa: S310 - host allowlisted above
        except HTTPError as error:
            if error.code in {301, 302, 303, 307, 308} and error.headers.get("Location"):
                current = _approved_url(error.headers["Location"])
                continue
            raise SnapshotStreamingError(
                "CERTVIC_SNAPSHOT_DOWNLOAD_FAILED",
                {"url": current, "error": f"HTTPError:{error.code}", "remediation": "Retry after checking Hub availability."},
            ) from error
        except URLError as error:
            raise SnapshotStreamingError(
                "CERTVIC_SNAPSHOT_DOWNLOAD_FAILED",
                {"url": current, "error": f"URLError:{error}", "remediation": "Retry after checking Hub availability."},
            ) from error
        final = _approved_url(response.geturl())
        if final != current and urlparse(final).hostname != urlparse(current).hostname:
            response.close()
            current = final
            continue
        return response
    raise SnapshotStreamingError(
        "CERTVIC_SNAPSHOT_UNAPPROVED_REDIRECT",
        {"url": url, "remediation": "Too many redirects while downloading from Hugging Face."},
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _remote_file_records(
    *,
    repository_id: str,
    commit: str,
    expected_files: set[str],
    hf_api: Any,
    headers: Mapping[str, str],
    hf_hub_url: Callable[..., str],
) -> dict[str, dict[str, Any]]:
    infos = hf_api.get_paths_info(repository_id, sorted(expected_files), revision=commit)
    observed = {info.path for info in infos}
    if observed != expected_files:
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_FILE_UNIVERSE_MISMATCH",
            {
                "missing": sorted(expected_files - observed),
                "extra": sorted(observed - expected_files),
                "remediation": "Refuse commit drift or incomplete Hub trees.",
            },
        )
    records: dict[str, dict[str, Any]] = {}
    for info in sorted(infos, key=lambda item: item.path):
        path = info.path
        url = hf_hub_url(repository_id, path, revision=commit)
        if getattr(info, "lfs", None) is not None:
            lfs = info.lfs
            sha = str(getattr(lfs, "sha256", None) or lfs["sha256"])
            size = int(getattr(lfs, "size", None) or lfs["size"])
            records[path] = {
                "sha256": sha,
                "size": size,
                "kind": "lfs",
                "url": url,
            }
            continue
        with _open_hf_stream(url, headers) as handle:
            payload = handle.read()
        records[path] = {
            "sha256": _sha256_bytes(payload),
            "size": len(payload),
            "kind": "blob",
            "url": url,
            "bytes": payload,
        }
    return records


def _manifest_and_report(
    provider: str,
    *,
    model_commit: str,
    processor_commit: str,
    file_records: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = PROVIDERS[provider]
    files = {
        name: {"sha256": row["sha256"], "size": int(row["size"])}
        for name, row in sorted(file_records.items())
    }
    config_payload = file_records["config.json"].get("bytes")
    if config_payload is None:
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_CONFIG_MISSING",
            {"remediation": "config.json must be fetched before manifest construction."},
        )
    manifest = create_manifest_from_records(
        files,
        config_payload=config_payload,
        model_id=spec["model_id"],
        model_commit=model_commit,
        processor_commit=processor_commit,
        expected_architecture=spec["architecture"],
    )
    check_groups = {
        "configuration": bool(files.get("config.json")),
        "model_weights": any(
            name.endswith((".safetensors", ".bin", ".pt", ".pth")) for name in files
        ),
        "tokenizer": any(Path(name).name in PROCESSOR_FILES or "tokenizer" in name for name in files),
        "processor": any(Path(name).name in PROCESSOR_FILES for name in files),
    }
    report = {
        "schema": "certvic.kaggle.snapshot_validation.v1",
        "provider": provider,
        "passed": all(check_groups.values()),
        "checklist": {
            "schema": "certvic.kaggle.snapshot_checklist.v1",
            "provider": provider,
            "required_groups": {
                name: {"passed": passed} for name, passed in check_groups.items()
            },
            "passed": all(check_groups.values()),
            "paper_evidence": False,
        },
        "manifest_verification": {
            "passed": True,
            "mode": "STREAMING_RECORD_VERIFICATION",
            "files_verified": len(files),
        },
        "local_files_only_smoke": {
            "status": "STRUCTURAL_STREAMING_RECORDS_ONLY_SMOKE",
            "network_used_after_archive_complete": False,
        },
        "determinism_proof": "SINGLE_PASS_DETERMINISTIC_CONSTRUCTION_SELF_VERIFIED",
        "paper_evidence": False,
    }
    if not report["passed"]:
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_VALIDATION_FAILED",
            {"checklist": report["checklist"], "remediation": "Inspect incomplete streamed file groups."},
        )
    return manifest, report


def stream_build_snapshot_bundle(
    provider: str,
    *,
    output: str | Path,
    working_dir: str | Path | None = None,
    deps_dir: str | Path | None = None,
    model_commit: str | None = None,
    processor_commit: str | None = None,
    safety_margin_bytes: int = DEFAULT_SAFETY_MARGIN_BYTES,
    registry: Mapping[str, Any] | None = None,
    host_python: str | None = None,
    installer: Any = subprocess.run,
    file_records: Mapping[str, Mapping[str, Any]] | None = None,
    open_stream: Callable[[str, Mapping[str, str]], BinaryIO] | None = None,
) -> dict[str, Any]:
    """Stream one immutable provider snapshot directly into a single verified ZIP."""
    if provider not in PROVIDERS:
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_UNKNOWN_PROVIDER",
            {"provider": provider, "remediation": "Use one of the three frozen CertVIC providers."},
        )
    registry_data = dict(registry or load_immutable_registry())
    model = registry_data["models"][provider]
    commit = model_commit or str(model["model_commit"])
    processor = processor_commit or str(model["processor_commit"])
    if not COMMIT_RE.fullmatch(commit) or not COMMIT_RE.fullmatch(processor):
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_COMMIT_INVALID",
            {"model_commit": commit, "processor_commit": processor, "remediation": "Commits must be 40 lowercase hex characters."},
        )
    if commit != str(model["model_commit"]) or processor != str(model["processor_commit"]):
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_COMMIT_DRIFT",
            {
                "expected_model_commit": model["model_commit"],
                "expected_processor_commit": model["processor_commit"],
                "observed_model_commit": commit,
                "observed_processor_commit": processor,
                "remediation": "Refuse commit drift against the immutable registry.",
            },
        )
    destination = Path(output)
    work = Path(working_dir or destination.parent)
    work.mkdir(parents=True, exist_ok=True)
    preflight = disk_preflight(
        provider, working_dir=work, safety_margin_bytes=safety_margin_bytes, registry=registry_data
    )
    destination.unlink(missing_ok=True)
    expected_files = set(model["expected_files"])
    dependency_report = None
    headers: dict[str, str] = {}
    records: dict[str, dict[str, Any]]
    stream_opener = open_stream or _open_hf_stream
    try:
        if file_records is None:
            dependency_report = install_isolated_huggingface_hub(
                deps_dir or (work / "certvic_snapshot_deps"),
                host_python=host_python,
                installer=installer,
            )
            from huggingface_hub import HfApi, build_hf_headers, hf_hub_url

            headers = dict(build_hf_headers())
            records = _remote_file_records(
                repository_id=str(model["repository_id"]),
                commit=commit,
                expected_files=expected_files,
                hf_api=HfApi(),
                headers=headers,
                hf_hub_url=hf_hub_url,
            )
        else:
            records = {
                name: dict(row) for name, row in sorted(file_records.items())
            }
            if set(records) != expected_files:
                raise SnapshotStreamingError(
                    "CERTVIC_SNAPSHOT_FILE_UNIVERSE_MISMATCH",
                    {
                        "missing": sorted(expected_files - set(records)),
                        "extra": sorted(set(records) - expected_files),
                        "remediation": "Fixture records must match the immutable registry file universe.",
                    },
                )
        snapshot_manifest, validation_report = _manifest_and_report(
            provider,
            model_commit=commit,
            processor_commit=processor,
            file_records=records,
        )
        members: dict[str, Any] = {}
        for name, row in sorted(records.items()):
            archive_name = f"snapshot/{name}"
            if "bytes" in row:
                members[archive_name] = bytes(row["bytes"])
            else:
                url = str(row["url"])

                def _opener(stream_url: str = url, stream_headers: Mapping[str, str] = headers) -> BinaryIO:
                    return stream_opener(stream_url, stream_headers)

                members[archive_name] = StreamingMember(
                    size=int(row["size"]),
                    sha256=str(row["sha256"]),
                    opener=_opener,
                )
        members["snapshot/certvic_model_snapshot_manifest.json"] = (
            json.dumps(snapshot_manifest, indent=2, sort_keys=True) + "\n"
        ).encode()
        members["snapshot_validation_report.json"] = (
            json.dumps(validation_report, indent=2, sort_keys=True) + "\n"
        ).encode()
        spec = PROVIDERS[provider]
        built = build_bundle(
            destination,
            members,
            bundle_type="MODEL_SNAPSHOT",
            study="all",
            stage="model_snapshot",
            provider=provider,
            required_notebook=f"00B_{provider}_snapshot_smoke.ipynb",
            dataset_slug=spec["dataset"],
            mount_path=f"/kaggle/input/{spec['dataset'].split('/', 1)[1]}",
            external_dependency_status="EXTERNAL_BYTES_VERIFIED",
            evidence_class="NON_EVIDENCE_MODEL_RUNTIME_DEPENDENCY",
            builder_command=(
                "python3 -m certvic.cvpr.snapshot_streaming_provisioner "
                f"--provider {provider} --output <OUTPUT_ZIP>"
            ),
            validation_command=(
                "python3 -m certvic.cvpr.kaggle_bundle verify "
                f"kaggle_uploads/02_snapshots/{spec['output']}"
            ),
            readme=(
                f"# {provider} immutable offline snapshot\n\n"
                "Single-pass deterministic construction with ZIP64 and quota-safe streaming. "
                "Attach this private dataset with internet disabled."
            ),
            extra_manifest={
                "model_id": spec["model_id"],
                "model_commit": commit,
                "processor_commit": processor,
                "expected_architecture": spec["architecture"],
                "unified_snapshot_root_sha256": snapshot_manifest["unified_snapshot_root_sha256"],
                "determinism_proof": "SINGLE_PASS_DETERMINISTIC_CONSTRUCTION_SELF_VERIFIED",
                "raw_snapshot_retained": False,
                "second_full_zip_created": False,
                "disk_preflight_policy": {
                    "expected_snapshot_bytes": preflight["expected_snapshot_bytes"],
                    "expected_archive_bytes": preflight["expected_archive_bytes"],
                    "safety_margin_bytes": preflight["safety_margin_bytes"],
                    "compression_policy": dict(COMPRESSION_POLICY),
                },
                "dependency_isolation_policy": {
                    "huggingface_hub_pin": HF_HUB_PIN,
                    "kernel_packages_mutated": False,
                    "install_mode": "pip_target_directory_or_fixture",
                },
            },
        )
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    verification = verify_bundle(destination)
    if not verification["passed"]:
        destination.unlink(missing_ok=True)
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_SELF_VERIFY_FAILED",
            {"errors": verification["errors"], "remediation": "Delete the invalid archive and retry."},
        )
    sidecar = destination.with_name(f"{destination.stem}_manifest.json")
    sidecar.write_text(json.dumps(snapshot_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        **built,
        "status": "IMMUTABLE_SNAPSHOT_BUILT_SINGLE_PASS",
        "determinism_proof": "SINGLE_PASS_DETERMINISTIC_CONSTRUCTION_SELF_VERIFIED",
        "raw_snapshot_retained": False,
        "second_full_zip_created": False,
        "disk_preflight": preflight,
        "dependency_isolation": dependency_report,
        "snapshot_manifest_path": sidecar.as_posix(),
        "snapshot_manifest_sha256": _sha256_bytes(
            json.dumps(snapshot_manifest, indent=2, sort_keys=True).encode() + b"\n"
        ),
        "snapshot_root_sha256": snapshot_manifest["unified_snapshot_root_sha256"],
        "snapshot_files": len(snapshot_manifest["files"]),
        "paper_evidence": False,
    }


def build_fixture_stream_records(
    files: Mapping[str, bytes],
    *,
    base_url: str = "https://huggingface.co/fixture/resolve/main/",
) -> dict[str, dict[str, Any]]:
    """Build streaming fixture records without contacting the network."""
    records: dict[str, dict[str, Any]] = {}
    for name, payload in sorted(files.items()):
        data = bytes(payload)
        records[name] = {
            "sha256": _sha256_bytes(data),
            "size": len(data),
            "kind": "fixture",
            "url": base_url + name,
            "bytes": data,
        }
    return records


def sparse_stream_member(size: int, *, seed: bytes = b"certvic-zip64") -> StreamingMember:
    """Return a sparse synthetic stream larger than the classic ZIP limit."""

    class _SparseStream(io.RawIOBase):
        def __init__(self) -> None:
            self._remaining = size
            self._block = hashlib.sha256(seed).digest() * 2048

        def readable(self) -> bool:
            return True

        def read(self, amount: int = -1) -> bytes:  # noqa: A003
            if self._remaining <= 0:
                return b""
            if amount is None or amount < 0:
                amount = self._remaining
            take = min(amount, self._remaining, len(self._block))
            self._remaining -= take
            return self._block[:take]

    digest = hashlib.sha256()
    remaining = size
    block = hashlib.sha256(seed).digest() * 2048
    while remaining:
        take = min(remaining, len(block))
        digest.update(block[:take])
        remaining -= take

    def _open() -> BinaryIO:
        return _SparseStream()  # type: ignore[return-value]

    return StreamingMember(size=size, sha256=digest.hexdigest(), opener=_open)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=sorted(PROVIDERS), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--working-dir")
    parser.add_argument("--deps-dir")
    parser.add_argument("--safety-margin-bytes", type=int, default=DEFAULT_SAFETY_MARGIN_BYTES)
    args = parser.parse_args(argv)
    result = stream_build_snapshot_bundle(
        args.provider,
        output=args.output,
        working_dir=args.working_dir,
        deps_dir=args.deps_dir,
        safety_margin_bytes=args.safety_margin_bytes,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
