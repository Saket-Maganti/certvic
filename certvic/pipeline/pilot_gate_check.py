"""Pilot gate checks.

Gates the main pilot at five stages so the project cannot advance (e.g. to VLM
inference, claims, or release) until the prerequisites for that stage hold. No
inference, no downloads, no evidence claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

GATE_STAGES = [
    "before_edit_generation",
    "before_visual_review",
    "before_vlm",
    "before_claims",
    "before_release",
]


def _exists(root: Path, rel: str | None) -> bool:
    return bool(rel) and (root / rel).exists()


def _load_yaml(path: Path) -> dict:
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


def _check(name: str, ok: bool, **detail) -> dict:
    return {"check": name, "ok": bool(ok), **detail}


def run_gate_check(stage: str, config_path: str, repo_root: str | None = None) -> dict:
    if stage not in GATE_STAGES:
        raise ValueError(f"unknown gate stage: {stage}; choose from {GATE_STAGES}")
    root = Path(repo_root) if repo_root else Path.cwd()
    cfg = _load_yaml(Path(config_path)) if config_path else {}
    outputs = cfg.get("outputs", {}) if isinstance(cfg, dict) else {}
    checks: list[dict] = []

    # Always-on policy invariants.
    checks.append(_check("zero_cost_policy", cfg.get("paid_services_enabled") is not True))
    checks.append(_check("label_policy_configured", _exists(root, cfg.get("label_policy") or "configs/ade20k_label_policy.yaml")))

    if stage == "before_edit_generation":
        checks.append(_check("source_manifest_present", _exists(root, outputs.get("source_manifest"))))
        checks.append(_check("mask_manifest_present", _exists(root, outputs.get("mask_manifest"))))
        checks.append(_check("pilot_selection_present", _exists(root, outputs.get("pilot_selection"))))
        checks.append(_check("edit_plan_present", _exists(root, outputs.get("pilot_edit_plan"))))
    elif stage == "before_visual_review":
        checks.append(_check("generated_edits_present", _exists(root, outputs.get("pilot_generated_edits"))))
        checks.append(_check("quality_report_present", _exists(root, (cfg.get("tiny_edit_generation", {}) or {}).get("quality_report") or "data/results/tiny_edit_quality_report")))
    elif stage == "before_vlm":
        review = (cfg.get("visual_review", {}) or {}).get("outputs", {})
        checks.append(_check("reviewed_tasks_present", _exists(root, review.get("reviewed_tasks"))))
        checks.append(_check("review_summary_present", _exists(root, review.get("review_summary"))))
        checks.append(_check("certification_policy_present", _exists(root, "configs/certification_policy.yaml")))
        checks.append(_check("tiny_reviewed_eval_config_present", _exists(root, "configs/tiny_reviewed_eval.yaml")))
    elif stage == "before_claims":
        checks.append(_check("certification_policy_present", _exists(root, "configs/certification_policy.yaml")))
        checks.append(_check("claim_ledger_doc_present", _exists(root, "docs/CLAIM_LEDGER.md")))
        checks.append(_check("paper_claim_checklist_present", _exists(root, "docs/PAPER_CLAIM_CHECKLIST.md")))
    elif stage == "before_release":
        checks.append(_check("release_config_present", _exists(root, "configs/release_recipe.yaml")))
        checks.append(_check("reviewer_defenses_present", _exists(root, "docs/REVIEWER_ATTACKS_AND_DEFENSES.md")))

    blocking = [c["check"] for c in checks if not c["ok"]]
    return {
        "stage": stage,
        "config": config_path,
        "checks": checks,
        "passed": not blocking,
        "blocking": blocking,
        "downloads_attempted": False,
        "inference_run": False,
        "evidence_status": "GATE_CHECK_NON_EVIDENCE",
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC pilot gate checks")
    parser.add_argument("--stage", required=True, choices=GATE_STAGES)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out")
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    result = run_gate_check(args.stage, args.config, repo_root=args.repo_root)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"stage": result["stage"], "passed": result["passed"], "blocking": result["blocking"]}, sort_keys=True))


if __name__ == "__main__":
    main()
