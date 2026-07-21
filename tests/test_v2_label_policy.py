"""Tests for the V2 ADE20K label policy, diagnostics, and integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from certvic.data import label_policy as lp
from certvic.data.label_policy_report import build_label_policy_report


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_POLICY = REPO_ROOT / "configs" / "ade20k_label_policy.yaml"


def _write_policy(tmp_path) -> str:
    text = """
version: certvic.test_policy.v1
verified: false
defaults:
  unresolved_eligible_task_families: [control_irrelevant]
  unresolved_allowed_edit_types: [control_irrelevant]
  unresolved_block_reason: null
labels:
  - label_id: 8
    label_name: bed
    eligible_task_families: [support_stability, control_irrelevant]
    allowed_edit_types: [remove, displace, control_irrelevant]
    domain_tags: [household]
  - label_id: 3
    label_name: sky
    eligible_task_families: []
    allowed_edit_types: []
    block_reason: background_stuff_not_a_manipulable_object
"""
    path = tmp_path / "policy.yaml"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_template_policy_loads_and_is_unverified():
    policy = lp.load_label_policy(str(TEMPLATE_POLICY))
    assert policy["verified"] is False
    assert policy["entries"]
    assert policy["policy_hash"].startswith("sha256:")


def test_resolved_label_eligibility(tmp_path):
    policy = lp.load_label_policy(_write_policy(tmp_path))
    assert lp.resolve_label_name(policy, 8) == "bed"
    assert "support_stability" in lp.eligible_families_for_label(policy, 8)
    assert "remove" in lp.allowed_edits_for_label(policy, 8)
    assert lp.is_label_blocked(policy, 8) is False


def test_blocked_label_has_no_eligibility(tmp_path):
    policy = lp.load_label_policy(_write_policy(tmp_path))
    assert lp.is_label_blocked(policy, 3) is True
    assert lp.eligible_families_for_label(policy, 3) == []
    assert lp.allowed_edits_for_label(policy, 3) == []


def test_unresolved_label_conservative_fallback(tmp_path):
    policy = lp.load_label_policy(_write_policy(tmp_path))
    assert lp.is_resolved(policy, 9999) is False
    assert lp.resolve_label_name(policy, 9999) == "ade20k_label_9999"
    # Conservative: control only, never a change-required family.
    assert lp.eligible_families_for_label(policy, 9999) == ["control_irrelevant"]
    assert "support_stability" not in lp.eligible_families_for_label(policy, 9999)


def test_explain_label_decision(tmp_path):
    policy = lp.load_label_policy(_write_policy(tmp_path))
    ok = lp.explain_label_decision(policy, 8, "support_stability", "remove")
    assert ok["eligible"] is True
    bad = lp.explain_label_decision(policy, 8, "occlusion_safety", "occlude")
    assert bad["eligible"] is False
    assert any("family_not_eligible" in r for r in bad["reasons"])
    blocked = lp.explain_label_decision(policy, 3)
    assert blocked["blocked"] is True


def test_none_policy_falls_through_to_conservative_default():
    policy = lp.load_label_policy(None)
    assert lp.eligible_families_for_label(policy, 8) == ["control_irrelevant"]
    assert lp.is_label_blocked(policy, 8) is False


def test_invalid_family_in_policy_raises(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "labels:\n  - label_id: 1\n    eligible_task_families: [not_a_family]\n",
        encoding="utf-8",
    )
    with pytest.raises(lp.LabelPolicyError):
        lp.load_label_policy(str(path))


def test_label_policy_report_outputs(tmp_path):
    from certvic.io import write_jsonl

    masks = [
        {"source_id": "s0", "mask_id": "m0", "label_id": 8, "bbox_xyxy": [0, 0, 4, 4]},
        {"source_id": "s1", "mask_id": "m1", "label_id": 3, "bbox_xyxy": [0, 0, 4, 4]},
        {"source_id": "s2", "mask_id": "m2", "label_id": 9999, "bbox_xyxy": [0, 0, 4, 4]},
    ]
    masks_path = tmp_path / "masks.jsonl"
    write_jsonl(masks_path, masks)
    out_dir = tmp_path / "report"
    summary = build_label_policy_report(str(masks_path), _write_policy(tmp_path), str(out_dir))
    assert summary["n_masks"] == 3
    assert summary["n_blocked_labels"] == 1
    assert summary["n_unresolved_labels"] == 1
    for name in [
        "label_policy_summary.json",
        "label_frequency.csv",
        "eligible_by_family.csv",
        "blocked_labels.csv",
        "unresolved_labels.csv",
        "label_policy_report.md",
    ]:
        assert (out_dir / name).exists(), name


def test_selector_respects_policy_block_and_unresolved(tmp_path):
    from certvic.data.select_pilot_items import select_pilot_items
    from certvic.io import read_jsonl, write_jsonl

    sources = [{"source_id": f"s{i}"} for i in range(3)]
    masks = [
        {"source_id": "s0", "mask_id": "m0", "label_id": 8, "bbox_xyxy": [0, 0, 4, 4], "mask_area_fraction": 0.1},
        {"source_id": "s1", "mask_id": "m1", "label_id": 3, "bbox_xyxy": [0, 0, 4, 4], "mask_area_fraction": 0.1},
        {"source_id": "s2", "mask_id": "m2", "label_id": 7777, "bbox_xyxy": [0, 0, 4, 4], "mask_area_fraction": 0.1},
    ]
    sp = tmp_path / "sources.jsonl"
    mp = tmp_path / "masks.jsonl"
    out = tmp_path / "sel.jsonl"
    write_jsonl(sp, sources)
    write_jsonl(mp, masks)
    summary = select_pilot_items(
        str(sp), str(mp), str(out), target=3, seed=0,
        label_policy_path=_write_policy(tmp_path),
        allowed_task_families=["support_stability", "control_irrelevant"],
        require_target=False,
    )
    # Blocked sky (3) is rejected; unresolved 7777 only allows control_irrelevant.
    assert summary["rejected"]["label_policy_blocked"] == 1
    assert summary["unresolved_label_count"] == 1
    assert summary["label_policy_version"] == "certvic.test_policy.v1"
    selected = read_jsonl(out)
    families = {row["task_family"] for row in selected}
    assert "support_stability" in families  # bed selected for change family


def test_planner_rejects_policy_incompatible_edits(tmp_path):
    from certvic.edit.plan_edits import build_edit_plan
    from certvic.io import write_jsonl

    # A candidate whose label only allows control edits but is planned as occlude.
    candidate = {
        "candidate_id": "c0",
        "source_id": "s0",
        "mask_id": "m0",
        "label_id": 3,  # sky, blocked
        "image_path": "https://example.com/img.jpg",
        "bbox": [0, 0, 4, 4],
        "mask_area_fraction": 0.1,
        "task_family": "occlusion_safety",
        "proposed_task_family": "occlusion_safety",
        "proposed_edit_type": "occlude",
        "proposed_required_change": "no_change",
        "domain": "driving",
        "release_mode": "recipe_only",
        "license_posture": {"release_mode": "recipe_only"},
        "evidence_status": "CANDIDATE_ONLY",
    }
    sel = tmp_path / "sel.jsonl"
    write_jsonl(sel, [candidate])
    summary = build_edit_plan(
        str(sel),
        str(tmp_path / "plan.jsonl"),
        str(tmp_path / "plan_summary.json"),
        label_policy_path=_write_policy(tmp_path),
    )
    assert summary["planned"] == 0
    assert summary["rejected"] == 1
    assert "rejections_by_label" in summary
    assert any("label policy" in reason for reason in summary["rejection_reasons"])
