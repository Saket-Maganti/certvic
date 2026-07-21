from certvic.providers.text_only import TextOnlyBaselineProvider


def test_text_only_independent_of_image():
    p = TextOnlyBaselineProvider(seed=1)
    assert p.answer("a", "same prompt") == p.answer("b", "same prompt")
