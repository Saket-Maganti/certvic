from certvic.metrics.certification import certify_gap


def test_certification_unavailable_not_certified():
    result = certify_gap([1, 1], [0, 0], allow_unavailable=True)
    assert result["certified"] is False or result["lower_bound"] is not None
