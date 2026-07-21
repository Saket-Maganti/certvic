"""Symptom-to-playbook failure diagnosis (V3 prompt 17).

Reads whatever report artifacts exist in a report directory, detects known
failure symptoms, and points each to its operational playbook in
`docs/playbooks/`. Read-only: no inference, no downloads, no evidence claims.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from certvic.io import read_json

# Symptom id -> (title, playbook file, default threshold description).
PLAYBOOKS = {
    "low_quality_pass": ("Edit quality pass rate is low", "EDIT_REALISM_FAILURE.md"),
    "high_detectability": ("Edits are low-level detectable (artifact confound)", "EDIT_REALISM_FAILURE.md"),
    "high_parse_failure": ("High parse-failure rate", "HIGH_PARSE_FAILURE.md"),
    "high_control_flip": ("High control-edit spurious-flip rate", "HIGH_CONTROL_FLIP.md"),
    "no_certified_gap": ("No certified intervention-consistency gap", "NO_CERTIFIED_GAP.md"),
    "low_original_accuracy": ("Low original-image accuracy", "LOW_ORIGINAL_ACCURACY.md"),
    "low_human_agreement": ("Low inter-annotator agreement", "LOW_HUMAN_AGREEMENT.md"),
    "too_few_candidates": ("Too few candidate edits", "TOO_FEW_CANDIDATES.md"),
    "gpu_preflight_failure": ("GPU / preflight failure", "GPU_PREFLIGHT_FAILURE.md"),
    "label_policy_failure": ("Label-policy rejections dominate", "LABEL_POLICY_FAILURE.md"),
    "claim_gate_failure": ("Claim gate blocked the claim", "CLAIM_GATE_FAILURE.md"),
    "kaggle_session_failure": ("Kaggle/Colab session died mid-run", "KAGGLE_SESSION_FAILURE.md"),
}


def _safe(path: Path):
    try:
        return read_json(path)
    except Exception:
        return None


def _first(report_dir: Path, *patterns: str):
    for pat in patterns:
        for f in sorted(report_dir.rglob(pat)):
            data = _safe(f)
            if isinstance(data, dict):
                return data
    return None


def _overall_metrics(summary: dict | None) -> dict:
    if not summary:
        return {}
    if isinstance(summary.get("overall"), dict):
        base = dict(summary["overall"])
    else:
        base = {k: v for k, v in summary.items() if isinstance(v, (int, float))}
    # Pull spurious-flip / parse-failure from any subgroup if not at top level.
    if "spurious_flip_rate" not in base or base.get("spurious_flip_rate") is None:
        flips = [g.get("spurious_flip_rate") for g in _iter_groups(summary) if g.get("spurious_flip_rate") is not None]
        if flips:
            base["spurious_flip_rate"] = max(flips)
    if "parse_failure_rate" not in base:
        rates = [g.get("parse_failure_rate") for g in _iter_groups(summary) if g.get("parse_failure_rate") is not None]
        if rates:
            base["parse_failure_rate"] = max(rates)
    return base


def _iter_groups(summary: dict):
    for key in ("by_domain", "by_required_change", "by_task_family", "by_edit_type"):
        node = summary.get(key)
        if isinstance(node, dict):
            for v in node.values():
                if isinstance(v, dict):
                    yield v


def diagnose(report_dir: str, *, thresholds: dict | None = None) -> dict:
    th = {
        "quality_pass_min": 0.7,
        "detectability_auc_max": 0.8,
        "parse_failure_max": 0.1,
        "control_flip_max": 0.1,
        "original_accuracy_min": 0.6,
        "iaa_kappa_min": 0.6,
        "candidate_min": 1,
        **(thresholds or {}),
    }
    rdir = Path(report_dir)

    summary = _first(rdir, "*summary*.json")
    overall = _overall_metrics(summary)
    edit_gen = _first(rdir, "*edit_generation_summary*.json", "*edit*summary*.json")
    detect = _first(rdir, "detectability_summary.json")
    triage = _first(rdir, "triage_summary.json")
    review = _first(rdir, "review_progress.json", "visual_review_summary.json")
    # Claim ledgers are often a JSON list, so load list-or-dict tolerantly.
    claims = None
    for f in sorted(rdir.rglob("claim_ledger.json")) + sorted(rdir.rglob("certification*.json")):
        data = _safe(f)
        if data is not None:
            claims = data
            break
    preflight = _first(rdir, "*preflight*.json")

    matched: list[dict] = []

    def add(symptom: str, detail: str):
        title, playbook = PLAYBOOKS[symptom]
        matched.append({"symptom": symptom, "title": title, "playbook": f"docs/playbooks/{playbook}", "detail": detail})

    # Edit quality pass rate.
    if isinstance(edit_gen, dict):
        passed = edit_gen.get("quality_passed")
        failed = edit_gen.get("quality_failed")
        if passed is not None and failed is not None and (passed + failed) > 0:
            rate = passed / (passed + failed)
            if rate < th["quality_pass_min"]:
                add("low_quality_pass", f"quality pass rate {rate:.2f} < {th['quality_pass_min']}")

    # Detectability.
    if isinstance(detect, dict):
        auc = (detect.get("classifier") or {}).get("auc")
        if (auc is not None and auc >= th["detectability_auc_max"]) or detect.get("artifact_risk"):
            add("high_detectability", f"detectability AUC {auc} >= {th['detectability_auc_max']}")

    # Parse failure (from triage or summary).
    pf = None
    if isinstance(triage, dict):
        rates = [s.get("parse_ok_rate") for s in triage.get("provider_stats", []) if s.get("parse_ok_rate") is not None]
        if rates:
            pf = 1.0 - min(rates)
    if pf is None and "parse_failure_rate" in overall:
        pf = overall["parse_failure_rate"]
    if pf is not None and pf > th["parse_failure_max"]:
        add("high_parse_failure", f"parse failure {pf:.2f} > {th['parse_failure_max']}")

    # Control flip.
    flip = overall.get("spurious_flip_rate")
    if flip is not None and flip > th["control_flip_max"]:
        add("high_control_flip", f"spurious flip rate {flip:.2f} > {th['control_flip_max']}")

    # Original accuracy.
    oa = overall.get("original_accuracy")
    if oa is not None and oa < th["original_accuracy_min"]:
        add("low_original_accuracy", f"original accuracy {oa:.2f} < {th['original_accuracy_min']}")

    # Human agreement.
    if isinstance(review, dict):
        kappas = []
        for field_info in (review.get("iaa") or {}).values():
            if isinstance(field_info, dict):
                k = field_info.get("cohens_kappa") if "cohens_kappa" in field_info else field_info.get("mean_majority_agreement")
                if isinstance(k, (int, float)):
                    kappas.append(k)
        if kappas and min(kappas) < th["iaa_kappa_min"]:
            add("low_human_agreement", f"min IAA {min(kappas):.2f} < {th['iaa_kappa_min']}")

    # Too few candidates.
    if isinstance(edit_gen, dict):
        gen = edit_gen.get("generated")
        if gen is not None and gen < th["candidate_min"]:
            add("too_few_candidates", f"generated {gen} < {th['candidate_min']}")

    # GPU / preflight.
    if isinstance(preflight, dict) and preflight.get("ready") is False:
        add("gpu_preflight_failure", f"preflight not ready: {preflight.get('blocking_failures')}")

    # Certified gap.
    certified = False
    if isinstance(claims, dict):
        cl = claims if isinstance(claims, list) else claims.get("claims", [])
        certified = any(str(c.get("certification_status", "")).lower() == "certified" and c.get("safe") for c in (cl or []))
    elif isinstance(claims, list):
        certified = any(str(c.get("certification_status", "")).lower() == "certified" for c in claims)
    if summary is not None and not certified:
        add("no_certified_gap", "no certified claim found in report")

    return {
        "diagnosis": "failure_mode",
        "report_dir": report_dir,
        "thresholds": th,
        "n_symptoms": len(matched),
        "symptoms": matched,
        "available_playbooks": {k: f"docs/playbooks/{v[1]}" for k, v in PLAYBOOKS.items()},
        "healthy": len(matched) == 0 and summary is not None,
        "report_present": summary is not None,
        "evidence_claims_made": False,
    }


def render_report(result: dict) -> str:
    lines = [
        "# Failure Diagnosis",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Report dir: `{result['report_dir']}`",
        f"Symptoms matched: {result['n_symptoms']}  |  report present: {result['report_present']}",
        "",
        "Read-only diagnosis; maps observed symptoms to operational playbooks. No claims.",
        "",
    ]
    if not result["report_present"]:
        lines += ["No report artifacts found yet. Run a (dry or real) pilot first.", ""]
    if result["symptoms"]:
        lines += ["## Matched symptoms", "", "| Symptom | Detail | Playbook |", "| --- | --- | --- |"]
        for s in result["symptoms"]:
            lines.append(f"| {s['title']} | {s['detail']} | `{s['playbook']}` |")
        lines.append("")
    elif result["report_present"]:
        lines += ["No failure symptoms detected in the available artifacts.", ""]
    lines += ["## All playbooks", "", *[f"- `{p}` — {PLAYBOOKS[k][0]}" for k, p in [(k, f'docs/playbooks/{PLAYBOOKS[k][1]}') for k in PLAYBOOKS]], ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC failure-mode diagnosis")
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--out", default="docs/playbooks/DIAGNOSIS.md")
    args = parser.parse_args(argv)
    result = diagnose(args.report_dir)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({
        "n_symptoms": result["n_symptoms"],
        "symptoms": [s["symptom"] for s in result["symptoms"]],
        "healthy": result["healthy"],
        "out": args.out,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
