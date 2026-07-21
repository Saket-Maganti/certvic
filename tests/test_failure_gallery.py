from certvic.reporting.failure_gallery import build_failure_gallery
from certvic.schema import ImageVariant, PairScore, PredictionRecord


def test_failure_gallery_filters(smoke_tasks):
    task = smoke_tasks[0]
    score = PairScore(run_id="r", item_id=task.item_id, provider_name="p", model_name="m", task_family=task.task_family, domain=task.domain, original_correct=True, edited_correct=False, consistent=False, required_change=task.required_change, parse_ok=True)
    preds = [
        PredictionRecord(run_id="r", item_id=task.item_id, provider_name="p", provider_type="mock", model_name="m", model_version="v1", image_variant=ImageVariant.ORIGINAL.value, prompt="q", raw_output="yes", parsed_answer="yes", parse_confidence=1.0, parse_ok=True, timestamp_utc="t"),
        PredictionRecord(run_id="r", item_id=task.item_id, provider_name="p", provider_type="mock", model_name="m", model_version="v1", image_variant=ImageVariant.EDITED.value, prompt="q", raw_output="yes", parsed_answer="yes", parse_confidence=1.0, parse_ok=True, timestamp_utc="t"),
    ]
    gallery = build_failure_gallery({task.item_id: task}, [score], preds)
    assert len(gallery) == 1
