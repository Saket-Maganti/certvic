from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V9 = ROOT / "data/results/main_real_200/v9_mega_upgrade"


def test_main500_does_not_go_without_resolved_specificity_branch():
    decision = json.loads((V9 / "main500_go_nogo_after_specificity.json").read_text())
    if decision["decision"].startswith("GO_"):
        assert decision["resolved_specificity_branch"] is True
        assert decision["main500_can_start"] is True
    else:
        assert decision["main500_can_start"] is False
    assert decision["decision"] == "HOLD_FOR_SPURIOUS_V2"
    assert decision["resolved_specificity_branch"] is False
    assert decision["paper_evidence"] is False
    assert "Do not start Main-500" in decision["forbidden_action"]
