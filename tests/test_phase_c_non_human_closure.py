from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest
import yaml

from certvic.cvpr.historical_outputs import HistoricalRestoreError, restore
from certvic.cvpr.non_human_continuation import (
    resume_after_confirmatory_returns,
    resume_after_human_review,
)
from certvic.cvpr.primary_endpoint import score_item, summarize_items, two_gate_certificate
from certvic.cvpr.protocol_authority import validate_authority


ROOT = Path(__file__).resolve().parents[1]


def _relevant(original: str, edited: str) -> dict:
    return score_item(
        original_gold="yes",
        edited_gold="no",
        original_prediction=original,
        edited_prediction=edited,
        required_change=True,
    )


def _irrelevant(original: str, edited: str) -> dict:
    return score_item(
        original_gold="yes",
        edited_gold="yes",
        original_prediction=original,
        edited_prediction=edited,
        required_change=False,
    )


def test_only_one_authoritative_prospective_protocol_and_v11_is_non_executable() -> None:
    result = validate_authority(ROOT)
    assert result["passed"] is True
    assert result["live_prospective_protocols"] == [
        "configs/studies/specificity_confirmatory_cvpr.yaml"
    ]
    old = yaml.safe_load((ROOT / "configs/certvic_v11_protocol.yaml").read_text())
    assert old["status"] == "DEPRECATED_NOT_FOR_EXECUTION"
    assert old["execution_allowed"] is False


def test_semantic_update_requires_both_correct_gold_change_and_change_to_edited_gold() -> None:
    success = _relevant(" YES ", "No")
    assert success["semantic_update_success"] is True
    assert success["model_answer_changes_to_edited_gold"] is True
    assert _relevant("yes", "yes")["semantic_update_success"] is False
    assert _relevant("no", "no")["semantic_update_success"] is False
    wrong_change = _relevant("yes", "maybe")
    assert wrong_change["semantic_update_success"] is False
    assert wrong_change["failure_taxonomy"] == "MODEL_CHANGED_TO_WRONG_ANSWER"


def test_never_updating_model_cannot_pass_responsiveness() -> None:
    rows = [_relevant("yes", "yes") for _ in range(120)]
    rows += [_irrelevant("yes", "yes") for _ in range(120)]
    summary = summarize_items(rows)
    assert summary["correct_semantic_update_rate"] == 0.0
    assert summary["raw_answer_change_rate"] == 0.0
    certificate = two_gate_certificate(
        rows,
        tau_update=0.5,
        tau_spurious=0.1,
        responsiveness_alpha=1 / 120,
        specificity_alpha=1 / 120,
    )
    assert certificate["responsiveness"]["pass"] is False
    assert certificate["specificity"]["pass"] is True
    assert certificate["decision"] == "FAIL"


def test_two_gate_certificate_requires_both_bounds() -> None:
    rows = [_relevant("yes", "no") for _ in range(120)]
    rows += [_irrelevant("yes", "yes") for _ in range(120)]
    certificate = two_gate_certificate(
        rows,
        tau_update=0.5,
        tau_spurious=0.1,
        responsiveness_alpha=1 / 120,
        specificity_alpha=1 / 120,
    )
    assert certificate["decision"] == "PASS"
    bad_specificity = rows[:120] + [_irrelevant("yes", "no") for _ in range(120)]
    assert two_gate_certificate(
        bad_specificity,
        tau_update=0.5,
        tau_spurious=0.1,
        responsiveness_alpha=1 / 120,
        specificity_alpha=1 / 120,
    )["decision"] == "FAIL"


def _manifest(path: Path, archive: Path) -> None:
    path.write_text(json.dumps({
        "historical_outputs": {
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "canonical_restore_root": "kaggleoutputs",
        }
    }))


def test_historical_restore_is_hash_bound_idempotent_and_refuses_conflicts(tmp_path: Path) -> None:
    archive = tmp_path / "historical.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("kaggleoutputs/run/result.json", b"{}\n")
    manifest = tmp_path / "manifest.json"
    _manifest(manifest, archive)
    project = tmp_path / "project"
    project.mkdir()
    first = restore(archive, manifest=manifest, project_root=project)
    assert first["files_created"] == 1
    second = restore(archive, manifest=manifest, project_root=project)
    assert second["identical_files_preserved"] == 1
    (project / "kaggleoutputs/run/result.json").write_text("conflict\n")
    with pytest.raises(HistoricalRestoreError, match="conflicting file"):
        restore(archive, manifest=manifest, project_root=project)


def test_historical_restore_rejects_traversal_and_duplicate_members(tmp_path: Path) -> None:
    for name, members in {
        "traversal.zip": [("kaggleoutputs/../escape", b"x")],
        "duplicate.zip": [("kaggleoutputs/a", b"x"), ("kaggleoutputs/a", b"x")],
    }.items():
        archive = tmp_path / name
        with zipfile.ZipFile(archive, "w") as handle:
            for member, payload in members:
                handle.writestr(member, payload)
        manifest = tmp_path / f"{name}.json"
        _manifest(manifest, archive)
        with pytest.raises(HistoricalRestoreError):
            restore(archive, manifest=manifest, project_root=tmp_path / "project")


def test_provisioning_notebooks_are_output_free_and_compile() -> None:
    root = ROOT / "notebooks/kaggle/provisioning"
    notebooks = sorted(root.glob("*.ipynb"))
    assert {path.name for path in notebooks} == {
        "00_build_certvic_linux_wheelhouse.ipynb",
        "00_build_certvic_cp312_wheelhouse.ipynb",
        "01_build_certvic_model_snapshot_parameterized.ipynb",
    }
    for path in notebooks:
        notebook = json.loads(path.read_text())
        assert notebook["metadata"]["certvic"]["paper_evidence"] is False
        for cell in notebook["cells"]:
            assert cell.get("outputs", []) == []
            assert cell.get("execution_count") is None
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), str(path), "exec")


@pytest.mark.parametrize(
    ("continuation", "runner"),
    [
        ("AFTER_HUMAN_REVIEW", resume_after_human_review),
        ("AFTER_CONFIRMATORY_RETURNS", resume_after_confirmatory_returns),
    ],
)
def test_phase_c_resume_commands_close_all_synthetic_routes(
    tmp_path: Path, continuation: str, runner
) -> None:
    result = runner(ROOT, synthetic_fixture=True, synthetic_out=tmp_path / continuation.lower())
    assert result["status"] == "SYNTHETIC_CONTINUATION_COMPLETE"
    assert result["continuation"] == continuation
    assert result["routes"] == ["coco", "confirmatory", "main"]
    assert result["synthetic_fixture"] is True
    assert result["paper_evidence"] is False
    assert result["human_reviewed"] is False
