from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from certvic.cvpr.candidate_selection import (
    SolverLimits,
    _exact_category_selection,
    balanced_select,
)
from certvic.cvpr.detectability_gate import evaluate as detectability_gate
from certvic.cvpr.notebook_builder import NOTEBOOKS, build_suite
from certvic.cvpr.permission_ledger import (
    PermissionLedgerError,
    claim,
    initialize,
    status,
    transition,
)
from certvic.cvpr.synthetic_smoke import run as run_synthetic_smoke
from certvic.cvpr.task_bundle import create_bundle, verify_bundle
from certvic.cvpr.task_schema import TASK_SCHEMA, with_task_hash


def _task(source: Path, edited: Path, index: int) -> dict[str, object]:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    return with_task_hash(
        {
            "task_schema_version": TASK_SCHEMA,
            "study": "synthetic_confirmatory",
            "task_id": f"portable-{index}",
            "item_id": f"portable-{index}",
            "source_dataset": "SYNTHETIC_FIXTURE",
            "source_split": "synthetic",
            "source_image_id": f"source-{index}",
            "source_image_path": str(source),
            "source_image_hash": digest,
            "original_image_path": str(source),
            "edited_image_path": str(edited),
            "license_status": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
            "question": "Is the fixture present?",
            "original_expected_answer": "yes",
            "edited_expected_answer": "yes",
            "required_change": False,
            "semantic_edit_family": None,
            "control_edit_family": "pixel_swap_control",
            "target_category": None,
            "queried_category": None,
            "queried_category_absent": False,
            "target_bbox": [1, 1, 2, 2],
            "target_mask_path": None,
            "target_mask_hash": None,
            "protected_scene_mask_path": None,
            "protected_scene_mask_hash": None,
            "attribute_name": None,
            "original_attribute": None,
            "edited_attribute": None,
            "attribute_transform": None,
            "original_attribute_verified": None,
            "edit_engine_policy": "synthetic_control_v1",
            "selected_engine": "pixel_swap",
            "engine_fallbacks": [],
            "engine_parameters": {},
            "seed": index,
            "primary_or_reserve": "primary",
            "strata": {},
            "review_status": "VALID_ADJUDICATED",
            "qa_status": "PASS",
            "paper_evidence": False,
        }
    )


def _tasks(root: Path, count: int = 12, *, detectable: bool = False) -> list[dict[str, object]]:
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(count):
        rng = np.random.default_rng(500 + index)
        array = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
        source, edited = root / f"source-{index}.png", root / f"edited-{index}.png"
        Image.fromarray(array, mode="RGB").save(source)
        changed = np.zeros_like(array) if detectable else array.copy()
        if not detectable:
            changed[0, 0], changed[0, 1] = changed[0, 1].copy(), changed[0, 0].copy()
        Image.fromarray(changed, mode="RGB").save(edited)
        rows.append(_task(source, edited, index))
    return rows


def test_portable_bundle_rebases_without_hash_changes(tmp_path: Path) -> None:
    local = tmp_path / "tmp/local_bundle"
    first = create_bundle(_tasks(tmp_path / "sources", 2), local)
    kaggle = tmp_path / "kaggle/input/certvic_bundle"
    shutil.copytree(local, kaggle)
    second = verify_bundle(kaggle, kaggle / "task_bundle_manifest.json")
    assert first["bundle_hash"] == second["bundle_hash"]
    assert first["task_hashes"] == second["task_hashes"]
    task_text = (kaggle / "tasks.jsonl").read_text()
    assert str(tmp_path) not in task_text and '"path_contract": "BUNDLE_RELATIVE"' in task_text


def test_permission_slots_are_atomic_consumable_and_nonretryable(tmp_path: Path) -> None:
    universe = "1" * 64
    ledger = tmp_path / "permission.json"
    initialize(
        ledger,
        study="study",
        providers=["p1", "p2", "p3"],
        run_tags="study_v1",
        task_universe_sha256=universe,
        output_schema="certvic.cvpr.output.v2",
        authorization_nonce="2" * 64,
    )
    with pytest.raises(PermissionLedgerError, match="wrong run tag"):
        claim(
            ledger,
            study="study",
            provider="p1",
            run_tag="wrong",
            notebook="n",
            task_universe_sha256=universe,
            permission_id="3" * 64,
            permission_signature="4" * 64,
        )
    claim(
        ledger,
        study="study",
        provider="p1",
        run_tag="study_v1",
        notebook="n",
        task_universe_sha256=universe,
        permission_id="3" * 64,
        permission_signature="4" * 64,
    )
    with pytest.raises(PermissionLedgerError, match="cannot be claimed"):
        claim(
            ledger,
            study="study",
            provider="p1",
            run_tag="study_v1",
            notebook="n2",
            task_universe_sha256=universe,
            permission_id="3" * 64,
            permission_signature="4" * 64,
        )
    for state in ("RUN_STARTED", "OUTPUT_PACKAGED", "IMPORTED", "CONSUMED"):
        transition(
            ledger,
            provider="p1",
            to_state=state,
            permission_id="3" * 64,
            permission_signature="4" * 64,
            run_tag="study_v1",
            actor="test",
        )
    assert status(ledger)["slots"]["p1"]["state"] == "CONSUMED"
    with pytest.raises(PermissionLedgerError, match="invalid/replayed"):
        transition(
            ledger,
            provider="p1",
            to_state="IMPORTED",
            permission_id="3" * 64,
            permission_signature="4" * 64,
            run_tag="study_v1",
            actor="replay",
        )
    retry = tmp_path / "permission_retry.json"
    initialize(
        retry,
        study="study",
        providers=["p1"],
        run_tags="study_retry_v2",
        task_universe_sha256=universe,
        output_schema="certvic.cvpr.output.v2",
        authorization_nonce="5" * 64,
    )
    assert status(retry)["slots"]["p1"]["state"] == "ISSUED"


def test_detectability_gate_passes_balanced_control_and_rejects_obvious_shift(
    tmp_path: Path,
) -> None:
    passed = detectability_gate(
        _tasks(tmp_path / "balanced"), threshold=0.80, folds=4, bootstrap_samples=50, seed=17
    )
    failed = detectability_gate(
        _tasks(tmp_path / "obvious", detectable=True),
        threshold=0.80,
        folds=4,
        bootstrap_samples=50,
        seed=17,
    )
    assert passed["status"] == "DETECTABILITY_GATE_PASS"
    assert failed["status"] == "DETECTABILITY_GATE_FAIL"
    assert passed["classifier"]["provider_outputs_used"] is False


def test_solver_resource_limit_uses_deterministic_optional_backend() -> None:
    rows = [
        {
            "source_id": f"s-{index}",
            "item_id": f"i-{index}",
            "category": "dog",
            "expected_answer": "yes" if index % 2 == 0 else "no",
            "target_size_stratum": "small",
            "target_position_stratum": "center",
            "placement_proposals": {"engine": [0, 0, 2, 2]},
        }
        for index in range(10)
    ]
    config = {
        "design": {
            "category_targets": {
                "dog": {
                    "primary": 4,
                    "reserve": 2,
                    "max_per_source": 1,
                    "expected_answer_polarities": {
                        "primary": {"yes": 2, "no": 2},
                        "reserve": {"yes": 1, "no": 1},
                    },
                    "size_strata": {"primary": {"small": 4}, "reserve": {"small": 2}},
                    "position_strata": {"primary": {"center": 4}, "reserve": {"center": 2}},
                }
            }
        }
    }
    limits = SolverLimits(max_states=1, timeout_seconds=1, progress_interval_states=1)
    first = balanced_select(rows, config, seed=9, solver_limits=limits)
    second = balanced_select(rows, config, seed=9, solver_limits=limits)
    assert first["status"] == "BALANCED_SELECTION_COMPLETE"
    assert first["selection_sha256"] == second["selection_sha256"]
    report = first["solution_report"]["categories"][0]
    assert report["fallback_used"] is True
    assert report["fallback_status"] == "FEASIBLE_SELECTION_FOUND"


def test_joint_exact_selection_solves_source_collision_that_greedy_misses() -> None:
    rows = [
        {
            "item_id": "removal-shared",
            "source_id": "shared",
            "semantic_edit_family": "object_removal",
        },
        {"item_id": "removal-free", "source_id": "free", "semantic_edit_family": "object_removal"},
        {
            "item_id": "insertion-only",
            "source_id": "shared",
            "semantic_edit_family": "object_insertion",
        },
    ]
    primary, reserve, report = _exact_category_selection(
        rows,
        {
            "primary": 2,
            "reserve": 0,
            "max_per_source": 1,
            "edit_family_balance": {"primary": {"object_removal": 1, "object_insertion": 1}},
        },
        seed=19,
    )
    assert report["feasible"] is True and reserve == []
    assert {row["item_id"] for row in primary} == {"removal-free", "insertion-only"}


def test_notebooks_verify_and_claim_before_output_creation(tmp_path: Path) -> None:
    build_suite(tmp_path)
    assert len(NOTEBOOKS) == 20
    for name, (stage, _) in NOTEBOOKS.items():
        text = (tmp_path / name).read_text()
        if stage in {"code_smoke", "snapshot_smoke", "real_model_smoke"}:
            assert "materialize_dataset" in text and "REQUIRED_USER_FILL" not in text
        else:
            assert "verify_bundle" in text and "TASK_BUNDLE_ROOT" in text
        if stage == "evaluation":
            assert "PERMISSION_INPUT_PATHS" in text and "expected_provider=PROVIDER" in text
            assert "claim_permission" in text
            assert text.index("claim_permission") < text.index("pathlib.Path(OUTPUT_DIR).mkdir")


def test_synthetic_smoke_uses_real_package_and_gate(tmp_path: Path) -> None:
    result = run_synthetic_smoke(tmp_path / "smoke")
    assert result["status"] == "SYNTHETIC_SMOKE_PASSED"
    assert result["strict_contract_verified"] is True
    for provider in result["providers"]:
        assert (tmp_path / "smoke" / f"00C2_{provider}_real_model_smoke.zip").is_file()
