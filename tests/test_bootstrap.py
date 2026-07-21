from certvic.metrics.bootstrap import paired_bootstrap_ci


def test_bootstrap_deterministic():
    ci1 = paired_bootstrap_ci([1, 0, 1], lambda xs: sum(xs) / len(xs), n_boot=20, seed=1)
    ci2 = paired_bootstrap_ci([1, 0, 1], lambda xs: sum(xs) / len(xs), n_boot=20, seed=1)
    assert ci1 == ci2
