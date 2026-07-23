from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from certvic.cvpr.smoke_input_builder import (
    SmokeInputBuilderError,
    build_smoke_bundle,
)
from local_operator.pre_smoke_operator import (
    ACTIVE_PROFILE,
    PROVIDERS,
    PreSmokeOperatorError,
    create_00b_matrix,
    generate_pre_smoke_permissions,
    matrix_payload,
    operator_status,
    verify_00b_matrix,
    verify_authenticated_runtime_state,
    verify_pre_smoke_permissions,
    verify_real_smoke_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
HEX = "a" * 64


def _matrix_rows() -> list[dict[str, object]]:
    rows = []
    for index, provider in enumerate(PROVIDERS):
        digest = f"{index + 1:064x}"
        rows.append({
            "provider": provider,
            "passed": True,
            "runtime_profile_id": ACTIVE_PROFILE,
            "runtime_profile_hash": HEX,
            "snapshot_content_identity_sha256": f"{index + 4:064x}",
            "snapshot_root_hash": f"{index + 7:064x}",
            "model_id": f"model-{provider}",
            "model_revision": "revision",
            "processor_model_contract": "contract",
            "runtime_record": f"data/runtime/00B_{provider}_snapshot.json",
            "runtime_record_sha256": digest,
            "source_archive": (
                f"data/runtime/00B_{provider}_snapshot_bundle.zip"
            ),
            "source_archive_sha256": f"{index + 10:064x}",
            "source_archive_size": 123 + index,
            "authenticated_member": f"00B_{provider}_snapshot.json",
            "authenticated_member_sha256": digest,
            "paper_evidence": False,
        })
    return rows


def _authenticated_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    common = project / "kagglefiles/inputs/00_COMMON"
    runtime = project / "data/runtime"
    common.mkdir(parents=True)
    runtime.mkdir(parents=True)
    shutil.copy2(
        ROOT / "kagglefiles/inputs/00_COMMON/certvic_code_bundle.zip",
        common / "certvic_code_bundle.zip",
    )
    shutil.copy2(
        ROOT / "kagglefiles/.IMPORTED_RETURNS.json",
        project / "kagglefiles/.IMPORTED_RETURNS.json",
    )
    names = ["00A_environment", *(
        f"00B_{provider}_snapshot" for provider in PROVIDERS
    )]
    for name in names:
        shutil.copy2(
            ROOT / f"data/runtime/{name}.json",
            runtime / f"{name}.json",
        )
        shutil.copy2(
            ROOT / f"data/runtime/{name}_bundle.zip",
            runtime / f"{name}_bundle.zip",
        )
    return project


def _real_tasks(project: Path) -> Path:
    smoke = project / "local_inputs/smoke"
    assets = smoke / "assets"
    assets.mkdir(parents=True)
    rows = []
    for index in range(2):
        original = assets / f"item-{index}-original.png"
        edited = assets / f"item-{index}-edited.png"
        original.write_bytes(b"real-original-" + bytes([index]))
        edited.write_bytes(b"real-edited-" + bytes([index]))
        rows.append({
            "item_id": f"licensed-item-{index}",
            "original_image_path": str(original),
            "edited_image_path": str(edited),
            "license_eligible": True,
            "license_id": f"LICENSE-RECORD-{index}",
            "prompt_template_hash": "b" * 64,
            "parser_version": "certvic-parser-v1",
            "run_contract_hash": "c" * 64,
            "synthetic_fixture": False,
            "paper_evidence": False,
        })
    manifest = smoke / "real_smoke_tasks.jsonl"
    manifest.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return manifest


def test_exact_three_provider_matrix_records_provenance() -> None:
    result = matrix_payload(_matrix_rows())

    assert result["providers"] == list(PROVIDERS)
    assert len(result["rows"]) == 3
    assert result["paper_evidence"] is False
    assert result["source_model_snapshot_archives_required_locally"] is False
    assert all(row["source_archive_sha256"] for row in result["rows"])
    assert all(row["authenticated_member_sha256"] for row in result["rows"])


@pytest.mark.parametrize("mutation", ["missing", "wrong", "duplicate"])
def test_wrong_missing_or_duplicate_provider_is_rejected(mutation: str) -> None:
    rows = _matrix_rows()
    if mutation == "missing":
        rows.pop()
    elif mutation == "wrong":
        rows[-1]["provider"] = "unexpected_provider"
    else:
        rows[-1]["provider"] = rows[0]["provider"]

    with pytest.raises(PreSmokeOperatorError, match="provider"):
        matrix_payload(rows)


def test_failed_00b_is_rejected() -> None:
    rows = _matrix_rows()
    rows[0]["passed"] = False

    with pytest.raises(PreSmokeOperatorError, match="failed 00B"):
        matrix_payload(rows)


def test_mixed_runtime_profiles_are_rejected() -> None:
    rows = _matrix_rows()
    rows[1]["runtime_profile_id"] = "kaggle_cp310_legacy"

    with pytest.raises(PreSmokeOperatorError, match="runtime profile"):
        matrix_payload(rows)


def test_matrix_reconciliation_is_idempotent_and_rejects_conflict(
    tmp_path: Path,
) -> None:
    project = _authenticated_project(tmp_path)
    first = create_00b_matrix(project)
    second = create_00b_matrix(project)

    assert first["created"] is True
    assert second["idempotent"] is True
    assert first["matrix_identity_sha256"] == second["matrix_identity_sha256"]
    path = project / "data/runtime/00B_matrix_complete.json"
    path.write_text('{"conflict":true}\n', encoding="utf-8")
    with pytest.raises(PreSmokeOperatorError, match="conflicting"):
        create_00b_matrix(project)


def test_live_authenticated_returns_are_exact_and_need_no_model_zips() -> None:
    state = verify_authenticated_runtime_state(ROOT)
    matrix = verify_00b_matrix(ROOT)

    assert state["runtime_profile_id"] == ACTIVE_PROFILE
    assert set(state["snapshots"]) == set(PROVIDERS)
    assert matrix["source_model_snapshot_archives_required_locally"] is False
    for provider, row in state["snapshots"].items():
        assert row["runtime_record_sha256"] == row["authenticated_member_sha256"]
        assert "snapshot_bundle.zip" in row["source_archive"]
        assert provider in row["source_archive"]


def test_placeholder_and_synthetic_smoke_inputs_are_rejected(
    tmp_path: Path,
) -> None:
    template = ROOT / "local_inputs/smoke/real_smoke_tasks.template.jsonl"
    with pytest.raises(SmokeInputBuilderError, match="licensing"):
        build_smoke_bundle(template, output=tmp_path / "placeholder.zip")

    asset = tmp_path / "fixture.png"
    asset.write_bytes(b"synthetic")
    rows = [{
        "item_id": f"fixture-{index}",
        "original_image_path": str(asset),
        "edited_image_path": str(asset),
        "license_eligible": True,
        "license_id": "PROJECT-FIXTURE",
        "prompt_template_hash": HEX,
        "parser_version": "parser",
        "run_contract_hash": HEX,
        "synthetic_fixture": True,
    } for index in range(2)]
    manifest = tmp_path / "synthetic.jsonl"
    manifest.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    with pytest.raises(SmokeInputBuilderError, match="synthetic"):
        build_smoke_bundle(manifest, output=tmp_path / "synthetic.zip")


def test_absent_real_items_report_explicit_blocked_boundary(
    tmp_path: Path,
) -> None:
    project = _authenticated_project(tmp_path)
    create_00b_matrix(project)

    status = operator_status(project)

    assert status["local_failures"] == 0
    assert status["operator_state"] == "READY_FOR_REAL_SMOKE_INPUTS"
    assert status["preparation_status"] == (
        "BLOCKED_BY_TWO_REAL_LICENSED_SMOKE_ITEMS"
    )
    assert status["00C2"] == "NOT_AUTHORIZED"
    assert status["paper_evidence"] is False
    assert not (
        project / "data/runtime/pre_smoke_matrix_authorization.json"
    ).exists()


def test_valid_two_item_smoke_builds_and_verifies(tmp_path: Path) -> None:
    project = _authenticated_project(tmp_path)
    create_00b_matrix(project)
    tasks = _real_tasks(project)
    output = (
        project
        / "kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip"
    )

    build_smoke_bundle(tasks, output=output)
    verified = verify_real_smoke_bundle(project)

    assert len(verified["rows"]) == 2
    assert verified["paper_evidence"] is False


def test_permissions_bind_all_parents_and_keep_science_unauthorized(
    tmp_path: Path,
) -> None:
    project = _authenticated_project(tmp_path)
    matrix = create_00b_matrix(project)
    tasks = _real_tasks(project)
    output = (
        project
        / "kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip"
    )
    build_smoke_bundle(tasks, output=output)

    generated = generate_pre_smoke_permissions(project)
    replay = verify_pre_smoke_permissions(project)

    assert generated == replay
    assert generated["providers"] == list(PROVIDERS)
    assert generated["execution_allowed"] is True
    assert generated["scientific_execution_allowed"] is False
    assert generated["confirmatory_execution_allowed"] is False
    assert generated["main_execution_allowed"] is False
    assert generated["coco_execution_allowed"] is False
    aggregate = json.loads(
        (
            project / "data/runtime/pre_smoke_provider_permissions.json"
        ).read_text(encoding="utf-8")
    )
    children = aggregate["permissions"]
    assert len({child["one_run_nonce"] for child in children.values()}) == 3
    assert all(
        child["runtime_class"] == "REAL_MODEL_SMOKE"
        and child["model_registry_hash"] == matrix["matrix_identity_sha256"]
        and child["paper_evidence"] is False
        for child in children.values()
    )
    status = operator_status(project)
    assert status["operator_state"] == "READY_FOR_00C2"
    assert status["paper_evidence"] is False


def test_status_never_reports_ready_with_partial_permissions(
    tmp_path: Path,
) -> None:
    project = _authenticated_project(tmp_path)
    create_00b_matrix(project)
    tasks = _real_tasks(project)
    output = (
        project
        / "kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip"
    )
    build_smoke_bundle(tasks, output=output)
    partial = project / "data/runtime/pre_smoke_provider_permissions.json"
    partial.write_text("{}\n", encoding="utf-8")

    status = operator_status(project)

    assert status["operator_state"] == "BLOCKED"
    assert status["00C2"] == "NOT_AUTHORIZED"
    assert status["local_failures"] == 1


def test_matrix_hash_or_paper_evidence_tampering_is_rejected() -> None:
    rows = _matrix_rows()
    tampered_hash = copy.deepcopy(rows)
    tampered_hash[0]["source_archive_sha256"] = "not-a-hash"
    with pytest.raises(PreSmokeOperatorError, match="hashes are invalid"):
        matrix_payload(tampered_hash)

    tampered_evidence = copy.deepcopy(rows)
    tampered_evidence[0]["paper_evidence"] = True
    with pytest.raises(PreSmokeOperatorError, match="paper evidence"):
        matrix_payload(tampered_evidence)
