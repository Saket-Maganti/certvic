"""Build the Kaggle main-200 diffusion upload bundle (deterministic, no pixels/weights).

Allowlist-based: copies only the code/config/planning artifacts a Kaggle T4x2
diffusion session needs. ADE20K pixels, edited images, model weights, caches and
VCS dirs are never included. Path-bearing planning manifests are sanitized — the
local ADE20K root is replaced with the neutral token ``__ADE20K_ROOT__`` so the
bundle carries no private absolute paths; the Kaggle runbook swaps the token for
the real ``$ADE20K_ROOT`` mount at run time. No GPU, no downloads, no evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SANITIZE_TOKEN = "__ADE20K_ROOT__"
FIXED_ZIP_DATE = (2026, 1, 1, 0, 0, 0)  # fixed timestamp -> reproducible zip bytes

INCLUDE_DIRS = ("certvic", "configs", "scripts", "commands", "docs/runbooks")
INCLUDE_FILES = (
    "pyproject.toml",
    "README_KAGGLE_BUNDLE.md",
    "docs/RUN_AFTER_V6_CHECKLIST.md",
    "docs/V6_SINGLE_FILE_HANDOFF_SUMMARY.md",
    "notebooks/kaggle/00_precache_weights.ipynb",
    "notebooks/kaggle/certvic_main200_diffusion_T4x2.ipynb",
    "notebooks/kaggle/certvic_main200_vlm_T4x2_AFTER_GATES.ipynb",
)
PLANNING_FILES = (
    "data/results/main_real_200/pilot_selection.jsonl",
    "data/results/main_real_200/pilot_selection_summary.json",
    "data/results/main_real_200/pilot_edit_plan.jsonl",
    "data/results/main_real_200/pilot_edit_plan_summary.json",
    "data/results/main_real_200/pilot_task_preview.jsonl",
    "data/results/main_real_200/pilot_task_preview_summary.json",
    "data/results/main_real_200/diffusion_job_queue.jsonl",
    "data/results/main_real_200/diffusion_resume.jsonl",
    "data/results/main_real_200/gpu_shards/pilot_edit_plan_shard0_of_2.jsonl",
    "data/results/main_real_200/gpu_shards/pilot_edit_plan_shard1_of_2.jsonl",
)

EXCLUDE_DIR_PARTS = {
    "__pycache__", ".git", ".svn", ".hg", ".venv", "venv", "env", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", "node_modules", ".ipynb_checkpoints", ".idea", ".vscode",
}
EXCLUDE_SUFFIXES = {
    ".pyc", ".pyo", ".pyd", ".so", ".safetensors", ".bin", ".ckpt", ".pt", ".pth",
    ".onnx", ".h5", ".gguf", ".npz", ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff",
}
EXCLUDE_NAMES = {".DS_Store", ".env", "kaggle.json", "credentials"}


def _excluded(rel: Path) -> bool:
    if set(rel.parts) & EXCLUDE_DIR_PARTS:
        return True
    if rel.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    if rel.name in EXCLUDE_NAMES:
        return True
    return False


def _detect_local_root(repo: Path, planning_files=PLANNING_FILES) -> str | None:
    for rel in planning_files:
        p = repo / rel
        if p.exists() and p.suffix == ".jsonl":
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                ip = row.get("image_path") or row.get("original_image_path")
                if ip and "/images/" in ip:
                    return ip.split("/images/")[0]
    return None


def _sanitize(data: bytes, repo: Path, local_root: str | None) -> bytes:
    text = data.decode("utf-8")
    if local_root:
        text = text.replace(local_root, SANITIZE_TOKEN)
    # Belt-and-suspenders: scrub any residual repo/home absolute paths.
    text = text.replace(str(repo), "__CERTVIC_ROOT__")
    text = text.replace(str(Path.home()), "__LOCAL__")
    return text.encode("utf-8")


def collect_bundle_files(repo: Path | None = None) -> dict[str, bytes]:
    """Return {bundle_relative_path: content_bytes}, deterministic and sorted."""
    repo = repo or REPO
    local_root = _detect_local_root(repo)
    files: dict[str, bytes] = {}

    for d in INCLUDE_DIRS:
        base = repo / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(repo)
            if _excluded(rel):
                continue
            files[rel.as_posix()] = p.read_bytes()

    for f in INCLUDE_FILES:
        p = repo / f
        if p.exists() and p.is_file() and not _excluded(Path(f)):
            files[f] = p.read_bytes()

    for f in PLANNING_FILES:
        p = repo / f
        if p.exists() and p.is_file():
            files[f] = _sanitize(p.read_bytes(), repo, local_root)

    return dict(sorted(files.items()))


def build_manifest(files: dict[str, bytes], *, bundle_name: str) -> dict:
    entries = []
    for name in sorted(files):
        data = files[name]
        entries.append({"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    digest_src = "".join(f"{e['path']}:{e['sha256']}\n" for e in entries)
    return {
        "bundle": bundle_name,
        "n_entries": len(entries),
        "total_uncompressed_bytes": sum(e["size"] for e in entries),
        "content_digest": hashlib.sha256(digest_src.encode("utf-8")).hexdigest(),
        "sanitize_token": SANITIZE_TOKEN,
        "excludes": ["ade20k pixels", "edited images", "model weights", ".git", "venvs", "caches"],
        "evidence_status": "PLANNED_NOT_EXECUTED",
        "evidence_claims_made": False,
        "entries": entries,
    }


def write_bundle(files: dict[str, bytes], zip_path: str) -> None:
    out = Path(zip_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(filename=name, date_time=FIXED_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, files[name])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the Kaggle main-200 diffusion upload bundle")
    parser.add_argument("--out", default="dist/certvic_kaggle_main200_bundle.zip")
    parser.add_argument("--manifest-out", default="dist/certvic_kaggle_main200_bundle_manifest.json")
    args = parser.parse_args(argv)

    files = collect_bundle_files(REPO)
    manifest = build_manifest(files, bundle_name=Path(args.out).name)
    write_bundle(files, args.out)
    Path(args.manifest_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.manifest_out).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "bundle": args.out,
        "manifest": args.manifest_out,
        "n_entries": manifest["n_entries"],
        "total_uncompressed_bytes": manifest["total_uncompressed_bytes"],
        "content_digest": manifest["content_digest"][:16],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
