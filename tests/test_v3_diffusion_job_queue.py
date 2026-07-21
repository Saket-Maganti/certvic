"""Tests for the V3 diffusion job queue / resume planner (prompt 04)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from certvic.edit import diffusion_resume, edit_generation_plan, job_queue
from certvic.hashing import sha256_file
from certvic.io import write_jsonl


def _edit_plan(tmp_path, n=12):
    rows = []
    types = ["remove", "occlude", "displace", "control_irrelevant"]
    for i in range(n):
        rows.append({
            "edit_id": f"e{i:03d}",
            "source_id": f"s{i % 5}",
            "mask_id": f"m{i}",
            "edit_type": types[i % len(types)],
            "task_family": "support_stability",
            "domain": "household",
        })
    path = tmp_path / "edit_plan.jsonl"
    write_jsonl(path, rows)
    return path, rows


def _make_edit_image(path: Path, text="img") -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return sha256_file(path)


# --- build -----------------------------------------------------------------

def test_build_queue_positive(tmp_path):
    plan, rows = _edit_plan(tmp_path)
    result = job_queue.build_queue(str(plan), num_shards=4, engine="diffusers_inpaint_optional")
    assert result["n_jobs"] == len(rows)
    e = result["entries"][0]
    assert e.evidence_status == "JOB_PLANNED_ONLY"
    assert e.status == "pending" and e.retry_count == 0
    assert e.expected_output_path.endswith(f"{e.edit_id}.png")
    assert e.config_hash is not None
    assert result["evidence_claims_made"] is False


def test_unknown_engine_rejected(tmp_path):
    plan, _ = _edit_plan(tmp_path)
    with pytest.raises(ValueError):
        job_queue.build_queue(str(plan), engine="not_an_engine")


def test_sharding_complete_and_no_overlap(tmp_path):
    plan, rows = _edit_plan(tmp_path, n=40)
    result = job_queue.build_queue(str(plan), num_shards=4)
    check = job_queue.verify_sharding(result["entries"], 4)
    assert check["complete"] is True and check["no_overlap"] is True
    assert check["covered"] == len(rows)
    assert sum(check["shard_sizes"].values()) == len(rows)


def test_next_shard_partitions(tmp_path):
    plan, rows = _edit_plan(tmp_path, n=40)
    result = job_queue.build_queue(str(plan), num_shards=4)
    qpath = tmp_path / "queue.jsonl"
    job_queue.write_queue(result, str(qpath))
    seen: set[str] = set()
    total = 0
    for s in range(4):
        shard = job_queue.next_shard(str(qpath), s, 4)
        ids = {e.edit_id for e in shard}
        assert seen.isdisjoint(ids)  # no overlap across shards
        seen |= ids
        total += len(shard)
    assert total == len(rows) and seen == {r["edit_id"] for r in rows}


def test_next_shard_bad_index(tmp_path):
    plan, _ = _edit_plan(tmp_path)
    result = job_queue.build_queue(str(plan), num_shards=4)
    qpath = tmp_path / "q.jsonl"
    job_queue.write_queue(result, str(qpath))
    with pytest.raises(ValueError):
        job_queue.next_shard(str(qpath), 5, 4)


# --- status: all seven statuses --------------------------------------------

def test_queue_status_all_statuses(tmp_path):
    plan, rows = _edit_plan(tmp_path, n=6)
    result = job_queue.build_queue(str(plan), num_shards=2)
    qpath = tmp_path / "queue.jsonl"
    job_queue.write_queue(result, str(qpath))
    entries = {e.edit_id: e for e in result["entries"]}
    edits_dir = tmp_path / "edits"

    generated = []
    # e000 -> generated (output present, hash matches)
    sha0 = _make_edit_image(Path(entries["e000"].expected_output_path))
    generated.append({"edit_id": "e000", "generation_status": "generated", "edited_image_path": entries["e000"].expected_output_path, "edited_sha256": sha0})
    # e001 -> duplicate
    sha1 = _make_edit_image(Path(entries["e001"].expected_output_path))
    generated.append({"edit_id": "e001", "generation_status": "generated", "edited_image_path": entries["e001"].expected_output_path, "edited_sha256": sha1, "duplicate_of": "e000"})
    # e002 -> missing_output (recorded but no file)
    generated.append({"edit_id": "e002", "generation_status": "generated", "edited_image_path": str(edits_dir / "missing_e002.png"), "edited_sha256": "deadbeef"})
    # e003 -> hash_mismatch (file present, wrong recorded hash)
    _make_edit_image(Path(entries["e003"].expected_output_path), "real")
    generated.append({"edit_id": "e003", "generation_status": "generated", "edited_image_path": entries["e003"].expected_output_path, "edited_sha256": "0" * 64})
    # e004 -> failed (generation_status != generated)
    generated.append({"edit_id": "e004", "generation_status": "error", "edited_image_path": entries["e004"].expected_output_path})
    # e005 -> rejected (in rejected manifest)
    gen_path = tmp_path / "generated.jsonl"
    rej_path = tmp_path / "rejected.jsonl"
    write_jsonl(gen_path, generated)
    write_jsonl(rej_path, [{"edit_id": "e005", "rejection_reason": "quality_fail"}])

    status = job_queue.queue_status(str(qpath), str(gen_path), rejected_path=str(rej_path))
    counts = status["status_counts"]
    assert counts["generated"] == 1
    assert counts["duplicate"] == 1
    assert counts["missing_output"] == 1
    assert counts["hash_mismatch"] == 1
    assert counts["failed"] == 1
    assert counts["rejected"] == 1
    assert counts["pending"] == 0
    assert status["all_done"] is False
    assert status["evidence_claims_made"] is False


def test_queue_status_pending_when_nothing_generated(tmp_path):
    plan, rows = _edit_plan(tmp_path, n=5)
    result = job_queue.build_queue(str(plan), num_shards=2)
    qpath = tmp_path / "q.jsonl"
    job_queue.write_queue(result, str(qpath))
    gen = tmp_path / "gen.jsonl"
    gen.write_text("", encoding="utf-8")
    status = job_queue.queue_status(str(qpath), str(gen))
    assert status["status_counts"]["pending"] == len(rows)
    assert status["completion_fraction"] == 0.0


# --- resume ----------------------------------------------------------------

def test_resume_plan_picks_incomplete_and_increments_retry(tmp_path):
    plan, rows = _edit_plan(tmp_path, n=4)
    result = job_queue.build_queue(str(plan), num_shards=2)
    qpath = tmp_path / "q.jsonl"
    job_queue.write_queue(result, str(qpath))
    entries = {e.edit_id: e for e in result["entries"]}
    sha = _make_edit_image(Path(entries["e000"].expected_output_path))
    gen = tmp_path / "gen.jsonl"
    write_jsonl(gen, [{"edit_id": "e000", "generation_status": "generated", "edited_image_path": entries["e000"].expected_output_path, "edited_sha256": sha}])

    rp = diffusion_resume.resume_plan(str(qpath), str(gen), max_retries=3)
    run_ids = {e.edit_id for e in rp["to_run"]}
    assert "e000" not in run_ids  # already generated
    assert run_ids == {"e001", "e002", "e003"}
    assert all(e.retry_count == 1 for e in rp["to_run"])


def test_resume_plan_gives_up_after_max_retries(tmp_path):
    plan, _ = _edit_plan(tmp_path, n=2)
    result = job_queue.build_queue(str(plan), num_shards=1)
    # Pre-set retry_count at the cap so the next attempt exhausts the budget.
    for e in result["entries"]:
        e.retry_count = 3
    qpath = tmp_path / "q.jsonl"
    job_queue.write_queue(result, str(qpath))
    gen = tmp_path / "gen.jsonl"
    gen.write_text("", encoding="utf-8")
    rp = diffusion_resume.resume_plan(str(qpath), str(gen), max_retries=3)
    assert rp["n_to_run"] == 0
    assert rp["n_give_up"] == 2


# --- progress report -------------------------------------------------------

def test_generation_plan_report(tmp_path):
    plan, rows = _edit_plan(tmp_path, n=8)
    result = job_queue.build_queue(str(plan), num_shards=4)
    qpath = tmp_path / "q.jsonl"
    job_queue.write_queue(result, str(qpath))
    gen = tmp_path / "gen.jsonl"
    gen.write_text("", encoding="utf-8")
    report = edit_generation_plan.build_plan_report(str(qpath), str(gen), num_shards=4)
    assert report["n_jobs"] == len(rows)
    md = edit_generation_plan.render_report(report)
    assert md.startswith("# Edit Generation Plan")
    assert "Per-shard progress" in md


def test_no_heavy_imports():
    assert "torch" not in sys.modules
    assert "diffusers" not in sys.modules
    assert "cv2" not in sys.modules
