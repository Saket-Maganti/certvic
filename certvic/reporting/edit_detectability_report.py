"""Markdown report for the edit detectability probe (V3 prompt 05).

Renders the construct-validity finding: how separable edited vs original images
are under cheap low-level features, and which items are most detectable. This is
a descriptive diagnostic, never evidence by itself.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from certvic.io import ensure_parent


def _risk_band(auc) -> str:
    if auc is None:
        return "unknown"
    if auc >= 0.9:
        return "HIGH (edits trivially separable from low-level features)"
    if auc >= 0.8:
        return "ELEVATED (low-level features separate edits well)"
    if auc >= 0.65:
        return "MODERATE"
    return "LOW (low-level features barely separate edits)"


def render_report(result: dict) -> str:
    cls = result.get("classifier", {})
    auc = cls.get("auc")
    lines = [
        "# Edit Detectability Probe",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Tasks: `{result['tasks_path']}`",
        f"Items analyzed: {result['n_items']} (skipped {result['n_skipped']})",
        f"Evidence status: `{result['evidence_status']}`",
        "",
        "**Descriptive construct-validity diagnostic — never evidence by itself.**",
        "",
        "## Question",
        "",
        "Can a trivial classifier tell edited images from their originals using only",
        "cheap low-level features (file size, edge density, sharpness, color stats,",
        "uniform-pixel fraction)? If yes, an observed VLM consistency gap may be",
        "confounded by the edit *artifact* rather than the intended semantic change.",
        "",
        "## Result",
        "",
        f"- Classifier backend: `{cls.get('backend')}`",
        f"- Cross-validation grouped by item pair: {cls.get('cv_grouped_by_item')}",
        f"- Separability AUC (symmetric): {auc}",
        f"- Raw oriented multivariate AUC: {cls.get('raw_multivariate_auc')}",
        f"- Multivariate separability AUC: {cls.get('multivariate_auc')}",
        f"- Symmetric accuracy: {cls.get('accuracy')}",
        f"- Raw oriented accuracy: {cls.get('raw_accuracy')}",
        f"- Most discriminative single feature: `{cls.get('best_single_feature')}`",
        f"- Artifact-risk flag (AUC >= {result['flag_auc']}): **{result['artifact_risk']}**",
        f"- Risk band: {_risk_band(auc)}",
        "",
        "### Per-feature separability (rank AUC, 0.5 = chance)",
        "",
        "| Feature | AUC |",
        "| --- | --- |",
        *[f"| `{f}` | {v} |" for f, v in sorted((cls.get("per_feature_auc") or {}).items(), key=lambda kv: kv[1], reverse=True)],
        "",
        "## Most-detectable items",
        "",
        f"{len(result['highly_detectable_items'])} item(s) flagged by largest paired low-level distance. "
        "Inspect these in human review; large low-level deltas suggest artifact confounds.",
        "",
        "| Item | Edit type | Detectability score |",
        "| --- | --- | --- |",
        *[f"| `{r['item_id']}` | {r.get('edit_type')} | {r['detectability_score']} |" for r in result["highly_detectable_items"]],
        "",
        "## Mitigations if risk is ELEVATED/HIGH",
        "",
        "- Prefer photorealistic diffusion-inpaint edits over flat-fill/blob edits.",
        "- Add original-only and edited-only ablations to bound artifact-driven flips.",
        "- Route flagged items through extra human review; drop non-photorealistic edits.",
        "- Report this probe alongside (never instead of) the certified gap.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render edit detectability report from a summary JSON")
    parser.add_argument("--summary", required=True, help="detectability_summary.json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    result.setdefault("highly_detectable_items", [])
    ensure_parent(args.out)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"out": args.out}, sort_keys=True))


if __name__ == "__main__":
    main()
