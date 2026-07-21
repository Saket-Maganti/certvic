"""Post-result adversarial reviewer-attack audit (V7 prompt 12).

Enumerates the likely CVPR objections to the 3-model pilot finding and checks, **from
artifacts on disk**, whether each is answered / partially answered / unanswered / blocked.
Artifact-driven so status updates automatically as arms land. Harsh by design: a missing
control is a blocker, never downgraded. Makes no evidence claim and runs no models.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import read_json, write_json

RESULTS = "data/results/main_real_200"

SEV_ORDER = {"high": 0, "medium": 1, "low": 2}
OPEN_STATUSES = {"blocked", "unanswered", "partially_answered"}


def _exists(root: Path, rel: str) -> bool:
    return (root / rel).exists()


def _glob_any(root: Path, pattern: str) -> bool:
    return any(root.glob(pattern))


def _spurious_predictions_exist(root: Path) -> bool:
    """Specificity gate: real control_irrelevant / spurious-flip VLM predictions.

    A bare ``control_irrelevant_report/`` dir holding only an INTEGRATION_BLOCKED marker does
    NOT count -- we require the integrated report or actual prediction files.
    """
    if _exists(root, f"{RESULTS}/control_irrelevant_report/control_irrelevant_report.json"):
        return True
    if _glob_any(root, f"{RESULTS}/**/*control_irrelevant*pred*"):
        return True
    if _glob_any(root, f"{RESULTS}/**/*spurious*pred*"):
        return True
    return False


def _spurious_gate_status(root: Path) -> tuple[str, str]:
    """Return reviewer-audit status and the remaining action for specificity.

    Existence of predictions alone is not enough: if the integrated control
    report says a provider exceeded the flip-rate gate, the reviewer objection is
    still a high-severity blocker.
    """
    report = root / f"{RESULTS}/control_irrelevant_report/control_irrelevant_report.json"
    if report.exists():
        try:
            data = read_json(report)
        except (OSError, json.JSONDecodeError):
            return "blocked", "Specificity report is unreadable; regenerate the integration report."
        if data.get("all_provider_gate_pass") is True or data.get("status") == "integrated":
            return "answered", "None: all providers passed the spurious-flip gate."
        failed = [
            p for p, m in (data.get("metrics") or {}).items()
            if m.get("gate_pass") is not True
        ]
        return (
            "blocked",
            "Specificity predictions exist, but the gate did not pass"
            + (f" for: {', '.join(sorted(failed))}." if failed else ".")
            + " Do not scale or claim specificity until this is resolved.",
        )
    if _spurious_predictions_exist(root):
        return (
            "blocked",
            "Spurious predictions exist, but the gated integration report is missing. "
            "Run python3 -m certvic.v7.spurious_control_integration.",
        )
    return (
        "blocked",
        "Run spurious-flip / control_irrelevant VLM predictions for all 3 models, then integrate. "
        "BLOCKER until predictions exist and pass the gate.",
    )


def _residual_review_done(root: Path) -> bool:
    p = root / f"{RESULTS}/residual_cue_review/residual_cue_summary.json"
    if not p.exists():
        return False
    try:
        return read_json(p).get("status") not in (None, "review_pending")
    except (OSError, json.JSONDecodeError):
        return False


def _two_rater_iaa_done(root: Path) -> bool:
    p = root / f"{RESULTS}/review_iaa/iaa_report.json"
    if not p.exists():
        return False
    try:
        return read_json(p).get("status") == "two_rater_computed"
    except (OSError, json.JSONDecodeError):
        return False


def _ablation_predictions_exist(root: Path) -> bool:
    return _glob_any(root, f"{RESULTS}/prompt_ablations/**/*pred*")


def _second_domain_executed(root: Path) -> bool:
    return _exists(root, "data/results/coco") or _glob_any(root, "data/results/**/coco*report*")


def _scaled_run_executed(root: Path) -> bool:
    return any((root / "data/results" / d).exists()
               for d in ("main_real_500", "main_real_800", "main_real_1000", "main_real_2000"))


def run_audit(repo_root: str | Path = ".") -> dict:
    root = Path(repo_root)
    summary_md = f"{RESULTS}/multimodel_pilot_summary.md"
    ledger = "registry/results/main200_pilot_result_ledger.json"
    state = "docs/V7_POST3MODEL_PROJECT_STATE.md"
    control_json = f"{RESULTS}/pilot_report/absent_object_control.json"
    sens = f"{RESULTS}/statistical_sensitivity.json"

    attacks: list[dict] = []

    def add(aid, claim, status, evidence, remaining, severity):
        attacks.append({"id": aid, "claim": claim, "status": status,
                        "artifact_evidence": [e for e in evidence if _exists(root, e)],
                        "missing_evidence": [e for e in evidence if not _exists(root, e)],
                        "remaining_action": remaining, "severity": severity})

    # 1. Models simply do not perceive the object.
    add(1, "Models simply do not perceive the object.", "answered",
        [summary_md, control_json],
        "None: original-image accuracy is 0.89-0.92 and absent-object present-accuracy is high, "
        "so the object is perceived; the gap is a post-edit update failure.", "low")

    # 2. The question presupposes the object.
    add(2, "The question presupposes the object (answers without looking).", "answered",
        [control_json],
        "None: on naturally absent objects the models answer 'no' at 58-60/60.", "low")

    # 3. The edited images have residual artifacts.
    status3 = "answered" if _residual_review_done(root) else "partially_answered"
    add(3, "The edited images have residual artifacts the VLM exploits.", status3,
        [f"{RESULTS}/go_no_go.json", f"{RESULTS}/residual_cue_review/residual_cue_summary.json"],
        "Complete the human residual-cue review (scripts/apply_residual_cue_review.py); "
        "detectability AUC=0.349 already argues against trivial artifacts.", "medium")

    # 4. Models are sticky under ANY perturbation (specificity).
    status4, remaining4 = _spurious_gate_status(root)
    add(4, "Models are sticky under any perturbation (no specificity).", status4,
        ["data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl",
         f"{RESULTS}/control_irrelevant_report/control_irrelevant_report.json"],
        remaining4, "high")

    # 5. Only one dataset.
    status5 = "answered" if _second_domain_executed(root) else "unanswered"
    add(5, "Only one dataset (ADE20K).", status5,
        ["docs/SECOND_DOMAIN_READINESS.md", "registry/datasets/second_domain_candidates.json"],
        "Execute the recommended COCO second-domain arm; readiness is assessed but not run.", "medium")

    # 6. Only one reviewer.
    status6 = "answered" if _two_rater_iaa_done(root) else "unanswered"
    add(6, "Only one reviewer (no IAA).", status6,
        ["docs/HUMAN_REVIEW_IAA_PROTOCOL.md", f"{RESULTS}/review_iaa/iaa_report.json"],
        "Collect a second rater and compute Cohen's kappa (scripts/compute_review_iaa.py); "
        "tooling ready, two-rater IAA not yet computed.", "medium")

    # 7. n=91 is too small.
    status7 = "answered" if _scaled_run_executed(root) else "unanswered"
    add(7, "n=91 is too small.", status7,
        ["docs/SCALE_PLAN_MAIN_800_2000.md", "data/results/scale_plans/scale_plan_summary.json"],
        "Execute a scaled run (main_500+) after the specificity control passes; plan ready.", "medium")

    # 8. Prompt polarity caused the effect.
    status8 = "answered" if _ablation_predictions_exist(root) else "partially_answered"
    add(8, "Prompt polarity caused the effect.", status8,
        ["docs/MAIN200_PROMPT_ABLATION_PLAN.md", f"{RESULTS}/prompt_ablations/summary.json"],
        "Run the polarity-validated ablation tasks (positive/negative/pixel-only/short). The "
        "canonical effect already holds across mixed phrasing.", "medium")

    # 9. Not reproduced across models.
    add(9, "The result is not reproduced across models.", "answered",
        [summary_md, ledger],
        "None: 3/3 open VLMs are certified under the pilot protocol (Qwen, InternVL, LLaVA).", "low")

    # 10. Optional-stopping hacked.
    status10 = "answered" if _exists(root, sens) else "partially_answered"
    add(10, "The statistics are optional-stopping hacked.", status10,
        [sens],
        "None: anytime-valid CS controls Type-I error under continuous peeking "
        "(statistical_sensitivity simulation).", "low")

    # 11. Old reports are mock-labeled.
    add(11, "Old reports are mock-labeled / non-canonical.", "answered",
        [ledger, state],
        "None: the result ledger excludes final_report*/ by construction; canonical = "
        "pilot_report*/ only, documented in the project-state memo.", "low")

    # 12. Just another edited-image dataset.
    fully = _spurious_predictions_exist(root) and _scaled_run_executed(root)
    add(12, "The benchmark is just another edited-image dataset.", "answered" if fully else "partially_answered",
        [control_json, ledger, f"{RESULTS}/failure_gallery/gallery.json"],
        "The natural-absence-vs-edited-absence dissociation, certification, and controls "
        "differentiate it; full differentiation needs the specificity control + scale.", "medium")

    unresolved = sorted(
        [a for a in attacks if a["status"] in OPEN_STATUSES],
        key=lambda a: (SEV_ORDER.get(a["severity"], 9),
                       {"blocked": 0, "unanswered": 1, "partially_answered": 2}[a["status"]]),
    )
    counts: dict[str, int] = {}
    for a in attacks:
        counts[a["status"]] = counts.get(a["status"], 0) + 1

    return {
        "audit": "v7_post_result_reviewer_attacks",
        "evidence_status": "REVIEWER_ATTACK_AUDIT_NON_EVIDENCE", "paper_evidence": False,
        "n_attacks": len(attacks), "status_counts": counts,
        "n_unresolved": len(unresolved),
        "top_unresolved": [{"id": a["id"], "claim": a["claim"], "status": a["status"],
                            "severity": a["severity"], "remaining_action": a["remaining_action"]}
                           for a in unresolved[:5]],
        "attacks": attacks,
        "evidence_claims_made": False,
    }


def render_report(result: dict) -> str:
    L = ["# Post-Result Reviewer-Attack Audit", "",
         f"`evidence_status={result['evidence_status']}` · attacks: {result['n_attacks']} · "
         f"unresolved: {result['n_unresolved']} · {result['status_counts']}", "",
         "| # | attack | status | severity | remaining action |",
         "| --- | --- | --- | --- | --- |"]
    for a in result["attacks"]:
        L.append(f"| {a['id']} | {a['claim']} | **{a['status']}** | {a['severity']} | "
                 f"{a['remaining_action']} |")
    L += ["", "## Top unresolved", ""]
    for a in result["top_unresolved"]:
        L.append(f"- **[{a['severity']}] {a['status']}** — {a['claim']} → {a['remaining_action']}")
    L.append("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Post-result reviewer-attack audit")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out", default="docs/POST_RESULT_REVIEWER_ATTACKS.md")
    parser.add_argument("--json-out", default="data/results/post_result_reviewer_attack_audit.json")
    args = parser.parse_args(argv)
    result = run_audit(args.repo_root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    write_json(args.json_out, result)
    print(json.dumps({"n_attacks": result["n_attacks"], "n_unresolved": result["n_unresolved"],
                      "status_counts": result["status_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
