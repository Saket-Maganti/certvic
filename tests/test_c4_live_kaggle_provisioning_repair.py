"""Regression proofs for the two failures observed in live C4 provisioning."""

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import certvic.cvpr.wheelhouse_builder as wheelhouse_builder
from certvic.cvpr.content_discovery import (
    ERROR_AMBIGUOUS,
    ERROR_AUTHENTICATION,
    ERROR_NOT_FOUND,
    ContentDiscoveryError,
    discover_authenticated_input,
)
from certvic.cvpr.environment_lock import load_environment_lock
from certvic.cvpr.kaggle_bundle import build_bundle
from certvic.cvpr.kagglefiles_pack import snapshot_provisioning_notebook
from certvic.cvpr.notebook_builder import content_early_code_bootstrap_source
from certvic.cvpr.runtime_profiles import WHEELHOUSE_ABI_MISMATCH
from certvic.cvpr.wheelhouse_builder import (
    build_wheelhouse,
    persist_failure_report,
    provisioning_failure_report,
    prune_redundant_incompatible_wheels,
)


ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")


def _code_bundle(path: Path, *, identity: str = "one") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    build_bundle(
        path,
        {
            "pyproject.toml": b"[build-system]\nrequires=[]\n",
            "certvic/__init__.py": b'"""fixture"""\n',
            "identity.txt": identity.encode(),
        },
        bundle_type="CODE",
        study="all",
        stage="repository",
        provider=None,
        required_notebook="C4-test.ipynb",
        dataset_slug="arbitrary/account-independent-title",
        mount_path="/kaggle/input/arbitrary",
        external_dependency_status="SYNTHETIC_TEST_FIXTURE",
        evidence_class="SYNTHETIC_TEST_FIXTURE",
        builder_command="pytest",
        validation_command="pytest",
        readme="C4 extracted-directory discovery fixture.",
    )
    return path


def _extract(source: Path, destination: Path) -> Path:
    destination.mkdir(parents=True)
    with zipfile.ZipFile(source) as archive:
        archive.extractall(destination)
    return destination


@pytest.mark.parametrize("provider", PROVIDERS)
def test_all_snapshot_provisioners_embed_the_one_shared_discovery_source(provider: str) -> None:
    notebook = json.loads(snapshot_provisioning_notebook(provider))
    code = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    shared = content_early_code_bootstrap_source()
    assert shared in code
    assert "early_verify_archive" in shared and "early_verify_directory" in shared
    assert "discover_authenticated_input(" in shared
    assert "CONTENT_AUTHENTICATED_ANY_LOCATION" in shared
    assert "def _authenticate_code(candidate)" not in code


@pytest.mark.parametrize("representation", ["zip", "extracted"])
def test_shared_snapshot_bootstrap_accepts_zip_renamed_or_extracted_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    representation: str,
) -> None:
    input_root = tmp_path / "different-account" / "deep" / "arbitrary-dataset-title"
    archive = _code_bundle(input_root / "payload-without-extension")
    if representation == "extracted":
        extracted = _extract(archive, input_root / "nested" / "materialized-by-kaggle")
        archive.unlink()
    monkeypatch.setenv("CERTVIC_INPUT_ROOTS", str(tmp_path / "different-account"))
    monkeypatch.setenv("CERTVIC_KAGGLE_WORKING_ROOT", str(tmp_path / "working"))
    namespace: dict[str, object] = {}
    before = list(sys.path)
    try:
        exec(compile(content_early_code_bootstrap_source(), "C4-bootstrap", "exec"), namespace)
    finally:
        sys.path[:] = before
    observed = namespace["DISCOVERED_PROVENANCE"]["CODE"]  # type: ignore[index]
    assert observed["representation"] == (
        "zip_archive" if representation == "zip" else "extracted_directory"
    )
    if representation == "extracted":
        assert observed["discovered_path"] == extracted.resolve().as_posix()


def test_snapshot_discovery_mirrors_ambiguity_tampering_and_missing_manifest(
    tmp_path: Path,
) -> None:
    first = _code_bundle(tmp_path / "a" / "one")
    mirror = tmp_path / "b" / "nested" / "two.random"
    mirror.parent.mkdir(parents=True)
    shutil.copyfile(first, mirror)
    discovered = discover_authenticated_input(
        "CODE", roots=tmp_path, materialization_root=tmp_path / "working"
    )
    assert discovered["mirror_count"] == 2

    _code_bundle(tmp_path / "c" / "distinct", identity="two")
    with pytest.raises(ContentDiscoveryError, match=ERROR_AMBIGUOUS):
        discover_authenticated_input("CODE", roots=tmp_path)

    isolated = tmp_path / "tamper-only"
    archive = _code_bundle(isolated / "source")
    extracted = _extract(archive, isolated / "extracted")
    archive.unlink()
    (extracted / "identity.txt").write_text("tampered", encoding="utf-8")
    with pytest.raises(ContentDiscoveryError, match=ERROR_AUTHENTICATION):
        discover_authenticated_input("CODE", roots=isolated)

    missing = tmp_path / "missing"
    missing.mkdir()
    (missing / "payload").write_text("no manifests", encoding="utf-8")
    with pytest.raises(ContentDiscoveryError, match=ERROR_NOT_FOUND):
        discover_authenticated_input("CODE", roots=missing)


def _filename_wheel(root: Path, name: str) -> Path:
    path = root / name
    path.write_bytes(b"filename-level compatibility fixture")
    return path


def _selected_cp312() -> dict:
    lock = load_environment_lock(ROOT / "configs/runtime/kaggle_t4x2_environment.lock.json")
    profile = lock["runtime_profiles"]["kaggle_cp312_2026_07"]
    from certvic.cvpr.runtime_profiles import profile_hash, runtime_probe, target_tags

    return {
        "profile_id": "kaggle_cp312_2026_07",
        "profile_hash": profile_hash("kaggle_cp312_2026_07", profile),
        "profile": profile,
        "observed_runtime": runtime_probe(
            executable="/usr/local/bin/python",
            implementation="CPython",
            python_version="3.12.13",
            architecture="x86_64",
            system="Linux",
            libc_name="glibc",
            libc_version="2.35",
            supported_tags=target_tags(profile),
        ),
    }


def test_redundant_foreign_wheel_is_removed_but_nonredundant_fails_closed(
    tmp_path: Path,
) -> None:
    supported = _selected_cp312()["observed_runtime"]["supported_tags"]
    replaceable = tmp_path / "replaceable"
    replaceable.mkdir()
    compatible = _filename_wheel(
        replaceable, "fixture-1.0-cp312-cp312-manylinux_2_17_x86_64.whl"
    )
    redundant = _filename_wheel(
        replaceable, "fixture-1.0-cp310-cp310-manylinux_2_17_x86_64.whl"
    )
    pruned = prune_redundant_incompatible_wheels(
        replaceable, supported_tags=supported
    )
    assert pruned["passed"] is True
    assert compatible.is_file() and not redundant.exists()
    assert pruned["removed_redundant_incompatible_wheels"][0]["package"] == "fixture"

    blocked = tmp_path / "blocked"
    blocked.mkdir()
    _filename_wheel(
        blocked, "fixture-1.0-cp312-cp312-manylinux_2_17_x86_64.whl"
    )
    blocked_redundant = _filename_wheel(
        blocked, "fixture-1.0-cp310-cp310-manylinux_2_17_x86_64.whl"
    )
    only = _filename_wheel(
        blocked, "only_foreign-2.0-cp310-cp310-manylinux_2_17_x86_64.whl"
    )
    failure = prune_redundant_incompatible_wheels(blocked, supported_tags=supported)
    assert failure["passed"] is False and only.is_file() and not blocked_redundant.exists()
    assert failure["retained_nonredundant_incompatible_wheels"][0]["package"] == "only-foreign"

    report = provisioning_failure_report(
        WHEELHOUSE_ABI_MISMATCH,
        selected=_selected_cp312(),
        required_packages={"only-foreign": "2.0"},
        incompatible_wheels=failure["retained_nonredundant_incompatible_wheels"],
        remediation="Supply a compatible exact replacement.",
    )
    path = persist_failure_report(tmp_path / "failure.json", report)
    saved = json.loads(path.read_text())
    assert saved["status"] == WHEELHOUSE_ABI_MISMATCH
    assert saved["incompatible_wheels"][0]["package"] == "only-foreign"


def _metadata_wheel(
    root: Path,
    package: str,
    version: str,
    *,
    requirements: tuple[str, ...] = (),
) -> Path:
    filename = f"{package.replace('-', '_')}-{version}-py3-none-any.whl"
    path = root / filename
    dist_info = f"{package.replace('-', '_')}-{version}.dist-info"
    metadata = (
        f"Metadata-Version: 2.1\nName: {package}\nVersion: {version}\n"
        + "".join(f"Requires-Dist: {value}\n" for value in requirements)
    ).encode()
    members = {
        f"{package.replace('-', '_')}.py": b"__version__ = 'fixture'\n",
        f"{dist_info}/METADATA": metadata,
        f"{dist_info}/WHEEL": (
            b"Wheel-Version: 1.0\nGenerator: certvic-c4-test\n"
            b"Root-Is-Purelib: true\nTag: py3-none-any\n"
        ),
        f"{dist_info}/RECORD": b"",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in sorted(members.items()):
            archive.writestr(name, payload)
    return path


def _minimal_requirements_and_lock(tmp_path: Path) -> tuple[Path, Path]:
    requirements = tmp_path / "requirements"
    requirements.mkdir()
    (requirements / "kaggle_base.lock").write_text(
        "torch==2.4.1\ntorchvision==0.19.1\n", encoding="utf-8"
    )
    for name in wheelhouse_builder.LOCK_NAMES[1:]:
        (requirements / name).write_text("-r kaggle_base.lock\n", encoding="utf-8")
    lock = load_environment_lock(ROOT / "configs/runtime/kaggle_t4x2_environment.lock.json")
    lock["packages"] = {"torch": "2.4.1", "torchvision": "0.19.1"}
    lock_path = tmp_path / "environment.lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    return requirements, lock_path


def test_validated_transitive_closure_builds_byte_deterministically(tmp_path: Path) -> None:
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    _metadata_wheel(wheels, "torch", "2.4.1+cu121")
    _metadata_wheel(
        wheels, "torchvision", "0.19.1+cu121", requirements=("torch==2.4.1",)
    )
    requirements, lock = _minimal_requirements_and_lock(tmp_path)
    first = tmp_path / "first" / "wheelhouse.zip"
    second = tmp_path / "second" / "wheelhouse.zip"
    first.parent.mkdir()
    second.parent.mkdir()
    one = build_wheelhouse(
        wheel_root=wheels,
        output=first,
        requirements_root=requirements,
        environment_lock=lock,
        selected_target=_selected_cp312(),
    )
    two = build_wheelhouse(
        wheel_root=wheels,
        output=second,
        requirements_root=requirements,
        environment_lock=lock,
        selected_target=_selected_cp312(),
    )
    assert one["passed"] is True and two["passed"] is True
    assert first.read_bytes() == second.read_bytes()


def test_kaggle_resolver_uses_live_tags_and_separates_cuda_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def runner(command: list[str], **_kwargs: object) -> SimpleNamespace:
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        wheelhouse_builder,
        "_selected_target",
        lambda *_args, **_kwargs: _selected_cp312(),
    )
    result = wheelhouse_builder._download(
        "KAGGLE_PROVISIONING_BUILD",
        tmp_path / "download",
        requirements_root=ROOT / "requirements",
        profile_id="kaggle_cp312_2026_07",
        environment_lock=ROOT / "configs/runtime/kaggle_t4x2_environment.lock.json",
        runner=runner,
    )
    assert len(commands) == 2
    assert not any(flag in commands[0] for flag in ("--platform", "--python-version", "--abi"))
    assert "torch==2.4.1+cu121" in commands[0]
    assert "torchvision==0.19.1+cu121" in commands[0]
    assert commands[0][commands[0].index("--index-url") + 1].endswith("/cu121")
    assert commands[1][commands[1].index("--index-url") + 1] == "https://pypi.org/simple"
    assert result["resolution_strategy"] == "LIVE_PACKAGING_SYS_TAGS"

    dirty = tmp_path / "dirty-download"
    dirty.mkdir()
    (dirty / "partial.whl").write_bytes(b"failed prior resolver session")
    with pytest.raises(wheelhouse_builder.WheelhouseBuilderError) as caught:
        wheelhouse_builder._download(
            "KAGGLE_PROVISIONING_BUILD",
            dirty,
            requirements_root=ROOT / "requirements",
            profile_id="kaggle_cp312_2026_07",
            environment_lock=ROOT / "configs/runtime/kaggle_t4x2_environment.lock.json",
            runner=runner,
        )
    assert caught.value.report["schema"] == wheelhouse_builder.FAILURE_REPORT_SCHEMA
    assert caught.value.report["status"] == wheelhouse_builder.RESOLVER_FAILED
    assert caught.value.report["observed_runtime"]["python_version"] == "3.12.13"
    assert "clean destination" in caught.value.report["remediation"]
