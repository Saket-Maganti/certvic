"""Private-path and dataset-root leak scanner (V3 prompt 16).

Scans text files under a root for private absolute paths (``/Users/...``,
``/home/...``, the home dir) and local dataset roots that must never ship in a
release. Static text inspection only. Generated output dirs and an allowlist of
files that legitimately show example paths are skipped.
"""

from __future__ import annotations

import re
from pathlib import Path

from certvic.storage.path_policy import PRIVATE_PREFIXES

TEXT_EXTS = {".py", ".md", ".txt", ".yaml", ".yml", ".tex", ".sh", ".json", ".jsonl", ".cfg", ".ini", ".toml", ".csv"}

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".ipynb_checkpoints", ".idea", ".vscode"}

# Generated / local output trees (not part of a recipe-first release).
GENERATED_PREFIXES = (
    "data/results", "data/predictions", "data/dashboard", "data/provenance",
    "data/edits", "data/masks", "data/annotations", "compute_bundles", "release",
)

# Files that legitimately contain example private paths / marker strings.
DEFAULT_ALLOWLIST = (
    "tests/",
    # Codex prompt packs are dev input specs (they say "Work in /Users/.../certVIC")
    # and are never part of a recipe-first release.
    "_prompt_pack",
    "promptpacks/",
    "certvic_codex_v6_directional_correction_pack",
    "certvic/security/",
    "certvic/storage/path_policy.py",
    "certvic/compute/job_bundle.py",
    "certvic/release/reproduction_audit.py",
    "docs/SECURITY_PRIVACY",
    "docs/STORAGE_AND_PATH_POLICY.md",
    "docs/ZERO_COST_POLICY.md",
    "docs/DOCKERLESS_REPRODUCTION.md",
    "docs/FREE_COMPUTE_BUNDLES.md",
    "docs/REPRO.md",
    "docs/RUN_LEDGER.md",
    "docs/DATA_CARD.md",
)

_PRIVATE_RE = re.compile("|".join(re.escape(p) + r"[^\s\"':]*" for p in PRIVATE_PREFIXES))
_DATASET_ROOT_RE = re.compile(r"(?:ade20k_root|dataset_root)\s*[:=]\s*['\"]?(/[^\s'\"]+)")


def is_allowlisted(rel_path: str, allowlist: tuple[str, ...]) -> bool:
    return any(token in rel_path for token in allowlist)


def iter_text_files(root: Path, *, skip_dirs=SKIP_DIRS, generated_prefixes=GENERATED_PREFIXES, exts=TEXT_EXTS):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        rel = path.relative_to(root)
        parts = set(rel.parts)
        if parts & skip_dirs:
            continue
        rel_str = rel.as_posix()
        if any(rel_str.startswith(pref) for pref in generated_prefixes):
            continue
        yield path, rel_str


def scan_private_paths(root: str, *, allowlist: tuple[str, ...] = DEFAULT_ALLOWLIST) -> dict:
    rootp = Path(root)
    findings: list[dict] = []
    home = str(Path.home())
    for path, rel in iter_text_files(rootp):
        if is_allowlisted(rel, allowlist):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for m in _PRIVATE_RE.finditer(line):
                findings.append({"file": rel, "line": line_no, "kind": "private_absolute_path", "match": m.group(0)[:120]})
            if home in line and home not in PRIVATE_PREFIXES:
                findings.append({"file": rel, "line": line_no, "kind": "home_dir_path", "match": home})
            for m in _DATASET_ROOT_RE.finditer(line):
                findings.append({"file": rel, "line": line_no, "kind": "local_dataset_root", "match": m.group(1)[:120]})
    return {"scan": "private_paths", "n_findings": len(findings), "findings": findings, "ok": not findings}
