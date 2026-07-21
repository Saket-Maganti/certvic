from __future__ import annotations

import pytest

from certvic.validation.leakage import check_path_no_leakage, check_prompt_no_leakage

LEAKAGE_TERMS = [
    "removed",
    "occluded",
    "edited",
    "displaced",
    "answer",
    "label",
    "ground_truth",
    "unsupported",
    "unsafe",
    "changed",
]


@pytest.mark.parametrize("term", LEAKAGE_TERMS)
def test_prompt_leakage_terms_blocked(term):
    assert check_prompt_no_leakage(f"This prompt contains {term}.")


@pytest.mark.parametrize("term", LEAKAGE_TERMS)
def test_filename_leakage_terms_blocked(term):
    assert check_path_no_leakage(f"scene_{term}.png")
