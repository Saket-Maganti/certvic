from __future__ import annotations

from certvic.eval.run_eval import run_eval
from certvic.io import write_jsonl
from certvic.metrics.score_predictions import score_predictions
from certvic.metrics.summary import summarize_pair_scores
from certvic.providers.registry import get_provider


def _score_provider(provider_name: str, smoke_tasks, tmp_path):
    tasks_path = tmp_path / f"{provider_name}_tasks.jsonl"
    preds_path = tmp_path / f"{provider_name}_preds.jsonl"
    config_path = tmp_path / f"{provider_name}_config.yaml"
    write_jsonl(tasks_path, smoke_tasks)
    config_path.write_text("paid_services_enabled: false\nseed: 123\n", encoding="utf-8")
    run_eval(
        str(config_path),
        str(tasks_path),
        str(preds_path),
        provider_name,
        f"{provider_name}_run",
    )
    scores = score_predictions(str(tasks_path), str(preds_path))
    return summarize_pair_scores(scores), scores


def test_mock_perfect_scores_perfect_consistency(smoke_tasks, tmp_path):
    summary, _ = _score_provider("mock_perfect", smoke_tasks, tmp_path)
    assert summary["original_accuracy"] == 1.0
    assert summary["edited_accuracy"] == 1.0
    assert summary["consistency_rate"] == 1.0
    assert summary["parse_failure_rate"] == 0.0


def test_mock_inconsistent_has_high_original_low_consistency(smoke_tasks, tmp_path):
    summary, _ = _score_provider("mock_inconsistent", smoke_tasks, tmp_path)
    assert summary["original_accuracy"] == 1.0
    assert summary["consistency_rate"] <= 0.5
    assert summary["by_required_change"]["change"]["consistency_rate"] == 0.0


def test_mock_spurious_flip_catches_control_flips(smoke_tasks, tmp_path):
    summary, _ = _score_provider("mock_spurious_flip", smoke_tasks, tmp_path)
    assert summary["original_accuracy"] == 1.0
    assert summary["by_required_change"]["no_change"]["spurious_flip_rate"] == 1.0
    assert summary["control_edit"]["spurious_flip_rate"] == 1.0


def test_mock_parser_fail_records_parse_failures(smoke_tasks, tmp_path):
    summary, scores = _score_provider("mock_parser_fail", smoke_tasks, tmp_path)
    assert summary["parse_failure_rate"] == 1.0
    assert summary["parse_failure_sensitivity"]["n_parse_failures"] == len(scores)
    assert all(not score.parse_ok for score in scores)


def test_mock_always_answer_behavior(smoke_tasks, tmp_path):
    yes_summary, _ = _score_provider("mock_always_yes", smoke_tasks, tmp_path)
    no_summary, _ = _score_provider("mock_always_no", smoke_tasks, tmp_path)
    assert yes_summary["original_accuracy"] == 0.75
    assert no_summary["original_accuracy"] == 0.25


def test_mock_random_seeded_reproducible(smoke_tasks):
    p1 = get_provider("mock_random_seeded", {"seed": 7})
    p2 = get_provider("mock_random_seeded", {"seed": 7})
    outputs_1 = [p1.answer(task.original_image_path, task.question_original) for task in smoke_tasks]
    outputs_2 = [p2.answer(task.original_image_path, task.question_original) for task in smoke_tasks]
    assert outputs_1 == outputs_2
