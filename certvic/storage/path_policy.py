"""Path-safety policy checks for CertVIC outputs and release dirs (V3 prompt 02).

Pure string/Path inspection — no network, no heavy imports, no real dataset
scanning. Detects:

- private absolute paths (``/Users/...``, ``/home/...``, the current home dir);
- Kaggle-hostile names (spaces / characters that break dataset slugs);
- symlink escapes (a path that resolves outside its declared root);
- unsafe overwrite roots (``/``, home, repo root, or other non-data targets);
- release path leaks (private absolute paths surfacing in release artifacts).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Prefixes that are private to a user's machine and must never ship in artifacts.
PRIVATE_PREFIXES = ("/Users/", "/home/", "/root/", "/mnt/", "/media/")

# Kaggle dataset/file names are safest restricted to this character class.
KAGGLE_SAFE_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")

# Roots that must never be used as a writable/overwritable output target.
def _unsafe_roots() -> set[str]:
    roots = {"/", str(Path.home()), str(Path.cwd())}
    # The repo root (two levels up from this file) is also off-limits as a dump.
    roots.add(str(Path(__file__).resolve().parents[2]))
    return {str(Path(r).resolve()) for r in roots}


def is_private_absolute(path: str) -> bool:
    text = str(path)
    if any(text.startswith(p) for p in PRIVATE_PREFIXES):
        return True
    home = str(Path.home())
    return text == home or text.startswith(home + os.sep)


def is_kaggle_safe(name: str) -> bool:
    return bool(name) and bool(KAGGLE_SAFE_RE.match(name)) and " " not in name


def kaggle_unsafe_reason(name: str) -> str | None:
    if not name:
        return "empty name"
    if " " in name:
        return "contains spaces"
    if not KAGGLE_SAFE_RE.match(name):
        bad = sorted({c for c in name if not re.match(r"[A-Za-z0-9._/\-]", c)})
        return f"contains characters unsafe for Kaggle slugs: {bad}"
    return None


def is_symlink_escape(path: str, root: str) -> bool:
    """True if ``path`` resolves to a location outside ``root`` (symlink escape)."""
    try:
        root_resolved = Path(root).resolve()
        target = Path(path).resolve()
    except (OSError, RuntimeError):
        return False
    try:
        target.relative_to(root_resolved)
        return False
    except ValueError:
        return True


def is_unsafe_overwrite_root(path: str) -> bool:
    """True if writing/overwriting ``path`` would clobber a top-level/system root."""
    try:
        resolved = str(Path(path).resolve())
    except (OSError, RuntimeError):
        return False
    return resolved in _unsafe_roots()


def audit_path(path: str, *, root: str | None = None, expect_kaggle_safe: bool = False) -> dict:
    """Return the policy findings for a single path."""
    findings: list[str] = []
    if is_private_absolute(path):
        findings.append("private_absolute_path")
    if is_unsafe_overwrite_root(path):
        findings.append("unsafe_overwrite_root")
    if root and is_symlink_escape(path, root):
        findings.append("symlink_escape")
    if expect_kaggle_safe:
        reason = kaggle_unsafe_reason(Path(path).name)
        if reason:
            findings.append(f"kaggle_unsafe:{reason}")
    return {"path": path, "ok": not findings, "findings": findings}


def audit_paths(paths: list[str], *, root: str | None = None, expect_kaggle_safe: bool = False) -> dict:
    audits = [audit_path(p, root=root, expect_kaggle_safe=expect_kaggle_safe) for p in paths]
    problems = [a for a in audits if not a["ok"]]
    return {
        "n_paths": len(audits),
        "n_problems": len(problems),
        "ok": not problems,
        "audits": audits,
        "private_absolute_paths": [a["path"] for a in audits if "private_absolute_path" in a["findings"]],
        "unsafe_overwrite_roots": [a["path"] for a in audits if "unsafe_overwrite_root" in a["findings"]],
        "symlink_escapes": [a["path"] for a in audits if "symlink_escape" in a["findings"]],
        "kaggle_unsafe": [a["path"] for a in audits if any(f.startswith("kaggle_unsafe") for f in a["findings"])],
        "evidence_claims_made": False,
    }


def collect_output_paths(config: dict) -> list[str]:
    """Pull declared output paths out of a pilot/eval config (no disk access)."""
    paths: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, str) and ("/" in node) and not node.startswith(("http", "planned://", "simulated://")):
            paths.append(node)

    for key in ("outputs", "mask_out_dir", "visual_review"):
        if key in config:
            walk(config[key])
    return sorted(set(paths))
