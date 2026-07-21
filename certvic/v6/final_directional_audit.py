"""Final V6 directional audit."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from certvic.io import write_json
from certvic.paper.identity_audit import audit_identity
from certvic.paper.open_only_audit import audit_open_only
from certvic.paper.proof_bridge_audit import audit_proof_bridge
from certvic.paper.related_work_task_audit import audit_related_work
from certvic.paper.v6_visual_story_audit import audit_manifests
from certvic.validation.directional_language_guard import scan_directional_language

MODULES = (
    "certvic.validity.load_bearing",
    "certvic.reporting.validity_shift_report",
    "certvic.validation.detectability_gate",
    "certvic.pipeline.tiny_pilot_go_no_go",
    "certvic.dashboard.tiny_pilot_decision",
    "certvic.validity.filter_scores",
    "certvic.reporting.naive_vs_validity_gated",
    "certvic.edit.family_risk",
    "certvic.review.cvpr_bar_checker",
    "certvic.validation.directional_language_guard",
    "certvic.review.v6_attack_harness",
    "certvic.v6.stop_condition_audit",
)
REQUIRED_FILES = (
    "paper/figure_manifest_v6.yaml",
    "paper/table_manifest_v6.yaml",
    "docs/OPEN_ONLY_EVALUATION_RATIONALE.md",
    "docs/RELATED_WORK_SEARCH_TASKS.md",
    "paper/related_work_todo.yaml",
    "docs/CS_PROOF_BRIDGE.md",
    "docs/TINY_PILOT_DECISION_TEMPLATE.md",
    "docs/EDIT_FAMILY_RISK_MATRIX.md",
    "configs/cvpr_bar_thresholds.yaml",
    "docs/V6_STOP_BUILDING_BEGIN_RUNS.md",
    "docs/RUN_AFTER_V6_CHECKLIST.md",
    "docs/V6_FULL_PACK_REPORT.md",
    "docs/V6_COMMAND_INDEX.md",
    "docs/V6_FINAL_GO_NO_GO.md",
    "docs/audit_prompts/V6_POST_DIRECTIONAL_AUDIT_PROMPT.md",
    "docs/V6_SINGLE_FILE_HANDOFF_SUMMARY.md",
)


def _import_checks() -> list[str]:
    errors: list[str] = []
    for module in MODULES:
        try:
            importlib.import_module(module)
        except Exception as exc:  # pragma: no cover
            errors.append(f"{module}: {exc}")
    return errors


def _new_docs_text(root: Path) -> str:
    names = [
        "docs/V6_FULL_PACK_REPORT.md",
        "docs/V6_FINAL_GO_NO_GO.md",
        "docs/V6_SINGLE_FILE_HANDOFF_SUMMARY.md",
        "docs/RUN_AFTER_V6_CHECKLIST.md",
    ]
    return "\n".join((root / name).read_text(encoding="utf-8", errors="ignore") for name in names if (root / name).exists()).lower()


def run_audit(repo_root: str | Path = ".") -> dict:
    root = Path(repo_root)
    import_errors = _import_checks()
    missing_files = [path for path in REQUIRED_FILES if not (root / path).exists()]
    identity = audit_identity(root / "paper")
    visual_story = audit_manifests(root / "paper/figure_manifest_v6.yaml", root / "paper/table_manifest_v6.yaml")
    open_only = audit_open_only(root / "paper")
    related = audit_related_work(str(root / "paper/related_work_todo.yaml"))
    proof = audit_proof_bridge(root / "paper")
    directional = scan_directional_language([str(root / "paper"), str(root / "docs/V6_FULL_PACK_REPORT.md")])
    text = _new_docs_text(root)
    no_evidence_claims = "no evidence claims" in text and "[result required]" in text
    no_fake_numbers = "0.913" not in text and "0.42" not in text
    checks = [
        {"name": "v6_modules_import", "passed": not import_errors, "errors": import_errors},
        {"name": "v6_required_files_exist", "passed": not missing_files, "missing": missing_files},
        {"name": "identity_audit_passes", "passed": identity["passed"]},
        {"name": "visual_story_manifests_pass", "passed": visual_story["passed"]},
        {"name": "open_only_audit_passes", "passed": open_only["passed"]},
        {"name": "related_work_tasks_pass", "passed": related["passed"]},
        {"name": "proof_bridge_passes", "passed": proof["passed"]},
        {"name": "directional_language_guard_passes", "passed": directional["passed"], "findings": directional["findings"]},
        {"name": "no_evidence_claims", "passed": no_evidence_claims},
        {"name": "no_obvious_fake_numbers", "passed": no_fake_numbers},
    ]
    return {
        "audit": "v6_final_directional_audit",
        "passed": all(check["passed"] for check in checks),
        "n_checks": len(checks),
        "n_passed": sum(1 for check in checks if check["passed"]),
        "checks": checks,
        "downloads_attempted": False,
        "gpu_jobs_run": False,
        "vlm_inference_run": False,
        "evidence_claims_made": False,
        "next_action": "Run the ADE20K dry-run, then the 20-edit diffusion pilot, then edit detectability.",
        "deciding_number": "tiny-pilot edit detectability AUC",
    }


def render_report(result: dict) -> str:
    lines = [
        "# V6 Final Directional Audit",
        "",
        f"Passed: {result['passed']}",
        f"Checks: {result['n_passed']}/{result['n_checks']}",
        "",
        "| Check | Passed |",
        "| --- | --- |",
    ]
    for check in result["checks"]:
        lines.append(f"| {check['name']} | {check['passed']} |")
    lines += ["", f"Next action: {result['next_action']}", f"Deciding number: {result['deciding_number']}", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the final V6 directional audit")
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
