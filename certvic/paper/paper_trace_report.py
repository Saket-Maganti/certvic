"""Paper-to-artifact traceability report (V3 prompt 12).

For each results section, traces every injected ``\\input`` target back to a
manifest entry (eligible? hash present?) and lists remaining placeholders. This
is the reviewer-facing proof that every paper number is real and traceable.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from certvic.io import ensure_parent, read_json
from certvic.validation.paper_numbers_guard import extract_paper_numbers

DEFAULT_RESULTS_FILES = ["sections/05_results.tex"]


def trace_paper(paper_dir: str, manifest_path: str, *, results_files: list[str] | None = None) -> dict:
    manifest = read_json(manifest_path) if Path(manifest_path).exists() else {"entries": []}
    by_basename = {e["basename"]: e for e in manifest.get("entries", [])}
    paper = Path(paper_dir)
    files = results_files or DEFAULT_RESULTS_FILES

    file_traces: list[dict] = []
    for rel in files:
        path = paper / rel
        if not path.exists():
            file_traces.append({"file": rel, "error": "missing"})
            continue
        text = path.read_text(encoding="utf-8")
        extracted = extract_paper_numbers(text)
        traces = []
        for target in extracted["inputs"]:
            base = Path(target).name
            entry = by_basename.get(base)
            if entry is None:
                status = "missing_in_manifest"
            elif not entry.get("sha256"):
                status = "missing_hash"
            elif not entry.get("eligible"):
                status = "ineligible_evidence"
            else:
                status = "traced"
            traces.append({"input": target, "status": status, "sha256": (entry or {}).get("sha256")})
        n_placeholders = text.count("[RESULT REQUIRED]")
        file_traces.append({
            "file": rel,
            "n_inputs": len(extracted["inputs"]),
            "n_placeholders": n_placeholders,
            "n_untraced_numbers": len(extracted["untraced_numbers"]),
            "traces": traces,
            "all_inputs_traced": all(t["status"] == "traced" for t in traces),
        })

    all_traced = all(f.get("all_inputs_traced", True) for f in file_traces if "error" not in f)
    no_untraced = all(f.get("n_untraced_numbers", 0) == 0 for f in file_traces if "error" not in f)
    return {
        "report": "paper_trace",
        "paper_dir": str(paper),
        "manifest": manifest_path,
        "files": file_traces,
        "all_inputs_traced": all_traced,
        "no_untraced_numbers": no_untraced,
        "ok": all_traced and no_untraced,
        "evidence_claims_made": False,
    }


def render_report(result: dict) -> str:
    lines = [
        "# Paper Result Traceability Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Paper: `{result['paper_dir']}`  |  manifest: `{result['manifest']}`",
        f"Status: **{'OK' if result['ok'] else 'INCOMPLETE'}** "
        f"(all inputs traced: {result['all_inputs_traced']}; no untraced numbers: {result['no_untraced_numbers']})",
        "",
        "Every injected result must trace to an eligible, hash-stamped artifact.",
        "Remaining `[RESULT REQUIRED]` placeholders are expected until eligible runs exist.",
        "",
    ]
    for f in result["files"]:
        lines.append(f"## `{f['file']}`")
        lines.append("")
        if "error" in f:
            lines.append(f"- ERROR: {f['error']}")
            lines.append("")
            continue
        lines.append(f"- inputs: {f['n_inputs']}  |  placeholders remaining: {f['n_placeholders']}  |  untraced numbers: {f['n_untraced_numbers']}")
        if f["traces"]:
            lines.append("")
            lines.append("| Input | Trace status |")
            lines.append("| --- | --- |")
            for t in f["traces"]:
                lines.append(f"| `{t['input']}` | {t['status']} |")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC paper result traceability report")
    parser.add_argument("--paper-dir", default="paper")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--results-files", nargs="*")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = trace_paper(args.paper_dir, args.manifest, results_files=args.results_files)
    ensure_parent(args.out)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    import json

    print(json.dumps({"ok": result["ok"], "all_inputs_traced": result["all_inputs_traced"], "out": args.out}, sort_keys=True))


if __name__ == "__main__":
    main()
