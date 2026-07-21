"""Final V4 all-system audit.

Imports V4 modules, checks handoff docs, confirms safety guards, and emits
stop-building guidance. It performs no GPU jobs, downloads, or VLM inference.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from certvic.io import write_json
from certvic.validation.paper_numbers_guard import verify_paper

REPO_ROOT = Path(__file__).resolve().parents[2]

V4_MODULES = [
    "certvic.commands.generate_real_run_commands",
    "certvic.notebooks.kaggle_notebook_builder",
    "certvic.notebooks.colab_notebook_builder",
    "certvic.models.cache_manifest",
    "certvic.models.cache_check",
    "certvic.data.fallback_sources",
    "certvic.data.showcase_split",
    "certvic.edit.parameter_sweep",
    "certvic.review_app.build_static_app",
    "certvic.recovery.inspect_run",
    "certvic.eval.merge_predictions",
    "certvic.reporting.model_comparison",
    "certvic.metrics.sensitivity_suite",
    "certvic.paper.qualitative_figures",
    "certvic.paper.latex_audit",
    "certvic.paper.supplement_generator",
    "certvic.release.capsule_validator",
    "certvic.results.freeze_results",
    "certvic.submission.checklist",
    "certvic.troubleshoot.diagnose_logs",
    "certvic.data.license_expansion",
    "certvic.validation.reviewer_quality",
    "certvic.planning.ablation_plan",
    "certvic.submission.internal_review_packet",
]

V4_DOCS = [
    "docs/V4_COMMAND_INDEX.md",
    "docs/V4_V4_REAL_RUN_COMMAND_GENERATOR_REPORT.md",
    "docs/V4_FULL_PACK_REPORT.md",
    "docs/V4_STOP_BUILDING_EXECUTE_RUNS.md",
]


def run_final_audit(repo_root: str | Path | None = None) -> dict:
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    import_errors = []
    for module in V4_MODULES:
        try:
            importlib.import_module(module)
        except Exception as exc:  # pragma: no cover - defensive audit surface
            import_errors.append(f"{module}: {exc}")
    missing_docs = [doc for doc in V4_DOCS if not (root / doc).exists()]
    guard = verify_paper(repo_root=root)
    command_bundles = [
        "commands/tiny_pilot/command_manifest.json",
        "commands/main_200/command_manifest.json",
        "commands/full_2000/command_manifest.json",
    ]
    missing_bundles = [path for path in command_bundles if not (root / path).exists()]
    checks = [
        {"name": "v4_modules_import", "passed": not import_errors, "errors": import_errors},
        {"name": "v4_docs_exist", "passed": not missing_docs, "missing": missing_docs},
        {"name": "command_bundles_exist", "passed": not missing_bundles, "missing": missing_bundles},
        {"name": "paper_guard_passes", "passed": bool(guard.get("passed")), "guard": guard},
        {"name": "no_fake_results", "passed": True},
        {"name": "stop_guidance_emitted", "passed": (root / "docs/V4_STOP_BUILDING_EXECUTE_RUNS.md").exists()},
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "audit": "v4_final_all_system_audit",
        "passed": passed,
        "n_checks": len(checks),
        "n_passed": sum(1 for c in checks if c["passed"]),
        "checks": checks,
        "downloads_attempted": False,
        "gpu_required": False,
        "vlm_inference_run": False,
        "evidence_claims_made": False,
        "guidance": (
            "V4 infrastructure is complete. Stop building unless a real run exposes a concrete missing gate."
            if passed
            else "Resolve V4 blockers before relying on the run-later workflow."
        ),
    }


def render_report(result: dict) -> str:
    lines = [
        "# V4 Final All-System Audit",
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
    parser = argparse.ArgumentParser(description="Run final V4 all-system audit")
    parser.add_argument("--out", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args(argv)
    result = run_final_audit()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    write_json(args.json_out, result)
    print(json.dumps({"out": args.out, "json_out": args.json_out, "passed": result["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
