"""V2 baseline audit.

Proves that the V1-V1.5 guarantees still hold before heavy V2 upgrades begin.
This module does not download data, run GPU jobs, run VLM inference, or make
evidence claims. It only inspects the repository for structural and policy
invariants and emits a markdown report.

Command:

    python3 -m certvic.v2.baseline_audit --out docs/V2_BASELINE_AUDIT_REPORT.md
"""

from __future__ import annotations

import argparse
import importlib
import json
from datetime import date
from pathlib import Path

import yaml

from certvic.providers.registry import (
    PAID_PROVIDER_NAMES,
    available_provider_names,
)
from certvic.validation.claims import FORBIDDEN_CLAIM_PHRASES, NON_EVIDENCE_STATUSES
from certvic.validation.paper_claims import scan_paper

# Repo root is three levels up from this file: certvic/v2/baseline_audit.py.
REPO_ROOT = Path(__file__).resolve().parents[2]

HANDOFF_DOCS = [
    "docs/V1_SMOKE_AUDIT_REPORT.md",
    "docs/V1_1_SCAFFOLD_HARDENING_REPORT.md",
    "docs/V1_2_REAL_PILOT_READINESS_REPORT.md",
    "docs/V1_3_ADE20K_MASK_MANIFEST_REPORT.md",
    "docs/V1_4_PILOT_CANDIDATE_EDIT_PLAN_REPORT.md",
    "docs/V1_5_TINY_EDIT_GENERATION_QUALITY_REPORT.md",
]

# Core command/library modules that must import cleanly without optional heavy
# dependencies. These are the modules behind the documented V1 commands.
CORE_COMMAND_MODULES = [
    "certvic.data.build_tasks",
    "certvic.data.manifest_checks",
    "certvic.eval.run_eval",
    "certvic.metrics.score_predictions",
    "certvic.reporting.build_report",
    "certvic.audit",
    "certvic.edit.generate_edits",
    "certvic.edit.quality_gates",
    "certvic.data.ade20k_adapter",
    "certvic.data.select_pilot_items",
    "certvic.edit.plan_edits",
]

SCHEMA_MODULES = [
    "certvic.schema.base",
    "certvic.schema.source",
    "certvic.schema.edit",
    "certvic.schema.task",
    "certvic.schema.prediction",
    "certvic.schema.manifest",
    "certvic.schema.claims",
]

CORE_CONFIGS = [
    "configs/smoke.yaml",
    "configs/real_pilot.yaml",
    "configs/real_pilot_ade20k.yaml",
    "configs/real_main.yaml",
    "configs/kaggle_open_vlm.yaml",
]

ZERO_COST_POLICY_DOC = "docs/ZERO_COST_POLICY.md"

# Files scanned for forbidden claim phrases and fabricated results.
PAPER_AND_RESULT_DOCS = [
    "paper/main.tex",
    "paper/sections/01_intro.tex",
    "paper/sections/02_related.tex",
    "paper/sections/03_method.tex",
    "paper/sections/04_experiments.tex",
    "paper/sections/05_results.tex",
    "paper/sections/06_limitations.tex",
    "paper/sections/07_conclusion.tex",
    "docs/CLAIM_LEDGER.md",
    "docs/PAPER_PLAN.md",
]

# V1.5 introduced these non-evidence statuses; the audit confirms they are still
# recognized by the claim machinery so generated-edit artifacts cannot be
# mistaken for paper evidence.
REQUIRED_NON_EVIDENCE_STATUSES = {
    "CANDIDATE_ONLY",
    "PLANNED_ONLY",
    "PREVIEW_ONLY",
    "GENERATED_EDIT_ONLY",
    "EDIT_READY_NON_EVIDENCE",
    "NOT_GENERATED",
}


def _check(name: str, passed: bool, **details) -> dict:
    return {"name": name, "passed": bool(passed), **details}


def _handoff_docs_check(root: Path) -> dict:
    missing = [doc for doc in HANDOFF_DOCS if not (root / doc).exists()]
    return _check(
        "handoff_docs_exist",
        not missing,
        expected=len(HANDOFF_DOCS),
        missing=missing,
    )


def _imports_check(name: str, modules: list[str]) -> dict:
    errors: list[str] = []
    for module in modules:
        try:
            importlib.import_module(module)
        except Exception as exc:  # pragma: no cover - failure path asserted in tests via monkeypatch
            errors.append(f"{module}: {exc}")
    return _check(name, not errors, checked=len(modules), errors=errors)


def _configs_check(root: Path) -> dict:
    missing = [cfg for cfg in CORE_CONFIGS if not (root / cfg).exists()]
    unreadable: list[str] = []
    for cfg in CORE_CONFIGS:
        path = root / cfg
        if path.exists():
            try:
                yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as exc:
                unreadable.append(f"{cfg}: {exc}")
    return _check(
        "core_configs_exist",
        not missing and not unreadable,
        expected=len(CORE_CONFIGS),
        missing=missing,
        unreadable=unreadable,
    )


def _paid_providers_check(root: Path) -> dict:
    errors: list[str] = []
    if PAID_PROVIDER_NAMES:
        errors.append(f"PAID_PROVIDER_NAMES is non-empty: {sorted(PAID_PROVIDER_NAMES)}")
    paid_in_registry = sorted(set(available_provider_names()) & set(PAID_PROVIDER_NAMES))
    if paid_in_registry:
        errors.append(f"paid providers exposed in registry: {paid_in_registry}")

    configs_enabling_paid: list[str] = []
    free_tier_default_on: list[str] = []
    for cfg in CORE_CONFIGS:
        path = root / cfg
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("paid_services_enabled") is True:
            configs_enabling_paid.append(cfg)
        if data.get("enable_free_tier_reference") is True:
            free_tier_default_on.append(cfg)
    if configs_enabling_paid:
        errors.append(f"configs enable paid services by default: {configs_enabling_paid}")
    if free_tier_default_on:
        errors.append(f"configs enable free-tier reference by default: {free_tier_default_on}")
    return _check(
        "no_paid_providers_enabled_by_default",
        not errors,
        errors=errors,
        configs_checked=len(CORE_CONFIGS),
    )


def _non_evidence_statuses_check() -> dict:
    missing = sorted(REQUIRED_NON_EVIDENCE_STATUSES - set(NON_EVIDENCE_STATUSES))
    return _check(
        "v1_5_non_evidence_statuses_recognized",
        not missing,
        required=sorted(REQUIRED_NON_EVIDENCE_STATUSES),
        recognized=sorted(NON_EVIDENCE_STATUSES),
        missing=missing,
    )


def _paper_no_fake_results_check(root: Path) -> dict:
    main_tex = root / "paper/main.tex"
    scan = scan_paper(str(main_tex)) if main_tex.exists() else {"passed": False, "errors": ["paper/main.tex missing"]}
    results_tex = root / "paper/sections/05_results.tex"
    placeholder_present = False
    if results_tex.exists():
        placeholder_present = "[RESULT REQUIRED]" in results_tex.read_text(encoding="utf-8")
    errors = list(scan.get("errors", []))
    if not placeholder_present:
        errors.append("results section lacks [RESULT REQUIRED] placeholders")
    return _check(
        "paper_contains_no_fake_results",
        scan.get("passed", False) and placeholder_present,
        scan_errors=scan.get("errors", []),
        scan_warnings=scan.get("warnings", []),
        results_placeholder_present=placeholder_present,
        errors=errors,
    )


def _zero_cost_policy_check(root: Path) -> dict:
    path = root / ZERO_COST_POLICY_DOC
    return _check(
        "zero_cost_policy_exists",
        path.exists(),
        path=ZERO_COST_POLICY_DOC,
    )


def _forbidden_claims_check(root: Path) -> dict:
    hits: list[str] = []
    scanned: list[str] = []
    for rel in PAPER_AND_RESULT_DOCS:
        path = root / rel
        if not path.exists():
            continue
        scanned.append(rel)
        text = path.read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN_CLAIM_PHRASES:
            if phrase in text:
                hits.append(f"{rel}: {phrase}")
    return _check(
        "no_forbidden_claim_phrases",
        not hits,
        scanned=scanned,
        hits=hits,
    )


def run_baseline_audit(repo_root: str | Path | None = None) -> dict:
    """Run all baseline-audit checks and return a structured result."""
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    checks = [
        _handoff_docs_check(root),
        _imports_check("core_command_modules_import", CORE_COMMAND_MODULES),
        _imports_check("schema_modules_import", SCHEMA_MODULES),
        _configs_check(root),
        _paid_providers_check(root),
        _non_evidence_statuses_check(),
        _paper_no_fake_results_check(root),
        _zero_cost_policy_check(root),
        _forbidden_claims_check(root),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "audit": "v2_baseline_audit",
        "repo_root": str(root),
        "passed": passed,
        "n_checks": len(checks),
        "n_passed": sum(1 for check in checks if check["passed"]),
        "checks": checks,
        "evidence_claims_made": False,
        "downloads_attempted": False,
        "gpu_required": False,
        "vlm_inference_run": False,
    }


def render_report(result: dict) -> str:
    status = "PASS" if result["passed"] else "FAIL"
    lines = [
        "# V2 Baseline Audit Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Overall status: **{status}** ({result['n_passed']}/{result['n_checks']} checks passed)",
        "",
        "This audit confirms that V1-V1.5 guarantees still hold before V2 upgrades.",
        "It performs no downloads, runs no GPU jobs, runs no VLM inference, and makes",
        "no evidence claims.",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in result["checks"]:
        mark = "pass" if check["passed"] else "FAIL"
        detail_keys = [k for k in check if k not in {"name", "passed"}]
        detail_parts = []
        for key in detail_keys:
            value = check[key]
            if isinstance(value, list) and not value:
                continue
            detail_parts.append(f"{key}={value}")
        detail = "; ".join(detail_parts) if detail_parts else "ok"
        detail = detail.replace("|", "/")
        if len(detail) > 220:
            detail = detail[:217] + "..."
        lines.append(f"| `{check['name']}` | {mark} | {detail} |")
    lines.extend(
        [
            "",
            "## Invariants asserted",
            "",
            "- V1-V1.5 handoff docs are present.",
            "- Core command and schema modules import without heavy optional deps.",
            "- Core configs exist and parse.",
            "- No paid provider is registered or enabled by default; free-tier reference is off by default.",
            "- V1.5 non-evidence statuses remain recognized by the claim gate.",
            "- Paper result sections remain `[RESULT REQUIRED]` with no fabricated numbers.",
            "- Zero-cost policy doc exists.",
            "- No forbidden claim phrases appear in paper/result docs.",
            "",
            "## Next prompt",
            "",
            "`02_V2_VISUAL_REVIEW_AND_APPROVAL_WORKFLOW.md`",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC V2 baseline audit")
    parser.add_argument("--out", default="docs/V2_BASELINE_AUDIT_REPORT.md")
    parser.add_argument("--json-out")
    parser.add_argument("--repo-root")
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="exit 0 even if the audit fails (report is still written)",
    )
    args = parser.parse_args(argv)

    result = run_baseline_audit(args.repo_root)
    report = render_report(result)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps({"passed": result["passed"], "n_passed": result["n_passed"], "n_checks": result["n_checks"], "report": str(out_path)}, sort_keys=True))
    if not result["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
