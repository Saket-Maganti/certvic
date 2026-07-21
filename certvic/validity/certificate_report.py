"""Reports for item validity certificates."""

from __future__ import annotations

from collections import Counter

from certvic.io import read_jsonl


def summarize_certificates(path: str) -> dict:
    rows = read_jsonl(path)
    reasons: Counter = Counter()
    warnings: Counter = Counter()
    for row in rows:
        reasons.update(row.get("blocking_reasons") or [])
        warnings.update(row.get("warnings") or [])
    return {
        "n_certificates": len(rows),
        "n_candidate_eligible": sum(1 for row in rows if row.get("evidence_eligible_candidate")),
        "blocking_reasons": dict(sorted(reasons.items())),
        "warnings": dict(sorted(warnings.items())),
    }


def render_certificate_report(summary: dict) -> str:
    lines = [
        "# Item Validity Certificate Report",
        "",
        f"Certificates: {summary['n_certificates']}",
        f"Evidence-eligible candidates: {summary['n_candidate_eligible']}",
        "",
        "## Blocking Reasons",
        "",
    ]
    if summary["blocking_reasons"]:
        lines.extend(f"- {key}: {value}" for key, value in summary["blocking_reasons"].items())
    else:
        lines.append("- none")
    lines += ["", "## Warnings", ""]
    if summary["warnings"]:
        lines.extend(f"- {key}: {value}" for key, value in summary["warnings"].items())
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)

