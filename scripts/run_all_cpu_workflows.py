#!/usr/bin/env python3
"""Execute, resume, or inspect the fail-closed CertVIC CPU workflow plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certvic.cvpr.cpu_execution import (  # noqa: E402
    execute,
    register_repository_bundles,
    status,
    validate_first_wave_returns,
    write_data_inventory,
)
from certvic.cvpr.non_human_continuation import (  # noqa: E402
    resume_after_confirmatory_returns,
    resume_after_human_review,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--resume", action="store_true")
    mode.add_argument("--resume-after-human-review", action="store_true")
    mode.add_argument("--resume-after-confirmatory-returns", action="store_true")
    mode.add_argument("--only", metavar="STAGE")
    mode.add_argument(
        "--internal",
        choices=("data_inventory", "first_wave_returns", "register_bundles"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--synthetic-fixture", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--synthetic-out", help=argparse.SUPPRESS)
    parser.add_argument(
        "--post-review-config",
        default="configs/execution/certvic_confirmatory_post_review_pipeline.json",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--confirmatory-return-dir")
    args = parser.parse_args()
    if args.status:
        result = status()
    elif args.resume_after_human_review:
        result = resume_after_human_review(
            ROOT,
            config_path=args.post_review_config,
            synthetic_fixture=args.synthetic_fixture,
            synthetic_out=args.synthetic_out,
        )
    elif args.resume_after_confirmatory_returns:
        result = resume_after_confirmatory_returns(
            ROOT,
            input_dir=args.confirmatory_return_dir,
            synthetic_fixture=args.synthetic_fixture,
            synthetic_out=args.synthetic_out,
        )
    elif args.internal == "data_inventory":
        write_data_inventory()
        result = {"status": "COMPLETED", "action": "data_inventory"}
    elif args.internal == "first_wave_returns":
        validate_first_wave_returns()
        result = {"status": "COMPLETED", "action": "first_wave_returns"}
    elif args.internal == "register_bundles":
        register_repository_bundles()
        result = {"status": "COMPLETED", "action": "register_bundles"}
    else:
        result = execute(resume=args.resume, only=args.only)
    print(json.dumps(result, indent=2, sort_keys=True))
    failed = result.get("status") in {
        "PHASE_B_LOCAL_REPAIR_REQUIRED",
        "BLOCKED_BY_GENUINE_HUMAN_REVIEW_OR_GENERATED_CANDIDATES",
        "BLOCKED_INVALID_OR_INCOMPLETE_GENUINE_REVIEW",
        "REVIEW_VALIDATED_POST_REVIEW_PIPELINE_INPUTS_PRESENT",
        "BLOCKED_MISSING_EXTERNAL_OR_REVIEW_INPUTS",
        "BLOCKED_FINAL_SELECTED_SET_DETECTABILITY_GATE",
        "BLOCKED_PRECONDITIONS",
        "BLOCKED_MISSING_TASK_MANIFEST",
        "BLOCKED_TASK_BUNDLE",
        "BLOCKED_EXECUTION_PERMISSION",
        "BLOCKED_MISSING_RETURNED_ARCHIVES",
        "BLOCKED_MISSING_PROVIDERS",
    }
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
