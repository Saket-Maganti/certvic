#!/usr/bin/env python3
"""Authenticate, import, and materialize one unchanged Kaggle return."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.cvpr.kagglefiles_pack import (  # noqa: E402
    KagglefilesPackError,
    identify_kaggle_return,
    import_kaggle_return,
)
from local_operator.runtime_materializer import (  # noqa: E402
    RuntimeMaterializationError,
    inspect_runtime_archive,
    materialize_runtime_archive,
    validate_materialization_destination,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Authenticate and import one unchanged Kaggle return"
    )
    parser.add_argument("return_zip")
    parser.add_argument("--pack-root", default=str(REPOSITORY_ROOT / "kagglefiles"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        identity = identify_kaggle_return(args.return_zip, pack_root=args.pack_root)
        plan = None
        if identity["return_type"] == "00A_ENVIRONMENT" or str(
            identity["return_type"]
        ).startswith("00B_SNAPSHOT_SMOKE:"):
            plan = inspect_runtime_archive(
                args.return_zip,
                pack_root=args.pack_root,
                expected_return_type=str(identity["return_type"]),
            )
            validate_materialization_destination(plan)
        result = import_kaggle_return(
            args.return_zip,
            pack_root=args.pack_root,
            dry_run=args.dry_run,
        )
        if plan is not None and not args.dry_run:
            result["materialization"] = materialize_runtime_archive(
                result["destination"],
                pack_root=args.pack_root,
            )
    except (
        KagglefilesPackError,
        RuntimeMaterializationError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        print(json.dumps({
            "status": "RETURN_IMPORT_REJECTED",
            "error": str(error),
            "paper_evidence": False,
        }, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"NEXT: {result['next_command']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
