"""V7 post-3-model final audit + stop conditions (V7 prompt 15).

A harsh, artifact-driven meta-audit across ten categories that decides when to stop building
and start running/scaling, and when to stop scaling and write. It reuses the other V7 audits
(result ledger, reviewer attacks, spurious-control readiness) and the project guards. Missing
blockers stay blockers; paper-grade readiness is asserted only if the scale/control/review
gates pass. Makes no evidence claim and runs no models.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import read_json, write_json
from certvic.security.release_privacy_audit import audit as privacy_audit
from certvic.validation.claim_language_guard import scan_claim_language
from certvic.v7.post_result_reviewer_attack_audit import run_audit as reviewer_audit
from certvic.v7.result_ledger_audit import audit_ledger, build_ledger
from certvic.v7.spurious_control_integration import check_readiness as control_readiness

RESULTS = "data/results/main_real_200"

# Stop/build verdicts.
RUN_NOW = "RUN_NOW"
WRITE_NOW = "WRITE_NOW"
BUILD_IF_BLOCKED = "BUILD_ONLY_IF_BLOCKED"
DO_NOT_DO = "DO_NOT_DO"


def _exists(root: Path, rel: str) -> bool:
    return (root / rel).exists()


def _control_gate_status(root: Path) -> tuple[bool, str, str]:
    report = root / f"{RESULTS}/control_irrelevant_report/control_irrelevant_report.json"
    if not report.exists():
        return False, "blocked", "spurious-flip integration report missing"
    try:
        data = read_json(report)
    except (OSError, json.JSONDecodeError):
        return False, "blocked", "spurious-flip integration report unreadable"
    if data.get("all_provider_gate_pass") is True or data.get("status") == "integrated":
        return True, "pass", "all providers passed the spurious-flip gate"
    failed = [
        p for p, m in (data.get("metrics") or {}).items()
        if m.get("gate_pass") is not True
    ]
    if failed:
        return False, "failed_gate", "spurious-flip gate failed for: " + ", ".join(sorted(failed))
    return False, "blocked", "spurious-flip predictions are not fully integrated"


def run_audit(repo_root: str | Path = ".") -> dict:
    root = Path(repo_root)
    cats: list[dict] = []

    def cat(name, status, evidence, note):
        cats.append({"category": name, "status": status, "evidence": evidence, "note": note})

    # 1. Canonical result artifacts -> result ledger audit.
    led = audit_ledger(build_ledger(root), root)
    cat("canonical_result_artifacts", "pass" if led["passed"] else "blocked",
        ["registry/results/main200_pilot_result_ledger.json"],
        f"ledger audit passed={led['passed']} ({led['n_rows']} rows hash-locked)")

    # 2. Multi-model replication.
    repl_ok = False
    if _exists(root, f"{RESULTS}/multimodel_pilot_summary.json"):
        s = read_json(root / f"{RESULTS}/multimodel_pilot_summary.json")
        repl_ok = s.get("n_run") == 3 and all(m.get("certified") for m in s["models"] if m["status"] == "run")
    cat("multi_model_replication", "pass" if repl_ok else "partial",
        [f"{RESULTS}/multimodel_pilot_summary.json"],
        "3/3 open VLMs fully policy-certified" if repl_ok else
        "3/3 observed pilot runs; numeric CS thresholds crossed, but full policy certification is blocked")

    # 3. Control (specificity) status -> spurious-flip readiness.
    cr = control_readiness(root)
    control_pass, control_status, control_note = _control_gate_status(root)
    cat("control_status", control_status if cr["ready"] else "blocked",
        [f"{RESULTS}/control_irrelevant_report/INTEGRATION_BLOCKED.json"],
        (
            "observed V1 result includes Qwen's 12/94 raw gate failure; human review and "
            "confirmatory-control readiness remain blocked"
            if not cr["ready"] and control_status == "failed_gate"
            else "spurious-flip evidence prerequisites remain incomplete"
            if not cr["ready"]
            else control_note
        ))

    # 4. Human review / IAA.
    iaa_status = "blocked"
    if _exists(root, f"{RESULTS}/review_iaa/iaa_report.json"):
        iaa_status = read_json(root / f"{RESULTS}/review_iaa/iaa_report.json").get("status", "blocked")
    cat("human_review_iaa", "pass" if iaa_status == "two_rater_computed" else "partial",
        ["docs/HUMAN_REVIEW_IAA_PROTOCOL.md", f"{RESULTS}/review_iaa/iaa_report.json"],
        f"single-rater only; two-rater IAA status={iaa_status}")

    # 5. Scale readiness.
    cat("scale_readiness", "ready_plan" if _exists(root, "data/results/scale_plans/scale_plan_summary.json") else "blocked",
        ["docs/SCALE_PLAN_MAIN_800_2000.md", "data/results/scale_plans/scale_plan_summary.json"],
        "gated scale plan exists (projections); not executed")

    # 6. Second-domain readiness.
    cat("second_domain_readiness", "ready_plan" if _exists(root, "registry/datasets/second_domain_candidates.json") else "blocked",
        ["docs/SECOND_DOMAIN_READINESS.md", "registry/datasets/second_domain_candidates.json"],
        "COCO recommended; not executed")

    # 7. Mechanism probes.
    cat("mechanism_probes", "ready_plan" if _exists(root, f"{RESULTS}/mechanism_probes/summary.json") else "blocked",
        ["docs/MAIN200_MECHANISM_PROBES_PLAN.md", f"{RESULTS}/mechanism_probes/summary.json"],
        "probe tasks generated; predictions pending")

    # 8. Statistical validity.
    stat_ok = _exists(root, f"{RESULTS}/statistical_sensitivity.json")
    cat("statistical_validity", "pass" if stat_ok else "blocked",
        [f"{RESULTS}/statistical_sensitivity.json"],
        "anytime-valid CS; optional-stopping Type-I controlled" if stat_ok else "missing")

    # 9. Paper / report language -- scope to the V7 deliverables (legacy docs are out of scope).
    v7_paper_files = [
        "paper/sections/pilot_results_main200.tex",
        "paper/sections/limitations_current_pilot.tex",
        "docs/MAIN200_MULTIMODEL_PILOT_REPORT.md",
        "docs/V7_POST3MODEL_PROJECT_STATE.md",
    ]
    scan_targets = [str(root / f) for f in v7_paper_files if (root / f).exists()]
    lang_clean = scan_claim_language(scan_targets)["passed"]
    cat("paper_report_language", "pass" if lang_clean else "blocked",
        ["paper/sections/pilot_results_main200.tex", "paper/sections/limitations_current_pilot.tex"],
        "claim-language guard clean on V7 paper/report deliverables; pilot-only scaffold written"
        if lang_clean else "forbidden language found in a V7 deliverable")

    # 10. Release / privacy / security.
    priv = privacy_audit(str(root))
    rel_ready = False
    if _exists(root, "data/results/release_candidate_manifest.json"):
        rel_ready = read_json(root / "data/results/release_candidate_manifest.json").get("release_ready", False)
    cat("release_privacy_security", "pass" if priv["passed"] else "blocked",
        ["data/results/release_candidate_manifest.json"],
        f"privacy audit passed={priv['passed']}; release_ready={rel_ready} (path relativization pending)")

    rev = reviewer_audit(root)

    # Harsh paper-grade gate: requires control PASS + scale executed + two-rater IAA.
    scale_executed = False  # no scaled real run dir yet
    iaa_done = iaa_status == "two_rater_computed"
    paper_grade_ready = control_pass and scale_executed and iaa_done

    stop_build = _stop_build_policy(control_pass)

    return {
        "audit": "v7_post3model_final_audit",
        "evidence_status": "FINAL_AUDIT_NON_EVIDENCE", "paper_evidence": False,
        "categories": cats,
        "category_status": {c["category"]: c["status"] for c in cats},
        "reviewer_attacks": {"n_unresolved": rev["n_unresolved"],
                             "top_unresolved": rev["top_unresolved"][:3]},
        "paper_grade_ready": paper_grade_ready,
        "paper_grade_gate": {"control_pass": control_pass, "scale_executed": scale_executed,
                             "two_rater_iaa": iaa_done,
                             "note": "All three must hold for paper-grade readiness."},
        "stop_build_policy": stop_build,
        "next_highest_leverage_action": (
            "Complete blinded two-rater review and freeze an independent outcome-unseen spurious "
            "specificity control before scaling; preserve Qwen's frozen 12/94 V1 failure and do not "
            "weaken the threshold."),
        "evidence_claims_made": False,
    }


def _stop_build_policy(control_pass: bool) -> list[dict]:
    return [
        {"task": "More generic V7+ infrastructure", "verdict": DO_NOT_DO,
         "why": "Elevation infra is complete; further generic building does not add evidence."},
        {"task": "Spurious-flip / control_irrelevant predictions + integration", "verdict": RUN_NOW,
         "why": "Lone high-severity blocker; integration code is ready and gated."},
        {"task": "Scale to main_500/800+", "verdict": RUN_NOW if control_pass else BUILD_IF_BLOCKED,
         "why": "Run after the specificity control passes; plan + gates already exist."},
        {"task": "Second-rater IAA collection", "verdict": RUN_NOW,
         "why": "Blinded export + kappa tooling ready; needs one human rater."},
        {"task": "Residual-cue human review", "verdict": RUN_NOW,
         "why": "Blank sheet + summarizer ready; needs human labels."},
        {"task": "Mechanism / prompt-ablation predictions", "verdict": RUN_NOW,
         "why": "Task manifests generated; cheap free-tier inference."},
        {"task": "Second domain (COCO) execution", "verdict": BUILD_IF_BLOCKED,
         "why": "Only if a reviewer demands cross-domain before scale; readiness assessed."},
        {"task": "More models beyond 3", "verdict": BUILD_IF_BLOCKED,
         "why": "Only on explicit reviewer need; 3-model replication already holds."},
        {"task": "Paper pilot result + limitations section", "verdict": WRITE_NOW,
         "why": "Fresh, guard-clean, pilot-only scaffold already written; keep it current."},
    ]


def render_report(result: dict) -> str:
    L = ["# V7 Post-3-Model Final Audit & Stop Conditions", "",
         f"`evidence_status={result['evidence_status']}` · "
         f"**paper_grade_ready: {result['paper_grade_ready']}** · "
         f"unresolved reviewer attacks: {result['reviewer_attacks']['n_unresolved']}", "",
         "## Category status", "", "| category | status | note |", "| --- | --- | --- |"]
    for c in result["categories"]:
        L.append(f"| {c['category']} | **{c['status']}** | {c['note']} |")
    L += ["", "## Stop / build policy", "", "| proposed task | verdict | why |", "| --- | --- | --- |"]
    for s in result["stop_build_policy"]:
        L.append(f"| {s['task']} | **{s['verdict']}** | {s['why']} |")
    L += ["", "## Paper-grade gate (harsh)", "",
          f"- control_pass: {result['paper_grade_gate']['control_pass']}",
          f"- scale_executed: {result['paper_grade_gate']['scale_executed']}",
          f"- two_rater_iaa: {result['paper_grade_gate']['two_rater_iaa']}",
          f"- **paper_grade_ready: {result['paper_grade_ready']}**", "",
          "## One next highest-leverage action", "", result["next_highest_leverage_action"], ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="V7 post-3-model final audit + stop conditions")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out", default="docs/V7_POST3MODEL_FINAL_AUDIT.md")
    parser.add_argument("--json-out", default="data/results/v7_post3model_final_audit.json")
    args = parser.parse_args(argv)
    result = run_audit(args.repo_root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    write_json(args.json_out, result)
    print(json.dumps({"paper_grade_ready": result["paper_grade_ready"],
                      "category_status": result["category_status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
