"""C6 regression coverage for Matplotlib backend sanitization and HF header imports."""

from __future__ import annotations

import importlib
import json
import os
import zipfile
from pathlib import Path

import pytest
from packaging.tags import sys_tags

from certvic.cvpr.environment_lock import (
    isolated_worker_environment,
    offline_environment_flags,
    prepare_offline_environment,
)
from certvic.cvpr.kagglefiles_pack import (
    PROVIDERS,
    cp312_provisioning_notebook,
    snapshot_provisioning_notebook,
)
from certvic.cvpr.runtime_profiles import profile_hash, runtime_probe, wheel_record
from certvic.cvpr.snapshot_streaming_provisioner import (
    HF_DEPENDENCY_API_MISMATCH,
    HF_HUB_PIN,
    SnapshotStreamingError,
    install_isolated_huggingface_hub,
    probe_pinned_huggingface_hub_api,
)


def _minimal_wheel(wheel_root: Path) -> Path:
    path = wheel_root / "fixture-1.0-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("fixture/__init__.py", "__version__ = '1.0'\n")
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


def test_isolated_worker_environment_overrides_notebook_matplotlib_backend(tmp_path: Path) -> None:
    polluted = {
        **os.environ,
        "MPLBACKEND": "module://matplotlib_inline.backend_inline",
        "MPLCONFIGDIR": "/tmp/notebook-inline-config",
    }
    env = isolated_worker_environment(venv_root=tmp_path / "venv", base=polluted)
    assert env["MPLBACKEND"] == "Agg"
    assert env["MPLCONFIGDIR"] == str((tmp_path / "venv" / "mplconfig").resolve()) or env[
        "MPLCONFIGDIR"
    ].endswith("mplconfig")
    assert Path(env["MPLCONFIGDIR"]).is_dir()
    assert offline_environment_flags()["MPLBACKEND"] == "Agg"
    assert "matplotlib_inline" not in env["MPLBACKEND"]


def test_prepare_offline_environment_ignores_inherited_notebook_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MPLBACKEND", "module://matplotlib_inline.backend_inline")
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "notebook_mpl"))
    selected, lock_path, wheel_root, manifest = _selected_and_lock(tmp_path)
    result = prepare_offline_environment(
        lock_path, wheelhouse=wheel_root, wheelhouse_manifest=manifest,
        allow_preinstalled=False, require_exact=True, require_cuda=False,
        selected_profile=selected, venv_root=tmp_path / "venv",
        import_modules=("fixture",),
    )
    assert result["status"] == "ISOLATED_OFFLINE_VENV_INSTALLED_AND_VERIFIED"
    assert result["offline_flags"]["MPLBACKEND"] == "Agg"
    assert result["matplotlib_backend"] == "Agg"
    assert result["kernel_packages_mutated"] is False
    assert "matplotlib-inline" not in json.dumps(result)


def test_genuine_matplotlib_import_failure_still_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected, lock_path, wheel_root, manifest = _selected_and_lock(tmp_path)

    def installer(command, **kwargs):
        script = command[-1] if command else ""
        if command[:3] == [selected["observed_runtime"]["executable"], "-m", "venv"]:
            root = Path(command[-1])
            (root / "bin").mkdir(parents=True)
            python = root / "bin" / "python"
            python.write_text("#!/bin/sh\n")
            python.chmod(0o755)
            (root / "pyvenv.cfg").write_text("include-system-site-packages = false\n")

            class Completed:
                returncode = 0
                stdout = ""
                stderr = ""

            return Completed()
        if len(command) >= 4 and command[2] == "pip" and command[3] in {"--help", "--version"}:
            class Completed:
                returncode = 0
                stdout = "  --python <python>\npip 26.0\n" if command[3] == "--help" else "pip 26.0"
                stderr = ""

            return Completed()
        if "pip" in command and "install" in command:
            class Completed:
                returncode = 0
                stdout = ""
                stderr = ""

            return Completed()
        if "matplotlib_backend" in script:
            class Completed:
                returncode = 1
                stdout = json.dumps({
                    "failed": {
                        "matplotlib": (
                            "ValueError: Key backend: "
                            "'module://matplotlib_inline.backend_inline'"
                        )
                    },
                    "versions": {},
                    "matplotlib_backend": None,
                }) + "\n"
                stderr = ""

            return Completed()

        class Completed:
            returncode = 0
            stdout = json.dumps({
                "passed": True, "mismatches": [], "python": "3.12.0",
                "packages": {"fixture": "1.0"},
                "cuda": {"required": False, "available": False},
                "executable": command[0],
            }) + "\n"
            stderr = ""

        return Completed()

    with pytest.raises(ValueError, match="isolated runtime import smoke failed"):
        prepare_offline_environment(
            lock_path, wheelhouse=wheel_root, wheelhouse_manifest=manifest,
            allow_preinstalled=False, require_exact=True, require_cuda=False,
            selected_profile=selected, venv_root=tmp_path / "venv",
            import_modules=("matplotlib",), installer=installer,
        )


def _plant_pinned_hf_api(target: Path) -> None:
    package = target / "huggingface_hub"
    utils = package / "utils"
    utils.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "__version__ = '0.26.2'\n"
        "class HfApi:\n"
        "    pass\n"
        "def hf_hub_url(*args, **kwargs):\n"
        "    return 'https://huggingface.co/fixture'\n",
        encoding="utf-8",
    )
    (utils / "__init__.py").write_text(
        "from .headers import build_hf_headers\n",
        encoding="utf-8",
    )
    (utils / "headers.py").write_text(
        "def build_hf_headers():\n"
        "    return {'user-agent': 'certvic-fixture'}\n",
        encoding="utf-8",
    )


def test_pinned_huggingface_hub_public_api_imports_from_utils(tmp_path: Path) -> None:
    def installer(command, **kwargs):
        target = Path(command[command.index("--target") + 1])
        _plant_pinned_hf_api(target)

        class Completed:
            returncode = 0
            stdout = "Successfully installed huggingface_hub-0.26.2\n"
            stderr = ""

        return Completed()

    report = install_isolated_huggingface_hub(tmp_path / "deps", installer=installer)
    assert report["version"] == "0.26.2"
    assert report["kernel_packages_mutated"] is False
    assert report["build_hf_headers_module"].startswith("huggingface_hub.utils")
    probe = probe_pinned_huggingface_hub_api()
    assert probe["status"] == "PINNED_HF_0262_IMPORT_PROBE_PASSED"
    assert probe["huggingface_hub.__version__"] == "0.26.2"
    assert probe["paper_evidence"] is False
    assert HF_HUB_PIN == "huggingface_hub==0.26.2"
    source = Path("certvic/cvpr/snapshot_streaming_provisioner.py").read_text(encoding="utf-8")
    assert "from huggingface_hub import HfApi, build_hf_headers, hf_hub_url" not in source
    assert "from huggingface_hub.utils import build_hf_headers" in source
    assert "from huggingface_hub import HfApi, hf_hub_url" in source


def test_hf_api_probe_fails_closed_on_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = importlib.import_module

    def fake_import(name, package=None):
        if name == "huggingface_hub.utils":
            raise ImportError("simulated missing utils.build_hf_headers")
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    # probe uses direct from-imports; patch builtins.__import__ instead
    import builtins

    real_builtins_import = builtins.__import__

    def fake_builtins(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "huggingface_hub.utils" or (
            name == "huggingface_hub" and fromlist and "build_hf_headers" in fromlist
        ):
            raise ImportError("cannot import name 'build_hf_headers'")
        module = real_builtins_import(name, globals, locals, fromlist, level)
        if name == "huggingface_hub" and fromlist and set(fromlist) <= {"HfApi", "hf_hub_url"}:
            return module
        if name == "huggingface_hub.utils":
            raise ImportError("cannot import name 'build_hf_headers'")
        return module

    monkeypatch.setattr(builtins, "__import__", fake_builtins)
    with pytest.raises(SnapshotStreamingError) as failure:
        probe_pinned_huggingface_hub_api()
    assert failure.value.code == HF_DEPENDENCY_API_MISMATCH


def test_provisioning_notebooks_include_c6_sanitization_and_hf_utils_import() -> None:
    cp312 = cp312_provisioning_notebook().decode()
    assert "MPLBACKEND" in cp312
    assert "isolated validation must force MPLBACKEND=Agg" in cp312
    assert "prepare_offline_environment" in cp312
    for provider in PROVIDERS:
        text = snapshot_provisioning_notebook(provider).decode()
        assert "stream_build_snapshot_bundle" in text
        assert "sys.executable, \"-m\", \"pip\", \"install\"" not in text
        assert "from huggingface_hub import HfApi, build_hf_headers" not in text
        notebook = json.loads(text)
        assert notebook["metadata"]["certvic"]["zero_edit"] is True
