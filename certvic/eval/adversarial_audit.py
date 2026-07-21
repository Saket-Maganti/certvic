"""Prompt/task adversarial audit (V2.3).

Attacks the *construct validity* of a CertVIC task set before any model is run:
can the consistency task be solved, or the gap inflated, without actually seeing
the visual change? A reviewer will probe exactly these failure modes.

Checks (each produces a finding with a severity):

* label_consistency  - ``answer_edited`` differs from ``answer_original`` iff
  ``required_change == change``. Mislabeled items silently corrupt the gap.
* prompt_leakage      - questions/paths must not leak the edit operation or the
  expected answer (reuses the V1 leakage guard).
* non_visual_gameability - deterministic non-visual baselines (text-only,
  answer-prior, majority, single-image, prompt-shuffle) must achieve LOW
  consistency; if any exceeds a threshold the task is gameable.
* answer_prior_imbalance - a heavily skewed answer marginal lets a constant
  responder score well; flagged overall and per family.
* design_balance      - degenerate distributions over family/domain/edit_type/
  required_change (e.g. all items are ``change``).
* question_diversity  - a single question template dominating invites
  pattern-matching rather than perception.
* mcq_position_prior  - for multiple-choice items, the correct option must not
  always be the same letter.

Runs no models, downloads nothing, makes no evidence claims.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from certvic.eval.ablation_baselines import (
    BASELINES,
    baseline_raw_outputs,
    build_context,
    score_item,
    summarize,
)
from certvic.io import read_jsonl, write_json
from certvic.validation.leakage import check_path_no_leakage, check_prompt_no_leakage

# Non-visual baselines that MUST fail a well-constructed consistency task.
NON_VISUAL_BASELINES = list(BASELINES)
DEFAULT_GAMEABLE_CONSISTENCY = 0.60
DEFAULT_PRIOR_IMBALANCE = 0.85
DEFAULT_TEMPLATE_DOMINANCE = 0.80
DEFAULT_MIN_GROUP_FRACTION = 0.05


def _finding(check: str, severity: str, passed: bool, **detail) -> dict:
    return {"check": check, "severity": severity, "passed": bool(passed), **detail}


def _label_consistency(tasks: list[dict]) -> dict:
    mislabeled = []
    for task in tasks:
        rc = str(task.get("required_change"))
        ao = str(task.get("answer_original"))
        ae = str(task.get("answer_edited"))
        differs = ao != ae
        if rc == "change" and not differs:
            mislabeled.append({"item": task.get("item_id"), "issue": "change but answers identical"})
        if rc == "no_change" and differs:
            mislabeled.append({"item": task.get("item_id"), "issue": "no_change but answers differ"})
    return _finding(
        "label_consistency",
        "high",
        not mislabeled,
        n_mislabeled=len(mislabeled),
        examples=mislabeled[:5],
    )


def _prompt_leakage(tasks: list[dict]) -> dict:
    leaks = []
    for task in tasks:
        answers = [str(task.get("answer_original")), str(task.get("answer_edited"))]
        for key in ("question_original", "question_edited"):
            q = str(task.get(key) or "")
            for w in check_prompt_no_leakage(q, answers=answers):
                leaks.append({"item": task.get("item_id"), "field": key, "warning": w})
        for key in ("original_image_path", "edited_image_path"):
            p = str(task.get(key) or "")
            for w in check_path_no_leakage(p):
                leaks.append({"item": task.get("item_id"), "field": key, "warning": w})
    return _finding("prompt_leakage", "high", not leaks, n_leaks=len(leaks), examples=leaks[:5])


def _non_visual_gameability(tasks: list[dict], threshold: float) -> dict:
    context = build_context(tasks)
    per_baseline = {}
    gameable = []
    for name in NON_VISUAL_BASELINES:
        rows = []
        for task in tasks:
            raw_o, raw_e = baseline_raw_outputs(name, task, context, seed=0)
            rows.append(score_item(task, raw_o, raw_e, strict=True))
        summary = summarize(rows)
        per_baseline[name] = summary
        if summary["consistency"] is not None and summary["consistency"] > threshold:
            gameable.append({"baseline": name, "consistency": round(summary["consistency"], 4)})
    return _finding(
        "non_visual_gameability",
        "high",
        not gameable,
        threshold=threshold,
        gameable_baselines=gameable,
        per_baseline={k: {"consistency": v["consistency"], "accuracy": v["accuracy"]} for k, v in per_baseline.items()},
    )


def _answer_prior_imbalance(tasks: list[dict], threshold: float) -> dict:
    overall = Counter(str(t.get("answer_original")) for t in tasks)
    n = sum(overall.values()) or 1
    top_fraction = overall.most_common(1)[0][1] / n if overall else 0.0
    by_family: dict[str, float] = {}
    fam_counts: dict[str, Counter] = {}
    for t in tasks:
        fam_counts.setdefault(str(t.get("task_family")), Counter())[str(t.get("answer_original"))] += 1
    skewed_families = []
    for fam, counts in fam_counts.items():
        fn = sum(counts.values()) or 1
        frac = counts.most_common(1)[0][1] / fn
        by_family[fam] = round(frac, 4)
        if frac > threshold:
            skewed_families.append({"family": fam, "top_fraction": round(frac, 4)})
    passed = top_fraction <= threshold and not skewed_families
    return _finding(
        "answer_prior_imbalance",
        "medium",
        passed,
        threshold=threshold,
        overall_top_fraction=round(top_fraction, 4),
        by_family=by_family,
        skewed_families=skewed_families,
    )


def _design_balance(tasks: list[dict], min_fraction: float) -> dict:
    n = len(tasks) or 1
    issues = []
    distributions = {}
    for attr in ("task_family", "domain", "edit_type", "required_change"):
        counts = Counter(str(t.get(attr)) for t in tasks)
        distributions[attr] = dict(sorted(counts.items()))
        if attr == "required_change":
            # Want both change and no_change present and not vanishingly rare.
            for level in ("change", "no_change"):
                frac = counts.get(level, 0) / n
                if frac < min_fraction:
                    issues.append({"attribute": attr, "level": level, "fraction": round(frac, 4)})
    return _finding(
        "design_balance",
        "medium",
        not issues,
        min_fraction=min_fraction,
        distributions=distributions,
        issues=issues,
    )


def _question_diversity(tasks: list[dict], dominance: float) -> dict:
    counts = Counter(str(t.get("question_original")) for t in tasks)
    n = sum(counts.values()) or 1
    top_fraction = counts.most_common(1)[0][1] / n if counts else 0.0
    return _finding(
        "question_diversity",
        "low",
        top_fraction <= dominance,
        dominance=dominance,
        unique_questions=len(counts),
        top_template_fraction=round(top_fraction, 4),
    )


def _mcq_position_prior(tasks: list[dict]) -> dict:
    mcq = [t for t in tasks if str(t.get("answer_format")) == "multiple_choice"]
    if not mcq:
        return _finding("mcq_position_prior", "info", True, n_mcq=0, note="no multiple-choice items")
    counts = Counter(str(t.get("answer_original")) for t in mcq)
    n = sum(counts.values()) or 1
    top_fraction = counts.most_common(1)[0][1] / n
    return _finding(
        "mcq_position_prior",
        "medium",
        top_fraction <= 0.5,
        n_mcq=len(mcq),
        top_option_fraction=round(top_fraction, 4),
    )


def run_adversarial_audit(
    tasks_path: str | Path,
    out_dir: str | Path | None = None,
    gameable_consistency_threshold: float = DEFAULT_GAMEABLE_CONSISTENCY,
    prior_imbalance_threshold: float = DEFAULT_PRIOR_IMBALANCE,
    template_dominance_threshold: float = DEFAULT_TEMPLATE_DOMINANCE,
    min_group_fraction: float = DEFAULT_MIN_GROUP_FRACTION,
) -> dict:
    tasks = read_jsonl(tasks_path)
    findings = [
        _label_consistency(tasks),
        _prompt_leakage(tasks),
        _non_visual_gameability(tasks, gameable_consistency_threshold),
        _answer_prior_imbalance(tasks, prior_imbalance_threshold),
        _design_balance(tasks, min_group_fraction),
        _question_diversity(tasks, template_dominance_threshold),
        _mcq_position_prior(tasks),
    ]
    high_fail = [f for f in findings if f["severity"] == "high" and not f["passed"]]
    medium_fail = [f for f in findings if f["severity"] == "medium" and not f["passed"]]
    result = {
        "audit": "prompt_task_adversarial_audit",
        "tasks_path": str(tasks_path),
        "n_tasks": len(tasks),
        "passed": not high_fail,
        "high_severity_failures": [f["check"] for f in high_fail],
        "medium_severity_warnings": [f["check"] for f in medium_fail],
        "findings": findings,
        "evidence_claims_made": False,
        "vlm_inference_run": False,
    }
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        write_json(out / "adversarial_audit.json", result)
        (out / "adversarial_audit.md").write_text(render_report(result), encoding="utf-8")
        result["out_dir"] = str(out)
    return result


def render_report(result: dict) -> str:
    status = "PASS" if result["passed"] else "FAIL"
    lines = [
        "# Prompt/Task Adversarial Audit (V2.3)",
        "",
        f"Overall: **{status}** ({result['n_tasks']} tasks). High-severity failures block real runs.",
        "",
        "| Check | Severity | Status | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for f in result["findings"]:
        mark = "pass" if f["passed"] else "FAIL"
        detail = "; ".join(
            f"{k}={v}" for k, v in f.items() if k not in {"check", "severity", "passed"} and not (isinstance(v, (list, dict)) and not v)
        )
        detail = (detail or "ok").replace("|", "/")
        if len(detail) > 220:
            detail = detail[:217] + "..."
        lines.append(f"| `{f['check']}` | {f['severity']} | {mark} | {detail} |")
    lines += [
        "",
        "Construct validity hinges on non-visual baselines failing this task; a high",
        "severity failure means the gap could be explained without seeing the change.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC prompt/task adversarial audit (V2.3)")
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--out-dir")
    parser.add_argument("--gameable-threshold", type=float, default=DEFAULT_GAMEABLE_CONSISTENCY)
    parser.add_argument("--prior-imbalance-threshold", type=float, default=DEFAULT_PRIOR_IMBALANCE)
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args(argv)
    result = run_adversarial_audit(
        args.tasks,
        out_dir=args.out_dir,
        gameable_consistency_threshold=args.gameable_threshold,
        prior_imbalance_threshold=args.prior_imbalance_threshold,
    )
    print(json.dumps({"passed": result["passed"], "high": result["high_severity_failures"], "medium": result["medium_severity_warnings"]}, sort_keys=True))
    if not result["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
