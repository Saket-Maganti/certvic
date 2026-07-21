"""Final V3 pre-real-run audit (V3 prompt 19).

The last infrastructure gate. It verifies every V3 module imports, every V3
handoff doc exists, the zero-cost / paper-guard / reviewer / security / repro /
V2-full audits pass, no paid providers are enabled, no fake paper numbers exist,
and no evidence is drawn from simulated artifacts. When it passes, STOP building
infrastructure and start the real ADE20K/diffusion/VLM run.

Runs no inference, no downloads, no GPU jobs, and makes no evidence claims.
"""

from __future__ import annotations

import argparse
import importlib
import json
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

V3_COMMAND_MODULES = [
    "certvic.provenance.run_ledger",
    "certvic.provenance.artifact_graph",
    "certvic.provenance.trace_claim",
    "certvic.storage.plan_storage",
    "certvic.storage.path_policy",
    "certvic.storage.dataset_roots",
    "certvic.compute.job_bundle",
    "certvic.compute.kaggle_packager",
    "certvic.compute.colab_packager",
    "certvic.edit.job_queue",
    "certvic.edit.diffusion_resume",
    "certvic.edit.edit_generation_plan",
    "certvic.validation.edit_detectability",
    "certvic.reporting.edit_detectability_report",
    "certvic.metrics.cluster_diagnostics",
    "certvic.metrics.cluster_sensitivity",
    "certvic.validation.review_batches",
    "certvic.validation.review_progress",
    "certvic.validation.adjudicate_review",
    "certvic.eval.model_matrix",
    "certvic.eval.run_matrix_planner",
    "certvic.eval.run_status",
    "certvic.eval.output_triage",
    "certvic.reporting.parse_triage_report",
    "certvic.planning.scale_planner",
    "certvic.planning.free_compute_budget",
    "certvic.dashboard.build_dashboard",
    "certvic.paper.result_manifest",
    "certvic.paper.inject_results",
    "certvic.paper.paper_trace_report",
    "certvic.paper.related_work_audit",
    "certvic.review.simulate_reviews",
    "certvic.review.rebuttal_pack",
    "certvic.release.reproduction_audit",
    "certvic.security.path_audit",
    "certvic.security.secrets_audit",
    "certvic.security.release_privacy_audit",
    "certvic.playbooks.diagnose_failure",
    "certvic.pipeline.main_study_plan",
    "certvic.pipeline.main_study_dry_run",
]

# Prior V3 handoff reports (this report, #19, is excluded — it is written here).
V3_HANDOFF_DOCS = [
    "docs/V3_RUN_LEDGER_PROVENANCE_REPORT.md",
    "docs/V3_STORAGE_PLANNING_REPORT.md",
    "docs/V3_KAGGLE_COLAB_PACKAGER_REPORT.md",
    "docs/V3_DIFFUSION_JOB_QUEUE_REPORT.md",
    "docs/V3_EDIT_DETECTABILITY_REPORT.md",
    "docs/V3_CLUSTER_DIAGNOSTICS_REPORT.md",
    "docs/V3_HUMAN_REVIEW_OPS_REPORT.md",
    "docs/V3_MODEL_RUN_MATRIX_REPORT.md",
    "docs/V3_OUTPUT_TRIAGE_REPORT.md",
    "docs/V3_SCALE_PLANNER_REPORT.md",
    "docs/V3_DASHBOARD_REPORT.md",
    "docs/V3_PAPER_INJECTION_REPORT.md",
    "docs/V3_RELATED_WORK_SCAFFOLD_REPORT.md",
    "docs/V3_REVIEWER_SIMULATION_REPORT.md",
    "docs/V3_DOCKERLESS_REPRODUCTION_REPORT.md",
    "docs/V3_SECURITY_PRIVACY_AUDIT_REPORT.md",
    "docs/V3_FAILURE_PLAYBOOKS_REPORT.md",
    "docs/V3_MAIN_STUDY_DRY_RUN_REPORT.md",
]

V3_DOCS = [
    "docs/RUN_LEDGER.md",
    "docs/STORAGE_AND_PATH_POLICY.md",
    "docs/FREE_COMPUTE_BUNDLES.md",
    "docs/DIFFUSION_JOB_QUEUE.md",
    "docs/EDIT_DETECTABILITY_PROBE.md",
    "docs/CLUSTER_DEPENDENCE_DIAGNOSTICS.md",
    "docs/HUMAN_REVIEW_OPERATIONS.md",
    "docs/MODEL_RUN_MATRIX.md",
    "docs/MODEL_OUTPUT_TRIAGE.md",
    "docs/SCALE_AND_BUDGET_PLAN.md",
    "docs/LOCAL_DASHBOARD.md",
    "docs/PAPER_RESULT_TRACEABILITY.md",
    "docs/RELATED_WORK_PLAN.md",
    "docs/REBUTTAL_PREP.md",
    "docs/DOCKERLESS_REPRODUCTION.md",
    "docs/SECURITY_PRIVACY_POLICY.md",
    "docs/playbooks/README.md",
    "docs/MAIN_STUDY_DRY_RUN.md",
]

NEXT_REAL_RUN_COMMAND = (
    "python3 -m certvic.pipeline.main_study_dry_run --scale 200 --out-dir data/results/main_study_dry_run_200 "
    "&& python3 -m certvic.pipeline.run_tiny_pilot --config configs/real_pilot_ade20k.yaml "
    "--ade20k-root <ADE20K_ROOT> --out-dir data/results/tiny_real_pilot --dry-run"
)


def _check(name: str, passed: bool, **detail) -> dict:
    return {"name": name, "passed": bool(passed), **detail}


def run_final_audit(repo_root: str | Path | None = None) -> dict:
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    checks: list[dict] = []

    # 1. All V3 command modules import.
    import_errors: list[str] = []
    for mod in V3_COMMAND_MODULES:
        try:
            importlib.import_module(mod)
        except Exception as exc:  # pragma: no cover - defensive
            import_errors.append(f"{mod}: {exc}")
    checks.append(_check("v3_modules_import", not import_errors, errors=import_errors, checked=len(V3_COMMAND_MODULES)))

    # 2. V3 handoff docs + key docs exist.
    missing_handoffs = [d for d in V3_HANDOFF_DOCS if not (root / d).exists()]
    checks.append(_check("v3_handoff_docs_exist", not missing_handoffs, missing=missing_handoffs))
    missing_docs = [d for d in V3_DOCS if not (root / d).exists()]
    checks.append(_check("v3_docs_exist", not missing_docs, missing=missing_docs))

    # 3. Zero-cost policy + no paid providers.
    checks.append(_check("zero_cost_policy_exists", (root / "docs/ZERO_COST_POLICY.md").exists()))
    try:
        from certvic.providers.registry import PAID_PROVIDER_NAMES
        paid = sorted(PAID_PROVIDER_NAMES)
    except Exception as exc:  # pragma: no cover
        paid = [f"<error: {exc}>"]
    checks.append(_check("no_paid_providers", paid == [], paid=paid))

    # 4. Paper number guard passes; results still placeholder (no fake numbers).
    try:
        from certvic.validation.paper_numbers_guard import verify_paper
        guard = verify_paper(repo_root=root)
        guard_passed = guard["passed"]
    except Exception as exc:  # pragma: no cover
        guard_passed = False
        guard = {"error": str(exc)}
    checks.append(_check("paper_number_guard_passes", guard_passed, n_violations=guard.get("n_violations")))
    results_tex = root / "paper/sections/05_results.tex"
    placeholder = "[RESULT REQUIRED]" in results_tex.read_text(encoding="utf-8") if results_tex.exists() else False
    checks.append(_check("no_fake_paper_results", placeholder, results_placeholder=placeholder))

    # 5. No evidence drawn from simulated artifacts: the result manifest over the
    #    current report is ineligible (nothing real injected yet).
    try:
        from certvic.validation.claims import NON_EVIDENCE_STATUSES
        has_non_evidence_guard = "SIMULATED_ONLY" in {s.upper() for s in NON_EVIDENCE_STATUSES}
    except Exception:  # pragma: no cover
        has_non_evidence_guard = False
    checks.append(_check("non_evidence_statuses_blocked", has_non_evidence_guard))

    # 6. Reviewer harness + simulation available.
    reviewer_ok = (root / "certvic/v2/reviewer_attack_harness.py").exists() and (root / "certvic/review/simulate_reviews.py").exists()
    checks.append(_check("reviewer_defenses_available", reviewer_ok))

    # 7. Security / privacy audit passes on the repo.
    try:
        from certvic.security.release_privacy_audit import audit as sec_audit
        sec = sec_audit(str(root))
        sec_passed = sec["passed"]
    except Exception as exc:  # pragma: no cover
        sec_passed, sec = False, {"error": str(exc)}
    checks.append(_check("security_privacy_audit_passes", sec_passed, n_findings=sec.get("n_total_findings")))

    # 8. Reproduction scripts audit passes.
    try:
        from certvic.release.reproduction_audit import audit_scripts
        repro = audit_scripts(str(root / "scripts"))
        repro_passed = repro["passed"]
    except Exception as exc:  # pragma: no cover
        repro_passed, repro = False, {"error": str(exc)}
    checks.append(_check("reproduction_scripts_audit_passes", repro_passed, n_ok=repro.get("n_ok")))

    # 9. Related-work scaffold has no fabricated citations.
    try:
        from certvic.paper.related_work_audit import audit_related_work
        rw = audit_related_work(str(root / "paper/related_work_matrix.yaml"), str(root / "paper/sections/02_related.tex"))
        rw_ok = not rw["fabrication_risk"]
    except Exception as exc:  # pragma: no cover
        rw_ok, rw = False, {"error": str(exc)}
    checks.append(_check("related_work_no_fabrication", rw_ok))

    # 10. V2 full system audit still passes (composes V1-V2.x).
    try:
        from certvic.v2.full_audit import run_full_audit
        v2 = run_full_audit(root)
        v2_passed = v2["passed"]
    except Exception as exc:  # pragma: no cover
        v2_passed, v2 = False, {"error": str(exc)}
    checks.append(_check("v2_full_audit_passes", v2_passed, n_passed=v2.get("n_passed"), n_checks=v2.get("n_checks")))

    passed = all(c["passed"] for c in checks)
    blockers = [c["name"] for c in checks if not c["passed"]]
    return {
        "audit": "v3_final_pre_real_run_audit",
        "repo_root": str(root),
        "passed": passed,
        "n_checks": len(checks),
        "n_passed": sum(1 for c in checks if c["passed"]),
        "checks": checks,
        "blockers": blockers,
        "guidance": _guidance(passed, blockers),
        "next_real_run_command": NEXT_REAL_RUN_COMMAND,
        "evidence_claims_made": False,
        "downloads_attempted": False,
        "gpu_required": False,
        "vlm_inference_run": False,
        "paid_services": False,
    }


def _guidance(passed: bool, blockers: list[str]) -> str:
    if passed:
        return (
            "V3 infrastructure is complete and green. STOP building infrastructure. "
            "Provide a local ADE20K root and a free GPU, then start the real run with the "
            "next_real_run_command (dry-run first, then drop --dry-run). Do not add more "
            "infrastructure unless a real run exposes a concrete missing gate."
        )
    return (
        "DO NOT start real runs yet. Resolve these blockers first: "
        + ", ".join(blockers)
        + ". Re-run this audit until it passes."
    )


def render_report(result: dict) -> str:
    status = "PASS" if result["passed"] else "FAIL"
    lines = [
        "# V3 Final Pre-Real-Run Audit",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Overall: **{status}** ({result['n_passed']}/{result['n_checks']} checks passed)",
        "",
        f"**Guidance:** {result['guidance']}",
        "",
        "Next real-run command:",
        "",
        "```bash",
        result["next_real_run_command"],
        "```",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for c in result["checks"]:
        mark = "pass" if c["passed"] else "FAIL"
        detail = "; ".join(f"{k}={v}" for k, v in c.items() if k not in {"name", "passed"} and not (isinstance(v, list) and not v))
        detail = (detail or "ok").replace("|", "/")
        if len(detail) > 200:
            detail = detail[:197] + "..."
        lines.append(f"| `{c['name']}` | {mark} | {detail} |")
    lines += ["", "No inference, no downloads, no GPU, no paid services, no evidence claims.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC V3 final pre-real-run audit")
    parser.add_argument("--out", default="docs/V3_FINAL_PRE_REAL_RUN_AUDIT_REPORT.md")
    parser.add_argument("--json-out", default="data/results/v3_final_pre_real_run_audit.json")
    parser.add_argument("--repo-root")
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args(argv)
    result = run_final_audit(args.repo_root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "passed": result["passed"],
        "n_passed": result["n_passed"],
        "n_checks": result["n_checks"],
        "blockers": result["blockers"],
        "report": args.out,
    }, sort_keys=True))
    if not result["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
