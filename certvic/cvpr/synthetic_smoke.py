"""Build realistic non-evidence smoke ZIPs and validate them through the real gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from certvic.cvpr.contracts import canonical_json_bytes
from certvic.cvpr.environment_lock import environment_lock_hash
from certvic.cvpr.model_snapshot_manifest import create_manifest, write_manifest
from certvic.cvpr.package_run import package
from certvic.cvpr.run_contract import build_run_contract
from certvic.cvpr.smoke_contract import build_contract
from certvic.cvpr.smoke_gate import evaluate, write_gate
from certvic.cvpr.task_bundle import create_bundle
from certvic.cvpr.task_schema import TASK_SCHEMA, with_task_hash
from certvic.cvpr.transactional import read_jsonl
from certvic.cvpr.worker import run_shard


PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture_tasks(out: Path) -> list[dict[str, Any]]:
    rows = []
    for index in (1, 2):
        source, edited = out / f"smoke_source_{index}.png", out / f"smoke_edited_{index}.png"
        image = Image.new("RGB", (48, 48))
        pixels = image.load()
        for y in range(48):
            for x in range(48):
                pixels[x, y] = (
                    (x * (index + 2) + y) % 256,
                    (y * (index + 3) + x) % 256,
                    (x * 2 + y * 3 + index) % 256,
                )
        image.save(source, format="PNG", compress_level=9)
        changed = image.copy()
        changed.putpixel((index, index), image.getpixel((index, index)))
        changed.save(edited, format="PNG", compress_level=9)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        rows.append(
            with_task_hash(
                {
                    "task_schema_version": TASK_SCHEMA,
                    "study": "synthetic_confirmatory",
                    "task_id": f"strict-smoke-{index}",
                    "item_id": f"strict-smoke-{index}",
                    "source_dataset": "SYNTHETIC_FIXTURE",
                    "source_split": "synthetic",
                    "source_image_id": f"strict-smoke-source-{index}",
                    "source_image_path": str(source),
                    "source_image_hash": digest,
                    "original_image_path": str(source),
                    "edited_image_path": str(edited),
                    "license_status": "SYNTHETIC_FIXTURE_NO_EXTERNAL_LICENSE",
                    "question": "Is this a synthetic fixture image?",
                    "answer_format": "yes_no",
                    "original_expected_answer": "yes",
                    "edited_expected_answer": "yes",
                    "required_change": False,
                    "semantic_edit_family": None,
                    "control_edit_family": "strict_smoke_identity_control",
                    "target_category": None,
                    "queried_category": None,
                    "queried_category_absent": False,
                    "target_bbox": [1, 1, 2, 2],
                    "target_mask_path": None,
                    "target_mask_hash": None,
                    "protected_scene_mask_path": None,
                    "protected_scene_mask_hash": None,
                    "attribute_name": None,
                    "original_attribute": None,
                    "edited_attribute": None,
                    "attribute_transform": None,
                    "original_attribute_verified": None,
                    "edit_engine_policy": "synthetic_strict_smoke_v1",
                    "selected_engine": "identity_fixture",
                    "engine_fallbacks": [],
                    "engine_parameters": {},
                    "seed": 19051 + index,
                    "primary_or_reserve": "primary",
                    "strata": {"fixture": "strict_smoke"},
                    "review_status": "VALID_ADJUDICATED",
                    "qa_status": "PASS",
                    "mock_raw_response": "yes",
                    "paper_evidence": False,
                }
            )
        )
    return rows


def run(out_dir: str | Path, providers: tuple[str, ...] = PROVIDERS) -> dict[str, Any]:
    out = Path(out_dir)
    if out.exists() and any(out.iterdir()):
        raise ValueError("synthetic smoke root must be new or empty")
    out.mkdir(parents=True, exist_ok=True)
    task_sources = out / "task_sources"
    task_sources.mkdir()
    bundle_root = out / "task_bundle"
    bundle_status = create_bundle(_fixture_tasks(task_sources), bundle_root)
    tasks_path = bundle_root / "tasks.jsonl"
    tasks = read_jsonl(tasks_path)

    environment_lock = out / "00_environment_lock.json"
    lock = {
        "schema": "certvic.cvpr.environment_lock.v1",
        "python": {"version": "3.11"},
        "packages": {"pillow": "1.0.0"},
        "cuda_contract": {"required": False},
        "offline_install": {"allow_index": False},
    }
    environment_lock.write_bytes(canonical_json_bytes(lock))
    environment_hash = environment_lock_hash(environment_lock)
    environment = {
        "schema": "certvic.cvpr.synthetic_environment.v1",
        "status": "EXACT_PREINSTALLED_ENVIRONMENT_ACCEPTED",
        "passed": True,
        "environment_hash": environment_hash,
        "runtime_class": "SYNTHETIC_END_TO_END_FIXTURE",
        "paper_evidence": False,
    }
    _json(out / "00A_environment.json", environment)
    code_bundle = out / "synthetic_code_bundle.zip"
    code_bundle.write_bytes(b"SYNTHETIC_FIXTURE_CODE_BUNDLE_NOT_EXECUTABLE")
    code_hash = hashlib.sha256(code_bundle.read_bytes()).hexdigest()
    prompt_template = "{prompt}"
    prompt_hash = hashlib.sha256(prompt_template.encode()).hexdigest()

    provider_inputs: dict[str, Any] = {"providers": {}}
    runtime_configs: dict[str, Path] = {}
    snapshot_statuses: dict[str, dict[str, Any]] = {}
    for index, provider in enumerate(providers, start=1):
        snapshot = out / "snapshots" / provider
        snapshot.mkdir(parents=True)
        architecture = f"SyntheticArchitecture{index}"
        _json(
            snapshot / "config.json", {"architectures": [architecture], "model_type": "synthetic"}
        )
        _json(snapshot / "tokenizer_config.json", {"synthetic": True})
        (snapshot / "model.safetensors").write_bytes(f"synthetic-weights-{provider}".encode())
        model_commit, processor_commit = f"{index}" * 40, f"{index + 3}" * 40
        model_id = f"synthetic/{provider}"
        snapshot_manifest = write_manifest(
            snapshot,
            create_manifest(
                snapshot,
                model_id=model_id,
                model_commit=model_commit,
                processor_commit=processor_commit,
                expected_architecture=architecture,
            ),
        )
        snapshot_hash = hashlib.sha256(snapshot_manifest.read_bytes()).hexdigest()
        snapshot_root_hash = json.loads(snapshot_manifest.read_text(encoding="utf-8"))[
            "unified_snapshot_root_sha256"
        ]
        snapshot_status = {
            "schema": "certvic.cvpr.synthetic_snapshot_status.v1",
            "provider": provider,
            "status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
            "passed": True,
            "snapshot_contract": "UNIFIED_SNAPSHOT",
            "manifest_sha256": snapshot_hash,
            "paper_evidence": False,
        }
        snapshot_statuses[provider] = snapshot_status
        _json(out / f"00B_{provider}_snapshot.json", snapshot_status)
        provider_out = out / "runs" / provider
        runtime_path = out / "runtime_configs" / f"{provider}.json"
        runtime = {
            "study": "synthetic_strict_smoke",
            "runtime_class": "REAL_MODEL_SMOKE",
            "synthetic_notebook_proof": True,
            "strict_smoke_fixture": True,
            "provider": provider,
            "model_id": model_id,
            "processor_id": model_id,
            "model_path": str(snapshot),
            "processor_path": str(snapshot),
            "model_commit": model_commit,
            "processor_commit": processor_commit,
            "snapshot_manifest_path": str(snapshot_manifest),
            "expected_architecture": architecture,
            "model_snapshot_manifest_hash": snapshot_hash,
            "processor_snapshot_manifest_hash": snapshot_hash,
            "snapshot_root_hash": snapshot_root_hash,
            "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
            "snapshot_contract": "UNIFIED_SNAPSHOT",
            "environment_lock_path": str(environment_lock),
            "environment_lock_hash": environment_hash,
            "prompt_template_id": "synthetic_strict_smoke_v1",
            "prompt_template": prompt_template,
            "prompt_template_hash": prompt_hash,
            "parser_version": "certvic.parse.v2",
            "output_schema": "certvic.cvpr.output.v2",
            "strict_run_contract": True,
            "run_tag": "synthetic_strict_smoke_v1",
            "task_manifest": str(tasks_path),
            "task_bundle_root": str(bundle_root),
            "task_bundle_manifest": str(bundle_root / "task_bundle_manifest.json"),
            "task_bundle_hash": bundle_status["bundle_hash"],
            "output_dir": str(provider_out),
            "code_bundle_hash": code_hash,
            "seed": 19061,
            "generation_parameters": {"do_sample": False, "max_new_tokens": 8},
            "defer_canonical_smoke_package": True,
            "canonical_smoke_destination": str(
                out / f"00C2_{provider}_real_model_smoke.zip"
            ),
        }
        _json(runtime_path, runtime)
        runtime_configs[provider] = runtime_path
        run_contract = build_run_contract(
            runtime,
            task_manifest_sha256=hashlib.sha256(canonical_json_bytes(tasks)).hexdigest(),
            strict=True,
        )
        run_contract_path = out / "run_contracts" / f"{provider}.json"
        _json(run_contract_path, run_contract)
        provider_inputs["providers"][provider] = {
            "model_id": model_id,
            "model_commit": model_commit,
            "processor_commit": processor_commit,
            "snapshot_manifest_path": str(snapshot_manifest),
            "run_contract_path": str(run_contract_path),
        }
    contract = build_contract(
        tasks,
        provider_inputs,
        environment_lock=environment_lock,
        code_bundle=code_bundle,
        prompt_template_hash=prompt_hash,
        bundle_root=bundle_root,
        synthetic_fixture=True,
    )
    contract_path = out / "trusted_synthetic_smoke_contract.json"
    _json(contract_path, contract)
    archives: dict[str, str] = {}
    for provider in providers:
        runtime_path = runtime_configs[provider]
        provider_out = Path(json.loads(runtime_path.read_text())["output_dir"])
        _json(provider_out / "environment_manifest.json", environment)
        worker = run_shard(runtime_path, shard=0, num_shards=1, mock_runtime=True)
        if worker["status"] != "SHARD_COMPLETE":
            raise RuntimeError(f"synthetic strict smoke worker failed: {provider}: {worker}")
        packaged = package(runtime_path, expected_shards=1)
        target = out / f"00C2_{provider}_real_model_smoke.zip"
        if Path(str(packaged["zip"])) != target or not target.is_file():
            raise RuntimeError("package_run did not emit the canonical smoke ZIP")
        archives[provider] = str(target)
    gate = evaluate(out, list(providers), contract=contract)
    if gate["status"] != "SYNTHETIC_SMOKE_PASSED":
        raise RuntimeError(f"strict synthetic smoke gate failed: {gate}")
    gate_csv = out / "synthetic_smoke_gate.csv"
    write_gate(gate, gate_csv)
    return {
        "schema": "certvic.cvpr.synthetic_strict_smoke.v1",
        "status": gate["status"],
        "strict_contract_verified": gate["strict_contract_verified"],
        "providers": list(providers),
        "archives": archives,
        "gate_json": str(gate_csv.with_suffix(".json")),
        "contract": str(contract_path),
        "task_bundle_manifest": str(bundle_root / "task_bundle_manifest.json"),
        "paper_evidence": False,
    }
