"""Pre-run master audit (V2.7).

The single gate that decides whether CertVIC is allowed to leave pre-run build
mode and start spending real edit-generation / human-review / GPU effort. It
aggregates every pre-run guarantee into one pass/fail verdict:

* V2 full system audit (which subsumes the baseline audit): structure, imports,
  configs, runbooks, zero-cost, claim discipline, no fabricated paper results.
* Reviewer attack harness (V2.5): every blocking reviewer defense is tooling-ready.
* Paper auto-injection guard (V2.6): result sections contain no untraced numbers.
* Anytime-validity lab (V2.1+): the certification estimator empirically controls
  Type-I error under optional stopping.
* (optional) Prompt/task adversarial audit (V2.3) on a supplied task manifest.

Runs no models, downloads nothing, needs no GPU, and makes no evidence claims.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import date
from pathlib import Path

from certvic.v2.full_audit import run_full_audit

REPO_ROOT = Path(__file__).resolve().parents[2]


def _component(name: str, passed: bool, summary: str, detail: dict | None = None) -> dict:
    return {"component": name, "passed": bool(passed), "summary": summary, "detail": detail or {}}


def run_pre_run_master_audit(
    repo_root: str | Path | None = None,
    tasks_path: str | None = None,
    validity_trials: int = 800,
    validity_n: int = 200,
) -> dict:
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    components: list[dict] = []

    full = run_full_audit(root)
    components.append(
        _component(
            "v2_full_system_audit",
            full["passed"],
            f"{full['n_passed']}/{full['n_checks']} structural checks",
            {"failed_checks": [c["name"] for c in full["checks"] if not c["passed"]]},
        )
    )

    from certvic.v2.reviewer_attack_harness import run_reviewer_attack_harness

    harness = run_reviewer_attack_harness()
    components.append(
        _component(
            "reviewer_attack_harness",
            harness["passed"],
            f"{harness['n_blocking_ready']}/{harness['n_blocking']} blocking defenses ready",
            {"blocking_unready": harness["blocking_unready"], "enhancement_unready": harness["enhancement_unready"]},
        )
    )

    from certvic.validation.paper_numbers_guard import verify_paper

    guard = verify_paper(repo_root=root)
    components.append(
        _component(
            "paper_numbers_guard",
            guard["passed"],
            f"{guard['n_violations']} untraced/fabrication violations",
            {"n_files": guard["n_files"]},
        )
    )

    from certvic.sim.anytime_validity import run_anytime_validity_lab

    with tempfile.TemporaryDirectory() as tmp:
        validity = run_anytime_validity_lab(
            tmp, n=validity_n, n_trials=validity_trials, alpha=0.05, threshold=0.0, seed=0
        )
    components.append(
        _component(
            "anytime_validity_lab",
            validity["all_checks_passed"],
            "CS Type-I controlled under optional stopping" if validity["all_checks_passed"] else "validity checks failed",
            {"checks": validity["checks"]},
        )
    )

    if tasks_path and Path(tasks_path).exists():
        from certvic.eval.adversarial_audit import run_adversarial_audit

        adv = run_adversarial_audit(tasks_path)
        components.append(
            _component(
                "prompt_task_adversarial_audit",
                adv["passed"],
                f"{adv['n_tasks']} tasks; high failures: {adv['high_severity_failures']}",
                {"high": adv["high_severity_failures"], "medium": adv["medium_severity_warnings"]},
            )
        )
    else:
        components.append(
            _component(
                "prompt_task_adversarial_audit",
                True,
                "skipped (no --tasks manifest supplied); run before real eval",
                {"skipped": True},
            )
        )

    passed = all(c["passed"] for c in components)
    return {
        "audit": "pre_run_master_audit",
        "repo_root": str(root),
        "passed": passed,
        "n_components": len(components),
        "n_passed": sum(1 for c in components if c["passed"]),
        "components": components,
        "cleared_for_real_runs": passed,
        "evidence_claims_made": False,
        "downloads_attempted": False,
        "gpu_required": False,
        "vlm_inference_run": False,
    }


def render_report(result: dict) -> str:
    status = "CLEARED" if result["passed"] else "BLOCKED"
    lines = [
        "# Pre-Run Master Audit (V2.7)",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Verdict: **{status} for real runs** ({result['n_passed']}/{result['n_components']} components passed).",
        "",
        "This is the single gate before spending real edit-generation, human-review,",
        "or GPU effort. It runs no models and makes no evidence claims.",
        "",
        "| Component | Status | Summary |",
        "| --- | --- | --- |",
    ]
    for c in result["components"]:
        mark = "pass" if c["passed"] else "FAIL"
        lines.append(f"| `{c['component']}` | {mark} | {c['summary']} |")
    lines += [
        "",
        "When CLEARED, proceed per `docs/V2_NEXT_ACTIONS.md`: real ADE20K dry-run,",
        "then tiny pilots, then the 200-item pilot. Empirical evidence remains empty",
        "until eligible open-VLM runs exist; this audit only certifies *readiness*.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC pre-run master audit (V2.7)")
    parser.add_argument("--out", default="docs/V2_7_PRE_RUN_MASTER_AUDIT_REPORT.md")
    parser.add_argument("--json-out")
    parser.add_argument("--repo-root")
    parser.add_argument("--tasks", help="optional task manifest to adversarially audit")
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args(argv)
    result = run_pre_run_master_audit(repo_root=args.repo_root, tasks_path=args.tasks)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"cleared_for_real_runs": result["passed"], "n_passed": result["n_passed"], "n_components": result["n_components"]}, sort_keys=True))
    if not result["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
