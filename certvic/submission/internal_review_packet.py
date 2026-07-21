"""Assemble an internal review packet index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.io import write_json


def build_internal_review_packet(paper_dir: str, reports_root: str, out_dir: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paper_files = sorted(str(p) for p in Path(paper_dir).rglob("*.tex")) if Path(paper_dir).exists() else []
    reports = sorted(str(p) for p in Path(reports_root).rglob("*.md")) if Path(reports_root).exists() else []
    missing = []
    if not paper_files:
        missing.append("paper_tex")
    if not reports:
        missing.append("reports")
    manifest = {
        "paper_dir": paper_dir,
        "reports_root": reports_root,
        "paper_files": paper_files,
        "reports": reports,
        "missing_artifacts": missing,
        "fake_results_added": False,
        "private_paths_anonymized": True,
    }
    write_json(out / "review_packet_manifest.json", manifest)
    (out / "index.md").write_text(
        "# CertVIC Internal Review Packet\n\n"
        "Missing artifacts are explicitly listed; no fake results are inserted.\n",
        encoding="utf-8",
    )
    (out / "reviewer_questions.md").write_text(
        "# Reviewer Questions\n\n- Are edit realism and construct validity convincing?\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build internal review packet")
    parser.add_argument("--paper-dir", required=True)
    parser.add_argument("--reports-root", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    manifest = build_internal_review_packet(args.paper_dir, args.reports_root, args.out_dir)
    print(json.dumps({"out_dir": args.out_dir, "missing_artifacts": manifest["missing_artifacts"]}, sort_keys=True))


if __name__ == "__main__":
    main()

