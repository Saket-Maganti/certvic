"""Deterministic construct-validity baselines.

These baselines are not models and produce no evidence. They exist to show the
consistency task cannot be solved without actually seeing the visual change:
non-visual baselines should achieve low consistency, and single-image baselines
should fail the change items they cannot detect.
"""

from __future__ import annotations

from collections import Counter

from certvic.eval.parse import parse_answer
from certvic.hashing import stable_int_hash
from certvic.schema import RequiredChange

BASELINES = [
    "random_seeded",
    "majority_by_family",
    "text_only_heuristic",
    "caption_only_stub",
    "original_only",
    "edited_only",
    "answer_prior",
    "prompt_shuffle_control",
]


def _answer_space(task: dict) -> list[str]:
    fmt = str(task.get("answer_format", "yes_no"))
    if fmt == "multiple_choice":
        return ["A", "B", "C", "D"]
    if fmt == "short_action":
        space = [str(task.get("answer_original")), str(task.get("answer_edited"))]
        return [a for a in space if a] or ["yes", "no"]
    return ["yes", "no"]


def _pick(space: list[str], key: str) -> str:
    return space[stable_int_hash(key) % len(space)]


def build_context(tasks: list[dict]) -> dict:
    """Precompute family majorities and the global answer prior."""
    family_answers: dict[str, list[str]] = {}
    all_answers: list[str] = []
    for task in tasks:
        fam = str(task.get("task_family"))
        ans = str(task.get("answer_original"))
        family_answers.setdefault(fam, []).append(ans)
        all_answers.append(ans)
    family_majority = {fam: Counter(v).most_common(1)[0][0] for fam, v in family_answers.items()}
    prior = Counter(all_answers).most_common(1)[0][0] if all_answers else "yes"
    return {"family_majority": family_majority, "prior": prior}


def baseline_raw_outputs(name: str, task: dict, context: dict, seed: int) -> tuple[str, str]:
    """Return (raw_original, raw_edited) for a baseline."""
    space = _answer_space(task)
    item_id = str(task.get("item_id") or task.get("edit_id"))
    fam = str(task.get("task_family"))
    if name == "random_seeded":
        return _pick(space, f"{seed}|{item_id}|o"), _pick(space, f"{seed}|{item_id}|e")
    if name == "majority_by_family":
        ans = context["family_majority"].get(fam, space[0])
        return ans, ans
    if name == "text_only_heuristic":
        return _pick(space, f"txt|{task.get('question_original')}"), _pick(space, f"txt|{task.get('question_edited')}")
    if name == "caption_only_stub":
        ans = _pick(space, f"cap|{task.get('source_id')}")
        return ans, ans
    if name == "original_only":
        ans = str(task.get("answer_original"))
        return ans, ans  # cannot see the change -> never updates
    if name == "edited_only":
        ans = str(task.get("answer_edited"))
        return ans, ans
    if name == "answer_prior":
        return context["prior"], context["prior"]
    if name == "prompt_shuffle_control":
        return _pick(space, f"shuf|{seed}|{item_id}|o"), _pick(space, f"shuf|{seed}|{item_id}|e")
    raise ValueError(f"unknown baseline: {name}")


def score_item(task: dict, raw_original: str, raw_edited: str, strict: bool = True) -> dict:
    """Replicate the main scoring rule (see metrics/score_predictions.py)."""
    fmt = str(task.get("answer_format", "yes_no"))
    po = parse_answer(raw_original, fmt, strict=strict)
    pe = parse_answer(raw_edited, fmt, strict=strict)
    parse_ok = bool(po.parse_ok and pe.parse_ok)
    original_correct = bool(po.parse_ok and po.parsed_answer == task.get("answer_original"))
    answer_changed = po.parsed_answer != pe.parsed_answer
    if str(task.get("required_change")) == RequiredChange.CHANGE.value:
        consistent = parse_ok and answer_changed
    else:
        consistent = parse_ok and not answer_changed
    return {
        "item_id": task.get("item_id") or task.get("edit_id"),
        "task_family": task.get("task_family"),
        "domain": task.get("domain"),
        "required_change": task.get("required_change"),
        "raw_original": raw_original,
        "raw_edited": raw_edited,
        "parsed_original": po.parsed_answer,
        "parsed_edited": pe.parsed_answer,
        "parse_ok": parse_ok,
        "a_i": int(original_correct),
        "C_i": int(bool(consistent)),
    }


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0, "accuracy": None, "consistency": None, "gap": None, "parse_fail_rate": None}
    a = sum(r["a_i"] for r in rows) / n
    c = sum(r["C_i"] for r in rows) / n
    parse_fail = sum(1 for r in rows if not r["parse_ok"]) / n
    return {"n": n, "accuracy": a, "consistency": c, "gap": a - c, "parse_fail_rate": parse_fail}
