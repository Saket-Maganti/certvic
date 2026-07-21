from certvic.metrics.summary import summarize_pair_scores
from certvic.schema import PairScore


def test_metrics_summary_gap():
    scores = [
        PairScore(run_id="r", item_id="a", provider_name="p", model_name="m", task_family="f", domain="d", original_correct=True, edited_correct=False, consistent=False, required_change="change", parse_ok=True),
        PairScore(run_id="r", item_id="b", provider_name="p", model_name="m", task_family="f", domain="d", original_correct=True, edited_correct=True, consistent=True, required_change="no_change", parse_ok=True),
    ]
    summary = summarize_pair_scores(scores)
    assert summary["intervention_consistency_gap"] == 0.5
