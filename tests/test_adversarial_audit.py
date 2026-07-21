"""Tests for the V2.3 prompt/task adversarial audit."""

from __future__ import annotations

from certvic.eval.adversarial_audit import run_adversarial_audit
from certvic.io import write_jsonl

FAMILIES = ["support_stability", "affordance_reachability", "occlusion_safety", "control_irrelevant"]


def _task(i, answer_o, answer_e, required_change, family, domain="household", edit_type="remove", question=None):
    q = question or f"Is condition {i % 5} satisfied for the highlighted object?"
    return {
        "item_id": f"item_{i:04d}",
        "source_id": f"src_{i:04d}",
        "question_original": q + " Respond yes or no.",
        "question_edited": q + " Respond yes or no.",
        "answer_original": answer_o,
        "answer_edited": answer_e,
        "required_change": required_change,
        "task_family": family,
        "domain": domain,
        "edit_type": edit_type,
        "answer_format": "yes_no",
        "original_image_path": f"data/src/{i:04d}_a.png",
        "edited_image_path": f"data/edit/{i:04d}_b.png",
    }


def _balanced_good_set():
    tasks = []
    for i in range(12):
        change = i % 2 == 0
        family = FAMILIES[i % len(FAMILIES)]
        answer_o = "yes" if i % 4 < 2 else "no"
        if change:
            answer_e = "no" if answer_o == "yes" else "yes"
            rc = "change"
            et = "remove"
        else:
            answer_e = answer_o
            rc = "no_change"
            et = "control_irrelevant"
        tasks.append(_task(i, answer_o, answer_e, rc, family, edit_type=et))
    return tasks


def test_balanced_set_passes(tmp_path):
    p = tmp_path / "good.jsonl"
    write_jsonl(p, _balanced_good_set())
    result = run_adversarial_audit(p, out_dir=tmp_path / "out")
    assert result["passed"] is True, result["high_severity_failures"]
    assert result["high_severity_failures"] == []
    assert (tmp_path / "out" / "adversarial_audit.json").exists()
    assert (tmp_path / "out" / "adversarial_audit.md").exists()


def test_mislabeled_and_leaky_set_fails(tmp_path):
    tasks = _balanced_good_set()
    # Mislabel: required change but answers identical.
    tasks[0]["answer_edited"] = tasks[0]["answer_original"]
    tasks[0]["required_change"] = "change"
    # Leak the edit operation in a prompt.
    tasks[1]["question_original"] = "After the object was removed, is it still supported? Respond yes or no."
    p = tmp_path / "bad.jsonl"
    write_jsonl(p, tasks)
    result = run_adversarial_audit(p)
    assert result["passed"] is False
    assert "label_consistency" in result["high_severity_failures"]
    assert "prompt_leakage" in result["high_severity_failures"]


def test_all_no_change_is_gameable(tmp_path):
    # A set where every item is no_change: a constant responder is perfectly
    # consistent, so non_visual_gameability must fire.
    tasks = [
        _task(i, "yes" if i % 2 else "no", "yes" if i % 2 else "no", "no_change", FAMILIES[i % 4], edit_type="control_irrelevant")
        for i in range(10)
    ]
    p = tmp_path / "gameable.jsonl"
    write_jsonl(p, tasks)
    result = run_adversarial_audit(p)
    assert result["passed"] is False
    assert "non_visual_gameability" in result["high_severity_failures"]
