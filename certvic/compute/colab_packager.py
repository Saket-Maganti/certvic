"""Colab free-compute packager (V3 prompt 03).

Wraps :mod:`certvic.compute.job_bundle` with Colab-specific guidance (free T4
GPU, idle/session timeouts, `/content` scratch, optional Drive mount). Fallback
to Kaggle is preferred for long jobs. Builds a bundle; never executes it.
"""

from __future__ import annotations

import argparse
import json

from certvic.compute.job_bundle import JOB_TYPES, build_bundle

COLAB_NOTES = [
    "Set Runtime > Change runtime type > GPU (free T4) before running.",
    "Free Colab disconnects on idle and caps session length; checkpoint and resume often.",
    "Use `/content` for scratch; optionally mount Google Drive for inputs/outputs (free tier).",
    "Place data and weights locally (Drive or uploaded); CertVIC never auto-downloads them.",
    "Never add paid Colab Pro-only assumptions, paid endpoints, or credentials.",
]


def package(job: str, config: str, out_dir: str, *, scale: int | None = None, anonymize_paths: bool = True) -> dict:
    return build_bundle(
        job,
        config=config,
        out_dir=out_dir,
        platform="colab",
        scale=scale,
        anonymize_paths=anonymize_paths,
        platform_notes=COLAB_NOTES,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC Colab free-compute packager")
    parser.add_argument("--job", required=True, choices=sorted(JOB_TYPES))
    parser.add_argument("--config", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--scale", type=int)
    parser.add_argument("--no-anonymize", action="store_true", help="keep absolute paths (NOT recommended)")
    args = parser.parse_args(argv)
    manifest = package(args.job, args.config, args.out_dir, scale=args.scale, anonymize_paths=not args.no_anonymize)
    print(json.dumps({
        "job": manifest["job"],
        "platform": manifest["platform"],
        "out_dir": args.out_dir,
        "safe": manifest["safe"],
        "evidence_status": manifest["evidence_status"],
        "files": manifest["files"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
