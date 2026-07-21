"""Validate future result artifacts against schema-freeze contracts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml

from certvic.io import read_jsonl


def _fields_for(path: Path) -> set[str]:
    if not path.exists():
        return set()
    if path.suffix == ".jsonl":
        rows = read_jsonl(path)
        return set(rows[0]) if rows else set()
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, dict) else set()
    if path.suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return set(reader.fieldnames or [])
    return set()


def validate_contracts(contracts: str, root: str) -> dict:
    spec = yaml.safe_load(Path(contracts).read_text(encoding="utf-8")) or {}
    errors: list[str] = []
    warnings: list[str] = []
    for contract in spec.get("contracts", []):
        rel = contract["path"]
        required = set(contract.get("required_fields") or [])
        path = Path(root) / rel
        if not path.exists():
            warnings.append(f"missing artifact: {rel}")
            continue
        fields = _fields_for(path)
        missing = sorted(required - fields)
        if missing:
            errors.append(f"{rel} missing fields: {', '.join(missing)}")
        extra = sorted(fields - required)
        if extra:
            warnings.append(f"{rel} extra fields: {', '.join(extra)}")
        if str(contract.get("evidence_status", "")).upper() in {"MOCK_ONLY", "SIMULATED_ONLY"}:
            errors.append(f"{rel} cannot be evidence under contract")
    return {"contracts": contracts, "root": root, "errors": errors, "warnings": warnings, "passed": not errors}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate result contracts")
    sub = parser.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("validate")
    pv.add_argument("--contracts", required=True)
    pv.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(validate_contracts(args.contracts, args.root), sort_keys=True))


if __name__ == "__main__":
    main()

