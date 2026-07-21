import pytest

from certvic.exceptions import MissingOptionalDependencyError
from certvic.metrics.confseq_wrappers import bounded_mean_cs_01


def test_confseq_unavailable_explicit():
    result = bounded_mean_cs_01([0, 1], allow_unavailable=True)
    assert "available" in result
    if not result["available"]:
        with pytest.raises(MissingOptionalDependencyError):
            bounded_mean_cs_01([0, 1], allow_unavailable=False)
