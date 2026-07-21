"""Answer parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass

from certvic.schema import AnswerFormat


@dataclass(frozen=True)
class ParsedAnswer:
    parsed_answer: str | None
    parse_confidence: float
    parse_ok: bool
    parse_status: str = "PARSE_FAILED"
    parser_version: str = "certvic.parse.v2"


DIAGNOSTIC_ANSWER_FORMATS = {"object_list", "describe_then_yes_no"}
_REFUSAL_RE = re.compile(
    r"\b(?:cannot|can't|unable|won't|will not|refuse|sorry|not able)\b",
    flags=re.IGNORECASE,
)


def _failed(status: str = "MALFORMED") -> ParsedAnswer:
    return ParsedAnswer(None, 0.0, False, status)


def _ok(answer: str, confidence: float) -> ParsedAnswer:
    return ParsedAnswer(answer, confidence, True, "PARSE_OK")


def parse_answer(raw_output: str | None, answer_format: str, strict: bool = True) -> ParsedAnswer:
    """Parse a model response without inventing a certification answer.

    ``yes_no``, ``multiple_choice``, and ``short_action`` are the TaskItem
    formats. The two additional formats are explicitly diagnostic-only flat
    runbook formats; TaskItem's enum does not admit them, so they cannot leak
    into the certification runner.
    """
    if not isinstance(raw_output, str):
        return _failed("INVALID_TYPE")
    fmt = getattr(answer_format, "value", answer_format)
    text = raw_output.strip().lower()
    normalized = text.strip(" .,!?:;\"'")
    if not normalized:
        return _failed("EMPTY")
    if _REFUSAL_RE.search(text):
        return _failed("REFUSAL")
    if fmt == AnswerFormat.YES_NO.value:
        if normalized in {"yes", "no"}:
            return _ok(normalized, 1.0)
        tokens = [tok.strip(" .,!?:;\"'") for tok in text.split()]
        hits = [tok for tok in tokens if tok in {"yes", "no"}]
        if not strict and len(set(hits)) == 1:
            return _ok(hits[0], 0.5)
        return _failed("AMBIGUOUS" if len(set(hits)) > 1 else "MALFORMED")
    if fmt == AnswerFormat.MULTIPLE_CHOICE.value:
        if len(normalized) == 1 and normalized in {"a", "b", "c", "d", "e"}:
            return _ok(normalized.upper(), 1.0)
        return _failed("AMBIGUOUS" if re.search(r"\b[a-e]\b.*\b[a-e]\b", text) else "MALFORMED")
    if fmt == AnswerFormat.SHORT_ACTION.value:
        return _ok(normalized, 0.5)
    if fmt == "object_list":
        # Diagnostic-only: preserve a normalized list for convenience while
        # retaining raw_output in the PredictionRecord. Refusals and empty
        # outputs remain explicit parse failures.
        parts = [
            re.sub(r"^(?:[-*]|\d+[.)])\s*", "", part.strip()).strip(" .,!?:;\"'")
            for part in re.split(r"[,;\n]+", text)
        ]
        parts = [part for part in parts if part]
        if not parts:
            return _failed("MALFORMED")
        return _ok(", ".join(parts), 0.5)
    if fmt == "describe_then_yes_no":
        # The diagnostic prompt requires a free description followed by one
        # yes/no token on its own final line. Strict mode enforces that
        # contract; lenient mode is diagnostic recovery only.
        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        if len(lines) >= 2:
            final = lines[-1].lower().strip(" .,!?:;\"'")
            explicit_decisions = [
                value
                for line in lines
                if (value := line.lower().strip(" .,!?:;\"'")) in {"yes", "no"}
            ]
            if len(set(explicit_decisions)) > 1:
                return _failed("AMBIGUOUS")
            if final in {"yes", "no"}:
                return _ok(final, 0.75)
        if not strict:
            hits = re.findall(r"\b(yes|no)\b", text)
            if hits:
                if len(set(hits)) > 1:
                    return _failed("AMBIGUOUS")
                return _ok(hits[-1], 0.4)
        return _failed("MALFORMED")
    raise ValueError(f"Unsupported answer format: {fmt}")


def parse_answer_record(
    raw_output: str | None,
    answer_format: str,
    *,
    strict: bool = True,
) -> dict[str, object]:
    """Return the import-safe parser record while retaining the provider text verbatim."""
    parsed = parse_answer(raw_output, answer_format, strict=strict)
    return {
        "raw_response": raw_output,
        "parsed_response": parsed.parsed_answer,
        "parse_ok": parsed.parse_ok,
        "parse_status": parsed.parse_status,
        "parse_confidence": parsed.parse_confidence,
        "parser_version": parsed.parser_version,
        "answer_format": getattr(answer_format, "value", answer_format),
        "strict": strict,
    }
