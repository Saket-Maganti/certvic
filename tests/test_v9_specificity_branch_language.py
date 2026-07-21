from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V9 = ROOT / "data/results/main_real_200/v9_mega_upgrade"


def test_specificity_branch_blocks_all_model_claim():
    decision = json.loads((V9 / "specificity_branch_decision.json").read_text())
    assert decision["branch"] == "MODEL_DEPENDENT_SPECIFICITY_V2_PENDING"
    assert decision["all_model_specificity_claim_allowed"] is False
    assert decision["main500_allowed"] is False
    assert decision["paper_evidence"] is False


def test_specificity_language_is_model_dependent():
    text = "\n".join(
        [
            (V9 / "SPECIFICITY_BRANCH_DECISION.md").read_text(),
            (ROOT / "paper/sections/v9_specificity_controls.tex").read_text(),
            (ROOT / "paper/sections/v9_model_dependent_limitations.tex").read_text(),
            (ROOT / "paper/tables/v9_specificity_controls.tex").read_text(),
        ]
    ).lower()
    assert "internvl and llava pass" in text
    assert "qwen shows a strong update-gap result but elevated sensitivity" in text
    assert "model-dependent specificity" in text
    assert "not all-model specificity" in text
    assert "must not claim all-model specificity" in text
    forbidden = [
        "all models pass",
        "all-model specificity is established",
        "qwen specificity resolved",
    ]
    assert not any(phrase in text for phrase in forbidden)
