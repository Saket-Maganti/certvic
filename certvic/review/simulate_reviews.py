"""Simulated CVPR reviews from current artifacts (V3 prompt 14).

Six harsh reviewer profiles assess the paper's *current* state. The cardinal rule:
if empirical results are missing, every reviewer complains about it and rejects --
no reviewer hallucinates numbers that do not exist. Descriptive prep only.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from certvic.io import ensure_parent, read_json

REVIEWER_PROFILES = [
    "benchmark_skeptic",
    "stats_reviewer",
    "vision_editing_reviewer",
    "reproducibility_reviewer",
    "construct_validity_reviewer",
    "open_model_scope_reviewer",
]

# CVPR-style score: 1 strong reject ... 5 strong accept.
NO_RESULTS_SCORE = 2


def assess_state(paper_dir: str, reports_root: str) -> dict:
    paper = Path(paper_dir)
    results_tex = paper / "sections" / "05_results.tex"
    placeholders = results_tex.read_text(encoding="utf-8").count("[RESULT REQUIRED]") if results_tex.exists() else 0

    reports = Path(reports_root)
    cl = reports / "claim_ledger.json"
    certified = False
    if cl.exists():
        raw = read_json(cl)
        claims = raw if isinstance(raw, list) else raw.get("claims", [])
        certified = any(str(c.get("certification_status", "")).lower() == "certified" and c.get("safe") for c in claims)

    has_results = placeholders == 0 and certified
    # Infrastructure that backs specific defenses (available regardless of results).
    def _exists(rel: str) -> bool:
        return (Path(rel)).exists()

    infra = {
        "edit_detectability": _exists("certvic/validation/edit_detectability.py"),
        "cluster_diagnostics": _exists("certvic/metrics/cluster_diagnostics.py"),
        "anytime_valid_cs": _exists("certvic/metrics/anytime_cs.py"),
        "paper_number_guard": _exists("certvic/validation/paper_numbers_guard.py"),
        "human_review_ops": _exists("certvic/validation/review_batches.py"),
        "recipe_release": _exists("certvic/release/build_artifact.py"),
        "ablations": _exists("certvic/eval/run_ablations.py"),
    }
    return {
        "placeholders_remaining": placeholders,
        "certified_claim": certified,
        "has_results": has_results,
        "infrastructure": infra,
    }


def _review(profile: str, state: dict) -> dict:
    has_results = state["has_results"]
    infra = state["infrastructure"]
    strengths: list[str] = []
    weaknesses: list[str] = []
    questions: list[str] = []

    # Cardinal rule: complain honestly when results are missing.
    if not has_results:
        weaknesses.append(
            f"No empirical results: {state['placeholders_remaining']} result cells are still "
            "[RESULT REQUIRED] and no certified claim exists. The paper cannot be evaluated on findings yet."
        )
        questions.append("What does even a single tiny real open-VLM run on reviewed edits show?")

    if profile == "benchmark_skeptic":
        strengths.append("The certified-evaluation-protocol framing is more than yet-another accuracy benchmark.")
        weaknesses.append("Dataset/benchmark contribution must be justified beyond standard VQA accuracy.")
        questions.append("Why is decision-update under intervention the right target vs fixed-image accuracy?")
    elif profile == "stats_reviewer":
        if infra["anytime_valid_cs"]:
            strengths.append("Anytime-valid CS is the right tool for optional stopping; native + confseq backends exist.")
        weaknesses.append("Multiplicity across subgroups and clustered dependence (repeated sources) must be controlled.")
        if not infra["cluster_diagnostics"]:
            weaknesses.append("No clustered-dependence sensitivity analysis.")
        questions.append("What is the effective-n after accounting for per-source clustering?")
    elif profile == "vision_editing_reviewer":
        weaknesses.append("Edit realism / single-factor validity is the make-or-break; crude edits would confound the gap.")
        if infra["edit_detectability"]:
            strengths.append("An edit-detectability probe quantifies artifact-confound risk.")
        else:
            weaknesses.append("No artifact-detectability analysis.")
        questions.append("Can a trivial classifier separate edited from original images (artifact confound)?")
    elif profile == "reproducibility_reviewer":
        if infra["recipe_release"]:
            strengths.append("Recipe-first release (pointers/hashes/scripts) avoids rehosting pixels.")
        weaknesses.append("Need exact seeds, environment, and dataset-root instructions for full reproduction.")
        questions.append("Can the full pipeline be reproduced on free compute from the released recipe?")
    elif profile == "construct_validity_reviewer":
        weaknesses.append("Must show the task is not gameable without vision (text-only / caption-only / answer-prior baselines).")
        if infra["ablations"]:
            strengths.append("Ablation/baseline infrastructure is present.")
        if infra["human_review_ops"]:
            strengths.append("Human review with IAA and adjudication is set up.")
        questions.append("Do non-visual baselines stay below the consistency threshold, with reported IAA?")
    elif profile == "open_model_scope_reviewer":
        weaknesses.append("Only open-local models are evaluated; generalization claims must be scoped accordingly.")
        questions.append("How many open VLMs, and how do you scope claims about closed/frontier models?")

    score = NO_RESULTS_SCORE if not has_results else 4 if strengths and len(weaknesses) <= 2 else 3
    recommendation = "reject" if score <= 2 else "borderline" if score == 3 else "weak accept"
    return {
        "profile": profile,
        "score": score,
        "recommendation": recommendation,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "questions": questions,
        "complained_about_missing_results": not has_results,
        "hallucinated_results": False,
    }


def simulate_reviews(paper_dir: str, reports_root: str) -> dict:
    state = assess_state(paper_dir, reports_root)
    reviews = [_review(p, state) for p in REVIEWER_PROFILES]
    scores = [r["score"] for r in reviews]
    return {
        "simulation": "reviewer_simulation",
        "paper_dir": paper_dir,
        "reports_root": reports_root,
        "state": state,
        "reviews": reviews,
        "mean_score": round(sum(scores) / len(scores), 2),
        "all_complain_when_no_results": (not state["has_results"]) == all(r["complained_about_missing_results"] for r in reviews),
        "any_hallucinated_results": any(r["hallucinated_results"] for r in reviews),
        "evidence_claims_made": False,
    }


def render_reviews_md(result: dict) -> str:
    lines = [
        "# Simulated CVPR Reviews",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Paper: `{result['paper_dir']}`  |  reports: `{result['reports_root']}`",
        f"Mean score: {result['mean_score']} / 5  (results present: {result['state']['has_results']})",
        "",
        "Honest simulation: when results are missing, reviewers complain rather than invent numbers.",
        "",
    ]
    for r in result["reviews"]:
        lines.append(f"## {r['profile']} — score {r['score']}/5 ({r['recommendation']})")
        lines.append("")
        if r["strengths"]:
            lines.append("**Strengths**")
            lines += [f"- {s}" for s in r["strengths"]]
        lines.append("")
        lines.append("**Weaknesses**")
        lines += [f"- {w}" for w in r["weaknesses"]]
        lines.append("")
        lines.append("**Questions**")
        lines += [f"- {q}" for q in r["questions"]]
        lines.append("")
    return "\n".join(lines)


def write_outputs(result: dict, out_dir: str) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {"reviews_json": str(out / "reviews.json"), "reviews_md": str(out / "reviews.md")}
    Path(paths["reviews_json"]).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    Path(paths["reviews_md"]).write_text(render_reviews_md(result), encoding="utf-8")
    return paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC reviewer simulation")
    parser.add_argument("--paper-dir", default="paper")
    parser.add_argument("--reports-root", default="data/results")
    parser.add_argument("--out-dir", default="docs/reviewer_simulation")
    args = parser.parse_args(argv)
    result = simulate_reviews(args.paper_dir, args.reports_root)
    ensure_parent(Path(args.out_dir) / "x")
    paths = write_outputs(result, args.out_dir)
    print(json.dumps({
        "mean_score": result["mean_score"],
        "has_results": result["state"]["has_results"],
        "any_hallucinated_results": result["any_hallucinated_results"],
        **paths,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
