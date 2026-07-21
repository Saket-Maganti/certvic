from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from certvic.cvpr.after_runs import process
from certvic.cvpr.contracts import (
    EvidenceClass,
    OutputContract,
    load_yaml,
    validate_evidence_row,
    validate_model_registry,
    validate_study_config,
)
from certvic.cvpr.notebook_builder import NOTEBOOKS
from certvic.cvpr.package_run import package
from certvic.cvpr.statistics import clopper_pearson_upper, exact_mcnemar, holm_adjust
from certvic.cvpr.transactional import TransactionError, promote_jsonl, read_jsonl, shard_resume_state
from certvic.cvpr.worker import run_shard
from certvic.eval.parse import parse_answer_record


ROOT = Path(__file__).resolve().parents[1]


REQUIRED = (
    "docs/CERTVIC_CANONICAL_PROJECT_INDEX.md",
    "configs/models/certvic_cvpr_model_registry.yaml",
    "configs/studies/specificity_confirmatory_cvpr.yaml",
    "configs/studies/specificity_confirmatory_exclusions.json",
    "configs/studies/main_study_cvpr.yaml",
    "configs/studies/second_domain_cvpr.yaml",
    "docs/methodology/CERTVIC_CVPR_SCIENTIFIC_PROTOCOL.md",
    "docs/methodology/CERTVIC_CVPR_STATISTICAL_ANALYSIS_PLAN.md",
    "docs/methodology/CERTVIC_CVPR_HUMAN_REVIEW_PROTOCOL.md",
    "docs/methodology/CERTVIC_CERTIFICATION_TERMINOLOGY.md",
    "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md",
    "docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md",
    "docs/execution/CERTVIC_KAGGLE_T4X2_NOTEBOOK_INDEX.md",
    "docs/execution/CERTVIC_FAILURE_RESUME_AND_RECOVERY.md",
    "docs/execution/CERTVIC_MODEL_REVISION_LOCK_GUIDE.md",
    "reports/cvpr_pre_execution/CERTVIC_CVPR_READINESS_AUDIT.md",
    "reports/cvpr_pre_execution/CERTVIC_CVPR_EVIDENCE_LEDGER.csv",
    "reports/cvpr_pre_execution/CERTVIC_CVPR_GATE_LEDGER.csv",
    "reports/cvpr_pre_execution/CERTVIC_POWER_PLAN.json",
    "reports/cvpr_pre_execution/CERTVIC_CVPR_BLOCKER_REGISTER.csv",
    "reports/cvpr_pre_execution/CERTVIC_CHANGE_MANIFEST.csv",
    "reports/cvpr_pre_execution/CERTVIC_COMMAND_LEDGER.csv",
    "reports/cvpr_pre_execution/CERTVIC_FINAL_VALIDATION.md",
    "reports/cvpr_pre_execution/CERTVIC_CVPR_PRE_EXECUTION_HANDOFF.md",
    "release/CERTVIC_CVPR_RELEASE_MANIFEST.md",
    "release/CERTVIC_DATA_AND_LICENSE_MATRIX.csv",
    "release/CERTVIC_REPRODUCIBILITY_CHECKLIST.md",
    "paper_cvpr/main.tex",
)


def test_required_cvpr_surfaces_exist_and_are_nonempty() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    empty = [path for path in REQUIRED if (ROOT / path).is_file() and not (ROOT / path).stat().st_size]
    assert not missing
    assert not empty


def test_builder_runs_from_scripts_path_and_is_deterministic() -> None:
    manifest = ROOT / "notebooks/kaggle/cvpr/notebook_manifest.json"
    before = manifest.read_bytes()
    result = subprocess.run(
        [sys.executable, "scripts/build_cvpr_pre_execution.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert manifest.read_bytes() == before


def test_model_registry_is_complete_but_execution_fails_closed_on_revisions() -> None:
    registry = load_yaml(ROOT / "configs/models/certvic_cvpr_model_registry.yaml")
    assert validate_model_registry(registry, for_execution=False)["passed"] is True
    execution = validate_model_registry(registry, for_execution=True)
    assert execution["passed"] is False
    assert len([
        error for error in execution["errors"] if "snapshot_manifest_sha256" in error
    ]) == 3


def test_study_configs_preserve_pre_execution_boundary() -> None:
    for name in ("specificity_confirmatory_cvpr", "main_study_cvpr", "second_domain_cvpr"):
        config = load_yaml(ROOT / f"configs/studies/{name}.yaml")
        result = validate_study_config(config, require_frozen=True)
        assert result["passed"] is True
        assert config["paper_evidence"] is False
        assert config["execution_allowed"] is False
    specificity = load_yaml(ROOT / "configs/studies/specificity_confirmatory_cvpr.yaml")
    assert specificity["prospective"] is True
    assert specificity["outcome_unseen"] is True
    assert specificity["design"]["primary_items"] == 240
    exclusions = json.loads(
        (ROOT / "configs/studies/specificity_confirmatory_exclusions.json").read_text()
    )
    assert len(exclusions["item_ids"]) == 94
    assert len(exclusions["source_image_ids"]) == 94
    assert exclusions["paper_evidence"] is False


def test_evidence_vocabulary_and_promotion_guards() -> None:
    assert EvidenceClass.RETROSPECTIVE_SENSITIVITY_ONLY.value
    invalid = {"evidence_class": "PLANNED_NOT_EXECUTED", "paper_evidence": True}
    assert validate_evidence_row(invalid)
    observed = {"evidence_class": "REAL_OBSERVED_EVIDENCE", "paper_evidence": False,
                "observed": True, "sha256": "a" * 64}
    assert validate_evidence_row(observed) == []


def test_parser_record_retains_raw_status_and_version() -> None:
    ok = parse_answer_record("Yes.", "yes_no")
    assert ok["raw_response"] == "Yes."
    assert ok["parse_status"] == "PARSE_OK"
    assert ok["parser_version"] == "certvic.parse.v2"
    assert parse_answer_record("yes no", "yes_no")["parse_status"] == "AMBIGUOUS"
    assert parse_answer_record("I cannot answer", "yes_no")["parse_status"] == "REFUSAL"
    assert parse_answer_record("", "yes_no")["parse_status"] == "EMPTY"


def _row(item_id: str, variant: str, *, revision: str = "a" * 40) -> dict:
    return {
        "item_id": item_id,
        "variant": variant,
        "raw_response": "yes",
        "parsed_response": "yes",
        "parse_status": "PARSE_OK",
        "provider": "qwen2_5_vl_7b",
        "model_id": "Qwen/Qwen2.5-VL-7B-Instruct",
        "model_commit": revision,
        "processor_commit": "b" * 40,
        "prompt_hash": "c" * 64,
        "image_hash": "d" * 64,
        "task_hash": "e" * 64,
        "code_bundle_hash": "f" * 64,
        "seed": 1,
        "generation_parameters": {"do_sample": False},
        "shard": 0,
        "timestamp": "2026-07-13T00:00:00Z",
        "run_tag": "specificity_confirmatory_cvpr_v1",
        "parser_version": "certvic.parse.v2",
    }


def _contract() -> OutputContract:
    return OutputContract(
        provider="qwen2_5_vl_7b",
        run_tag="specificity_confirmatory_cvpr_v1",
        model_commit="a" * 40,
        processor_commit="b" * 40,
        item_ids=("i1",),
        bundle_sha256="f" * 64,
    )


def test_transactional_import_is_atomic_idempotent_and_conflict_refusing(tmp_path: Path) -> None:
    rows = [_row("i1", "original"), _row("i1", "edited")]
    destination = tmp_path / "canonical.jsonl"
    assert promote_jsonl(rows, destination, _contract())["status"] == "PROMOTED"
    assert promote_jsonl(rows, destination, _contract())["status"] == "IDEMPOTENT"
    changed = [dict(row) for row in rows]
    changed[0]["raw_response"] = "no"
    with pytest.raises(TransactionError, match="conflicting"):
        promote_jsonl(changed, destination, _contract())


@pytest.mark.parametrize(
    "defect",
    ["duplicate", "wrong_revision", "missing_variant", "wrong_image_hash"],
)
def test_transactional_import_rejects_structural_defects(tmp_path: Path, defect: str) -> None:
    rows = [_row("i1", "original"), _row("i1", "edited")]
    if defect == "duplicate":
        rows[1]["variant"] = "original"
    elif defect == "wrong_revision":
        rows[0]["model_commit"] = "9" * 40
    elif defect == "missing_variant":
        rows.pop()
    else:
        rows[0]["image_hash"] = "bad"
    with pytest.raises(TransactionError):
        promote_jsonl(rows, tmp_path / "bad.jsonl", _contract())


def test_corrupt_final_line_and_resume_state_are_explicit(tmp_path: Path) -> None:
    path = tmp_path / "shard.jsonl"
    path.write_text(json.dumps(_row("i1", "original")) + "\n{", encoding="utf-8")
    with pytest.raises(TransactionError, match="corrupt final line"):
        read_jsonl(path)
    state = shard_resume_state([path], _contract())
    assert state["corrupt"]
    assert len(state["missing"]) == 2


def test_exact_statistics_known_values_and_multiplicity_helpers() -> None:
    assert clopper_pearson_upper(0, 29) < 0.10
    assert clopper_pearson_upper(0, 28) > 0.10
    assert exact_mcnemar(0, 0) == 1.0
    adjusted = holm_adjust([0.01, 0.04, 0.2])
    assert adjusted == sorted(adjusted)
    assert adjusted[0] == pytest.approx(0.03)


def test_after_runs_refuses_current_unpinned_and_blocked_state(tmp_path: Path) -> None:
    result = process(tmp_path, "specificity_confirmatory_cvpr", project_root=ROOT)
    assert result["status"] == "BLOCKED_PRECONDITIONS"
    assert result["paper_evidence"] is False
    assert any("snapshot_manifest_sha256" in blocker for blocker in result["blockers"])


def test_worker_mock_runtime_exercises_sharding_resume_and_output_contract(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks.jsonl"
    task_rows = [
        {"item_id": f"i{index}", "original_image_path": f"original-{index}.png",
         "edited_image_path": f"edited-{index}.png", "question": "Is the object present?",
         "answer_format": "yes_no", "mock_raw_response": "yes"}
        for index in range(4)
    ]
    tasks.write_text("".join(json.dumps(row) + "\n" for row in task_rows), encoding="utf-8")
    config = tmp_path / "runtime.json"
    output_dir = tmp_path / "output"
    config.write_text(json.dumps({
        "provider": "qwen2_5_vl_7b", "model_id": "mock-only",
        "model_commit": "a" * 40, "processor_commit": "b" * 40,
        "run_tag": "specificity_confirmatory_cvpr_v1", "task_manifest": str(tasks),
        "output_dir": str(output_dir), "code_bundle_hash": "f" * 64, "seed": 12013,
        "generation_parameters": {"do_sample": False, "max_new_tokens": 16},
    }), encoding="utf-8")
    first = [run_shard(config, shard=shard, num_shards=2, mock_runtime=True) for shard in range(2)]
    assert sum(result["rows"] for result in first) == 8
    second = [run_shard(config, shard=shard, num_shards=2, mock_runtime=True) for shard in range(2)]
    assert {result["status"] for result in second} == {"SHARD_ALREADY_COMPLETE"}
    rows = [row for path in output_dir.glob("*.complete.jsonl") for row in read_jsonl(path)]
    assert len(rows) == 8
    assert all(row["parse_status"] == "PARSE_OK" for row in rows)
    packaged = package(config, expected_shards=2)
    assert packaged["status"] == "PACKAGED"
    assert packaged["rows"] == 8
    assert Path(str(packaged["zip"])).is_file()
    assert package(config, expected_shards=2)["zip_sha256"] == packaged["zip_sha256"]


def test_cvpr_notebooks_are_clean_static_contracts() -> None:
    notebook_dir = ROOT / "notebooks/kaggle/cvpr"
    assert {path.name for path in notebook_dir.glob("*.ipynb")} == set(NOTEBOOKS)
    for name in NOTEBOOKS:
        value = json.loads((notebook_dir / name).read_text(encoding="utf-8"))
        assert value["nbformat"] == 4
        assert all(cell.get("execution_count") is None for cell in value["cells"] if cell["cell_type"] == "code")
        assert all(not cell.get("outputs") for cell in value["cells"] if cell["cell_type"] == "code")
        text = json.dumps(value)
        stage = NOTEBOOKS[name][0]
        if stage in {"code_smoke", "snapshot_smoke", "real_model_smoke"}:
            required = ["materialize_dataset", "CANONICAL_RETURN_ZIP", "paper_evidence=false"]
            assert "REQUIRED_USER_FILL" not in text
        else:
            required = ["shard_for", "shard_complete", "single_gpu_fallback",
                        "runtime_manifest.json", "failure_report.json", "hash_manifest.json",
                        "REQUIRED_USER_FILL", "CUDA_VISIBLE_DEVICES"]
        for token in required:
            assert token in text, (name, token)
        assert "/Users/" not in text
        assert "paper_evidence=false" in text


def test_master_plan_preserves_scientific_boundaries_and_execution_types() -> None:
    text = (ROOT / "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md").read_text(encoding="utf-8")
    for token in (
        "CVPR_PRE_EXECUTION_READY",
        "paper_evidence=false",
        "12/94",
        "retrospective sensitivity",
        "CPU_LOCAL",
        "CPU_KAGGLE",
        "GPU_KAGGLE_T4X2",
        "GPU_KAGGLE_SINGLE_FALLBACK",
        "HUMAN_REVIEW",
        "MANUAL_DATA_PROVISION",
        "POST_RUN_CPU_ANALYSIS",
        "Final paper trigger",
    ):
        assert token in text
