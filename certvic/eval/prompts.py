"""Prompt builders."""

from __future__ import annotations

from certvic.schema import AnswerFormat, TaskItem


def build_prompt(task: TaskItem, image_variant: str) -> str:
    question = task.question_original if image_variant == "original" else task.question_edited
    if task.answer_format == AnswerFormat.YES_NO.value and "yes or no" not in question.lower():
        return f"{question} Respond with exactly one token: yes or no."
    if task.answer_format == AnswerFormat.MULTIPLE_CHOICE.value and "option letter" not in question.lower():
        return f"{question} Respond with exactly one option letter."
    return question
