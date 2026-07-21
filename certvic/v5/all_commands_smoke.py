"""Smoke-test safe V5 commands with local fixtures or help-mode."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from certvic.io import write_json

SAFE_COMMANDS = [
    ["certvic.validation.rater_training", "--out-dir", "data/results/v5_smoke/rater_training"],
    ["certvic.cards.model_card", "--provider", "qwen2_5_vl_7b", "--out", "data/results/v5_smoke/model_card.md"],
    ["certvic.experiments.registry", "validate", "--config", "configs/experiments.yaml"],
    ["certvic.contracts.result_contracts", "validate", "--contracts", "configs/result_contracts.yaml", "--root", "data/results"],
]
SKIPPED_UNSAFE = [
    "real ADE20K pipeline execution",
    "diffusion GPU generation",
    "open-local VLM inference",
    "dataset or model downloads",
]


def run_smoke(out: str) -> dict:
    records = []
    for command in SAFE_COMMANDS:
        proc = subprocess.run(
            [sys.executable, "-m", *command],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )
        records.append(
            {
                "command": "python3 -m " + " ".join(command),
                "returncode": proc.returncode,
                "status": "pass" if proc.returncode == 0 else "fail",
                "stdout_tail": proc.stdout[-500:],
                "stderr_tail": proc.stderr[-500:],
            }
        )
    result = {
        "safe_commands": records,
        "skipped_unsafe": SKIPPED_UNSAFE,
        "passed": all(row["returncode"] == 0 for row in records),
        "downloads_attempted": False,
        "gpu_required": False,
        "vlm_inference_run": False,
    }
    write_json(out, result)
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run safe V5 command smoke tests")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = run_smoke(args.out)
    print(json.dumps({"out": args.out, "passed": result["passed"], "skipped": len(result["skipped_unsafe"])}, sort_keys=True))


if __name__ == "__main__":
    main()

