from certvic.io import write_json
from certvic.reporting.ablations import build_ablation_report


def test_ablation_report_writes(tmp_path):
    report = tmp_path / "summary.json"
    out = tmp_path / "ablation.md"
    write_json(report, {"summary": {"n": 1, "consistency_rate": 1.0, "intervention_consistency_gap": 0.0}})
    build_ablation_report([str(report)], str(out))
    assert out.exists()
