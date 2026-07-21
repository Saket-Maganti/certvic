from certvic.providers.random_baseline import RandomBaselineProvider


def test_random_baseline_deterministic():
    p = RandomBaselineProvider(seed=1)
    assert p.answer("a", "q") == p.answer("a", "q")
