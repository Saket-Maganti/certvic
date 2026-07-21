"""CLI for generating one simulation-only CertVIC run."""

from __future__ import annotations

import argparse
import json

from certvic.sim.simulated_manifests import build_synthetic_run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate one SIMULATED_ONLY CertVIC run.")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--n-items", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    result = build_synthetic_run(args.out_dir, args.scenario, args.n_items, args.seed)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
