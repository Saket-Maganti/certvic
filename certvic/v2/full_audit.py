"""Full V2 system audit.

Verifies the project is ready to run real tiny/main pilots and produce paper
outputs without breaking safety, cost, or claim discipline. Runs no inference,
no downloads, and makes no evidence claims.
"""

from __future__ import annotations

import argparse
import importlib
import json
from datetime import date
from pathlib import Path

from certvic.v2.baseline_audit import (
    FORBIDDEN_CLAIM_PHRASES,
    PAID_PROVIDER_NAMES,
    REPO_ROOT,
    run_baseline_audit,
)

V1_HANDOFFS = [
    "docs/V1_SMOKE_AUDIT_REPORT.md",
    "docs/V1_1_SCAFFOLD_HARDENING_REPORT.md",
    "docs/V1_2_REAL_PILOT_READINESS_REPORT.md",
    "docs/V1_3_ADE20K_MASK_MANIFEST_REPORT.md",
    "docs/V1_4_PILOT_CANDIDATE_EDIT_PLAN_REPORT.md",
    "docs/V1_5_TINY_EDIT_GENERATION_QUALITY_REPORT.md",
]

V2_HANDOFFS = [
    "docs/V2_BASELINE_AUDIT_REPORT.md",
    "docs/V2_LABEL_POLICY_TASK_FAMILY_REPORT.md",
    "docs/V2_EDIT_ENGINE_QUALITY_REPORT.md",
    "docs/V2_VISUAL_REVIEW_WORKFLOW_REPORT.md",
    "docs/V2_BASELINES_ABLATIONS_REPORT.md",
    "docs/V2_CERTIFICATION_POWER_REPORT.md",
    "docs/V2_RESULTS_REPORTING_REPORT.md",
    "docs/V2_FAILURE_TAXONOMY_GALLERY_REPORT.md",
    "docs/V2_RECIPE_FIRST_ARTIFACT_REPORT.md",
    "docs/V2_PAPER_SCAFFOLD_UPGRADE_REPORT.md",
    "docs/V2_TINY_REAL_PILOT_ORCHESTRATOR_REPORT.md",
    "docs/V2_TINY_EVAL_SCORING_REPORT.md",
    "docs/V2_OPEN_VLM_INFERENCE_READINESS_REPORT.md",
    "docs/V2_MAIN_PILOT_200_RUNBOOK_REPORT.md",
]

V2_CONFIGS = [
    "configs/ade20k_label_policy.yaml",
    "configs/edit_quality.yaml",
    "configs/certification_policy.yaml",
    "configs/tiny_reviewed_eval.yaml",
    "configs/release_recipe.yaml",
]

V2_RUNBOOKS = [
    "docs/TINY_REAL_PILOT_RUNBOOK.md",
    "docs/TINY_EVAL_RUNBOOK.md",
    "docs/MAIN_PILOT_200_RUNBOOK.md",
    "docs/PILOT_GATE_CHECKS.md",
]

# Important V2 command modules that must import.
V2_COMMAND_MODULES = [
    "certvic.v2.baseline_audit",
    "certvic.data.label_policy",
    "certvic.data.label_policy_report",
    "certvic.edit.engines",
    "certvic.validation.export_visual_review",
    "certvic.validation.aggregate_visual_review",
    "certvic.data.apply_visual_review",
    "certvic.eval.run_ablations",
    "certvic.reporting.ablations",
    "certvic.metrics.power",
    "certvic.metrics.power_plan",
    "certvic.metrics.certification_policy",
    "certvic.reporting.build_v2_report",
    "certvic.reporting.failure_gallery_v2",
    "certvic.release.build_artifact",
    "certvic.eval.vlm_preflight",
    "certvic.pipeline.run_tiny_pilot",
    "certvic.pipeline.run_tiny_eval",
    "certvic.pipeline.pilot_gate_check",
    # V2.x pre-run hardening modules.
    "certvic.metrics.anytime_cs",
    "certvic.sim.anytime_validity",
    "certvic.validation.paper_numbers_guard",
    "certvic.eval.adversarial_audit",
    "certvic.edit.diffusion_preflight",
    "certvic.v2.reviewer_attack_harness",
    "certvic.v2.pre_run_master_audit",
]

FORBIDDEN_SCAN_DOCS = [
    "paper/main.tex",
    "paper/sections/05_results.tex",
    "docs/CLAIM_LEDGER.md",
    "docs/PAPER_PLAN.md",
]


def _check(name: str, passed: bool, **detail) -> dict:
    return {"name": name, "passed": bool(passed), **detail}


def _files_exist(root: Path, rels: list[str]) -> dict:
    missing = [r for r in rels if not (root / r).exists()]
    return {"expected": len(rels), "missing": missing}


def run_full_audit(repo_root: str | Path | None = None) -> dict:
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    checks: list[dict] = []

    v1 = _files_exist(root, V1_HANDOFFS)
    checks.append(_check("v1_handoffs_exist", not v1["missing"], **v1))
    v2 = _files_exist(root, V2_HANDOFFS)
    checks.append(_check("v2_handoffs_exist", not v2["missing"], **v2))
    cfg = _files_exist(root, V2_CONFIGS)
    checks.append(_check("v2_configs_exist", not cfg["missing"], **cfg))
    rb = _files_exist(root, V2_RUNBOOKS)
    checks.append(_check("runbooks_exist", not rb["missing"], **rb))

    import_errors: list[str] = []
    for module in V2_COMMAND_MODULES:
        try:
            importlib.import_module(module)
        except Exception as exc:
            import_errors.append(f"{module}: {exc}")
    checks.append(_check("v2_commands_import", not import_errors, errors=import_errors, checked=len(V2_COMMAND_MODULES)))

    checks.append(_check("no_paid_provider_enabled", PAID_PROVIDER_NAMES == set(), paid=sorted(PAID_PROVIDER_NAMES)))

    # zero-cost policy doc + release audit availability
    checks.append(_check("zero_cost_policy_exists", (root / "docs/ZERO_COST_POLICY.md").exists()))
    checks.append(_check("claim_policy_exists", (root / "configs/certification_policy.yaml").exists()))
    checks.append(_check("release_audit_available", (root / "certvic/release/build_artifact.py").exists()))
    checks.append(_check("gate_checks_available", (root / "certvic/pipeline/pilot_gate_check.py").exists()))

    # forbidden claims / fake results scan
    hits: list[str] = []
    for rel in FORBIDDEN_SCAN_DOCS:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN_CLAIM_PHRASES:
            if phrase in text:
                hits.append(f"{rel}: {phrase}")
    checks.append(_check("no_forbidden_claims", not hits, hits=hits))

    results_tex = root / "paper/sections/05_results.tex"
    placeholder = "[RESULT REQUIRED]" in results_tex.read_text(encoding="utf-8") if results_tex.exists() else False
    checks.append(_check("no_fake_paper_results", placeholder, results_placeholder=placeholder))

    # baseline audit still green
    baseline = run_baseline_audit(root)
    checks.append(_check("baseline_audit_passes", baseline["passed"], n_passed=baseline["n_passed"], n_checks=baseline["n_checks"]))

    passed = all(c["passed"] for c in checks)
    return {
        "audit": "v2_full_system_audit",
        "repo_root": str(root),
        "passed": passed,
        "n_checks": len(checks),
        "n_passed": sum(1 for c in checks if c["passed"]),
        "checks": checks,
        "evidence_claims_made": False,
        "downloads_attempted": False,
        "gpu_required": False,
        "vlm_inference_run": False,
    }


def render_report(result: dict) -> str:
    status = "PASS" if result["passed"] else "FAIL"
    lines = [
        "# V2 Full System Audit Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Overall status: **{status}** ({result['n_passed']}/{result['n_checks']} checks passed)",
        "",
        "Verifies V1-V1.5 + V2 handoffs, configs, runbooks, command imports, zero-cost,",
        "claim discipline, and no fake paper results. No inference, no downloads.",
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
    lines += ["", "See docs/V2_COMMAND_INDEX.md and docs/V2_NEXT_ACTIONS.md.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC V2 full system audit")
    parser.add_argument("--out", default="docs/V2_FULL_SYSTEM_AUDIT_REPORT.md")
    parser.add_argument("--json-out")
    parser.add_argument("--repo-root")
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args(argv)
    result = run_full_audit(args.repo_root)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "n_passed": result["n_passed"], "n_checks": result["n_checks"], "report": args.out}, sort_keys=True))
    if not result["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
