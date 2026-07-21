"""Focused Phase A tests for secure bundles, builders, T4x2, seeds, and bootstrap."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from certvic.cvpr.confirmatory_input_builder import build_confirmatory_input
from certvic.cvpr.kaggle_bundle import KaggleBundleError, build_bundle, diff_bundles, verify_bundle
from certvic.cvpr.notebook_bootstrap import (
    NotebookBootstrapError,
    locate_dataset,
    offline_install_command,
    validate_run_identity,
)
from certvic.cvpr.pre_smoke_packager import build_pre_smoke_permissions
from certvic.cvpr.scientific_input_builder import build_scientific_input
from certvic.cvpr.smoke_input_builder import SmokeInputBuilderError, build_smoke_bundle
from certvic.cvpr.snapshot_bundle_builder import build_snapshot_bundle
from certvic.cvpr.t4x2 import T4x2Error, assign_shards, derive_seed_manifest, detect_topology
from certvic.cvpr.wheelhouse_builder import WheelhouseBuilderError, _wheel_record, parse_locks


ROOT = Path(__file__).resolve().parents[1]


def _bundle(path: Path, files: dict[str, bytes] | None = None) -> dict:
    return build_bundle(
        path,
        files or {"payload.json": b'{"paper_evidence": false}\n'},
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
        validation_command="pytest",
        readme="Synthetic proof only.",
    )


def test_bundle_is_deterministic_diffable_and_rejects_host_paths(tmp_path: Path) -> None:
    first = tmp_path / "a.zip"
    second = tmp_path / "b.zip"
    _bundle(first)
    _bundle(second)
    assert first.read_bytes() == second.read_bytes()
    assert verify_bundle(first)["passed"] is True
    assert diff_bundles(first, second)["identical_bytes"] is True
    with pytest.raises(KaggleBundleError, match="host-specific"):
        _bundle(tmp_path / "private.zip", {"x.txt": b"/Users/alice/project/file.txt\n"})


def test_bundle_rejects_traversal_and_tampered_unmanifested_member(tmp_path: Path) -> None:
    with pytest.raises(KaggleBundleError, match="unsafe"):
        _bundle(tmp_path / "bad.zip", {"../escape": b"x"})
    source = tmp_path / "valid.zip"
    _bundle(source)
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(tampered, "w") as target:
        for info in original.infolist():
            target.writestr(info, original.read(info.filename))
        target.writestr("extra.txt", "unexpected")
    result = verify_bundle(tampered)
    assert result["passed"] is False
    assert any("unexpected or unmanifested" in error for error in result["errors"])


def test_t4x2_topologies_seed_hierarchy_and_shards_are_deterministic() -> None:
    dual = detect_topology(device_names=["NVIDIA T4", "NVIDIA T4"])
    single = detect_topology(device_names=["NVIDIA T4"])
    assert dual.mode == "T4X2_DUAL_SHARD_PARALLEL" and dual.parallel_workers == 2
    assert single.mode == "SINGLE_T4_VALIDATED_SEQUENTIAL_FALLBACK"
    with pytest.raises(T4x2Error, match="ZERO_GPU"):
        detect_topology(device_names=[])
    with pytest.raises(T4x2Error, match="UNEXPECTED_ACCELERATOR"):
        detect_topology(device_names=["NVIDIA A100"])
    ids = [f"task-{index}" for index in range(100)]
    assert assign_shards(ids) == assign_shards(reversed(ids))
    manifests = [
        derive_seed_manifest(
            global_seed=12013,
            study="confirmatory",
            provider=provider,
            gpu_id=gpu,
            shard_id=gpu,
            task_ids=ids,
            attempts=3,
        )
        for provider in ("qwen", "internvl", "llava") for gpu in (0, 1)
    ]
    provider_seeds = {manifest["provider_seed"] for manifest in manifests}
    shard_seeds = {manifest["shard_seed"] for manifest in manifests}
    assert len(provider_seeds) == 3 and len(shard_seeds) == 6
    assert all(manifest["collision_check"] == "PASS" for manifest in manifests)


def test_bootstrap_discovery_identity_and_offline_command(tmp_path: Path) -> None:
    dataset = tmp_path / "my-dataset"
    dataset.mkdir()
    expected = dataset / "input.zip"
    expected.write_bytes(b"zip")
    assert locate_dataset(
        slug="certvic/my-dataset", expected_filename="input.zip", input_root=tmp_path
    ) == expected.resolve()
    command = offline_install_command("wheels", "requirements/kaggle_qwen.lock")
    assert command[-3:] == ["wheels", "-r", "requirements/kaggle_qwen.lock"]
    identity = validate_run_identity({
        "notebook": "n", "study": "s", "stage": "x", "provider": "p", "run_tag": "r",
        "code_bundle_sha256": "a" * 64,
        "prompt_sha256": "b" * 64,
        "run_contract_sha256": "c" * 64,
    })
    assert len(identity["identity_sha256"]) == 64
    with pytest.raises(NotebookBootstrapError, match="IDENTITY_INCOMPLETE"):
        validate_run_identity({})


def test_locks_are_exact_and_macos_wheel_is_rejected(tmp_path: Path) -> None:
    locks = parse_locks(ROOT / "requirements")
    assert set(locks) == {
        "kaggle_base.lock", "kaggle_qwen.lock", "kaggle_internvl.lock",
        "kaggle_llava.lock", "kaggle_generation.lock", "kaggle_analysis.lock",
    }
    linux = tmp_path / "numpy-1.26.4-cp310-cp310-manylinux2014_x86_64.whl"
    linux.write_bytes(b"synthetic-wheel-name-proof-not-a-packaged-wheel")
    assert _wheel_record(linux)["python_tag"] == "cp310"
    mac = tmp_path / "numpy-1.26.4-cp310-cp310-macosx_11_0_x86_64.whl"
    mac.write_bytes(b"not-packaged")
    with pytest.raises(WheelhouseBuilderError, match="non-Linux"):
        _wheel_record(mac)


def test_snapshot_builder_structural_synthetic_proof(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "config.json").write_text(json.dumps({
        "architectures": ["Qwen2_5_VLForConditionalGeneration"], "model_type": "qwen2_5_vl",
    }))
    (snapshot / "model.safetensors").write_bytes(b"synthetic-not-real-weight")
    (snapshot / "tokenizer.json").write_text("{}")
    (snapshot / "processor_config.json").write_text("{}")
    output = tmp_path / "snapshot.zip"
    result = build_snapshot_bundle(
        "qwen2_5_vl_7b",
        snapshot,
        model_commit="a" * 40,
        processor_commit="a" * 40,
        output=output,
        import_smoke=False,
        synthetic_fixture=True,
    )
    assert result["passed"] is True and verify_bundle(output)["passed"] is True


def _smoke_tasks(tmp_path: Path, *, synthetic: bool) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(2):
        original = tmp_path / f"original-{index}.png"
        edited = tmp_path / f"edited-{index}.png"
        original.write_bytes(f"original-{index}".encode())
        edited.write_bytes(f"edited-{index}".encode())
        rows.append({
            "item_id": f"item-{index}",
            "original_image_path": str(original),
            "edited_image_path": str(edited),
            "license_eligible": True,
            "license_id": "SYNTHETIC_TEST",
            "source_dataset": "SYNTHETIC_FIXTURE" if synthetic else "LICENSED_TEST",
            "synthetic_fixture": synthetic,
            "prompt_template_hash": "a" * 64,
            "run_contract_hash": "b" * 64,
            "parser_version": "certvic.parse.v2",
        })
    manifest = tmp_path / "tasks.jsonl"
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return manifest


def test_smoke_builder_rejects_synthetic_real_mode_and_proves_synthetic_mode(tmp_path: Path) -> None:
    tasks = _smoke_tasks(tmp_path, synthetic=True)
    with pytest.raises(SmokeInputBuilderError, match="synthetic"):
        build_smoke_bundle(tasks, output=tmp_path / "real.zip")
    result = build_smoke_bundle(
        tasks, output=tmp_path / "synthetic.zip", synthetic_fixture=True
    )
    assert result["passed"] is True


def test_permission_confirmatory_and_scientific_builders_with_synthetic_bytes(tmp_path: Path) -> None:
    code = tmp_path / "code.zip"
    _bundle(code)
    smoke_tasks = _smoke_tasks(tmp_path / "smoke", synthetic=True)
    smoke = tmp_path / "smoke.zip"
    build_smoke_bundle(smoke_tasks, output=smoke, synthetic_fixture=True)
    inputs = {"environment_identity": tmp_path / "environment.json", "code_bundle": code, "smoke_bundle": smoke}
    inputs["environment_identity"].write_text("{}")
    for provider in ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"):
        path = tmp_path / f"{provider}.json"
        path.write_text("{}")
        inputs[f"snapshot_{provider}"] = path
    permission = build_pre_smoke_permissions(
        inputs,
        prompt_hash="a" * 64,
        parser_version="certvic.parse.v2",
        run_contract_hashes={provider: "b" * 64 for provider in ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")},
        output=tmp_path / "permission.zip",
    )
    assert permission["passed"] is True

    source = tmp_path / "source.png"
    source.write_bytes(b"synthetic-source")
    source_manifest = tmp_path / "source.jsonl"
    source_manifest.write_text(json.dumps({
        "item_id": "source-1", "source_image_path": str(source),
        "license_eligible": True, "license_id": "SYNTHETIC_TEST",
        "zero_v1_overlap": True, "synthetic_fixture": True,
    }) + "\n")
    controls: dict[str, Path] = {"source_manifest": source_manifest}
    for role in (
        "exclusion_inventory", "generation_config", "licenses", "engine_policy",
        "seed_plan", "shard_plan", "resume_ledger",
    ):
        path = tmp_path / f"{role}.json"
        path.write_text("{}")
        controls[role] = path
    confirmatory = build_confirmatory_input(
        controls, output=tmp_path / "confirmatory.zip", synthetic_fixture=True
    )
    assert confirmatory["passed"] is True

    roles = {}
    for role in (
        "task_bundle", "task_freeze", "review_ledger", "detectability_gate",
        "environment_lock", "model_registry", "snapshot_manifest", "code_bundle",
        "prompt_contract", "run_contract", "parent_authorization", "child_permission",
        "output_schema",
    ):
        path = tmp_path / f"role_{role}.json"
        value = {"synthetic_fixture": True}
        if role == "parent_authorization":
            value["execution_allowed"] = False
        if role == "child_permission":
            value["provider"] = "qwen2_5_vl_7b"
        path.write_text(json.dumps(value))
        roles[role] = path
    scientific = build_scientific_input(
        "confirmatory", "qwen", roles, run_tag="synthetic-proof",
        output=tmp_path / "scientific.zip", synthetic_fixture=True,
    )
    assert scientific["passed"] is True


def test_five_local_bundles_exist_and_verify_after_factory_build() -> None:
    expected = {
        "certvic_code_bundle.zip", "certvic_notebooks_bundle.zip", "certvic_configs_bundle.zip",
        "certvic_execution_tools_bundle.zip", "certvic_synthetic_validation_bundle.zip",
    }
    root = ROOT / "kaggle_uploads/00_code"
    assert {path.name for path in root.glob("*.zip")} == expected
    assert all(verify_bundle(root / name)["passed"] for name in expected)
