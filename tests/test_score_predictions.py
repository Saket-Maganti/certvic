from certvic.eval.run_eval import run_eval
from certvic.io import write_jsonl
from certvic.metrics.score_predictions import score_predictions
from certvic.metrics.summary import summarize_pair_scores


def test_score_predictions_expected_values(smoke_tasks, tmp_path):
    tasks_path = tmp_path / "tasks.jsonl"
    preds_path = tmp_path / "preds.jsonl"
    config_path = tmp_path / "smoke.yaml"
    write_jsonl(tasks_path, smoke_tasks[:4])
    config_path.write_text("paid_services_enabled: false\n", encoding="utf-8")
    run_eval(str(config_path), str(tasks_path), str(preds_path), "mock_inconsistent", "run")
    scores = score_predictions(str(tasks_path), str(preds_path))
    summary = summarize_pair_scores(scores)
    assert len(scores) == 4
    assert summary["original_accuracy"] == 1.0
    assert summary["consistency_rate"] == 0.5
