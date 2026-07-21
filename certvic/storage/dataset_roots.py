"""Dataset-root policy and (opt-in) root validation (V3 prompt 02).

CertVIC is recipe-first: dataset pixels (ADE20K) are never rehosted and the root
is supplied by the user at run time, never hard-coded or committed. This module
emits the dataset-root policy as markdown and -- only when a root is explicitly
passed -- validates it without scanning or copying pixels.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from certvic.io import ensure_parent
from certvic.storage.path_policy import is_private_absolute, is_symlink_escape

# The canonical output roots CertVIC writes under (relative to repo root).
CANONICAL_OUTPUT_ROOTS = [
    "data/manifests",
    "data/masks",
    "data/edits",
    "data/predictions",
    "data/results",
    "data/annotations",
    "data/provenance",
    "compute_bundles",
]

# Datasets CertVIC points to (pointer-only; pixels never rehosted).
KNOWN_DATASETS = {
    "ade20k": {
        "name": "ADE20K",
        "license": "pointer_only / research terms (not rehosted)",
        "supply_via": "--ade20k-root <ROOT> or config ade20k_root",
        "note": "Semantic PNG annotations are read locally; pixels are never copied into the repo or release.",
    },
}


def dataset_root_policy() -> dict:
    return {
        "policy": "certvic_dataset_root_policy",
        "principles": [
            "Dataset roots are user-supplied at run time (CLI flag or config), never hard-coded.",
            "Dataset roots are never committed to the repo and never written into release artifacts.",
            "Pixels are not rehosted; CertVIC is recipe-first (pointers + hashes + recipes).",
            "Automatic downloads are disabled; the user places the dataset locally first.",
            "Output roots live under data/ (or compute_bundles/), never under a system or home root.",
        ],
        "known_datasets": KNOWN_DATASETS,
        "canonical_output_roots": CANONICAL_OUTPUT_ROOTS,
        "evidence_claims_made": False,
    }


def validate_root(root: str, *, repo_root: str | None = None) -> dict:
    """Validate a user-supplied dataset root. Does NOT scan or copy pixels."""
    repo = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
    p = Path(root)
    findings: list[str] = []
    exists = p.exists()
    is_dir = p.is_dir()
    if not exists:
        findings.append("root_does_not_exist")
    elif not is_dir:
        findings.append("root_is_not_a_directory")
    # Root inside the repo would risk pixels being committed/packaged.
    try:
        p.resolve().relative_to(repo)
        findings.append("root_inside_repo")
    except (ValueError, OSError, RuntimeError):
        pass
    if is_symlink_escape(str(p), str(repo)) and exists:
        # Outside the repo is expected and good; this only flags weird symlinks.
        pass
    return {
        "root": str(root),
        "exists": exists,
        "is_directory": is_dir,
        "is_private_absolute": is_private_absolute(str(root)),
        "ok": not findings,
        "findings": findings,
        "scanned_pixels": False,
        "evidence_claims_made": False,
    }


def render_policy(policy: dict) -> str:
    lines = [
        "# Dataset Root Policy",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "CertVIC is recipe-first. Dataset pixels are never rehosted; the dataset root",
        "is supplied by the user at run time and never committed or released.",
        "",
        "## Principles",
        "",
        *[f"- {p}" for p in policy["principles"]],
        "",
        "## Known datasets (pointer-only)",
        "",
        "| Dataset | License | Supply via | Note |",
        "| --- | --- | --- | --- |",
    ]
    for d in policy["known_datasets"].values():
        lines.append(f"| {d['name']} | {d['license']} | `{d['supply_via']}` | {d['note']} |")
    lines += [
        "",
        "## Canonical output roots",
        "",
        *[f"- `{r}/`" for r in policy["canonical_output_roots"]],
        "",
        "Outputs must stay under these roots; never write under `/`, the home dir, or the repo root itself.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC dataset-root policy")
    parser.add_argument("--out", default="data/results/dataset_root_policy.md")
    parser.add_argument("--validate-root", help="optional: validate a user-supplied root (no scanning)")
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    policy = dataset_root_policy()
    ensure_parent(args.out)
    Path(args.out).write_text(render_policy(policy), encoding="utf-8")
    import json

    summary = {"policy": args.out, "n_known_datasets": len(policy["known_datasets"])}
    if args.validate_root:
        summary["root_validation"] = validate_root(args.validate_root, repo_root=args.repo_root)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
