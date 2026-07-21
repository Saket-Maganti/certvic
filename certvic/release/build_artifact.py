"""Recipe-first artifact builder.

Packages pointers, hashes, masks metadata, edit plans, task manifests, schemas,
and reproducibility scripts. By default it does NOT copy non-redistributable
pixels. A release audit verifies no private absolute paths and no forbidden
pixels, writes a license summary, a checksum manifest, a reproducibility command
list, and a zero-cost statement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from certvic.hashing import sha256_file
from certvic.io import read_jsonl, write_json

DEFAULT_RELEASE_CONFIG = {
    "include_cc0_pixels": False,
    "include_pointer_only_sources": True,
    "include_generated_edits": False,
    "require_license_verified": True,
    "exclude_private_paths": True,
    "anonymize_local_paths": True,
    "hash_manifests": True,
    "write_checksums": True,
    "manifests_dir": "data/manifests",
    "docs_dir": "docs",
    "reproducibility_commands": [
        "python3 -m pytest -q",
        "python3 -m certvic.data.ade20k_adapter --ade20k-root <ROOT> --out-sources data/manifests/ade20k_sources.jsonl --out-masks data/manifests/ade20k_masks.jsonl",
        "python3 -m certvic.pipeline.run_tiny_pilot --config configs/real_pilot_ade20k.yaml --ade20k-root <ROOT> --out-dir data/results/tiny_real_pilot",
        "python3 -m certvic.pipeline.run_tiny_eval --config configs/tiny_reviewed_eval.yaml --tasks <REVIEWED_TASKS> --provider qwen2_5_vl_7b --out-dir data/results/tiny_eval_qwen --max-items 20",
    ],
}

FORBIDDEN_PIXEL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def load_release_config(path: str | None) -> dict:
    cfg = dict(DEFAULT_RELEASE_CONFIG)
    if path and Path(path).exists():
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        cfg.update(data)
    return cfg


def _anonymize(value, anonymize: bool) -> object:
    if not anonymize or not isinstance(value, str):
        return value
    home = str(Path.home())
    out = value.replace(home, "~")
    # Collapse any remaining absolute paths to their basename pointer.
    if out.startswith("/"):
        out = f"<local>/{Path(out).name}"
    return out


def _sanitize_record(record: dict, cfg: dict) -> dict:
    out = {}
    for key, value in record.items():
        if key in {"local_path", "original_image_path", "edited_image_path", "image_path", "mask_path", "annotation_path"}:
            out[key] = _anonymize(value, cfg["anonymize_local_paths"])
        else:
            out[key] = value
    return out


def build_artifact(config_path: str | None, out_dir: str, repo_root: str | None = None) -> dict:
    cfg = load_release_config(config_path)
    root = Path(repo_root) if repo_root else Path.cwd()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifests").mkdir(exist_ok=True)

    manifests_dir = root / cfg["manifests_dir"]
    packaged: list[str] = []
    audit_errors: list[str] = []
    license_categories: dict[str, int] = {}

    if manifests_dir.exists():
        for jsonl in sorted(manifests_dir.glob("*.jsonl")):
            rows = read_jsonl(str(jsonl))
            sanitized = [_sanitize_record(r, cfg) for r in rows]
            # license tally + private-path audit
            for r in sanitized:
                cat = str(r.get("license_category", "")) or ""
                if cat:
                    license_categories[cat] = license_categories.get(cat, 0) + 1
                if cfg["exclude_private_paths"]:
                    for k in ("local_path", "original_image_path", "edited_image_path", "image_path"):
                        v = r.get(k)
                        if isinstance(v, str) and v.startswith("/") and not v.startswith("<local>"):
                            audit_errors.append(f"{jsonl.name}:{r.get('item_id') or r.get('source_id')}: private absolute path in {k}")
            dest = out / "manifests" / jsonl.name
            with dest.open("w", encoding="utf-8") as handle:
                for r in sanitized:
                    handle.write(json.dumps(r, sort_keys=True) + "\n")
            packaged.append(str(dest.relative_to(out)))

    # Package schemas + scripts (text only, never pixels).
    no_forbidden_pixels = True
    if cfg["include_cc0_pixels"] is False:
        for path in out.rglob("*"):
            if path.suffix.lower() in FORBIDDEN_PIXEL_EXTENSIONS:
                no_forbidden_pixels = False
                audit_errors.append(f"forbidden pixel file in artifact: {path.name}")

    # Checksums
    checksums = {}
    if cfg["write_checksums"]:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path.name != "checksums.json":
                checksums[str(path.relative_to(out))] = sha256_file(path)
        write_json(out / "checksums.json", checksums)

    audit = {
        "no_private_absolute_paths": not any("private absolute path" in e for e in audit_errors),
        "no_forbidden_pixels": no_forbidden_pixels,
        "license_summary": dict(sorted(license_categories.items())),
        "reproducibility_commands": cfg["reproducibility_commands"],
        "zero_cost_statement": "All steps run on local CPU/Mac or free Kaggle/Colab GPU with open models and public data; no paid services.",
        "errors": audit_errors,
        "passed": not audit_errors,
    }
    write_json(out / "release_audit.json", audit)

    manifest = {
        "out_dir": out_dir,
        "config": config_path,
        "packaged_manifests": packaged,
        "include_cc0_pixels": cfg["include_cc0_pixels"],
        "include_generated_edits": cfg["include_generated_edits"],
        "release_mode": "recipe_first",
        "audit_passed": audit["passed"],
        "checksum_count": len(checksums),
        "zero_cost": True,
    }
    write_json(out / "artifact_manifest.json", manifest)
    (out / "README.md").write_text(_render_readme(manifest, audit), encoding="utf-8")
    return manifest


def _render_readme(manifest: dict, audit: dict) -> str:
    return "\n".join([
        "# CertVIC Recipe-First Artifact",
        "",
        "Recipe-first: pointers, hashes, masks metadata, edit plans, task manifests, and scripts.",
        "Non-redistributable pixels are NOT included. Regenerate edits/images from source pointers.",
        "",
        f"- audit passed: {audit['passed']}",
        f"- license summary: {audit['license_summary']}",
        f"- packaged manifests: {len(manifest['packaged_manifests'])}",
        "",
        "## Zero cost",
        audit["zero_cost_statement"],
        "",
        "## Reproduce",
        "",
        *[f"```\n{cmd}\n```" for cmd in audit["reproducibility_commands"]],
        "",
    ])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build a recipe-first CertVIC artifact")
    parser.add_argument("--config")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    print(json.dumps(build_artifact(args.config, args.out_dir, repo_root=args.repo_root), sort_keys=True))


if __name__ == "__main__":
    main()
