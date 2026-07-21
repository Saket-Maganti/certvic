"""Prompt suite for prompt-sensitivity ablations.

Generates several neutral phrasings of the same question so prompt robustness can
be measured. Includes a leakage stress variant used only to verify the leakage
guard fires; it is never used for evidence runs.
"""

from __future__ import annotations

from certvic.validation.leakage import check_prompt_no_leakage

PROMPT_VARIANTS = [
    "canonical",
    "terse",
    "yes_no_strict",
    "multiple_choice",
    "rationale_forbidden",
    "prompt_leakage_stress",
]


def build_prompt_variants(question: str, answer_format: str = "yes_no", edit_hint: str | None = None) -> dict[str, str]:
    q = question.strip().rstrip("?.") + "?"
    variants = {
        "canonical": f"{q} Respond yes or no.",
        "terse": q,
        "yes_no_strict": f"{q} Respond with exactly one token: yes or no.",
        "multiple_choice": f"{q} Options: (A) yes (B) no. Respond with one option letter.",
        "rationale_forbidden": f"{q} Do not explain. Respond only yes or no.",
        # Intentionally leaks the edit operation to verify the guard fires; never
        # used for evidence runs.
        "prompt_leakage_stress": f"{q} Note: the image was edited ({edit_hint or 'object removed'}); respond yes or no.",
    }
    return variants


def variant_leakage_flags(question: str, edit_hint: str | None = None) -> dict[str, list[str]]:
    """Return leakage warnings per variant (the stress variant should be flagged)."""
    flags: dict[str, list[str]] = {}
    for name, text in build_prompt_variants(question, edit_hint=edit_hint).items():
        flags[name] = list(check_prompt_no_leakage(text))
    return flags
