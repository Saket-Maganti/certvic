from certvic.schema import ImageVariant, PairScore, PredictionRecord, ProviderType, RequiredChange


def test_prediction_and_pair_score_creation():
    pred = PredictionRecord(
        run_id="r",
        item_id="i",
        provider_name="mock",
        provider_type=ProviderType.MOCK.value,
        model_name="mock",
        model_version="v1",
        image_variant=ImageVariant.ORIGINAL.value,
        prompt="Q",
        raw_output="yes",
        parsed_answer="yes",
        parse_confidence=1.0,
        parse_ok=True,
        timestamp_utc="2026-01-01T00:00:00+00:00",
    )
    score = PairScore(
        run_id="r",
        item_id="i",
        provider_name="mock",
        model_name="mock",
        task_family="support_stability",
        domain="synthetic_sanity",
        original_correct=True,
        edited_correct=False,
        consistent=False,
        required_change=RequiredChange.CHANGE.value,
        parse_ok=True,
    )
    assert pred.parsed_answer == "yes"
    assert not score.consistent
