"""Tests for the V2 modular edit engine and quality upgrades."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from certvic.edit import engines
from certvic.edit.generate_edits import EditGenerationError
from certvic.edit.quality_gates import is_all_black, is_all_white, sharpness_score, uniform_pixel_fraction
from certvic.io import read_jsonl, write_jsonl


def _make_image(path: Path, seed: int = 0) -> None:
    rng = np.random.RandomState(seed)
    arr = rng.randint(0, 255, size=(32, 32, 3), dtype=np.uint8)
    Image.fromarray(arr).save(path)


def _plan(tmp_path: Path, edit_type: str, edit_id: str = "e0") -> dict:
    img = tmp_path / f"{edit_id}_src.png"
    _make_image(img)
    return {
        "edit_id": edit_id,
        "source_id": "s0",
        "mask_id": "m0",
        "label_id": 8,
        "image_path": str(img),
        "bbox": [4, 4, 20, 20],
        "edit_type": edit_type,
        "required_change": "change" if edit_type in {"remove", "displace"} else "no_change",
        "task_family": "support_stability",
        "domain": "household",
        "planned_params": {"bbox": [4, 4, 20, 20], "offset_xy": [6, 0]},
        "evidence_status": "PLANNED_ONLY",
        "generation_status": "not_generated",
    }


def test_quality_metric_helpers():
    black = np.zeros((8, 8, 3), dtype=np.uint8)
    white = np.full((8, 8, 3), 255, dtype=np.uint8)
    assert is_all_black(black) and not is_all_white(black)
    assert is_all_white(white) and not is_all_black(white)
    assert uniform_pixel_fraction(black) == 1.0
    rng = np.random.RandomState(0).randint(0, 255, size=(8, 8, 3)).astype(np.uint8)
    assert sharpness_score(rng) > sharpness_score(black)


def test_available_engines_and_defaults():
    assert "simple_fill" in engines.available_engines()
    assert "diffusers_inpaint_optional" in engines.available_engines()
    assert engines.default_engine_for_edit_type("occlude") == "simple_occlude"


@pytest.mark.parametrize("edit_type,engine", [
    ("remove", "simple_fill"),
    ("occlude", "simple_occlude"),
    ("displace", "simple_displace"),
    ("control_irrelevant", "simple_control"),
    ("occlude", "composite_occluder"),
    ("remove", "no_op_debug"),
])
def test_generate_with_each_simple_engine(tmp_path, edit_type, engine):
    plan = _plan(tmp_path, edit_type)
    out_dir = tmp_path / "edits"
    record = engines.generate_with_engine(plan, out_dir, seed=0, index=0, quality_config={}, engine=engine)
    assert Path(record["edited_image_path"]).exists()
    assert record["evidence_status"] == "GENERATED_EDIT_ONLY"
    meta = record["replay_metadata"]
    assert meta["engine"] == engine
    assert meta["engine_version"] == engines.ENGINE_VERSION
    assert meta["source_image_sha256"]
    assert meta["edit_plan_hash"] and meta["mask_spec_hash"] and meta["generation_config_hash"]


def test_replay_metadata_is_deterministic(tmp_path):
    plan = _plan(tmp_path, "remove")
    out1 = tmp_path / "a"
    out2 = tmp_path / "b"
    r1 = engines.generate_with_engine(plan, out1, seed=7, index=0, quality_config={}, engine="simple_fill")
    r2 = engines.generate_with_engine(plan, out2, seed=7, index=0, quality_config={}, engine="simple_fill")
    assert r1["edited_sha256"] == r2["edited_sha256"]
    assert r1["replay_metadata"]["edit_plan_hash"] == r2["replay_metadata"]["edit_plan_hash"]


def test_diffusers_engine_is_disabled_without_weights(tmp_path):
    plan = _plan(tmp_path, "remove")
    with pytest.raises(EditGenerationError, match="disabled by default"):
        engines.generate_with_engine(plan, tmp_path / "d", seed=0, index=0, quality_config={}, engine="diffusers_inpaint_optional")


def test_no_overwrite_by_default(tmp_path):
    plan = _plan(tmp_path, "remove")
    out_dir = tmp_path / "edits"
    engines.generate_with_engine(plan, out_dir, seed=0, index=0, quality_config={}, engine="simple_fill")
    with pytest.raises(EditGenerationError, match="overwrite"):
        engines.generate_with_engine(plan, out_dir, seed=0, index=0, quality_config={}, engine="simple_fill")
    # overwrite=True is allowed.
    engines.generate_with_engine(plan, out_dir, seed=0, index=0, quality_config={}, engine="simple_fill", overwrite=True)


def test_batch_requires_max_items_unless_full_run(tmp_path):
    plan_path = tmp_path / "plan.jsonl"
    write_jsonl(plan_path, [_plan(tmp_path, "remove")])
    with pytest.raises(EditGenerationError, match="max_items is required"):
        engines.batch_generate(
            str(plan_path), str(tmp_path / "o"), str(tmp_path / "m.jsonl"),
            str(tmp_path / "r.jsonl"), str(tmp_path / "s.json"),
        )


def test_batch_generate_and_resume(tmp_path):
    plans = [_plan(tmp_path, "remove", edit_id=f"e{i}") for i in range(3)]
    plan_path = tmp_path / "plan.jsonl"
    write_jsonl(plan_path, plans)
    out_dir = tmp_path / "o"
    manifest = tmp_path / "m.jsonl"
    rejected = tmp_path / "r.jsonl"
    summary = tmp_path / "s.json"
    s1 = engines.batch_generate(str(plan_path), str(out_dir), str(manifest), str(rejected), str(summary), engine="simple_fill", max_items=2, seed=0)
    assert s1["generated"] == 2
    # Resume with more items: previously generated ones are skipped, not regenerated.
    s2 = engines.batch_generate(str(plan_path), str(out_dir), str(manifest), str(rejected), str(summary), engine="simple_fill", max_items=3, seed=0, resume=True)
    assert s2["generated"] == 3
    assert len(read_jsonl(manifest)) == 3


def test_uniform_warning_opt_in_does_not_regress_default(tmp_path):
    # A degenerate all-gray edit only warns when the gate is enabled in config.
    plan = _plan(tmp_path, "remove")
    rec_default = engines.generate_with_engine(plan, tmp_path / "x", seed=0, index=0, quality_config={}, engine="no_op_debug")
    # no_op leaves a random image: not uniform, no warning either way.
    assert "edited_uniform_fraction" in rec_default["quality"]
