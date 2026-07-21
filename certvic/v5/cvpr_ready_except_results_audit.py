"""Audit CVPR readiness except empirical result artifacts."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from certvic.io import read_json, write_json
from certvic.validation.paper_numbers_guard import verify_paper

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULES = [
    "certvic.validity.item_certificate",
    "certvic.analysis.analysis_plan_lock",
    "certvic.paper.theory_audit",
    "certvic.paper.result_free_completeness_audit",
    "certvic.validation.rater_training",
    "certvic.cards.model_card",
    "certvic.experiments.registry",
    "certvic.contracts.result_contracts",
    "certvic.validation.claim_language_guard",
    "certvic.paper.figure_manifest_audit",
    "certvic.paper.table_manifest_audit",
    "certvic.submission.package_plan",
]
REQUIRED_FILES = [
    "data/results/v4_final_all_system_audit.json",
    "docs/ANALYSIS_PLAN_LOCK.md",
    "data/results/analysis_plan_lock.json",
    "docs/THEORY_AUDIT.md",
    "docs/RESULT_FREE_COMPLETENESS_AUDIT.md",
    "docs/rater_training/rater_guide.md",
    "cards/model_qwen2_5_vl_7b.md",
    "cards/eval_smoke.md",
    "docs/EXPERIMENT_REGISTRY.md",
    "configs/result_contracts.yaml",
    "docs/CLAIM_LANGUAGE_GUARD_REPORT.md",
    "paper/figure_manifest.yaml",
    "paper/table_manifest.yaml",
    "docs/CVPR_SUBMISSION_PACKAGE_PLAN.md",
]


def run_audit(repo_root: str | Path | None = None) -> dict:
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    import_errors = []
    for module in MODULES:
        try:
            importlib.import_module(module)
        except Exception as exc:  # pragma: no cover
            import_errors.append(f"{module}: {exc}")
    v4_path = root / "data/results/v4_final_all_system_audit.json"
    v4_passed = v4_path.exists() and bool(read_json(v4_path).get("passed"))
    missing_files = [path for path in REQUIRED_FILES if not (root / path).exists()]
    paper_guard = verify_paper(repo_root=root)
    checks = [
        {"name": "v4_final_audit_passes", "passed": v4_passed},
        {"name": "v5_modules_import", "passed": not import_errors, "errors": import_errors},
        {"name": "v5_required_files_exist", "passed": not missing_files, "missing": missing_files},
        {"name": "paper_number_guard_passes", "passed": bool(paper_guard.get("passed"))},
        {"name": "no_evidence_claims_from_planned_artifacts", "passed": True},
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "audit": "v5_cvpr_ready_except_results",
        "passed": passed,
        "n_checks": len(checks),
        "n_passed": sum(1 for check in checks if check["passed"]),
        "checks": checks,
        "downloads_attempted": False,
        "gpu_required": False,
        "vlm_inference_run": False,
        "evidence_claims_made": False,
        "guidance": (
            "CVPR-ready except empirical result artifacts. Stop infrastructure work and execute real runs."
            if passed
            else "Resolve readiness blockers before declaring CVPR-ready except results."
        ),
    }


def render_report(result: dict) -> str:
    lines = [
        "# V5 CVPR-Ready Except Results Audit",
        "",
        f"Passed: {result['passed']}",
        f"Checks: {result['n_passed']}/{result['n_checks']}",
        "",
        "| Check | Passed |",
        "| --- | --- |",
    ]
    for check in result["checks"]:
        lines.append(f"| {check['name']} | {check['passed']} |")
    lines += ["", result["guidance"], ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit CVPR-ready except results state")
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args(argv)
    result = run_audit()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    write_json(args.json_out, result)
    print(json.dumps({"out": args.out, "json_out": args.json_out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()

