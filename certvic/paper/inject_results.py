"""Claim-gated paper result injection (V3 prompt 12).

Replaces ``[RESULT REQUIRED]`` placeholders with ``\\input``/``\\includegraphics``
of generated artifacts, but ONLY for artifacts that are eligible (non-mock /
non-simulated), hash-stamped in the manifest, and present. Ineligible or unhashed
artifacts leave the placeholder intact. Dry-run by default; ``--allow-write`` is
required to modify the paper, and the number guard runs after any write.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from certvic.io import read_json
from certvic.validation.paper_numbers_guard import verify_paper_numbers

PLACEHOLDER = "[RESULT REQUIRED]"
_ARTIFACT_TOKEN_RE = re.compile(r"[\w./-]+\.(?:tex|png|pdf|csv|json)")
DEFAULT_RESULTS_FILES = ["sections/05_results.tex"]


def _injectable(entry: dict | None) -> bool:
    return bool(entry) and bool(entry.get("eligible")) and bool(entry.get("sha256")) and entry.get("kind") in {"table", "figure"}


def _referenced(comment_buffer: list[str]) -> list[str]:
    text = " ".join(comment_buffer)
    return [Path(tok).name for tok in _ARTIFACT_TOKEN_RE.findall(text)]


def _inject_line(entry: dict) -> str:
    if entry["kind"] == "table":
        return f"\\input{{tables/{entry['basename']}}}"
    return f"\\includegraphics[width=\\linewidth]{{figures/{entry['basename']}}}"


def plan_injection(tex_text: str, by_basename: dict[str, dict]) -> tuple[str, list[dict]]:
    out_lines: list[str] = []
    decisions: list[dict] = []
    comment_buffer: list[str] = []
    for line in tex_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("%"):
            comment_buffer.append(stripped)
            out_lines.append(line)
            continue
        if stripped == PLACEHOLDER:
            refs = _referenced(comment_buffer)
            injectable = [by_basename[b] for b in refs if _injectable(by_basename.get(b))]
            refused = []
            for b in refs:
                e = by_basename.get(b)
                if not _injectable(e):
                    if e is None:
                        refused.append({"artifact": b, "reason": "not in manifest"})
                    elif not e.get("sha256"):
                        refused.append({"artifact": b, "reason": "missing hash"})
                    elif not e.get("eligible"):
                        refused.append({"artifact": b, "reason": f"non-evidence (status={e.get('evidence_status')}, provider={e.get('provider_type')})"})
                    else:
                        refused.append({"artifact": b, "reason": "not an injectable kind"})
            if injectable:
                for e in injectable:
                    out_lines.append(_inject_line(e))
                decisions.append({"action": "inject", "artifacts": [e["basename"] for e in injectable], "refused": refused})
            else:
                out_lines.append(line)  # preserve placeholder
                decisions.append({"action": "preserve_placeholder", "referenced": refs, "refused": refused})
            continue
        if stripped == "":
            out_lines.append(line)
            continue
        # A real content line (e.g. \subsection) starts a fresh comment context.
        comment_buffer = []
        out_lines.append(line)
    new_text = "\n".join(out_lines)
    if tex_text.endswith("\n"):
        new_text += "\n"
    return new_text, decisions


def inject_results(
    manifest_path: str,
    paper_dir: str,
    *,
    results_files: list[str] | None = None,
    allow_write: bool = False,
) -> dict:
    manifest = read_json(manifest_path)
    entries = manifest.get("entries", [])
    by_basename = {e["basename"]: e for e in entries}
    paper = Path(paper_dir)
    files = results_files or DEFAULT_RESULTS_FILES

    file_results: list[dict] = []
    total_injected = 0
    total_preserved = 0
    for rel in files:
        path = paper / rel
        if not path.exists():
            file_results.append({"file": rel, "error": "results file missing"})
            continue
        original = path.read_text(encoding="utf-8")
        new_text, decisions = plan_injection(original, by_basename)
        n_inject = sum(1 for d in decisions if d["action"] == "inject")
        n_preserve = sum(1 for d in decisions if d["action"] == "preserve_placeholder")
        total_injected += n_inject
        total_preserved += n_preserve
        wrote = False
        guard = None
        changed = new_text != original
        if allow_write and changed:
            path.write_text(new_text, encoding="utf-8")
            wrote = True
        if wrote:
            guard = verify_paper_numbers(path, manifest_path=manifest_path)
        file_results.append({
            "file": rel,
            "n_injected": n_inject,
            "n_preserved_placeholders": n_preserve,
            "changed": changed,
            "wrote": wrote,
            "decisions": decisions,
            "guard": guard,
        })

    guard_ok = all(f.get("guard", {}).get("passed", True) for f in file_results if f.get("guard"))
    return {
        "action": "inject_results",
        "manifest": manifest_path,
        "paper_dir": str(paper),
        "dry_run": not allow_write,
        "n_injected": total_injected,
        "n_preserved_placeholders": total_preserved,
        "files": file_results,
        "guard_passed": guard_ok,
        "refused_non_evidence": any(d.get("refused") for f in file_results for d in f.get("decisions", [])),
        "evidence_claims_made": False,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC claim-gated paper result injection")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--paper-dir", default="paper")
    parser.add_argument("--results-files", nargs="*")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="(default) plan only, do not write")
    group.add_argument("--allow-write", action="store_true", help="write changes to the paper")
    args = parser.parse_args(argv)
    result = inject_results(args.manifest, args.paper_dir, results_files=args.results_files, allow_write=args.allow_write)
    print(json.dumps({
        "dry_run": result["dry_run"],
        "n_injected": result["n_injected"],
        "n_preserved_placeholders": result["n_preserved_placeholders"],
        "guard_passed": result["guard_passed"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
