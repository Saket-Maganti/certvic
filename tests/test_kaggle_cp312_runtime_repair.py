"""C3 regression coverage for Kaggle CP312 ABI and isolated-runtime repair."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

import pytest
from packaging.tags import sys_tags

from certvic.cvpr.environment_lock import load_environment_lock, prepare_offline_environment
from certvic.cvpr.kaggle_bundle import build_bundle
from certvic.cvpr.notebook_builder import NOTEBOOKS, build_suite
from certvic.cvpr.notebook_permission_binding import derive_permission_binding
from certvic.cvpr.runtime_profiles import (
    MULTIPLE_PROFILES_AMBIGUOUS,
    PYTHON_PROFILE_NOT_SUPPORTED,
    REQUIRED_WHEEL_MISSING,
    WHEELHOUSE_ABI_MISMATCH,
    RuntimeProfileError,
    discover_runtime_wheelhouse,
    profile_hash,
    runtime_probe,
    select_runtime_profile,
    target_tags,
    validate_wheelhouse,
    wheel_record,
)


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "configs/runtime/kaggle_t4x2_environment.lock.json"


def _probe(version: str, abi: str) -> dict:
    lock = load_environment_lock(LOCK)
    profile_id = "kaggle_cp310_legacy" if abi == "cp310" else "kaggle_cp312_2026_07"
    profile = lock["runtime_profiles"][profile_id]
    return runtime_probe(
        executable="/usr/bin/python3", implementation="CPython",
        python_version=version, architecture="x86_64", system="Linux",
        libc_name="glibc", libc_version="2.35", supported_tags=target_tags(profile),
    )


def _selected(profile_id: str) -> dict:
    lock = load_environment_lock(LOCK)
    probe = _probe("3.10.14", "cp310") if profile_id.endswith("legacy") else _probe("3.12.13", "cp312")
    return select_runtime_profile(lock, probe)


def _bundle(path: Path, profile_id: str, payload: bytes = b"same") -> None:
    selected = _selected(profile_id)
    build_bundle(
        path, {"payload.bin": payload}, bundle_type="OFFLINE_LINUX_WHEELHOUSE",
        study="all", stage="environment", provider=None,
        required_notebook="00A_certvic_code_and_environment_smoke.ipynb",
        dataset_slug="arbitrary/portable", mount_path="/kaggle/input/arbitrary-mount",
        external_dependency_status="SYNTHETIC_TEST_FIXTURE",
        evidence_class="SYNTHETIC_TEST_FIXTURE", builder_command="pytest",
        readme="runtime selection fixture", extra_manifest={
            "runtime_profile_id": profile_id,
            "runtime_profile_hash": selected["profile_hash"],
        },
    )


def _wheel(path: Path, name: str) -> Path:
    value = path / name
    value.write_bytes(b"synthetic filename-level wheel fixture")
    return value


def test_v2_lock_selects_cp310_and_live_kaggle_cp312() -> None:
    lock = load_environment_lock(LOCK)
    legacy = select_runtime_profile(lock, _probe("3.10.14", "cp310"))
    current = select_runtime_profile(lock, _probe("3.12.13", "cp312"))
    assert legacy["profile_id"] == "kaggle_cp310_legacy"
    assert current["profile_id"] == "kaggle_cp312_2026_07"
    assert current["profile"]["glibc_minimum"] == "2.17"
    assert current["profile"]["glibc_observed"] == "2.35"
    assert current["profile"]["isolated_venv"] == "/kaggle/working/certvic_runtime/kaggle_cp312_2026_07"
    for name, version in {
        "numpy": "1.26.4", "pandas": "2.2.3", "pillow": "11.0.0",
        "pyyaml": "6.0.2", "scipy": "1.14.1", "torch": "2.4.1",
        "torchvision": "0.19.1", "transformers": "4.46.3",
        "tokenizers": "0.20.3", "accelerate": "1.1.1",
        "bitsandbytes": "0.44.1", "diffusers": "0.31.0",
        "safetensors": "0.4.5",
    }.items():
        assert lock["packages"][name] == version


def test_profile_selection_fails_unsupported_and_ambiguous() -> None:
    lock = load_environment_lock(LOCK)
    with pytest.raises(RuntimeProfileError) as unsupported:
        select_runtime_profile(lock, _probe("3.11.9", "cp312"))
    assert unsupported.value.code == PYTHON_PROFILE_NOT_SUPPORTED
    duplicate = json.loads(json.dumps(lock))
    duplicate["runtime_profiles"]["duplicate"] = duplicate["runtime_profiles"]["kaggle_cp312_2026_07"]
    with pytest.raises(RuntimeProfileError) as ambiguous:
        select_runtime_profile(duplicate, _probe("3.12.13", "cp312"))
    assert ambiguous.value.code == MULTIPLE_PROFILES_AMBIGUOUS


def test_cp312_wheel_preflight_rejects_wrong_abi_platform_arch_and_sdist(tmp_path: Path) -> None:
    selected = _selected("kaggle_cp312_2026_07")
    valid = _wheel(tmp_path, "fixture-1.0-cp312-cp312-manylinux_2_17_x86_64.whl")
    record = wheel_record(valid, supported_tags=selected["observed_runtime"]["supported_tags"])
    assert record["compatible"] is True
    checked = validate_wheelhouse(
        tmp_path, selected_profile=selected, required_packages={"fixture": "1.0"}
    )
    assert checked["passed"] is True

    for bad_name in (
        "fixture-1.0-cp310-cp310-manylinux_2_17_x86_64.whl",
        "fixture-1.0-cp312-cp312-manylinux_2_17_aarch64.whl",
        "fixture-1.0-cp312-cp312-macosx_11_0_x86_64.whl",
    ):
        isolated = tmp_path / bad_name.replace(".whl", "")
        isolated.mkdir()
        _wheel(isolated, bad_name)
        with pytest.raises(RuntimeProfileError) as failure:
            validate_wheelhouse(
                isolated, selected_profile=selected, required_packages={"fixture": "1.0"}
            )
        assert failure.value.code == WHEELHOUSE_ABI_MISMATCH

    sdist_root = tmp_path / "sdist"
    sdist_root.mkdir()
    _wheel(sdist_root, valid.name)
    (sdist_root / "fixture-1.0.tar.gz").write_bytes(b"source prohibited")
    with pytest.raises(RuntimeProfileError) as sdist:
        validate_wheelhouse(
            sdist_root, selected_profile=selected, required_packages={"fixture": "1.0"}
        )
    assert sdist.value.code == WHEELHOUSE_ABI_MISMATCH

    with pytest.raises(RuntimeProfileError) as missing:
        validate_wheelhouse(
            tmp_path / "absent", selected_profile=selected,
            required_packages={"fixture": "1.0"},
        )
    assert missing.value.code == REQUIRED_WHEEL_MISSING


def test_portable_discovery_selects_compatible_profile_and_deduplicates_mirrors(
    tmp_path: Path,
) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    _bundle(inputs / "legacy.data", "kaggle_cp310_legacy", b"legacy")
    cp312 = inputs / "anything.bin"
    _bundle(cp312, "kaggle_cp312_2026_07", b"cp312")
    shutil.copyfile(cp312, inputs / "mirror_without_zip_extension")
    selected = discover_runtime_wheelhouse(
        _selected("kaggle_cp312_2026_07"), roots=[inputs],
        materialization_root=tmp_path / "materialized",
    )
    assert selected["bundle_manifest"]["runtime_profile_id"] == "kaggle_cp312_2026_07"
    assert selected["mirror_count"] == 2


def test_distinct_compatible_wheelhouses_require_expected_identity(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    _bundle(inputs / "first", "kaggle_cp312_2026_07", b"one")
    _bundle(inputs / "second", "kaggle_cp312_2026_07", b"two")
    with pytest.raises(RuntimeProfileError) as failure:
        discover_runtime_wheelhouse(
            _selected("kaggle_cp312_2026_07"), roots=[inputs],
            materialization_root=tmp_path / "materialized",
        )
    assert failure.value.code == MULTIPLE_PROFILES_AMBIGUOUS


def _minimal_wheel(path: Path) -> Path:
    wheel = path / "fixture-1.0-py3-none-any.whl"
    members = {
        "fixture.py": b"__version__ = '1.0'\n",
        "fixture-1.0.dist-info/METADATA": b"Metadata-Version: 2.1\nName: fixture\nVersion: 1.0\n",
        "fixture-1.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nGenerator: certvic-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        "fixture-1.0.dist-info/RECORD": b"",
    }
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return wheel


def test_actual_offline_install_uses_isolated_venv_not_kernel(tmp_path: Path) -> None:
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
    result = prepare_offline_environment(
        lock_path, wheelhouse=wheel_root, wheelhouse_manifest=manifest,
        allow_preinstalled=False, require_exact=True, require_cuda=False,
        selected_profile=selected, venv_root=tmp_path / "venv",
        import_modules=("fixture",),
    )
    assert result["status"] == "ISOLATED_OFFLINE_VENV_INSTALLED_AND_VERIFIED"
    assert Path(result["python_executable"]) != Path(sys.executable)
    assert Path(result["python_executable"]).is_relative_to(tmp_path / "venv")
    assert "include-system-site-packages = false" in (tmp_path / "venv/pyvenv.cfg").read_text().lower()
    assert "--no-index" in result["install_command"]
    assert "--only-binary=:all:" in result["install_command"]


def test_all_active_runbooks_route_workers_through_profile_and_preserve_order(tmp_path: Path) -> None:
    build_suite(tmp_path)
    assert set(path.name for path in tmp_path.glob("*.ipynb")) == set(NOTEBOOKS)
    for name, (stage, _provider) in NOTEBOOKS.items():
        text = (tmp_path / name).read_text()
        assert "IMMEDIATE_KERNEL_RUNTIME_PROBE" in text
        assert "RUNTIME_PROFILE_ID" in text and "RUNTIME_PROFILE_HASH" in text
        assert "RUNTIME_PYTHON" in text
        assert "ISOLATED_OFFLINE_VENV_INSTALLED_AND_VERIFIED" in text
        notebook = json.loads(text)
        assert notebook["metadata"]["language_info"]["version"] == "3.12"
        if stage in {"code_smoke", "snapshot_smoke"}:
            assert "EXPECTED_GPUS = 0" in text
    evaluation = (tmp_path / "02_qwen_specificity_confirmatory_T4x2.ipynb").read_text()
    assert evaluation.index("verify_provider_permission") < evaluation.index(
        "prepare_offline_environment("
    ) < evaluation.index("hardware_report(python_executable=RUNTIME_PYTHON)")
    evaluation_source = "\n".join(
        "".join(cell["source"])
        for cell in json.loads(evaluation)["cells"] if cell["cell_type"] == "code"
    )
    assert '[RUNTIME_PYTHON, "-m", "certvic.cvpr.worker"' in evaluation_source


def test_profile_identity_is_permission_bound_and_evidence_boundary_is_explicit() -> None:
    prompt = "{prompt}\n"
    variables = {
        "PROMPT_TEMPLATE": prompt,
        "PROMPT_TEMPLATE_HASH": hashlib.sha256(prompt.encode()).hexdigest(),
        "RUNTIME_PROFILE_ID": "kaggle_cp312_2026_07",
        "RUNTIME_PROFILE_HASH": "a" * 64,
        "WHEELHOUSE_CONTENT_IDENTITY_SHA256": "b" * 64,
        "SCHEMA_VERSION": "certvic.cvpr.output.v2", "PROVIDER": "qwen2_5_vl_7b",
        "RUN_TAG": "fixture",
        **{name: f"/fixture/{name}" for name in (
            "TASK_BUNDLE_MANIFEST", "FINAL_TASK_FREEZE", "FINAL_REVIEW_LEDGER",
            "SMOKE_GATE_JSON", "ENVIRONMENT_LOCK", "MODEL_REGISTRY", "SNAPSHOT_MANIFEST",
            "CODE_BUNDLE", "STUDY_CONFIG", "MATRIX_AUTHORIZATION",
        )},
    }
    binding = derive_permission_binding(variables, require_files=False)
    assert binding["scalars"]["runtime_profile_id"] == "kaggle_cp312_2026_07"
    assert binding["scalars"]["runtime_profile_hash"] == "a" * 64
    assert binding["scalars"]["wheelhouse_content_identity_sha256"] == "b" * 64
    handoff = (ROOT / "reports/non_human_closure/CERTVIC_KAGGLE_CP312_RUNTIME_REPAIR_HANDOFF.md").read_text()
    assert "Fresh real Kaggle 00A: not yet executed" in handoff
    assert "READY_TO_BUILD_CP312_WHEELHOUSE" in handoff
    assert "READY_FOR_00B" not in handoff
    provisioning = (
        ROOT / "notebooks/kaggle/provisioning/00_build_certvic_cp312_wheelhouse.ipynb"
    ).read_text()
    for token in (
        "deterministic_provision", "certvic_offline_wheelhouse_cp312.zip",
        "prepare_offline_environment", "offline_install_import_validation",
        "Accelerator OFF", "Internet ON",
    ):
        assert token in provisioning
