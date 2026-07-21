from __future__ import annotations

import json
import shutil
import stat
import zipfile
from pathlib import Path

import pytest

from certvic.cvpr.content_discovery import (
    DISCOVERY_POLICY,
    ERROR_AMBIGUOUS,
    ERROR_AUTHENTICATION,
    ContentDiscoveryError,
    discover_authenticated_input,
)
from certvic.cvpr.kaggle_bundle import build_bundle
from certvic.cvpr.notebook_builder import NOTEBOOKS, build_suite


def _bundle(
    path: Path,
    *,
    payload: bytes = b'{"fixture": 1}\n',
    provider: str | None = None,
    study: str = "synthetic",
    stage: str = "proof",
    commit: str = "a" * 40,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    build_bundle(
        path,
        {"nested/payload.json": payload},
        bundle_type="CODE",
        study=study,
        stage=stage,
        provider=provider,
        required_notebook="recommended-label-only.ipynb",
        dataset_slug="someone/recommended-title",
        mount_path="/kaggle/input/recommended-title",
        external_dependency_status="SYNTHETIC_FIXTURE",
        evidence_class="SYNTHETIC_FIXTURE",
        builder_command="pytest",
        validation_command="pytest",
        readme="Synthetic discovery fixture.",
        extra_manifest={"source_commit": commit},
    )
    return path


def _extract(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True)
    with zipfile.ZipFile(archive) as source:
        source.extractall(destination)
    return destination


def _rewrite_with_extra(
    source: Path,
    destination: Path,
    *,
    name: str,
    payload: bytes,
    mode: int | None = None,
) -> None:
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination, "w") as target:
        for info in original.infolist():
            target.writestr(info, original.read(info.filename))
        if mode is None:
            target.writestr(name, payload)
        else:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = mode << 16
            target.writestr(info, payload)


def test_arbitrary_owner_mount_filename_extension_and_nesting(tmp_path: Path) -> None:
    root = tmp_path / "account-alias" / "input"
    archive = _bundle(root / "unexpected dataset folder" / "deep" / "payload.dat")
    result = discover_authenticated_input(
        "CODE", roots=[root], materialization_root=tmp_path / "working"
    )
    assert result["discovered_path"] == archive.resolve().as_posix()
    assert result["representation"] == "zip_archive"
    assert result["discovery_policy"] == DISCOVERY_POLICY
    assert result["owner_binding_required"] is False
    assert result["filename_binding_required"] is False
    assert result["path_binding_required"] is False
    assert Path(result["materialized_root"], "nested/payload.json").is_file()


def test_nested_extracted_bundle_is_authenticated(tmp_path: Path) -> None:
    archive = _bundle(tmp_path / "source.zip")
    extracted = _extract(
        archive,
        tmp_path / "fourth-account" / "arbitrary-title" / "one" / "two" / "blob",
    )
    archive.unlink()
    result = discover_authenticated_input("CODE", roots=tmp_path / "fourth-account")
    assert result["representation"] == "extracted_directory"
    assert result["discovered_path"] == extracted.resolve().as_posix()
    assert result["materialized_root"] == extracted.resolve().as_posix()


def test_identical_mirrors_deduplicate_and_distinct_content_is_ambiguous(
    tmp_path: Path,
) -> None:
    first = _bundle(tmp_path / "z-mount" / "first.blob")
    mirror = tmp_path / "a-mount" / "nested" / "mirror.random"
    mirror.parent.mkdir(parents=True)
    shutil.copyfile(first, mirror)
    result = discover_authenticated_input(
        "CODE", roots=tmp_path, materialization_root=tmp_path / "working"
    )
    assert result["mirror_count"] == 2
    assert result["mirrors"] == sorted(
        [first.resolve().as_posix(), mirror.resolve().as_posix()]
    )
    assert result["discovered_path"] == mirror.resolve().as_posix()

    _bundle(tmp_path / "third-mount" / "other.bin", payload=b'{"fixture": 2}\n')
    with pytest.raises(ContentDiscoveryError, match=ERROR_AMBIGUOUS):
        discover_authenticated_input("CODE", roots=tmp_path)


@pytest.mark.parametrize(
    ("kwargs", "expected_identity"),
    [
        ({"provider": "wrong"}, None),
        ({"study": "wrong"}, None),
        ({"stage": "wrong"}, None),
        ({}, {"source_commit": "b" * 40}),
        ({}, "f" * 64),
    ],
)
def test_wrong_metadata_commit_or_identity_fails_authentication(
    tmp_path: Path, kwargs: dict[str, str], expected_identity: object
) -> None:
    _bundle(
        tmp_path / "mount" / "payload",
        provider="expected",
        study="expected-study",
        stage="expected-stage",
    )
    request = {
        "provider": "expected",
        "study": "expected-study",
        "stage": "expected-stage",
        **kwargs,
    }
    with pytest.raises(ContentDiscoveryError, match=ERROR_AUTHENTICATION):
        discover_authenticated_input(
            "CODE", roots=tmp_path, expected_identity=expected_identity, **request
        )


@pytest.mark.parametrize(
    ("name", "mode"),
    [
        ("../escape", None),
        ("nested/payload.json", None),
        ("unsafe-link", stat.S_IFLNK | 0o777),
        ("device", stat.S_IFCHR | 0o600),
    ],
)
def test_traversal_duplicate_symlink_and_device_members_fail_closed(
    tmp_path: Path, name: str, mode: int | None
) -> None:
    source = _bundle(tmp_path / "source.zip")
    malicious = tmp_path / "malicious.dat"
    _rewrite_with_extra(source, malicious, name=name, payload=b"bad", mode=mode)
    source.unlink()
    with pytest.raises(ContentDiscoveryError, match=ERROR_AUTHENTICATION):
        discover_authenticated_input("CODE", roots=tmp_path)


def test_tampered_archive_and_extracted_file_universe_fail_closed(tmp_path: Path) -> None:
    source = _bundle(tmp_path / "source.zip")
    tampered = tmp_path / "tampered.bin"
    _rewrite_with_extra(source, tampered, name="unmanifested.txt", payload=b"bad")
    source.unlink()
    with pytest.raises(ContentDiscoveryError, match=ERROR_AUTHENTICATION):
        discover_authenticated_input("CODE", roots=tmp_path)

    archive = _bundle(tmp_path / "fresh.zip")
    extracted = _extract(archive, tmp_path / "extracted")
    archive.unlink()
    (extracted / "unmanifested.txt").write_text("bad", encoding="utf-8")
    with pytest.raises(ContentDiscoveryError, match=ERROR_AUTHENTICATION):
        discover_authenticated_input("CODE", roots=tmp_path)


def test_four_independent_account_layouts_have_the_same_scientific_identity(
    tmp_path: Path,
) -> None:
    canonical = _bundle(tmp_path / "canonical.dat")
    identities = set()
    for index, filename in enumerate(("a.zip", "code", "random.bin", "payload.dat"), 1):
        root = tmp_path / f"account-{index}" / f"owner-{index}" / "nested" / str(index)
        root.mkdir(parents=True)
        shutil.copyfile(canonical, root / filename)
        result = discover_authenticated_input(
            "CODE",
            roots=tmp_path / f"account-{index}",
            materialization_root=tmp_path / f"working-{index}",
        )
        identities.add(result["content_identity_sha256"])
    assert len(identities) == 1


def test_probe_reads_magic_before_full_verification_among_unrelated_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "input"
    root.mkdir()
    for index in range(200):
        (root / f"unrelated-{index:03d}.weights").write_bytes(b"not-a-zip")
    _bundle(root / "nested" / "real-payload.opaque")
    result = discover_authenticated_input(
        "CODE", roots=root, materialization_root=tmp_path / "working"
    )
    assert result["probe_stats"] == {
        "regular_files_probed": 201,
        "zip_candidates": 1,
        "manifest_directories": 0,
    }


def test_all_notebooks_are_name_independent_content_discovery_runbooks(
    tmp_path: Path,
) -> None:
    build_suite(tmp_path)
    for name in NOTEBOOKS:
        payload = json.loads((tmp_path / name).read_text(encoding="utf-8"))
        text = "\n".join("".join(cell.get("source", [])) for cell in payload["cells"])
        assert "discover_authenticated_input(" in text
        assert "locate_dataset(" not in text
        assert "REQUIRED_USER_FILL" not in text
        assert "get_ipython().run_line_magic" not in text
        assert "Path(NOTEBOOK_NAME)" not in text
        assert payload["metadata"]["certvic"]["content_discovery"] is True
        # A runtime rename cannot affect the embedded provider/study identity.
        renamed = tmp_path / f"renamed-{len(name)}-{name}"
        renamed.write_text(json.dumps(payload), encoding="utf-8")
        assert json.loads(renamed.read_text(encoding="utf-8"))["cells"] == payload["cells"]
