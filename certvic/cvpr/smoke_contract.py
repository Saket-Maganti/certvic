"""Build the trusted, byte-bound contract consumed by the real smoke gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from certvic.cvpr.task_schema import require_task_matrix, resolve_task_path
from certvic.cvpr.transactional import read_jsonl


class SmokeContractError(ValueError):
    pass


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _prompt(task: dict[str, Any], variant: str) -> str:
    prompts = task.get("prompts")
    value = prompts.get(variant) if isinstance(prompts, dict) else None
    value = value or task.get("prompt") or task.get("question")
    if not isinstance(value, str) or not value.strip():
        raise SmokeContractError(f"{task.get('task_id')}: smoke prompt is missing")
    return value


def build_contract(
    tasks: list[dict[str, Any]], provider_inputs: dict[str, Any], *,
    environment_lock: str | Path, code_bundle: str | Path, prompt_template_hash: str,
    parser_version: str = "certvic.parse.v2",
    bundle_root: str | Path | None = None,
    synthetic_fixture: bool = False,
) -> dict[str, Any]:
    tasks = require_task_matrix(tasks, verify_files=True, bundle_root=bundle_root)
    if len(tasks) != 2:
        raise SmokeContractError("trusted real-model smoke requires exactly two canonical tasks")
    if not _hash(prompt_template_hash):
        raise SmokeContractError("prompt template hash must be SHA-256")
    fixture_rows: list[dict[str, str]] = []
    for task in sorted(tasks, key=lambda row: str(row["task_id"])):
        for variant, image_field in (
            ("original", "original_image_path"), ("edited", "edited_image_path")
        ):
            image = resolve_task_path(task, image_field, bundle_root=bundle_root)
            if image is None:
                raise SmokeContractError(f"{task['task_id']}: {image_field} is missing")
            if not image.is_file():
                raise SmokeContractError(f"{task['task_id']}: {image_field} is missing")
            fixture_rows.append({
                "item_id": str(task["task_id"]), "variant": variant,
                "task_hash": str(task["task_hash"]), "image_hash": _sha(image),
                "prompt_hash": hashlib.sha256(_prompt(task, variant).encode()).hexdigest(),
            })
    providers = provider_inputs.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise SmokeContractError("provider input must contain a nonempty providers mapping")
    normalized: dict[str, dict[str, str]] = {}
    for provider, value in sorted(providers.items()):
        if not isinstance(value, dict):
            raise SmokeContractError(f"{provider}: provider contract must be a mapping")
        snapshot_path = Path(str(value.get("snapshot_manifest_path", "")))
        run_contract_path = Path(str(value.get("run_contract_path", "")))
        if not snapshot_path.is_file() or not run_contract_path.is_file():
            raise SmokeContractError(f"{provider}: snapshot or run contract is missing")
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        run_contract = json.loads(run_contract_path.read_text(encoding="utf-8"))
        expected = {
            "model_id": value.get("model_id"), "model_commit": value.get("model_commit"),
            "processor_commit": value.get("processor_commit"),
        }
        if any(not str(field or "").strip() for field in expected.values()):
            raise SmokeContractError(f"{provider}: model identity/revisions are incomplete")
        if snapshot.get("model_id") != expected["model_id"] or snapshot.get(
            "model_commit"
        ) != expected["model_commit"]:
            raise SmokeContractError(f"{provider}: snapshot identity/revision mismatch")
        run_hash = run_contract.get("run_contract_hash")
        if not _hash(run_hash):
            raise SmokeContractError(f"{provider}: run contract hash is invalid")
        normalized[str(provider)] = {
            **{key: str(field) for key, field in expected.items()},
            "snapshot_manifest_hash": _sha(snapshot_path),
            "run_contract_hash": str(run_hash),
        }
    environment = Path(environment_lock)
    bundle = Path(code_bundle)
    if not environment.is_file() or not bundle.is_file():
        raise SmokeContractError("environment lock or code bundle is missing")
    return {
        "schema": "certvic.cvpr.trusted_smoke_contract.v2",
        "fixture_rows": fixture_rows, "providers": normalized,
        "environment_hash": _sha(environment), "code_hash": _sha(bundle),
        "prompt_template_hash": prompt_template_hash,
        "prompt_hash": prompt_template_hash,  # documented compatibility alias
        "parser_version": parser_version,
        "inputs": {
            "task_manifest_sha256": hashlib.sha256(
                "".join(json.dumps(task, sort_keys=True) + "\n" for task in tasks).encode()
            ).hexdigest(),
            "provider_inputs_sha256": hashlib.sha256(json.dumps(
                provider_inputs, sort_keys=True, separators=(",", ":")
            ).encode()).hexdigest(),
        },
        "runtime_class": ("SYNTHETIC_SMOKE" if synthetic_fixture else "REAL_MODEL_SMOKE"),
        "synthetic_fixture": synthetic_fixture, "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an importer-grade trusted smoke contract")
    parser.add_argument("--task-manifest", required=True)
    parser.add_argument("--provider-contracts", required=True)
    parser.add_argument("--environment-lock", required=True)
    parser.add_argument("--code-bundle", required=True)
    parser.add_argument("--prompt-template-hash", required=True)
    parser.add_argument("--parser-version", default="certvic.parse.v2")
    parser.add_argument("--bundle-root")
    parser.add_argument("--synthetic-fixture", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        result = build_contract(
            read_jsonl(args.task_manifest),
            json.loads(Path(args.provider_contracts).read_text(encoding="utf-8")),
            environment_lock=args.environment_lock, code_bundle=args.code_bundle,
            prompt_template_hash=args.prompt_template_hash, parser_version=args.parser_version,
            bundle_root=args.bundle_root, synthetic_fixture=args.synthetic_fixture,
        )
    except (SmokeContractError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "TRUSTED_SMOKE_CONTRACT_BLOCKED", "reason": str(exc),
                          "paper_evidence": False}, sort_keys=True))
        return 2
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "TRUSTED_SMOKE_CONTRACT_WRITTEN", "out": str(destination),
                      "paper_evidence": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
