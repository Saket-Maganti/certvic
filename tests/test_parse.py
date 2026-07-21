import pytest

from certvic.eval.parse import DIAGNOSTIC_ANSWER_FORMATS, parse_answer


def test_parse_yes_no_strict():
    assert parse_answer("yes", "yes_no").parsed_answer == "yes"
    assert not parse_answer("yes, because...", "yes_no").parse_ok


@pytest.mark.parametrize(
    ("raw", "answer"),
    [
        ("YES", "yes"),
        (" no. ", "no"),
        ("'Yes!'", "yes"),
    ],
)
def test_strict_yes_no_accepts_only_punctuated_single_tokens(raw, answer):
    parsed = parse_answer(raw, "yes_no", strict=True)
    assert parsed.parse_ok is True
    assert parsed.parsed_answer == answer
    assert parsed.parse_confidence == 1.0


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        None,
        "yes because the object is visible",
        "yes no",
        "yes, but actually no",
        "I cannot answer",
        "maybe",
    ],
)
def test_strict_yes_no_fails_closed_on_malformed_freeform_and_contradictions(raw):
    parsed = parse_answer(raw, "yes_no", strict=True)
    assert parsed == parse_answer(raw, "yes_no", strict=True)  # deterministic
    assert parsed.parse_ok is False
    assert parsed.parsed_answer is None
    assert parsed.parse_confidence == 0.0


def test_lenient_yes_no_is_diagnostic_recovery_and_rejects_contradiction():
    assert parse_answer("Yes, because it is visible.", "yes_no", strict=False).parsed_answer == "yes"
    assert not parse_answer("yes, but actually no", "yes_no", strict=False).parse_ok


@pytest.mark.parametrize(("raw", "answer"), [("A", "A"), (" e. ", "E")])
def test_multiple_choice_single_token_only(raw, answer):
    assert parse_answer(raw, "multiple_choice").parsed_answer == answer


@pytest.mark.parametrize("raw", ["", "option a", "A or B", "(A)", None])
def test_multiple_choice_malformed_is_failure(raw):
    assert not parse_answer(raw, "multiple_choice").parse_ok


def test_short_action_preserves_nonempty_normalized_text_but_empty_fails():
    assert parse_answer(" Turn left. ", "short_action").parsed_answer == "turn left"
    assert not parse_answer("", "short_action").parse_ok


def test_diagnostic_object_list_parsing_is_explicit_and_refusals_fail():
    assert "object_list" in DIAGNOSTIC_ANSWER_FORMATS
    parsed = parse_answer("Chair, table; lamp", "object_list", strict=True)
    assert parsed.parse_ok and parsed.parsed_answer == "chair, table, lamp"
    assert not parse_answer("I cannot identify objects", "object_list", strict=True).parse_ok
    assert not parse_answer("", "object_list", strict=True).parse_ok


def test_describe_then_yes_no_requires_final_own_line_in_strict_mode():
    assert "describe_then_yes_no" in DIAGNOSTIC_ANSWER_FORMATS
    parsed = parse_answer("A room with a table.\nNo.", "describe_then_yes_no", strict=True)
    assert parsed.parse_ok and parsed.parsed_answer == "no"
    assert not parse_answer("A room with a table. No.", "describe_then_yes_no", strict=True).parse_ok
    assert parse_answer(
        "A room with a table. No.", "describe_then_yes_no", strict=False
    ).parsed_answer == "no"
    assert not parse_answer("No", "describe_then_yes_no", strict=True).parse_ok
    assert not parse_answer("Description.\nyes\nno", "describe_then_yes_no", strict=True).parse_ok


def test_invalid_answer_format_raises_instead_of_guessing():
    with pytest.raises(ValueError, match="Unsupported answer format"):
        parse_answer("yes", "unknown_format")
