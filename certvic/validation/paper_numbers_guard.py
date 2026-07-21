"""Paper auto-injection guard (V2.6).

Enforces the hard project rule that result sections never contain fabricated or
hand-entered numbers. The guard treats the results section as *append-only from
eligible artifacts*:

A results section may contain ONLY
  * placeholder tokens (``[RESULT REQUIRED]``, ``--``, ``TBD``),
  * LaTeX comments (``% ...``),
  * generated tables/figures pulled in via ``\\input{...}`` / ``\\include{...}``,
  * explicitly declared method constants (e.g. ``alpha = 0.05``).

Any other numeric literal in the result prose is flagged as an untraced number
(a fabrication / hand-entry risk). When a results-provenance manifest is
supplied, every ``\\input`` target and every declared result value must trace to
an entry produced by an *eligible* run (not mock / smoke / simulated / planned).

This module makes no evidence claims and runs no models. It only inspects text
and a provenance manifest, so it is safe to run in CI and in the master audit.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from certvic.io import read_json
from certvic.validation.claims import FORBIDDEN_CLAIM_PHRASES, NON_EVIDENCE_STATUSES

PLACEHOLDER_TOKENS = ("[RESULT REQUIRED]", "--", "TBD", "N/A")
INELIGIBLE_PROVIDER_TYPES = {"mock", "baseline", "random", "text_only", "caption_only"}

# Method constants that legitimately appear in a results section as prose. These
# are configuration, not findings, so they do not require artifact provenance.
DEFAULT_ALLOWED_CONSTANTS = {"0.05", "0.5", "0.0", "0.95"}

_NUMBER_RE = re.compile(r"(?<![\w.])(?:\d+(?:\.\d+)?|\.\d+)(?![\w])")
_INPUT_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")
_COMMENT_RE = re.compile(r"(?<!\\)%.*$")
_SECTION_REF_RE = re.compile(r"(?:section|sec\.|figure|fig\.|table|tab\.|eq\.|equation)\s*~?\s*\d", re.IGNORECASE)


def _strip_comments(text: str) -> str:
    return "\n".join(_COMMENT_RE.sub("", line) for line in text.splitlines())


def extract_paper_numbers(tex_text: str, allowed_constants: set[str] | None = None) -> dict:
    """Extract input targets and inline numeric tokens from results prose."""
    allowed = set(DEFAULT_ALLOWED_CONSTANTS if allowed_constants is None else allowed_constants)
    body = _strip_comments(tex_text)

    inputs = sorted(set(_INPUT_RE.findall(body)))

    # Remove \input{...}/\include{...} targets before scanning for loose numbers
    # (so generated filenames like by_family_table.tex are not mis-read).
    body_wo_inputs = _INPUT_RE.sub(" ", body)

    inline_numbers: list[dict] = []
    for raw_line in body_wo_inputs.splitlines():
        # Neutralize placeholder tokens *in place* rather than skipping the whole
        # line. The old whole-line skip let a fabricated number ride along on any
        # line that also contained "--", "TBD" or "N/A" -- and em-dashes ("---")
        # and ranges ("10--20") are ordinary LaTeX, so this silently defeated the
        # guard. Placeholder tokens carry no digits, so removing only the tokens
        # keeps bare-placeholder lines clean while still scanning any real number
        # that shares the line (fail-closed).
        scan_line = raw_line
        for token in PLACEHOLDER_TOKENS:
            if token in scan_line:
                scan_line = scan_line.replace(token, " ")
        context = raw_line.strip()
        for match in _NUMBER_RE.finditer(scan_line):
            value = match.group(0)
            is_section_ref = bool(_SECTION_REF_RE.search(context))
            allowed_constant = value in allowed
            inline_numbers.append(
                {
                    "value": value,
                    "context": context[:160],
                    "allowed_constant": allowed_constant,
                    "section_ref": is_section_ref,
                }
            )
    untraced = [
        n for n in inline_numbers if not n["allowed_constant"] and not n["section_ref"]
    ]
    return {"inputs": inputs, "inline_numbers": inline_numbers, "untraced_numbers": untraced}


def _load_manifest(manifest_path: str | Path | None) -> dict | None:
    if manifest_path is None:
        return None
    path = Path(manifest_path)
    if not path.exists():
        return None
    return read_json(path)


def _eligible_entry(entry: dict) -> bool:
    status = str(entry.get("evidence_status", "")).upper()
    provider = str(entry.get("provider_type", "")).lower()
    if status in {s.upper() for s in NON_EVIDENCE_STATUSES}:
        return False
    if status in {"", "MOCK_ONLY", "UNKNOWN"}:
        return False
    if provider in INELIGIBLE_PROVIDER_TYPES:
        return False
    return True


def verify_paper_numbers(
    tex_path: str | Path,
    manifest_path: str | Path | None = None,
    allowed_constants: set[str] | None = None,
) -> dict:
    """Return a structured guard result for one results-section file."""
    path = Path(tex_path)
    if not path.exists():
        return {
            "tex_path": str(path),
            "passed": False,
            "violations": [f"results file missing: {path}"],
            "extracted": {},
        }
    text = path.read_text(encoding="utf-8")
    extracted = extract_paper_numbers(text, allowed_constants=allowed_constants)
    violations: list[str] = []

    # 1. No untraced inline numbers in result prose.
    for num in extracted["untraced_numbers"]:
        violations.append(f"untraced number {num['value']!r} in: {num['context']!r}")

    # 2. Forbidden claim phrases.
    lowered = text.lower()
    for phrase in FORBIDDEN_CLAIM_PHRASES:
        if phrase in lowered:
            violations.append(f"forbidden claim phrase: {phrase}")

    # 3. Provenance: every \input target + declared value must trace to an
    #    eligible artifact when a manifest is supplied.
    manifest = _load_manifest(manifest_path)
    has_results = bool(extracted["inputs"]) or bool(extracted["untraced_numbers"])
    if manifest is None:
        if extracted["inputs"]:
            violations.append(
                "results pull in \\input artifacts but no provenance manifest was supplied"
            )
    else:
        entries = manifest.get("entries", [])
        eligible_artifacts = {
            str(e.get("artifact")) for e in entries if _eligible_entry(e)
        }
        ineligible_used = []
        for target in extracted["inputs"]:
            base = Path(target).name
            matched = [
                e
                for e in entries
                if Path(str(e.get("artifact", ""))).name == base or str(e.get("artifact")) == target
            ]
            if not matched:
                violations.append(f"\\input target not in provenance manifest: {target}")
            elif not any(_eligible_entry(e) for e in matched):
                ineligible_used.append(target)
        for target in ineligible_used:
            violations.append(f"\\input target traces to ineligible (mock/simulated) run: {target}")
        # Manifest itself must not be globally ineligible.
        if entries and not eligible_artifacts:
            violations.append("provenance manifest contains no eligible (non-mock/non-simulated) entries")

    placeholder_only = (
        not extracted["inputs"] and not extracted["untraced_numbers"]
    )
    return {
        "tex_path": str(path),
        "passed": not violations,
        "violations": violations,
        "placeholder_only": placeholder_only,
        "has_results": has_results,
        "manifest_supplied": manifest is not None,
        "extracted": extracted,
    }


def verify_paper(
    results_files: list[str] | None = None,
    repo_root: str | Path | None = None,
    manifest_path: str | Path | None = None,
    allowed_constants: set[str] | None = None,
) -> dict:
    """Run the guard over all configured results files."""
    root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
    files = results_files or ["paper/sections/05_results.tex"]
    results = [
        verify_paper_numbers(root / f, manifest_path=manifest_path, allowed_constants=allowed_constants)
        for f in files
    ]
    passed = all(r["passed"] for r in results)
    return {
        "guard": "paper_numbers_guard",
        "repo_root": str(root),
        "passed": passed,
        "n_files": len(results),
        "n_violations": sum(len(r["violations"]) for r in results),
        "files": results,
        "evidence_claims_made": False,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC paper auto-injection / number-provenance guard")
    parser.add_argument("--results", nargs="*", help="results .tex files (relative to repo root)")
    parser.add_argument("--repo-root")
    parser.add_argument("--manifest", help="results provenance manifest JSON")
    parser.add_argument("--allowed-constants", nargs="*")
    parser.add_argument("--json-out")
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args(argv)
    allowed = set(args.allowed_constants) if args.allowed_constants else None
    result = verify_paper(
        results_files=args.results,
        repo_root=args.repo_root,
        manifest_path=args.manifest,
        allowed_constants=allowed,
    )
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "n_violations": result["n_violations"]}, sort_keys=True))
    if not result["passed"] and not args.no_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
