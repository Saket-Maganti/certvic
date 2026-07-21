"""Related-work coverage and citation audit (V3 prompt 13).

Checks the related-work matrix against the related-work section: which categories
are discussed, which still need citations, whether any `\\cite` keys appear
without a verified bibliography (fabrication risk), and whether unsupported
novelty claims ("first to", "novel", ...) appear. It never invents citations; it
only reports TODOs and flags. No inference, no downloads.
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

import yaml

from certvic.io import ensure_parent

_CITE_RE = re.compile(r"\\cite[tp]?\*?\{([^}]+)\}")
# Novelty phrases that need a citation/qualifier or risk overclaiming.
NOVELTY_PHRASES = [
    "first to", "we are the first", "for the first time", "the first benchmark",
    "no prior work", "novel", "unprecedented", "never been", "unlike all prior",
]


def load_matrix(matrix_path: str) -> dict:
    data = yaml.safe_load(Path(matrix_path).read_text(encoding="utf-8")) or {}
    return data


def audit_related_work(matrix_path: str, paper_path: str, *, bib_keys: set[str] | None = None) -> dict:
    matrix = load_matrix(matrix_path)
    categories = matrix.get("categories", {})
    text = Path(paper_path).read_text(encoding="utf-8") if Path(paper_path).exists() else ""
    lowered = text.lower()

    category_rows = []
    for key, cat in categories.items():
        keywords = [k.lower() for k in cat.get("keywords", [])]
        covered = any(kw in lowered for kw in keywords)
        needs_cite = not cat.get("representative_works")
        category_rows.append({
            "category": key,
            "title": cat.get("title"),
            "covered_in_paper": covered,
            "needs_citations": needs_cite,
            "n_representative_works": len(cat.get("representative_works") or []),
            "differentiator": cat.get("differentiator"),
        })

    # Citation fabrication check: any \cite keys present without a verified bib.
    cite_keys = sorted({k.strip() for group in _CITE_RE.findall(text) for k in group.split(",")})
    bib = bib_keys or set()
    unverified_cites = [k for k in cite_keys if k not in bib]

    # Novelty-claim flags.
    novelty_flags = []
    for line in text.splitlines():
        low = line.lower()
        for phrase in NOVELTY_PHRASES:
            if phrase in low:
                has_cite = bool(_CITE_RE.search(line))
                novelty_flags.append({"phrase": phrase, "line": line.strip()[:160], "has_citation": has_cite})

    missing_categories = [r["category"] for r in category_rows if not r["covered_in_paper"]]
    categories_needing_cites = [r["category"] for r in category_rows if r["needs_citations"]]

    return {
        "audit": "related_work",
        "matrix_path": matrix_path,
        "paper_path": paper_path,
        "n_categories": len(category_rows),
        "categories": category_rows,
        "missing_categories": missing_categories,
        "categories_needing_citations": categories_needing_cites,
        "cite_keys_found": cite_keys,
        "unverified_cite_keys": unverified_cites,
        "fabrication_risk": bool(unverified_cites),
        "novelty_claim_flags": novelty_flags,
        "all_categories_covered": not missing_categories,
        "no_unverified_citations": not unverified_cites,
        "evidence_claims_made": False,
        "fabricated_citations": False,
    }


def render_report(result: dict) -> str:
    lines = [
        "# Related Work Audit",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        f"Matrix: `{result['matrix_path']}`  |  paper: `{result['paper_path']}`",
        f"Categories covered in paper: {result['n_categories'] - len(result['missing_categories'])}/{result['n_categories']}",
        "",
        "No citations are fabricated. Empty `representative_works` are citation TODOs.",
        "",
        "## Category coverage",
        "",
        "| Category | In paper | Needs citations | Differentiator |",
        "| --- | --- | --- | --- |",
    ]
    for r in result["categories"]:
        lines.append(f"| `{r['category']}` | {r['covered_in_paper']} | {r['needs_citations']} | {r['differentiator']} |")
    lines += [
        "",
        "## Citation integrity",
        "",
        f"- `\\cite` keys found: {result['cite_keys_found'] or 'none'}",
        f"- Unverified cite keys (fabrication risk): {result['unverified_cite_keys'] or 'none'}",
        "",
        "## Novelty-claim flags",
        "",
    ]
    if result["novelty_claim_flags"]:
        lines.append("| Phrase | Has citation | Line |")
        lines.append("| --- | --- | --- |")
        for f in result["novelty_claim_flags"]:
            lines.append(f"| {f['phrase']} | {f['has_citation']} | {f['line']} |")
    else:
        lines.append("None found.")
    lines += [
        "",
        "## TODO",
        "",
        *[f"- Add verified citations for `{c}`." for c in result["categories_needing_citations"]],
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC related-work coverage / citation audit")
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--paper", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = audit_related_work(args.matrix, args.paper)
    ensure_parent(args.out)
    Path(args.out).write_text(render_report(result), encoding="utf-8")
    import json

    print(json.dumps({
        "n_categories": result["n_categories"],
        "all_categories_covered": result["all_categories_covered"],
        "categories_needing_citations": result["categories_needing_citations"],
        "fabrication_risk": result["fabrication_risk"],
        "out": args.out,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
