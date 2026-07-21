"""Security / integrity audit for a Kaggle upload bundle (zip).

Inspects a built bundle zip without executing anything: rejects VCS/venv/cache
dirs and model-weight binaries, flags raw dataset image pixels and oversized
files, scans text entries for private local absolute paths (``/Users/...`` etc.)
and API-key-looking strings, and explicitly permits Kaggle mount paths
(``/kaggle/input/...``). Static inspection only; no GPU, no downloads, no
evidence. Mirrors the allowlist of ``certvic.security.path_audit`` for the handful
of code files that legitimately contain prefix *constants* (not real home paths).
"""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

from certvic.io import write_json

# --- forbidden entries -------------------------------------------------------
FORBIDDEN_DIR_PARTS = (
    ".git", ".svn", ".hg", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", "node_modules", ".ipynb_checkpoints", ".idea", ".vscode",
)
WEIGHT_SUFFIXES = {
    ".safetensors", ".bin", ".ckpt", ".pt", ".pth", ".onnx", ".h5", ".pb",
    ".gguf", ".msgpack", ".tflite", ".npz", ".joblib",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".gif"}
SECRET_FILE_NAMES = {
    ".env", ".netrc", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "credentials", "kaggle.json", ".pypirc", ".npmrc",
}
DATASET_DIR_MARKERS = ("ade20k_root", "ADEChallengeData2016", "ade20kdataset", "ADE20K_2021", "ADE20K-main")

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".yaml", ".yml", ".tex", ".sh", ".json", ".jsonl",
    ".cfg", ".ini", ".toml", ".csv", ".cff", ".rst", ".ipynb",
}
LARGE_FILE_BYTES = 5 * 1024 * 1024  # raw datasets / weights should never be here

# Private absolute path = prefix + at least one real path segment. A bare constant
# like the tuple element '/Users/' is NOT matched (no segment after the slash).
PRIVATE_PATH_RE = re.compile(r"(?:/Users/|/home/|/root/|/mnt/|/media/)[A-Za-z0-9._][A-Za-z0-9._\-]*")
KAGGLE_PATH_RE = re.compile(r"^/kaggle/(?:input|working|temp|src)(?:/|$)")

# Files that legitimately contain prefix constants / regexes (never real secrets).
PATH_SCAN_ALLOWLIST = (
    "certvic/security/",
    "certvic/storage/path_policy.py",
    "certvic/compute/job_bundle.py",
    "certvic/release/reproduction_audit.py",
)

SECRET_RES: list[tuple[str, re.Pattern]] = [
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("aws_access_key_id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_\-]{30,}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
    (
        "generic_secret_assignment",
        re.compile(
            r"(?i)(?:api[_-]?key|secret[_-]?key|secret|password|passwd|access[_-]?token|auth[_-]?token)"
            r"\s*[:=]\s*['\"][A-Za-z0-9_\-/+]{16,}['\"]"
        ),
    ),
]


def is_allowlisted(name: str, allowlist: tuple[str, ...] = PATH_SCAN_ALLOWLIST) -> bool:
    return any(token in name for token in allowlist)


def scan_text(name: str, text: str, *, allowlist: tuple[str, ...] = PATH_SCAN_ALLOWLIST) -> list[dict]:
    """Scan one text entry for private paths and secret-looking strings."""
    findings: list[dict] = []
    skip_paths = is_allowlisted(name, allowlist)
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not skip_paths:
            for m in PRIVATE_PATH_RE.finditer(line):
                findings.append({"entry": name, "line": line_no, "kind": "private_absolute_path", "match": m.group(0)[:120]})
        if not skip_paths:
            for label, pat in SECRET_RES:
                for m in pat.finditer(line):
                    findings.append({"entry": name, "line": line_no, "kind": f"secret:{label}", "match": m.group(0)[:24] + "..."})
    return findings


def classify_entry(name: str, size: int) -> list[dict]:
    """Structural checks on a single zip entry (no content read)."""
    findings: list[dict] = []
    posix = name.replace("\\", "/")
    parts = set(Path(posix).parts)
    base = Path(posix).name
    suffix = Path(posix).suffix.lower()
    if parts & set(FORBIDDEN_DIR_PARTS):
        findings.append({"entry": name, "kind": "forbidden_dir", "match": sorted(parts & set(FORBIDDEN_DIR_PARTS))[0]})
    if suffix in WEIGHT_SUFFIXES:
        findings.append({"entry": name, "kind": "model_weight_file", "match": suffix})
    if suffix in IMAGE_SUFFIXES:
        findings.append({"entry": name, "kind": "raw_image_pixels", "match": suffix})
    if any(marker in posix for marker in DATASET_DIR_MARKERS):
        findings.append({"entry": name, "kind": "dataset_pixels_path", "match": next(m for m in DATASET_DIR_MARKERS if m in posix)})
    if base in SECRET_FILE_NAMES or base.endswith(".pem") or base.endswith(".key"):
        findings.append({"entry": name, "kind": "secret_file", "match": base})
    if size > LARGE_FILE_BYTES:
        findings.append({"entry": name, "kind": "large_file", "match": f"{size} bytes"})
    return findings


def audit_bundle(bundle_path: str, *, allowlist: tuple[str, ...] = PATH_SCAN_ALLOWLIST) -> dict:
    path = Path(bundle_path)
    if not path.exists():
        return {"bundle": bundle_path, "ok": False, "error": "bundle_not_found", "findings": [], "n_findings": 1}
    findings: list[dict] = []
    n_entries = 0
    n_text = 0
    total_bytes = 0
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            n_entries += 1
            total_bytes += info.file_size
            findings.extend(classify_entry(info.filename, info.file_size))
            if Path(info.filename).suffix.lower() in TEXT_SUFFIXES and info.file_size <= LARGE_FILE_BYTES:
                try:
                    text = zf.read(info.filename).decode("utf-8", errors="replace")
                except (OSError, zipfile.BadZipFile):
                    continue
                n_text += 1
                findings.extend(scan_text(info.filename, text, allowlist=allowlist))
    by_kind: dict[str, int] = {}
    for f in findings:
        by_kind[f["kind"]] = by_kind.get(f["kind"], 0) + 1
    return {
        "bundle": bundle_path,
        "n_entries": n_entries,
        "n_text_scanned": n_text,
        "total_uncompressed_bytes": total_bytes,
        "n_findings": len(findings),
        "findings_by_kind": dict(sorted(by_kind.items())),
        "findings": findings,
        "ok": not findings,
        "evidence_claims_made": False,
    }


def render_report(result: dict) -> str:
    status = "PASS" if result.get("ok") else "FAIL"
    lines = [
        "# Kaggle Bundle Security Audit",
        "",
        f"- Bundle: `{result.get('bundle')}`",
        f"- Status: **{status}**",
        f"- Entries: {result.get('n_entries')} ({result.get('n_text_scanned')} text files scanned)",
        f"- Uncompressed size: {result.get('total_uncompressed_bytes', 0) / 1_000_000:.2f} MB",
        f"- Findings: {result.get('n_findings')}",
        "",
    ]
    if result.get("error"):
        lines.append(f"Error: `{result['error']}`")
        return "\n".join(lines) + "\n"
    if result.get("ok"):
        lines += [
            "No forbidden entries, no model weights, no raw dataset pixels, no private",
            "absolute paths, and no API-key-looking strings were found. Kaggle mount",
            "paths (`/kaggle/input/...`) are permitted by design.",
            "",
        ]
    else:
        lines += ["## Findings by kind", ""]
        for kind, n in result["findings_by_kind"].items():
            lines.append(f"- `{kind}`: {n}")
        lines += ["", "## Detail", ""]
        for f in result["findings"][:200]:
            loc = f"{f['entry']}" + (f":{f['line']}" if "line" in f else "")
            lines.append(f"- `{f['kind']}` — {loc} — `{f.get('match','')}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit a Kaggle upload bundle for secrets/pixels/private paths")
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--out", help="markdown report path")
    parser.add_argument("--json-out", help="json findings path")
    parser.add_argument("--strict", action="store_true", help="exit non-zero if findings exist")
    args = parser.parse_args(argv)

    result = audit_bundle(args.bundle)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(render_report(result), encoding="utf-8")
    if args.json_out:
        write_json(args.json_out, result)
    print(
        '{"bundle": "%s", "ok": %s, "n_findings": %d}'
        % (result["bundle"], str(result["ok"]).lower(), result["n_findings"])
    )
    if args.strict and not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
