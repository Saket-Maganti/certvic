"""Generate V4 real-run command bundles without executing them."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certvic.commands.command_manifest import (
    ADE20K_PLACEHOLDER,
    MODEL_CACHE_PLACEHOLDER,
    SUPPORTED_STAGES,
    build_command_manifest,
    commands_md,
    commands_sh,
    expected_inputs_md,
    expected_outputs_md,
    resume_notes_md,
    staged_scripts,
)
from certvic.io import write_json


def write_command_bundle(
    stage: str,
    out_dir: str,
    *,
    ade20k_root: str = ADE20K_PLACEHOLDER,
    model_cache_root: str = MODEL_CACHE_PLACEHOLDER,
    providers: list[str] | None = None,
    anonymize_paths: bool = True,
    staged_only: bool = False,
) -> dict:
    manifest = build_command_manifest(
        stage,
        ade20k_root=ade20k_root,
        model_cache_root=model_cache_root,
        providers=providers,
        anonymize_paths=anonymize_paths,
    )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "commands.sh": commands_sh(manifest),
        "commands.md": commands_md(manifest),
        "expected_inputs.md": expected_inputs_md(manifest),
        "expected_outputs.md": expected_outputs_md(manifest),
        "resume_notes.md": resume_notes_md(manifest),
    }
    for name, content in files.items():
        path = out / name
        path.write_text(content, encoding="utf-8")
        if name.endswith(".sh"):
            path.chmod(0o755)
    staged = staged_scripts(manifest)
    for name, content in staged.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)
    write_json(out / "command_manifest.json", manifest)
    manifest["out_dir"] = str(out)
    manifest["files"] = sorted([*files, *staged, "command_manifest.json"])
    manifest["staged_only"] = staged_only
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC V4 real-run command generator")
    parser.add_argument("--stage", required=True, choices=SUPPORTED_STAGES)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--ade20k-root", default=ADE20K_PLACEHOLDER)
    parser.add_argument("--model-cache-root", default=MODEL_CACHE_PLACEHOLDER)
    parser.add_argument("--providers", nargs="+")
    parser.add_argument("--no-anonymize", action="store_true", help="keep absolute paths in outputs")
    parser.add_argument("--staged-only", action="store_true", help="write staged scripts and guarded command index")
    args = parser.parse_args(argv)
    manifest = write_command_bundle(
        args.stage,
        args.out_dir,
        ade20k_root=args.ade20k_root,
        model_cache_root=args.model_cache_root,
        providers=args.providers,
        anonymize_paths=not args.no_anonymize,
        staged_only=args.staged_only,
    )
    print(
        json.dumps(
            {
                "stage": manifest["stage"],
                "out_dir": manifest["out_dir"],
                "files": manifest["files"],
                "n_commands": manifest["n_commands"],
                "executed": manifest["safety"]["executed"],
                "evidence_status": manifest["safety"]["planned_artifacts_evidence_status"],
                "command_manifest_sha256": manifest["command_manifest_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
