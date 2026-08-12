#!/usr/bin/env python3
"""One-command fail-closed intake for two genuine user-licensed smoke pairs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from PIL import Image

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes  # noqa: E402
from certvic.cvpr.smoke_input_builder import build_smoke_bundle  # noqa: E402
from certvic.cvpr.task_schema import convert_legacy_task  # noqa: E402
from local_operator.pre_smoke_operator import (  # noqa: E402
    CANONICAL_PROMPT_TEMPLATE_HASH,
    generate_pre_smoke_permissions,
    operator_status,
    verify_real_smoke_bundle,
)


SMOKE_ROOT = REPOSITORY_ROOT / "local_inputs/smoke"
TASKS = SMOKE_ROOT / "real_smoke_tasks.jsonl"
DECLARATIONS = SMOKE_ROOT / "license_declarations"
OUTPUT = REPOSITORY_ROOT / "kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip"
PROHIBITED_PATH_TOKENS = re.compile(r"(^|[_.\-/])(synthetic|fixture|mock|generated|test)([_.\-/]|$)", re.I)


class SmokeIntakeError(ValueError):
    """User-supplied bytes or licensing declarations are incomplete or unsafe."""


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _historical_identities(paths: Iterable[Path]) -> set[str]:
    identities: set[str] = set()
    hash_pattern = re.compile(r"^[0-9a-f]{64}$")
    for path in paths:
        if not path.is_file() or path.is_symlink():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(value, dict):
                continue
            for key, item in value.items():
                if key in {"item_id", "task_id", "source_id", "source_image_id"} and item:
                    identities.add(str(item))
                if "sha256" in key.lower() and hash_pattern.fullmatch(str(item)):
                    identities.add(str(item))
    return identities


def _inspect_image(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise SmokeIntakeError(f"image is missing or symlinked: {path}")
    if PROHIBITED_PATH_TOKENS.search(path.as_posix()):
        raise SmokeIntakeError(f"synthetic/fixture-like path is prohibited: {path}")
    try:
        with Image.open(path) as opened:
            opened.verify()
        with Image.open(path) as opened:
            opened.load()
            width, height = opened.size
            mode = opened.mode
            image_format = opened.format
    except (OSError, ValueError) as error:
        raise SmokeIntakeError(f"image does not decode: {path}: {error}") from error
    if min(width, height) < 64 or mode not in {"RGB", "RGBA"}:
        raise SmokeIntakeError(f"image must be RGB/RGBA and at least 64 px per side: {path}")
    return {
        "path": path.resolve(),
        "sha256": _sha(path),
        "width": width,
        "height": height,
        "mode": mode,
        "format": image_format,
    }


def _status() -> dict[str, Any]:
    current = operator_status(REPOSITORY_ROOT)
    if current.get("operator_state") == "READY_FOR_00C2":
        action = (
            "Upload kaggle_uploads/03_smoke/certvic_real_two_item_smoke_bundle.zip and "
            "kaggle_uploads/04_permissions/certvic_pre_smoke_permissions.zip, then Run All on "
            "the three provider-specific 00C2 notebooks with T4x2 and Internet OFF."
        )
    else:
        action = (
            "Run this command with four genuine image paths plus --license-owner USER_OWNED "
            "--affirm-research-use --affirm-redistribution."
        )
    return {
        "schema": "certvic.cvpr2027.c12.real_smoke_intake_status.v1",
        "status": current.get("preparation_status", current.get("operator_state")),
        "operator_state": current.get("operator_state"),
        "real_smoke_bundle": current.get("real_smoke_bundle"),
        "pre_smoke_permissions": current.get("pre_smoke_permissions"),
        "exact_next_action": action,
        "paper_evidence": False,
    }


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    if args.license_owner != "USER_OWNED":
        raise SmokeIntakeError("--license-owner must affirm USER_OWNED for this intake route")
    if not args.affirm_research_use or not args.affirm_redistribution:
        raise SmokeIntakeError(
            "both --affirm-research-use and --affirm-redistribution are required"
        )
    pairs = [
        (_inspect_image(args.item1_original), _inspect_image(args.item1_edited)),
        (_inspect_image(args.item2_original), _inspect_image(args.item2_edited)),
    ]
    hashes = [image["sha256"] for pair in pairs for image in pair]
    if len(set(hashes)) != 4:
        raise SmokeIntakeError("all four original/edited files must have distinct bytes")
    for original, edited in pairs:
        if (original["width"], original["height"]) != (edited["width"], edited["height"]):
            raise SmokeIntakeError("each original/edited pair must have equal dimensions")
    historical = _historical_identities(
        path
        for root in (REPOSITORY_ROOT / "data", REPOSITORY_ROOT / "reports")
        for path in root.rglob("*.jsonl")
    )
    overlap = sorted(set(hashes) & historical)
    if overlap:
        raise SmokeIntakeError(f"historical byte overlap rejected: {overlap}")
    assets_root = SMOKE_ROOT / "assets"
    rows = []
    declaration_rows = []
    task_binding_hash = sha256_bytes(canonical_json_bytes({
        "schema": "certvic.cvpr2027.c12.provider_run_contract_derivation.v1",
        "derivation": "provider_specific_from_authenticated_00A_00B_and_final_task_bytes",
        "prompt_template_hash": CANONICAL_PROMPT_TEMPLATE_HASH,
        "parser_version": "certvic.parse.v2",
    }))
    for index, (original, edited) in enumerate(pairs, start=1):
        item_id = f"user-owned-smoke-{index}-{original['sha256'][:12]}"
        destination = assets_root / item_id
        destination.mkdir(parents=True, exist_ok=True)
        copied: dict[str, Path] = {}
        for role, image in (("original", original), ("edited", edited)):
            suffix = image["path"].suffix.lower() or ".img"
            target = destination / f"{role}{suffix}"
            if target.exists() and _sha(target) != image["sha256"]:
                raise SmokeIntakeError(f"conflicting canonical smoke asset exists: {target}")
            if not target.exists():
                shutil.copy2(image["path"], target)
            copied[role] = target
        declaration = {
            "schema": "certvic.cvpr2027.c12.user_owned_license_declaration.v1",
            "item_id": item_id,
            "creator": "WITHHELD_FROM_PUBLIC_BUNDLE",
            "capture_date_optional": None,
            "ownership_basis": "USER_DECLARED_CREATOR_OR_RIGHTSHOLDER",
            "redistribution_permission": True,
            "research_use_permission": True,
            "license_id": f"USER_OWNED-{item_id}",
            "declaration_date": date.today().isoformat(),
            "notes": args.license_notes or "Local affirmative declaration; no PII exported.",
            "asset_sha256": {"original": original["sha256"], "edited": edited["sha256"]},
            "public_bundle_contains_personal_identity": False,
        }
        declaration_rows.append(declaration)
        row = convert_legacy_task(
            {
                "item_id": item_id,
                "original_image_path": str(copied["original"]),
                "edited_image_path": str(copied["edited"]),
                "source_image_path": str(copied["original"]),
                "source_image_hash": original["sha256"],
                "source_dataset": "USER_OWNED_REAL_SMOKE",
                "source_split": "operator_smoke",
                "question": "Is the main visible content coherent? Answer yes or no.",
                "original_expected_answer": "yes",
                "edited_expected_answer": "yes",
                "required_change": False,
                "control_edit_family": "user_owned_smoke_edit",
                "target_bbox": [0, 0, 1, 1],
                "license_eligible": True,
                "license_status": "VERIFIED_ELIGIBLE",
                "license_id": declaration["license_id"],
                "prompt_template_hash": CANONICAL_PROMPT_TEMPLATE_HASH,
                "parser_version": "certvic.parse.v2",
                "run_contract_hash": task_binding_hash,
                "synthetic_fixture": False,
                "paper_evidence": False,
                "review_status": "HUMAN_REVIEW_PENDING",
                "qa_status": "REAL_SMOKE_INTAKE_VERIFIED",
                "selected_engine": "user_supplied_edit",
            },
            study="specificity_confirmatory_cvpr",
        )
        rows.append(row)
    DECLARATIONS.mkdir(parents=True, exist_ok=True)
    for declaration in declaration_rows:
        path = DECLARATIONS / f"{declaration['item_id']}.json"
        payload = json.dumps(declaration, indent=2, sort_keys=True) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != payload:
            raise SmokeIntakeError(f"conflicting license declaration exists: {path}")
        path.write_text(payload, encoding="utf-8")
    TASKS.parent.mkdir(parents=True, exist_ok=True)
    task_payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    if TASKS.exists() and TASKS.read_text(encoding="utf-8") != task_payload:
        raise SmokeIntakeError(f"conflicting real smoke task manifest exists: {TASKS}")
    TASKS.write_text(task_payload, encoding="utf-8")
    build_smoke_bundle(TASKS, output=OUTPUT, historical_manifests=[])
    verify_real_smoke_bundle(REPOSITORY_ROOT)
    generate_pre_smoke_permissions(REPOSITORY_ROOT)
    return _status()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--item1-original", type=Path)
    parser.add_argument("--item1-edited", type=Path)
    parser.add_argument("--item2-original", type=Path)
    parser.add_argument("--item2-edited", type=Path)
    parser.add_argument("--license-owner")
    parser.add_argument("--affirm-research-use", action="store_true")
    parser.add_argument("--affirm-redistribution", action="store_true")
    parser.add_argument("--license-notes")
    args = parser.parse_args(argv)
    required = [args.item1_original, args.item1_edited, args.item2_original, args.item2_edited]
    try:
        if args.status or not any(required):
            result = _status()
        elif not all(required):
            raise SmokeIntakeError("all four original/edited image paths are required")
        else:
            result = prepare(args)
    except (SmokeIntakeError, OSError, ValueError) as error:
        print(json.dumps({
            "status": "BLOCKED_REAL_SMOKE_INTAKE",
            "error": str(error),
            "paper_evidence": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
