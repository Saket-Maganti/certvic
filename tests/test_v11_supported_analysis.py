from __future__ import annotations

import json
from pathlib import Path

from scripts.rebuild_v11_supported_analysis import rebuild


def test_v11_supported_analysis_reproduces_verified_real_counts(tmp_path: Path) -> None:
    result = rebuild(tmp_path)
    pilot = {row["provider"]: row for row in result["pilot"]}
    v1 = {row["provider"]: row for row in result["v1_specificity"]}

    assert [pilot[name]["original_correct"] for name in pilot] == [84, 84, 81]
    assert [pilot[name]["raw_answer_changes"] for name in pilot] == [16, 9, 16]
    assert [pilot[name]["correct_semantic_updates"] for name in pilot] == [16, 9, 13]
    assert [v1[name]["flips"] for name in v1] == [12, 1, 3]
    assert [v1[name]["frozen_v1_gate"] for name in v1] == ["FAIL", "PASS", "PASS"]
    assert all(row["full_policy_passed"] is False for row in pilot.values())
    assert result["qwen_failure_count"] == 12
    assert result["paper_evidence"] is False


def test_paired_statistics_and_artifacts_are_locked(tmp_path: Path) -> None:
    result = rebuild(tmp_path)
    paired = {
        (row["left_provider"], row["right_provider"]): row
        for row in result["paired_comparisons"]
    }
    qwen_intern = paired[("qwen2_5_vl_7b", "internvl_8b")]
    qwen_llava = paired[("qwen2_5_vl_7b", "llava_onevision_7b")]
    assert qwen_intern["paired_risk_difference"] == 11 / 94
    assert qwen_intern["mcnemar_exact_p"] == 0.00341796875
    assert qwen_llava["paired_risk_difference"] == 9 / 94
    assert qwen_llava["mcnemar_exact_p"] == 0.03515625
    assert len(list(tmp_path.glob("*.csv"))) == 8
    stored = json.loads((tmp_path / "supported_analysis.json").read_text())
    assert stored["paper_evidence"] is False
    assert stored["human_reviewed"] is False
