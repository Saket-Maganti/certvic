from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
import yaml

from certvic.cvpr.detectability_gate import evaluate as evaluate_detectability
from certvic.cvpr.import_transaction import (
    consumed_nonces,
    load_journal,
    recover_transaction,
    transactional_import,
)
from certvic.cvpr.kaggle_session_simulator import PROVIDERS, simulate
from certvic.cvpr.notebook_builder import build_suite
from certvic.cvpr.notebook_permission_binding import (
    NotebookPermissionBindingError,
    assert_runtime_binding,
    derive_permission_binding,
)
from certvic.cvpr.reconcile_provider_permissions import (
    ProviderPermissionError,
    derive_provider_permission,
    reconcile_provider_permissions,
)
from certvic.cvpr.smoke_artifacts import (
    SMOKE_MEMBERS,
    read_smoke_archive,
    write_environment_artifacts,
    write_snapshot_artifacts,
)
from certvic.cvpr.smoke_gate import require_scientific_run_gate
from certvic.cvpr.smoke_handoff import run_handoff
from certvic.cvpr.synthetic_smoke import run as run_synthetic_smoke
from certvic.cvpr.transactional import read_jsonl


def test_canonical_smoke_is_directly_consumed_and_synthetic_cannot_authorize(tmp_path: Path) -> None:
    root = tmp_path / "smoke"
    result = run_synthetic_smoke(root)
    assert result["status"] == "SYNTHETIC_SMOKE_PASSED"
    for provider in PROVIDERS:
        archive = root / f"00C2_{provider}_real_model_smoke.zip"
        with zipfile.ZipFile(archive) as handle:
            assert set(handle.namelist()) == set(SMOKE_MEMBERS)
        loaded = read_smoke_archive(archive)
        assert loaded["authorization_proof"]["runtime_class"] == "SYNTHETIC_SMOKE"
        assert loaded["authorization_proof"]["synthetic_fixture"] is True
        assert loaded["runtime"]["expected_shards"] == 1
        assert loaded["runtime"]["produced_shards"] == 1
        assert loaded["runtime"]["task_bundle_hash"] == loaded["task_bundle"]["bundle_hash"]
    with pytest.raises(ValueError, match="synthetic smoke cannot authorize"):
        require_scientific_run_gate(result["gate_json"], list(PROVIDERS))


def test_notebooks_use_active_bindings_provider_permissions_and_one_smoke_shard(
    tmp_path: Path,
) -> None:
    build_suite(tmp_path)
    for number in ("02_", "03_", "04_", "11_", "12_", "13_", "21_", "22_", "23_"):
        path = next(tmp_path.glob(number + "*.ipynb"))
        text = path.read_text(encoding="utf-8")
        assert "PERMISSION_INPUT_PATHS =" not in text
        assert "derive_permission_binding(globals())" in text
        assert "PROVIDER_PERMISSION" in text and "provider_permission_events_path" in text
        assert text.index("derive_permission_binding(globals())") < text.index("hardware_report()")
        assert text.index("derive_permission_binding(globals())") < text.index(
            "pathlib.Path(OUTPUT_DIR).mkdir"
        )
    for provider in ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"):
        notebook = json.loads(
            (tmp_path / f"00C2_{provider}_real_model_two_item_smoke.ipynb").read_text()
        )
        smoke = "".join("".join(cell["source"]) for cell in notebook["cells"])
        assert '"--num-shards", "1"' in smoke
        for field in ("task_bundle_root", "task_bundle_manifest", "task_bundle_hash"):
            assert field in smoke
        assert f"00C2_{provider}_real_model_smoke.zip" in smoke
        assert "REQUIRED_USER_FILL" not in smoke


def test_active_permission_binding_detects_worker_drift(tmp_path: Path) -> None:
    variables: dict[str, object] = {
        "SCHEMA_VERSION": "certvic.cvpr.output.v2",
        "PROVIDER": "qwen2_5_vl_7b",
        "RUN_TAG": "confirmatory_v1",
        "TASK_BUNDLE_ROOT": str(tmp_path / "bundle"),
    }
    for name in (
        "TASK_BUNDLE_MANIFEST",
        "FINAL_TASK_FREEZE",
        "FINAL_REVIEW_LEDGER",
        "SMOKE_GATE_JSON",
        "ENVIRONMENT_LOCK",
        "MODEL_REGISTRY",
        "SNAPSHOT_MANIFEST",
        "CODE_BUNDLE",
        "STUDY_CONFIG",
    ):
        path = tmp_path / f"{name}.json"
        path.write_text(name, encoding="utf-8")
        variables[name] = str(path)
    binding = derive_permission_binding(variables)
    runtime = {
        **binding["input_paths"],
        **binding["scalars"],
        "final_task_freeze": binding["input_paths"]["freeze_manifest"],
        "final_review_ledger": binding["input_paths"]["final_review"],
        "smoke_gate_json": binding["input_paths"]["smoke_gate"],
        "code_bundle": binding["input_paths"]["code_bundle"],
        "output_schema": binding["scalars"]["schema_version"],
    }
    assert assert_runtime_binding(binding, runtime)["status"] == "ACTIVE_RUNTIME_BINDING_VERIFIED"
    runtime["snapshot_manifest"] = str(tmp_path / "different.json")
    with pytest.raises(NotebookPermissionBindingError, match="differs"):
        assert_runtime_binding(binding, runtime)


def test_provider_reconciliation_failure_matrix_and_transaction_recovery(tmp_path: Path) -> None:
    simulation_root = tmp_path / "simulation"
    result = simulate(simulation_root)
    assert result["status"] == "KAGGLE_MULTI_SESSION_SIMULATION_PASSED"
    matrix_path = simulation_root / "matrix_authorization.json"
    archives = {provider: Path(path) for provider, path in result["returned_archives"].items()}
    with pytest.raises(ProviderPermissionError, match="incomplete"):
        reconcile_provider_permissions(matrix_path, {PROVIDERS[0]: archives[PROVIDERS[0]]})
    duplicate = dict(archives)
    duplicate[PROVIDERS[1]] = archives[PROVIDERS[0]]
    with pytest.raises(ProviderPermissionError):
        reconcile_provider_permissions(matrix_path, duplicate)

    child = json.loads(
        (simulation_root / "isolated_sessions" / PROVIDERS[0] / "provider_permission.json").read_text()
    )
    smoke = {
        "provider": child["provider"],
        "runtime_class": "REAL_MODEL_SMOKE",
        "synthetic_fixture": False,
        "model_id": child["model_id"],
        "model_revision": child["model_revision"],
        "snapshot_manifest_hash": "f" * 64,
        "snapshot_root_hash": child["snapshot_root_hash"],
        "environment_manifest_hash": child["environment_hash"],
        "code_hash": child["code_hash"],
        "parser_version": child["parser_version"],
        "processor_model_contract": child["processor_model_contract"],
    }
    with pytest.raises(ProviderPermissionError, match="snapshot_manifest_hash"):
        derive_provider_permission(
            matrix_path,
            provider=child["provider"],
            model_id=child["model_id"],
            model_revision=child["model_revision"],
            snapshot_hash=child["snapshot_hash"],
            snapshot_root_hash=child["snapshot_root_hash"],
            environment_hash=child["environment_hash"],
            task_bundle_hash=child["task_bundle_hash"],
            run_tag=child["run_tag"],
            code_hash=child["code_hash"],
            parser_version=child["parser_version"],
            processor_model_contract=child["processor_model_contract"],
            smoke_identity=smoke,
            active_input_hashes=child["active_input_hashes"],
            active_scalars=child["active_scalars"],
        )

    nonce_ledger = tmp_path / "recovery_nonces.json"
    destination = tmp_path / "recovered_import"
    with pytest.raises(RuntimeError, match="injected"):
        transactional_import(
            archives,
            matrix_authorization=matrix_path,
            destination=destination,
            nonce_ledger=nonce_ledger,
            fail_after_promotion=True,
        )
    journal_path = next((tmp_path / ".certvic_import_transactions").rglob("journal.json"))
    assert load_journal(journal_path)["state"] == "RECOVERY_REQUIRED"
    recovered = recover_transaction(journal_path, nonce_ledger=nonce_ledger)
    assert recovered["status"] == "COMMITTED_RECOVERED"
    assert consumed_nonces(nonce_ledger) == set(result_nonce for result_nonce in json.loads(
        (simulation_root / "provider_permission_reconciliation.json").read_text()
    )["provider_nonces"])
    idempotent = transactional_import(
        archives,
        matrix_authorization=matrix_path,
        destination=destination,
        nonce_ledger=nonce_ledger,
    )
    assert idempotent["status"] == "IDEMPOTENT"


def test_detectability_binds_exact_frozen_task_and_image_bytes(tmp_path: Path) -> None:
    smoke_root = tmp_path / "smoke"
    smoke = run_synthetic_smoke(smoke_root)
    manifest = Path(smoke["task_bundle_manifest"])
    bundle_root = manifest.parent
    qa = tmp_path / "qa.json"
    config = tmp_path / "study.json"
    qa.write_text('{"status":"PASS"}\n', encoding="utf-8")
    config.write_text('{"study":"synthetic_confirmatory"}\n', encoding="utf-8")
    result = evaluate_detectability(
        read_jsonl(bundle_root / "tasks.jsonl"),
        bundle_root=bundle_root,
        threshold=1.0,
        folds=2,
        bootstrap_samples=10,
        final_task_manifest=bundle_root / "tasks.jsonl",
        task_bundle_manifest=manifest,
        study_config=config,
        qa_manifest=qa,
    )
    exact = result["exact_byte_binding"]
    assert result["exact_byte_binding_verified"] is True
    assert exact["task_bundle_hash"] == json.loads(manifest.read_text())["bundle_hash"]
    assert len(exact["task_byte_bindings"]) == 2
    assert all(row["source_image_sha256"] and row["edited_image_sha256"] for row in exact[
        "task_byte_bindings"
    ])


def test_main_oversampling_preserves_final_quotas_and_has_rejection_buffer() -> None:
    config = yaml.safe_load(Path("configs/studies/main_study_cvpr.yaml").read_text())
    candidates = config["task_builder"]["family_candidate_targets"]
    primary = config["main_finalization"]["primary_family_targets"]
    reserve = config["main_finalization"]["reserve_family_targets"]
    policy = config["task_builder"]["candidate_oversampling"]
    assert sum(candidates.values()) == 1150
    assert sum(primary.values()) == 500 and sum(reserve.values()) == 125
    assert policy["overall_ratio"] >= 1.5
    for family, target in candidates.items():
        assert target >= 1.5 * (primary[family] + reserve[family])
        assert policy["projected_post_review"][family] >= primary[family] + reserve[family]


def test_one_click_handoff_discovers_canonical_names_without_renaming(tmp_path: Path) -> None:
    root = tmp_path / "smoke"
    result = run_synthetic_smoke(root)
    environment = json.loads((root / "00A_environment.json").read_text())
    write_environment_artifacts(root, environment)
    for provider in PROVIDERS:
        snapshot = json.loads((root / f"00B_{provider}_snapshot.json").read_text())
        write_snapshot_artifacts(root, provider, snapshot)
    registry = tmp_path / "registry.yaml"
    registry.write_text("primary_models:\n" + "".join(f"  - {p}\n" for p in PROVIDERS))
    lock = root / "00_environment_lock.json"
    handoff = run_handoff(
        root,
        smoke_contract=result["contract"],
        model_registry=registry,
        environment_lock=lock,
        out_dir=tmp_path / "handoff",
    )
    assert handoff["status"] == "SYNTHETIC_SMOKE_PASSED"
    assert handoff["next_authorization_command"] is None
    assert {Path(path).name for path in handoff["outputs"]} == {
        "REAL_MODEL_SMOKE_GATE.json",
        "REAL_MODEL_SMOKE_GATE.csv",
        "SMOKE_HANDOFF_REPORT.md",
    }
