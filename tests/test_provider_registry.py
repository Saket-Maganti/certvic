import pytest

from certvic.exceptions import MissingOptionalDependencyError
from certvic.providers.registry import PAID_PROVIDER_NAMES, available_provider_names, get_provider


def test_registry_returns_mock():
    assert get_provider("mock_perfect").provider_name == "mock_perfect"


def test_free_tier_reference_disabled_by_default():
    with pytest.raises(MissingOptionalDependencyError):
        get_provider("free_tier_reference_stub", {})


def test_no_paid_provider_names():
    assert not PAID_PROVIDER_NAMES
    assert "mock_inconsistent" in available_provider_names()
