"""C5 regression coverage for ensurepip-free venv, ZIP64, and quota-safe streaming."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from packaging.tags import sys_tags

from certvic.cvpr.environment_lock import (
    HOST_PIP_CANNOT_TARGET_VENV,
    EnvironmentLockError,
    prepare_offline_environment,
)
from certvic.cvpr.kaggle_bundle import (
    build_bundle,
    member_compression,
    verify_bundle,
)
from certvic.cvpr.kagglefiles_pack import (
    PROVIDERS,
    cp312_provisioning_notebook,
    snapshot_provisioning_notebook,
)
from certvic.cvpr.runtime_profiles import profile_hash, runtime_probe, wheel_record
from certvic.cvpr.snapshot_streaming_provisioner import (
    INSUFFICIENT_WORKING_DISK,
    SnapshotStreamingError,
    build_fixture_stream_records,
    disk_preflight,
    sparse_stream_member,
    stream_build_snapshot_bundle,
)


def _minimal_wheel(wheel_root: Path) -> Path:
    name = "fixture-1.0-py3-none-any.whl"
    path = wheel_root / name
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "fixture/__init__.py",
            "__version__ = '1.0'\n",
        )
        archive.writestr(
            "fixture-1.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: fixture\nVersion: 1.0\n",
        )
        archive.writestr(
            "fixture-1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nGenerator: certvic\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr("fixture-1.0.dist-info/RECORD", "")
    return path


def _selected_and_lock(tmp_path: Path) -> tuple[dict, Path, Path, Path]:
    wheel_root = tmp_path / "wheels"
    wheel_root.mkdir()
    wheel = _minimal_wheel(wheel_root)
    host_probe = runtime_probe()
    profile = {
        "implementation": host_probe["implementation"],
        "python_version": host_probe["python_major_minor"],
        "python_abi": next(iter(sys_tags())).interpreter,
        "system": host_probe["system"], "architecture": host_probe["architecture"],
        "libc": host_probe["libc"]["name"], "glibc_minimum": host_probe["libc"]["version"],
        "glibc_observed": host_probe["libc"]["version"],
        "isolated_venv": str(tmp_path / "unused"),
        "expected_wheelhouse_filename": "fixture.zip", "status": "TEST",
    }
    selected = {
        "profile_id": "kaggle_cp312_2026_07",
        "profile_hash": profile_hash("kaggle_cp312_2026_07", profile),
        "profile": profile, "observed_runtime": host_probe,
    }
    legacy = dict(profile)
    legacy["python_version"] = "0.0"
    legacy["python_abi"] = "cp00"
    lock = {
        "schema": "certvic.cvpr.kaggle_environment_lock.v2",
        "python": {"implementation": host_probe["implementation"], "selection": "TEST"},
        "runtime_profiles": {"kaggle_cp310_legacy": legacy, "kaggle_cp312_2026_07": profile},
        "packages": {"fixture": "1.0"},
        "cuda_contract": {},
        "offline_install": {"allow_index": False, "isolated_venv_required": True,
                            "system_site_packages": False, "wheelhouse_manifest_required": True},
        "torch_cuda_distribution": {"cuda_family": "test", "index_url": "https://example.invalid",
                                    "torch": "0", "torchvision": "0"},
    }
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(json.dumps(lock))
    record = wheel_record(wheel, supported_tags=host_probe["supported_tags"])
    manifest = tmp_path / "wheelhouse_manifest.json"
    manifest.write_text(json.dumps({
        "runtime_profile_id": selected["profile_id"],
        "runtime_profile_hash": selected["profile_hash"],
        "required_packages": {"fixture": "1.0"}, "files": {wheel.name: record},
    }))
    return selected, lock_path, wheel_root, manifest


def test_prepare_offline_environment_is_ensurepip_free_and_host_pip_targeted(tmp_path: Path) -> None:
    selected, lock_path, wheel_root, manifest = _selected_and_lock(tmp_path)
    result = prepare_offline_environment(
        lock_path, wheelhouse=wheel_root, wheelhouse_manifest=manifest,
        allow_preinstalled=False, require_exact=True, require_cuda=False,
        selected_profile=selected, venv_root=tmp_path / "venv",
        import_modules=("fixture",),
    )
    assert result["status"] == "ISOLATED_OFFLINE_VENV_INSTALLED_AND_VERIFIED"
    assert result["ensurepip_used"] is False
    assert result["kernel_packages_mutated"] is False
    assert result["venv_create_command"][2:4] == ["venv", "--without-pip"]
    assert "ensurepip" not in " ".join(result["venv_create_command"])
    assert result["install_command"][:5] == [
        result["host_python"], "-m", "pip", "--python", str(tmp_path / "venv"),
    ]
    assert "--no-index" in result["install_command"]
    assert "--only-binary=:all:" in result["install_command"]
    assert Path(result["python_executable"]).is_relative_to(tmp_path / "venv")


def test_host_pip_without_python_target_raises_runtime_10(tmp_path: Path) -> None:
    selected, lock_path, wheel_root, manifest = _selected_and_lock(tmp_path)

    def fake_installer(command, **kwargs):
        class Completed:
            returncode = 0
            stdout = "Usage: pip\n  --isolated\n"
            stderr = ""

        if command[:3] == [selected["observed_runtime"]["executable"], "-m", "venv"]:
            root = Path(command[-1])
            (root / "bin").mkdir(parents=True)
            (root / "bin" / "python").write_text("#!/bin/sh\n")
            (root / "bin" / "python").chmod(0o755)
            (root / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
            return Completed()
        if len(command) >= 4 and command[2] == "pip" and command[3] == "--help":
            return Completed()
        if len(command) >= 4 and command[2] == "pip" and command[3] == "--version":
            completed = Completed()
            completed.stdout = "pip 1.0 from /tmp/pip"
            return completed
        raise AssertionError(f"unexpected command: {command}")

    with pytest.raises(EnvironmentLockError) as failure:
        prepare_offline_environment(
            lock_path, wheelhouse=wheel_root, wheelhouse_manifest=manifest,
            allow_preinstalled=False, require_exact=True, require_cuda=False,
            selected_profile=selected, venv_root=tmp_path / "venv",
            import_modules=("fixture",), installer=fake_installer,
        )
    assert failure.value.code == HOST_PIP_CANNOT_TARGET_VENV
    assert failure.value.report["remediation"]


def test_zip64_large_member_sets_file_size_and_force_zip64(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 1024)
    large = sparse_stream_member(2048)
    output = tmp_path / "large.zip"
    built = build_bundle(
        output,
        {"snapshot/model-00001-of-00001.safetensors": large, "note.txt": b"small\n"},
        bundle_type="TEST",
        study="synthetic",
        stage="proof",
        provider=None,
        required_notebook="test.ipynb",
        dataset_slug="certvic/test",
        mount_path="/kaggle/input/test",
        external_dependency_status="SYNTHETIC_PROOF_ONLY",
        evidence_class="SYNTHETIC_FIXTURE",
        builder_command="pytest",
        readme="ZIP64 proof",
    )
    assert built["passed"] is True
    plan = {row["name"]: row for row in built["member_write_plan"]}
    assert plan["snapshot/model-00001-of-00001.safetensors"]["force_zip64"] is True
    assert plan["snapshot/model-00001-of-00001.safetensors"]["size"] == large.size
    assert plan["snapshot/model-00001-of-00001.safetensors"]["compress_type"] == zipfile.ZIP_STORED
    assert member_compression("config.json", 12)[0] == zipfile.ZIP_DEFLATED
    verification = verify_bundle(output)
    assert verification["passed"] is True
    assert verification["bundle_manifest"]["zip64_enabled"] is True
    assert verification["bundle_manifest"]["compression_policy"]["large_model_weights"] == "ZIP_STORED"
    with zipfile.ZipFile(output) as archive:
        info = archive.getinfo("snapshot/model-00001-of-00001.safetensors")
        assert info.file_size == large.size
        assert info.date_time == (1980, 1, 1, 0, 0, 0)
        assert info.compress_type == zipfile.ZIP_STORED


def _provider_fixture_files(provider: str) -> dict[str, bytes]:
    architecture = {
        "qwen2_5_vl_7b": "Qwen2_5_VLForConditionalGeneration",
        "internvl_8b": "InternVLChatModel",
        "llava_onevision_7b": "LlavaOnevisionForConditionalGeneration",
    }[provider]
    model_type = {
        "qwen2_5_vl_7b": "qwen2_5_vl",
        "internvl_8b": "internvl_chat",
        "llava_onevision_7b": "llava_onevision",
    }[provider]
    files = {
        "config.json": json.dumps({
            "architectures": [architecture],
            "model_type": model_type,
        }, indent=2).encode() + b"\n",
        "generation_config.json": b"{}\n",
        "preprocessor_config.json": b"{}\n",
        "tokenizer.json": b'{"model":{"vocab":{}}}\n',
        "tokenizer_config.json": b"{}\n",
        "model.safetensors.index.json": b'{"metadata":{},"weight_map":{}}\n',
        "model-00001-of-00001.safetensors": b"WEIGHTS" + b"\0" * 1024,
    }
    if provider == "llava_onevision_7b":
        files["processor_config.json"] = b"{}\n"
    if provider == "internvl_8b":
        files["tokenizer.model"] = b"sentencepiece"
    return files


def test_streaming_snapshot_is_single_pass_quota_safe_and_deterministic(tmp_path: Path) -> None:
    provider = "qwen2_5_vl_7b"
    files = _provider_fixture_files(provider)
    registry = {
        "models": {
            provider: {
                "repository_id": "fixture/qwen",
                "model_commit": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
                "processor_commit": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
                "expected_files": sorted(files),
                "remote_repository_bytes_at_lock": sum(len(value) for value in files.values()),
                "architecture": "Qwen2_5_VLForConditionalGeneration",
            }
        }
    }
    records = build_fixture_stream_records(files)
    first_out = tmp_path / "first.zip"
    second_out = tmp_path / "second.zip"
    first = stream_build_snapshot_bundle(
        provider,
        output=first_out,
        working_dir=tmp_path,
        registry=registry,
        file_records=records,
        safety_margin_bytes=0,
    )
    stream_build_snapshot_bundle(
        provider,
        output=second_out,
        working_dir=tmp_path,
        registry=registry,
        file_records=records,
        safety_margin_bytes=0,
    )
    assert first["determinism_proof"] == "SINGLE_PASS_DETERMINISTIC_CONSTRUCTION_SELF_VERIFIED"
    assert first["raw_snapshot_retained"] is False
    assert first["second_full_zip_created"] is False
    assert first_out.read_bytes() == second_out.read_bytes()
    assert verify_bundle(first_out)["passed"] is True
    assert not (tmp_path / "model_snapshot").exists()
    assert list(tmp_path.glob("*.deterministic_rebuild.zip")) == []


def test_disk_preflight_fails_early_with_snapshot_08(tmp_path: Path) -> None:
    registry = {
        "models": {
            "qwen2_5_vl_7b": {
                "repository_id": "fixture/qwen",
                "model_commit": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
                "processor_commit": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
                "expected_files": ["config.json"],
                "remote_repository_bytes_at_lock": 10 ** 15,
                "architecture": "Qwen2_5_VLForConditionalGeneration",
            }
        }
    }
    with pytest.raises(SnapshotStreamingError) as failure:
        disk_preflight(
            "qwen2_5_vl_7b",
            working_dir=tmp_path,
            safety_margin_bytes=10 ** 12,
            registry=registry,
        )
    assert failure.value.code == INSUFFICIENT_WORKING_DISK
    report = failure.value.report
    for key in (
        "available_bytes", "expected_snapshot_bytes", "expected_archive_bytes",
        "largest_member_bytes", "safety_margin_bytes", "provider", "remediation",
    ):
        assert key in report
    assert report["multipart_plan"]["strategy"] == (
        "DETERMINISTIC_AUTHENTICATED_MULTI_PART_SNAPSHOT_SHARDS"
    )


def test_partial_stream_failure_deletes_invalid_output(tmp_path: Path) -> None:
    provider = "qwen2_5_vl_7b"
    files = _provider_fixture_files(provider)
    registry = {
        "models": {
            provider: {
                "repository_id": "fixture/qwen",
                "model_commit": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
                "processor_commit": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
                "expected_files": sorted(files),
                "remote_repository_bytes_at_lock": sum(len(value) for value in files.values()),
                "architecture": "Qwen2_5_VLForConditionalGeneration",
            }
        }
    }
    records = build_fixture_stream_records(files)
    weight = "model-00001-of-00001.safetensors"
    records[weight].pop("bytes")
    records[weight]["kind"] = "lfs"

    def boom(_url: str, _headers):
        raise SnapshotStreamingError(
            "CERTVIC_SNAPSHOT_DOWNLOAD_FAILED",
            {"remediation": "simulated partial network failure"},
        )

    records[weight]["url"] = "https://huggingface.co/fixture/resolve/main/" + weight
    output = tmp_path / "partial.zip"
    with pytest.raises(SnapshotStreamingError):
        stream_build_snapshot_bundle(
            provider,
            output=output,
            working_dir=tmp_path,
            registry=registry,
            file_records=records,
            open_stream=boom,
            safety_margin_bytes=0,
        )
    assert not output.exists()


def test_provisioning_notebooks_are_quota_safe_and_kernel_immutable() -> None:
    cp312 = cp312_provisioning_notebook().decode()
    assert "EnvironmentLockError" in cp312
    assert "HOST_PIP_CANNOT_TARGET_VENV" in cp312
    assert "prepare_offline_environment" in cp312
    for provider in PROVIDERS:
        text = snapshot_provisioning_notebook(provider).decode()
        assert "stream_build_snapshot_bundle" in text
        assert "sys.executable, \"-m\", \"pip\", \"install\"" not in text
        assert "deterministic_rebuild.zip" not in text
        assert "snapshot_download" not in text
        assert "determinism_proof" in text
        assert f"PROVIDER = {provider!r}" in text
        notebook = json.loads(text)
        assert notebook["metadata"]["certvic"]["accelerator"] == "OFF"
        assert notebook["metadata"]["certvic"]["internet"] == "ON"
        assert notebook["metadata"]["certvic"]["zero_edit"] is True
