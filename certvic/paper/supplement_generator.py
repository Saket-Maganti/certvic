"""Generate supplement skeletons from available real reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

NON_EVIDENCE_MARKERS = ("MOCK", "SIMULATED", "NON_EVIDENCE", "PLANNED")


def generate_supplement(reports_root: str, out: str, *, dry_run: bool = True) -> dict:
    root = Path(reports_root)
    reports = sorted(root.rglob("*.md")) if root.exists() else []
    included: list[str] = []
    placeholders: list[str] = []
    for report in reports:
        text = report.read_text(encoding="utf-8", errors="ignore")
        if any(marker in text.upper() for marker in NON_EVIDENCE_MARKERS):
            placeholders.append(str(report))
        else:
            included.append(str(report))
    lines = [
        "% Auto-generated supplement skeleton",
        "% Real report sections are referenced only when available.",
        "\\section{Reproducibility}",
        "Traceability and command manifests will be inserted after result freeze.",
    ]
    if included:
        lines.append("\\section{Available Report Sources}")
        lines.extend(f"% source: {path}" for path in included)
    if placeholders or not included:
        lines.append("\\section{Pending Results}")
        lines.append("[RESULT REQUIRED: non-evidence or missing reports are not inserted.]")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "reports_root": reports_root,
        "out": out,
        "dry_run": dry_run,
        "included_reports": included,
        "placeholder_warnings": placeholders or ["missing_real_reports"],
        "non_evidence_refused": bool(placeholders),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate supplement skeleton")
    parser.add_argument("--reports-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(generate_supplement(args.reports_root, args.out, dry_run=not args.apply), sort_keys=True))


if __name__ == "__main__":
    main()

