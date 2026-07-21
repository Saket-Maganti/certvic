"""Kaggle free-compute packager (V3 prompt 03).

Wraps :mod:`certvic.compute.job_bundle` with Kaggle-specific guidance (free T4/P100
GPU, ~12 h session limit, `/kaggle/input` read-only datasets, `/kaggle/working`
~20 GB scratch, internet off by default). Builds a bundle; never executes it.
"""

from __future__ import annotations

import argparse
import json

from certvic.compute.job_bundle import JOB_TYPES, build_bundle

KAGGLE_NOTES = [
    "Enable the GPU accelerator (free T4 or P100) in Notebook settings.",
    "Free GPU sessions are capped (~12 h) and weekly GPU quota is limited; shard long jobs.",
    "Mount data and weights as read-only Kaggle **input** datasets under `/kaggle/input`.",
    "Write outputs to `/kaggle/working` (~20 GB); offload finished shards before it fills.",
    "Keep internet **off** unless a step truly needs it; never add paid endpoints or keys.",
]


def package(job: str, config: str, out_dir: str, *, scale: int | None = None, anonymize_paths: bool = True) -> dict:
    return build_bundle(
        job,
        config=config,
        out_dir=out_dir,
        platform="kaggle",
        scale=scale,
        anonymize_paths=anonymize_paths,
        platform_notes=KAGGLE_NOTES,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CertVIC Kaggle free-compute packager")
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
