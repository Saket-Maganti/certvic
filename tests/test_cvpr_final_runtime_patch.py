from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from certvic.cvpr.kaggle_session_simulator import PROVIDERS, simulate
from certvic.cvpr.notebook_00c2_proof import execute_generated_route
from certvic.cvpr.notebook_builder import build_suite
from certvic.cvpr.notebook_permission_binding import (
    NotebookPermissionBindingError, derive_permission_binding,
)
from certvic.cvpr.package_run import package
from certvic.cvpr.smoke_artifacts import (
    SMOKE_MEMBERS, SmokeArtifactError, package_smoke, read_smoke_archive,
)
from certvic.cvpr.smoke_gate import evaluate
from certvic.cvpr.synthetic_smoke import run as run_synthetic_smoke
from certvic.cvpr.worker import run_shard


def _rewrite_member(archive: Path, name: str, transform) -> None:
    with zipfile.ZipFile(archive) as source:
        members = {item: source.read(item) for item in source.namelist()}
    members[name] = transform(members[name])
    manifest = json.loads(members["hash_manifest.json"])
    manifest["files"] = {
        item: hashlib.sha256(payload).hexdigest()
        for item, payload in members.items()
        if item != "hash_manifest.json"
    }
    members["hash_manifest.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for item, payload in sorted(members.items()):
            info = zipfile.ZipInfo(item, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            target.writestr(info, payload)


def _change_json(field: str, value):
    def transform(payload: bytes) -> bytes:
        row = json.loads(payload)
        row[field] = value
        return (json.dumps(row, indent=2, sort_keys=True) + "\n").encode()

    return transform


def _change_first_jsonl(field: str, value):
    def transform(payload: bytes) -> bytes:
        rows = [json.loads(line) for line in payload.splitlines() if line]
        rows[0][field] = value
        return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()

    return transform


def test_real_model_smoke_package_copies_snapshot_and_is_canonical(tmp_path: Path) -> None:
    result = run_synthetic_smoke(tmp_path / "route")
    assert result["status"] == "SYNTHETIC_SMOKE_PASSED"
    for provider in PROVIDERS:
        output = tmp_path / "route" / "runs" / provider
        assert (output / "snapshot_manifest.json").is_file()
        archive = Path(result["archives"][provider])
        with zipfile.ZipFile(archive) as handle:
            assert set(handle.namelist()) == set(SMOKE_MEMBERS)
        loaded = read_smoke_archive(archive)
        assert loaded["runtime"]["runtime_class"] == "REAL_MODEL_SMOKE"
        assert loaded["runtime"]["synthetic_notebook_proof"] is True
        assert loaded["authorization_proof"]["runtime_class"] == "SYNTHETIC_SMOKE"


def test_synthetic_notebook_proof_cannot_be_repackaged_as_real(tmp_path: Path) -> None:
    result = run_synthetic_smoke(tmp_path / "route")
    provider = PROVIDERS[0]
    with pytest.raises(SmokeArtifactError, match="cannot be promoted"):
        package_smoke(
            tmp_path / "route" / "runs" / provider,
            provider=provider,
            task_bundle_manifest=result["task_bundle_manifest"],
            destination=tmp_path / "forbidden-real.zip",
            synthetic=False,
        )


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("cleanup_status", "FAIL", "SMOKE_CLEANUP_FAILED"),
        ("model_release_status", "FAIL", "SMOKE_CLEANUP_FAILED"),
        ("cuda_cleanup_status", "FAIL", "SMOKE_CLEANUP_FAILED"),
        ("oom_events", 1, "SMOKE_OOM_DETECTED"),
        ("unresolved_warnings", [{"code": "UNKNOWN"}], "SMOKE_WARNING_UNRESOLVED"),
    ],
)
def test_strict_gate_rejects_runtime_failures(
    tmp_path: Path, field: str, value, code: str
) -> None:
    root = tmp_path / field
    result = run_synthetic_smoke(root)
    provider = PROVIDERS[0]
    _rewrite_member(
        Path(result["archives"][provider]), "runtime_manifest.json", _change_json(field, value)
    )
    gate = evaluate(root, list(PROVIDERS), contract=json.loads(Path(result["contract"]).read_text()))
    assert gate["status"] == "REAL_MODEL_SMOKE_FAILED"
    failed = next(row for row in gate["models"] if row["model"] == provider)
    assert code in {row["error_code"] for row in failed["diagnostics"]}


@pytest.mark.parametrize(
    ("member", "field"),
    [
        ("runtime_manifest.json", "run_contract_hash"),
        ("validation_report.json", "run_contract_hash"),
        ("authorization_proof.json", "run_contract_hash"),
        ("predictions.jsonl", "run_contract_hash"),
        ("runtime_manifest.json", "prompt_template_hash"),
        ("validation_report.json", "prompt_template_hash"),
        ("authorization_proof.json", "prompt_template_hash"),
        ("predictions.jsonl", "prompt_template_hash"),
    ],
)
def test_identity_tamper_fails_closed(tmp_path: Path, member: str, field: str) -> None:
    result = run_synthetic_smoke(tmp_path / f"{member}-{field}")
    archive = Path(result["archives"][PROVIDERS[0]])
    transform = (
        _change_first_jsonl(field, "0" * 64)
        if member == "predictions.jsonl"
        else _change_json(field, "0" * 64)
    )
    _rewrite_member(archive, member, transform)
    with pytest.raises(SmokeArtifactError, match="identity|signature"):
        read_smoke_archive(archive)


def test_snapshot_parent_and_permission_tamper_fail(tmp_path: Path) -> None:
    for member, field in (
        ("snapshot_manifest.json", "model_id"),
        ("provider_permission.json", "provider"),
        ("provider_permission.json", "parent_matrix_authorization_id"),
    ):
        result = run_synthetic_smoke(tmp_path / f"tamper-{field}")
        archive = Path(result["archives"][PROVIDERS[0]])
        _rewrite_member(archive, member, _change_json(field, "tampered"))
        with pytest.raises(SmokeArtifactError):
            read_smoke_archive(archive)


@pytest.mark.parametrize("field", ["run_contract_hash", "prompt_template_hash"])
def test_trusted_contract_identity_tamper_fails_gate(tmp_path: Path, field: str) -> None:
    root = tmp_path / f"trusted-{field}"
    result = run_synthetic_smoke(root)
    contract = json.loads(Path(result["contract"]).read_text())
    if field == "run_contract_hash":
        contract["providers"][PROVIDERS[0]][field] = "0" * 64
    else:
        contract[field] = "0" * 64
        contract["prompt_hash"] = "0" * 64
    gate = evaluate(root, list(PROVIDERS), contract=contract)
    assert gate["status"] == "REAL_MODEL_SMOKE_FAILED"
    failed = next(row for row in gate["models"] if row["model"] == PROVIDERS[0])
    expected = (
        "SMOKE_RUN_CONTRACT_MISMATCH"
        if field == "run_contract_hash"
        else "SMOKE_PROMPT_MISMATCH"
    )
    assert expected in {row["error_code"] for row in failed["diagnostics"]}


def test_notebook_derived_route_passes_all_providers(tmp_path: Path) -> None:
    proof = execute_generated_route(tmp_path / "notebook-proof")
    assert proof["status"] == "NOTEBOOK_DERIVED_SYNTHETIC_00C2_PASSED"
    assert proof["strict_gate_status"] == "SYNTHETIC_SMOKE_PASSED"
    assert set(proof["proof_archives"]) == set(PROVIDERS)
    assert all(Path(path).is_file() for path in proof["proof_archives"].values())


def test_notebook_preflight_binds_parent_and_exact_prompt_before_hardware(tmp_path: Path) -> None:
    build_suite(tmp_path)
    for prefix in ("00C2_", "02_", "03_", "04_", "11_", "12_", "13_", "21_", "22_", "23_"):
        text = next(tmp_path.glob(prefix + "*.ipynb")).read_text()
        assert "MATRIX_AUTHORIZATION" in text
        assert "verify_matrix_authorization(MATRIX_AUTHORIZATION)" in text
        assert "PROMPT_TEMPLATE_HASH" in text
        assert text.index("verify_matrix_authorization(MATRIX_AUTHORIZATION)") < text.index(
            "hardware = hardware_report()"
        )
    variables: dict[str, object] = {
        "SCHEMA_VERSION": "certvic.cvpr.output.v2", "PROVIDER": PROVIDERS[0],
        "RUN_TAG": "test", "TASK_BUNDLE_ROOT": str(tmp_path),
        "PROMPT_TEMPLATE": "{prompt}",
        "PROMPT_TEMPLATE_HASH": hashlib.sha256(b"{prompt}").hexdigest(),
    }
    for name in (
        "TASK_BUNDLE_MANIFEST", "FINAL_TASK_FREEZE", "FINAL_REVIEW_LEDGER",
        "SMOKE_GATE_JSON", "ENVIRONMENT_LOCK", "MODEL_REGISTRY", "SNAPSHOT_MANIFEST",
        "CODE_BUNDLE", "STUDY_CONFIG", "MATRIX_AUTHORIZATION",
    ):
        path = tmp_path / name
        path.write_text(name)
        variables[name] = str(path)
    derive_permission_binding(variables)
    variables["PROMPT_TEMPLATE"] = "{prompt}!"
    with pytest.raises(NotebookPermissionBindingError, match="exact active prompt"):
        derive_permission_binding(variables)


def _legacy_runtime(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text(json.dumps({
        "item_id": "i1", "original_image_path": "original.png",
        "edited_image_path": "edited.png", "question": "Yes?",
        "answer_format": "yes_no", "mock_raw_response": "yes",
    }) + "\n")
    config = tmp_path / "runtime.json"
    config.write_text(json.dumps({
        "provider": PROVIDERS[0], "model_id": "mock", "model_commit": "a" * 40,
        "processor_commit": "b" * 40, "run_tag": "retry_test",
        "task_manifest": str(tasks), "output_dir": str(tmp_path / "output"),
        "code_bundle_hash": "c" * 64, "seed": 1,
        "generation_parameters": {"do_sample": False},
    }))
    run_shard(config, shard=0, num_shards=1, mock_runtime=True)
    return config


@pytest.mark.parametrize("failure", ["write", "validate", "rename"])
def test_package_failures_leave_no_final_zip_and_are_retryable(
    tmp_path: Path, failure: str
) -> None:
    config = _legacy_runtime(tmp_path / failure)
    kwargs = {}
    if failure == "write":
        kwargs["zip_writer"] = lambda path, members: (_ for _ in ()).throw(OSError("write"))
    elif failure == "validate":
        kwargs["archive_validator"] = lambda path: (_ for _ in ()).throw(ValueError("validate"))
    else:
        kwargs["atomic_replace"] = lambda source, target: (_ for _ in ()).throw(OSError("rename"))
    with pytest.raises((OSError, ValueError)):
        package(config, expected_shards=1, **kwargs)
    runtime = json.loads(config.read_text())
    final = Path(runtime["output_dir"]) / f"certvic_cvpr_retry_test_{PROVIDERS[0]}.zip"
    assert not final.exists()
    retried = package(config, expected_shards=1)
    assert retried["status"] == "PACKAGED" and final.is_file()


def test_portable_proof_precedes_final_permission_commit(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    result = simulate(root)
    assert result["status"] == "KAGGLE_MULTI_SESSION_SIMULATION_PASSED"
    for provider, archive in result["returned_archives"].items():
        with zipfile.ZipFile(archive) as handle:
            events = [json.loads(line) for line in handle.read("permission_events.jsonl").splitlines()]
        assert events[-1]["to_state"] == "PACKAGE_WRITTEN"
        external = [json.loads(line) for line in (
            root / "isolated_sessions" / provider / "permission_events.jsonl"
        ).read_text().splitlines()]
        assert external[-1]["to_state"] == "OUTPUT_PACKAGED"
        assert Path(archive).is_file()
