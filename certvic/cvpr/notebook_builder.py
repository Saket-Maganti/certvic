"""Deterministic builder for executable, evidence-isolated CVPR Kaggle notebooks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class _NotebookRegistry(dict[str, tuple[str, str]]):
    """Expose one historical membership alias without regenerating obsolete notebooks."""
    def __contains__(self, key: object) -> bool:
        return key == "00C_certvic_adapter_two_item_smoke.ipynb" or super().__contains__(key)


NOTEBOOKS = _NotebookRegistry({
    "00A_certvic_code_and_environment_smoke.ipynb": ("code_smoke", "all"),
    "00B_certvic_model_snapshot_smoke.ipynb": ("snapshot_smoke", "all"),
    "00C1_certvic_mock_adapter_smoke.ipynb": ("mock_smoke", "all"),
    "00C2_certvic_real_model_two_item_smoke.ipynb": ("real_model_smoke", "all"),
    "01_specificity_confirmatory_generation_T4x2.ipynb": ("generation", "controls"),
    "02_qwen_specificity_confirmatory_T4x2.ipynb": ("evaluation", "qwen2_5_vl_7b"),
    "03_internvl_specificity_confirmatory_T4x2.ipynb": ("evaluation", "internvl_8b"),
    "04_llava_specificity_confirmatory_T4x2.ipynb": ("evaluation", "llava_onevision_7b"),
    "10_main_study_generation_T4x2.ipynb": ("generation", "main_study"),
    "11_qwen_main_study_T4x2.ipynb": ("evaluation", "qwen2_5_vl_7b"),
    "12_internvl_main_study_T4x2.ipynb": ("evaluation", "internvl_8b"),
    "13_llava_main_study_T4x2.ipynb": ("evaluation", "llava_onevision_7b"),
    "20_second_domain_generation_T4x2.ipynb": ("generation", "coco_object_presence"),
    "21_second_domain_qwen_T4x2.ipynb": ("evaluation", "qwen2_5_vl_7b"),
    "22_second_domain_internvl_T4x2.ipynb": ("evaluation", "internvl_8b"),
    "23_second_domain_llava_T4x2.ipynb": ("evaluation", "llava_onevision_7b"),
})


def expected_return_zip(name: str, stage: str, provider: str) -> str:
    """Return the one canonical downloadable ZIP for a runbook identity."""
    if stage == "code_smoke":
        return "00A_environment_bundle.zip"
    if stage == "snapshot_smoke":
        return "00B_{PROVIDER}_snapshot_bundle.zip"
    if stage == "mock_smoke":
        return "00C1_synthetic_adapter_smoke.zip"
    if stage == "real_model_smoke":
        return "00C2_{PROVIDER}_real_model_smoke.zip"
    if stage == "generation":
        if name.startswith("01_"):
            return "confirmatory_generation_return.zip"
        if name.startswith("10_"):
            return "main_generation_return.zip"
        return "coco_generation_return.zip"
    prefix = "confirmatory" if name.startswith(("02_", "03_", "04_")) else (
        "main" if name.startswith(("11_", "12_", "13_")) else "coco"
    )
    short = {
        "qwen2_5_vl_7b": "qwen",
        "internvl_8b": "internvl",
        "llava_onevision_7b": "llava",
    }[provider]
    return f"{prefix}_{short}_return.zip"


def _cell(kind: str, source: str) -> dict:
    cell_id = hashlib.sha256(f"{kind}:{source}".encode()).hexdigest()[:12]
    base = {"cell_type": kind, "id": cell_id, "metadata": {},
            "source": source.splitlines(keepends=True)}
    if kind == "code":
        base.update({"execution_count": None, "outputs": []})
    return base


def notebook(name: str, stage: str, provider: str) -> dict:
    return_name = expected_return_zip(name, stage, provider)
    expected_gpus = 0 if stage in {"code_smoke", "snapshot_smoke"} else 2
    if stage == "snapshot_smoke":
        return_expression = '"00B_" + PROVIDER + "_snapshot_bundle.zip"'
    elif stage == "real_model_smoke":
        return_expression = '"00C2_" + PROVIDER + "_real_model_smoke.zip"'
    else:
        return_expression = repr(return_name)
    config = f'''# Fill only this cell. Every placeholder is fail-closed.
STAGE = {stage!r}
PROVIDER = {provider!r}
NOTEBOOK_NAME = {name!r}
STUDY = "REQUIRED_USER_FILL"
MODEL_ID = "REQUIRED_USER_FILL"
MODEL_COMMIT = "REQUIRED_USER_FILL"
PROCESSOR_COMMIT = "REQUIRED_USER_FILL"
PROCESSOR_ID = "REQUIRED_USER_FILL"
MODEL_PATH = "REQUIRED_USER_FILL"
PROCESSOR_PATH = "REQUIRED_USER_FILL"
SNAPSHOT_MANIFEST = "REQUIRED_USER_FILL"
SNAPSHOT_MANIFEST_HASH = "REQUIRED_USER_FILL"
SNAPSHOT_ROOT_HASH = None  # derived from the byte-verified unified snapshot manifest
EXPECTED_ARCHITECTURE = "REQUIRED_USER_FILL"
TASK_MANIFEST = "REQUIRED_USER_FILL"
TASK_BUNDLE_ROOT = "REQUIRED_USER_FILL"
TASK_BUNDLE_MANIFEST = "REQUIRED_USER_FILL"
TASK_BUNDLE_HASH = None  # always derived from the verified manifest before worker creation
EDIT_PLAN = "REQUIRED_USER_FILL"
CODE_BUNDLE_PATH = "REQUIRED_USER_FILL"
CODE_BUNDLE = CODE_BUNDLE_PATH  # canonical active-variable name; never a duplicate value
CODE_BUNDLE_HASH = "REQUIRED_USER_FILL"
RUN_TAG = "REQUIRED_USER_FILL"
ENVIRONMENT_LOCK = "REQUIRED_USER_FILL"
ENVIRONMENT_LOCK_HASH = "REQUIRED_USER_FILL"
WHEELHOUSE_PATH = "REQUIRED_USER_FILL"
WHEELHOUSE_MANIFEST = "REQUIRED_USER_FILL"
ALLOW_USE_PREINSTALLED_ENVIRONMENT = True
REQUIRE_EXACT_ENVIRONMENT = True
SNAPSHOT_CONTRACT = "UNIFIED_SNAPSHOT"
SMOKE_GATE_JSON = "REQUIRED_USER_FILL"
MATRIX_AUTHORIZATION = "REQUIRED_USER_FILL"
REAL_MODEL_SMOKE_GATE = SMOKE_GATE_JSON  # backward-compatible alias of the active value
EXECUTION_PERMISSION = "REQUIRED_USER_FILL"
PROVIDER_PERMISSION = "REQUIRED_USER_FILL"
PROVIDER_PERMISSION_EVENTS = "/kaggle/working/provider_permission_events.jsonl"
FINAL_TASK_FREEZE = "REQUIRED_USER_FILL"
FINAL_REVIEW_LEDGER = "REQUIRED_USER_FILL"
DETECTABILITY_GATE = "REQUIRED_USER_FILL"
MODEL_REGISTRY = "REQUIRED_USER_FILL"
STUDY_CONFIG = "REQUIRED_USER_FILL"
EXECUTION_SMOKE_GATE_JSON = SMOKE_GATE_JSON  # backward-compatible alias of the active value
# PERMISSION_INPUT_PATHS is deprecated and intentionally not accepted; derive_permission_binding
# constructs the sole role map from the active variables above.
# claim_permission is superseded by the provider-local transition_provider_permission state machine.
# Retired names SYNTHETIC_MOCK_RUNTIME and NON_EVIDENCE_REAL_MODEL_SMOKE are not authorization
# classes; the active classes are SYNTHETIC_SMOKE and REAL_MODEL_SMOKE.
PRIMARY_PROVIDERS = ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]
PROMPT_TEMPLATE_ID = "certification_yes_no_v1"
PROMPT_TEMPLATE = "{{prompt}}\n"  # exact string passed to the worker
PROMPT_TEMPLATE_HASH = __import__("hashlib").sha256(PROMPT_TEMPLATE.encode("utf-8")).hexdigest()
ATTACHED_INPUT_HASHES = {{}}  # path -> sha256
EXPECTED_GPUS = {expected_gpus}
ALLOW_SINGLE_GPU_FALLBACK = True
INITIAL_BATCH_SIZE = 4
MAX_ITEMS = 2  # global bound; never pass per-shard --max-items after pre-slicing
ALLOW_FULL_RUN = False
GENERATION_ENGINE = "structured_texture_patch"
SEMANTIC_ENGINE = "deterministic_preliminary"  # optional: manifest_verified_offline_inpainting
INPAINTING_SNAPSHOT = "REQUIRED_USER_FILL"
INPAINTING_MANIFEST = "REQUIRED_USER_FILL"
USE_REAL_MODEL = False  # 00C2 refuses to run until explicitly changed to True
# GPU workers bind explicitly through CUDA_VISIBLE_DEVICES when this stage launches them.
OUTPUT_DIR = "/kaggle/working/certvic_cvpr_non_evidence_smoke" if STAGE.endswith("smoke") else "/kaggle/working/certvic_cvpr"
RUNTIME_CONFIG = "/kaggle/working/certvic_cvpr_runtime.json"
SCHEMA_VERSION = "certvic.cvpr.output.v2"
GLOBAL_SEED = 12013
CANONICAL_RETURN_ZIP = {return_expression}
'''
    bootstrap = '''import hashlib, json, os, pathlib, shutil, subprocess, sys, time, zipfile

def shard_for(item_id, n):
    return int(hashlib.sha256(item_id.encode()).hexdigest(), 16) % n

def shard_complete(path, expected):
    # Convenience only. The worker performs full contract validation before skip/promotion.
    if not pathlib.Path(path).is_file(): return False
    rows = [json.loads(line) for line in pathlib.Path(path).read_text().splitlines() if line]
    return len(rows) == expected and len({(row.get("item_id"), row.get("variant")) for row in rows}) == expected

bundle = pathlib.Path(CODE_BUNDLE_PATH)
if CODE_BUNDLE_HASH == "REQUIRED_USER_FILL" or not bundle.is_file():
    raise RuntimeError("Attach the hash-locked code bundle")
if hashlib.sha256(bundle.read_bytes()).hexdigest() != CODE_BUNDLE_HASH:
    raise RuntimeError("code bundle hash mismatch")
extract_to = pathlib.Path("/kaggle/working/certvic_code")
if extract_to.exists(): shutil.rmtree(extract_to)
with zipfile.ZipFile(bundle) as archive:
    names = [member.filename for member in archive.infolist()]
    if len(names) != len(set(names)) or archive.testzip() is not None:
        raise RuntimeError("duplicate or corrupt code archive members")
    if any(pathlib.PurePosixPath(name).is_absolute() or ".." in pathlib.PurePosixPath(name).parts for name in names):
        raise RuntimeError("unsafe code archive member")
    archive.extractall(extract_to)
candidates = [path.parent for path in extract_to.rglob("pyproject.toml")
              if (path.parent / "certvic/__init__.py").is_file()]
print({"discovered_project_candidates": [str(path) for path in candidates]})
if len(candidates) != 1: raise RuntimeError("code archive project discovery is ambiguous")
PROJECT_ROOT = candidates[0]
sys.path.insert(0, str(PROJECT_ROOT))
import certvic
from certvic.cvpr.model_snapshot_manifest import verify_manifest
from certvic.cvpr.notebook_bootstrap import configure_offline_environment, import_smoke
from certvic.cvpr.t4x2 import derive_seed_manifest, detect_topology, write_seed_manifest
from certvic.cvpr.environment_lock import (
    environment_lock_hash, offline_environment_flags, prepare_offline_environment,
)
from certvic.cvpr.schema_contract import OUTPUT_SCHEMA
from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.run_contract import build_run_contract
from certvic.cvpr.smoke_gate import require_scientific_run_gate
from certvic.cvpr.task_bundle import verify_bundle
from certvic.cvpr.notebook_permission_binding import derive_permission_binding
from certvic.cvpr.reconcile_provider_permissions import (
    transition_provider_permission, verify_matrix_authorization, verify_provider_permission,
)
PACKAGE_SOURCE_HASH = hashlib.sha256((PROJECT_ROOT / "certvic/__init__.py").read_bytes()).hexdigest()
print({"certvic_source": certvic.__file__, "package_source_hash": PACKAGE_SOURCE_HASH})
configure_offline_environment()
print({"offline_install_template": "python -m pip install --no-index --find-links <wheelhouse> -r <lock>"})
if ENVIRONMENT_LOCK == "REQUIRED_USER_FILL" or ENVIRONMENT_LOCK_HASH == "REQUIRED_USER_FILL":
    raise RuntimeError("attach the exact offline environment lock and fill its SHA-256")
if environment_lock_hash(ENVIRONMENT_LOCK) != ENVIRONMENT_LOCK_HASH:
    raise RuntimeError("environment lock hash mismatch")
if offline_environment_flags().get("HF_HUB_OFFLINE") != "1" or \
        offline_environment_flags().get("PIP_NO_INDEX") != "1":
    raise RuntimeError("offline environment flag contract is incomplete")
if SCHEMA_VERSION != OUTPUT_SCHEMA:
    raise RuntimeError(f"mixed output schema prohibited: {SCHEMA_VERSION} != {OUTPUT_SCHEMA}")
if STAGE in {"evaluation", "generation", "mock_smoke", "real_model_smoke"}:
    if TASK_BUNDLE_ROOT == "REQUIRED_USER_FILL" or TASK_BUNDLE_MANIFEST == "REQUIRED_USER_FILL":
        raise RuntimeError("attach the portable task bundle root and manifest")
    bundle_verification = verify_bundle(TASK_BUNDLE_ROOT, TASK_BUNDLE_MANIFEST)
    TASK_BUNDLE_HASH = bundle_verification["bundle_hash"]
    if pathlib.Path(bundle_verification["tasks_path"]).resolve() != pathlib.Path(TASK_MANIFEST).resolve():
        raise RuntimeError("TASK_MANIFEST is not the verified portable bundle task matrix")
if STAGE in {"evaluation", "snapshot_smoke", "real_model_smoke"}:
    snapshot_manifest_value = json.loads(pathlib.Path(SNAPSHOT_MANIFEST).read_text())
    SNAPSHOT_ROOT_HASH = snapshot_manifest_value.get("unified_snapshot_root_sha256")
    if not SNAPSHOT_ROOT_HASH:
        raise RuntimeError("snapshot manifest does not declare its unified snapshot root hash")
if STAGE in {"evaluation", "real_model_smoke"}:
    # This is deliberately before hardware inspection, output creation, adapter creation, or model load.
    if MATRIX_AUTHORIZATION == "REQUIRED_USER_FILL":
        raise RuntimeError("attach the exact parent matrix authorization")
    matrix_authorization = verify_matrix_authorization(MATRIX_AUTHORIZATION)
    if STAGE == "evaluation":
        if SMOKE_GATE_JSON == "REQUIRED_USER_FILL":
            raise RuntimeError("scientific evaluation requires the returned REAL_MODEL_SMOKE_GATE.json")
        require_scientific_run_gate(SMOKE_GATE_JSON, PRIMARY_PROVIDERS)
    if PROVIDER_PERMISSION == "REQUIRED_USER_FILL":
        raise RuntimeError("model execution requires its provider-specific child permission")
    permission_binding = derive_permission_binding(globals())
    active_runtime_contract_input = {
        "study": STUDY,
        "runtime_class": "SCIENTIFIC_RUN" if STAGE == "evaluation" else "REAL_MODEL_SMOKE",
        "provider": PROVIDER, "model_id": MODEL_ID, "processor_id": PROCESSOR_ID,
        "model_commit": MODEL_COMMIT, "processor_commit": PROCESSOR_COMMIT,
        "model_snapshot_manifest_hash": SNAPSHOT_MANIFEST_HASH,
        "processor_snapshot_manifest_hash": SNAPSHOT_MANIFEST_HASH,
        "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
        "snapshot_contract": SNAPSHOT_CONTRACT,
        "environment_lock_hash": ENVIRONMENT_LOCK_HASH,
        "prompt_template_id": PROMPT_TEMPLATE_ID,
        "prompt_template_hash": PROMPT_TEMPLATE_HASH,
        "parser_version": "certvic.parse.v2", "output_schema": SCHEMA_VERSION,
        "run_tag": RUN_TAG, "code_bundle_hash": CODE_BUNDLE_HASH,
        "seed": 12013,
        "generation_parameters": {"do_sample": False, "max_new_tokens": 8} if STAGE == "real_model_smoke" else {"do_sample": False, "temperature": 0.0, "max_new_tokens": 16},
    }
    active_tasks = [json.loads(line) for line in pathlib.Path(TASK_MANIFEST).read_text().splitlines() if line]
    active_run_contract = build_run_contract(
        active_runtime_contract_input,
        task_manifest_sha256=sha256_bytes(canonical_json_bytes(active_tasks)), strict=True,
    )
    permission = verify_provider_permission(
        PROVIDER_PERMISSION, matrix=MATRIX_AUTHORIZATION,
        expected_provider=PROVIDER, expected_run_tag=RUN_TAG,
    )
    if (permission["active_input_hashes"] != permission_binding["input_hashes"]
            or permission["active_scalars"] != permission_binding["scalars"]
            or permission["task_bundle_hash"] != TASK_BUNDLE_HASH
            or permission["environment_hash"] != ENVIRONMENT_LOCK_HASH
            or permission["snapshot_hash"] != SNAPSHOT_MANIFEST_HASH
            or permission["snapshot_root_hash"] != SNAPSHOT_ROOT_HASH
            or permission["code_hash"] != CODE_BUNDLE_HASH
            or permission["prompt_template_hash"] != PROMPT_TEMPLATE_HASH
            or permission["run_contract_hash"] != active_run_contract["run_contract_hash"]
            or permission["parser_version"] != "certvic.parse.v2"):
        raise RuntimeError("provider permission differs from active model runtime identity")
    permission_claim = transition_provider_permission(
        permission, PROVIDER_PERMISSION_EVENTS, to_state="CLAIMED",
        actor=NOTEBOOK_NAME, detail={"binding_hash": permission_binding["binding_hash"]},
    )
environment_verification = prepare_offline_environment(
    ENVIRONMENT_LOCK,
    wheelhouse=None if WHEELHOUSE_PATH == "REQUIRED_USER_FILL" else WHEELHOUSE_PATH,
    wheelhouse_manifest=(None if WHEELHOUSE_MANIFEST == "REQUIRED_USER_FILL"
                         else WHEELHOUSE_MANIFEST),
    allow_preinstalled=ALLOW_USE_PREINSTALLED_ENVIRONMENT,
    require_exact=REQUIRE_EXACT_ENVIRONMENT,
    require_cuda=STAGE in {"generation", "evaluation", "real_model_smoke"},
)
if environment_verification["status"] not in {
    "EXACT_PREINSTALLED_ENVIRONMENT_ACCEPTED",
    "OFFLINE_WHEELHOUSE_INSTALLED_AND_VERIFIED",
}:
    raise RuntimeError("00A did not establish an exact offline environment")
'''
    preflight = '''from certvic.cvpr.runtime_preflight import hardware_report
hardware = hardware_report()
print(hardware)
gpu_stage = STAGE in {"generation", "evaluation", "real_model_smoke"}
if gpu_stage and not hardware["cuda_available"]:
    raise RuntimeError("CUDA is required for this notebook stage")
gpu_count = hardware["gpu_count"]
if gpu_stage and gpu_count < 2 and not (gpu_count == 1 and ALLOW_SINGLE_GPU_FALLBACK):
    raise RuntimeError(f"No allowed GPU topology: {gpu_count}")
GPU_IDS = list(range(min(gpu_count, EXPECTED_GPUS))) if gpu_stage else []
single_gpu_fallback = gpu_stage and len(GPU_IDS) == 1
if single_gpu_fallback: print("single_gpu_fallback: deterministic sequential shards")
T4_PLAN = detect_topology(
    device_names=[row["name"] for row in hardware.get("gpus", [])],
    allow_single_t4=ALLOW_SINGLE_GPU_FALLBACK,
) if gpu_stage else None
if T4_PLAN is not None: print(T4_PLAN.as_dict())
mismatches = [path for path, expected in ATTACHED_INPUT_HASHES.items()
              if not pathlib.Path(path).is_file()
              or hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest() != expected]
if mismatches: raise RuntimeError(f"attached input hash mismatch: {mismatches}")
if STAGE in {"evaluation", "snapshot_smoke", "real_model_smoke"}:
    if any(value == "REQUIRED_USER_FILL" for value in
           [MODEL_COMMIT, PROCESSOR_COMMIT, MODEL_PATH, SNAPSHOT_MANIFEST, SNAPSHOT_MANIFEST_HASH, EXPECTED_ARCHITECTURE]):
        raise RuntimeError("snapshot contract is incomplete")
    if SNAPSHOT_CONTRACT != "UNIFIED_SNAPSHOT":
        raise RuntimeError("current notebooks require the frozen unified snapshot contract")
    if pathlib.Path(MODEL_PATH).resolve() != pathlib.Path(PROCESSOR_PATH).resolve():
        raise RuntimeError("unified snapshot requires identical model and processor roots")
    if hashlib.sha256(pathlib.Path(SNAPSHOT_MANIFEST).read_bytes()).hexdigest() != SNAPSHOT_MANIFEST_HASH:
        raise RuntimeError("snapshot manifest file hash mismatch")
    snapshot = verify_manifest(MODEL_PATH, SNAPSHOT_MANIFEST, expected_model_id=MODEL_ID,
        expected_model_commit=MODEL_COMMIT, expected_processor_commit=PROCESSOR_COMMIT,
        expected_architecture=EXPECTED_ARCHITECTURE)
    if not snapshot["passed"]: raise RuntimeError(snapshot["errors"])
'''
    worker = '''if not pathlib.Path(TASK_MANIFEST).is_file(): raise RuntimeError("TASK_MANIFEST is missing")
runtime = {
    "study": STUDY, "provider": PROVIDER, "model_id": MODEL_ID, "model_path": MODEL_PATH,
    "processor_id": PROCESSOR_ID, "processor_path": PROCESSOR_PATH, "model_commit": MODEL_COMMIT,
    "processor_commit": PROCESSOR_COMMIT, "model_snapshot_manifest_hash": SNAPSHOT_MANIFEST_HASH,
    "processor_snapshot_manifest_hash": SNAPSHOT_MANIFEST_HASH,
    "snapshot_root_hash": SNAPSHOT_ROOT_HASH,
    "snapshot_contract": SNAPSHOT_CONTRACT,
    "snapshot_manifest_path": SNAPSHOT_MANIFEST, "expected_architecture": EXPECTED_ARCHITECTURE,
    "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
    "environment_lock_hash": ENVIRONMENT_LOCK_HASH,
    "environment_lock_path": ENVIRONMENT_LOCK,
    "prompt_template_id": PROMPT_TEMPLATE_ID, "prompt_template": PROMPT_TEMPLATE,
    "prompt_template_hash": PROMPT_TEMPLATE_HASH,
    "parser_version": "certvic.parse.v2", "output_schema": SCHEMA_VERSION,
    "runtime_class": "SCIENTIFIC_RUN", "strict_run_contract": True,
    "strict_permission_binding": True,
    "run_tag": RUN_TAG, "task_manifest": TASK_MANIFEST, "output_dir": OUTPUT_DIR,
    "task_bundle_root": TASK_BUNDLE_ROOT, "task_bundle_manifest": TASK_BUNDLE_MANIFEST,
    "task_bundle_hash": TASK_BUNDLE_HASH,
    "final_task_freeze": FINAL_TASK_FREEZE, "final_review_ledger": FINAL_REVIEW_LEDGER,
    "smoke_gate_json": SMOKE_GATE_JSON, "model_registry": MODEL_REGISTRY,
    "study_config": STUDY_CONFIG, "code_bundle": CODE_BUNDLE,
    "matrix_authorization": MATRIX_AUTHORIZATION,
    "code_bundle_hash": CODE_BUNDLE_HASH, "seed": 12013,
    "execution_permission_id": permission["permission_id"],
    "execution_permission_signature": permission["content_signature_sha256"],
    "provider_permission_path": PROVIDER_PERMISSION,
    "provider_permission_events_path": PROVIDER_PERMISSION_EVENTS,
    "permission_binding": permission_binding,
    "notebook_name": NOTEBOOK_NAME,
    "generation_parameters": {"do_sample": False, "temperature": 0.0, "max_new_tokens": 16},
}
pathlib.Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
pathlib.Path(RUNTIME_CONFIG).write_text(json.dumps(runtime, indent=2, sort_keys=True))
active_task_ids = [str(row["item_id"]) for row in active_tasks]
seed_manifests = [derive_seed_manifest(
    global_seed=GLOBAL_SEED, study=STUDY, provider=PROVIDER,
    gpu_id=(GPU_IDS[shard] if len(GPU_IDS) > 1 else 0), shard_id=shard,
    task_ids=[item for item in active_task_ids if shard_for(item, max(1, len(GPU_IDS))) == shard],
    attempts=2,
) for shard in range(max(1, len(GPU_IDS)))]
write_seed_manifest(pathlib.Path(OUTPUT_DIR) / "seed_manifest.json", {
    "schema": "certvic.kaggle.seed_manifest.v1", "collision_check": "PASS",
    "manifests": seed_manifests, "prospective": True, "paper_evidence": False,
})
processes = []
for shard, gpu in enumerate(GPU_IDS):
    env = dict(os.environ); env["CUDA_VISIBLE_DEVICES"] = str(gpu)
    command = [sys.executable, "-m", "certvic.cvpr.worker", "--shard", str(shard),
               "--num-shards", str(len(GPU_IDS)), "--resume", "--batch-size", str(INITIAL_BATCH_SIZE),
               "--oom-reduce-to-one", "--fail-closed", "--frozen-runtime-config", RUNTIME_CONFIG]
    stdout = open(pathlib.Path(OUTPUT_DIR) / f"worker_{shard}.stdout.log", "w")
    stderr = open(pathlib.Path(OUTPUT_DIR) / f"worker_{shard}.stderr.log", "w")
    processes.append((subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr), stdout, stderr))
for process, stdout, stderr in processes:
    code = process.wait(); stdout.close(); stderr.close()
    if code: raise RuntimeError("worker failed; preserve outputs and resume after repair")
'''
    generation = '''if not pathlib.Path(EDIT_PLAN).is_file(): raise RuntimeError("EDIT_PLAN is missing")
if MAX_ITEMS is None and not ALLOW_FULL_RUN:
    raise RuntimeError("choose a bounded MAX_ITEMS or explicitly set ALLOW_FULL_RUN=True")
rows = [json.loads(line) for line in pathlib.Path(EDIT_PLAN).read_text().splitlines() if line]
# MAX_ITEMS is global across the study, never per shard.
bounded_rows = rows if MAX_ITEMS is None else rows[:MAX_ITEMS]
seed_manifests = [derive_seed_manifest(
    global_seed=GLOBAL_SEED, study=STUDY, provider=PROVIDER,
    gpu_id=(GPU_IDS[shard] if len(GPU_IDS) > 1 else 0), shard_id=shard,
    task_ids=[str(row.get("edit_id", row.get("item_id"))) for row in bounded_rows
              if shard_for(str(row.get("edit_id", row.get("item_id"))), max(1, len(GPU_IDS))) == shard],
    attempts=2,
) for shard in range(max(1, len(GPU_IDS)))]
pathlib.Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
write_seed_manifest(pathlib.Path(OUTPUT_DIR) / "seed_manifest.json", {
    "schema": "certvic.kaggle.seed_manifest.v1", "collision_check": "PASS",
    "manifests": seed_manifests, "prospective": True, "paper_evidence": False,
})
processes = []
for shard, gpu in enumerate(GPU_IDS):
    shard_rows = [row for row in bounded_rows if shard_for(str(row.get("edit_id", row.get("item_id"))), len(GPU_IDS)) == shard]
    shard_path = pathlib.Path(OUTPUT_DIR) / f"edit_plan_shard_{shard}.jsonl"
    shard_path.parent.mkdir(parents=True, exist_ok=True)
    shard_path.write_text("".join(json.dumps(row, sort_keys=True) + "\\n" for row in shard_rows))
    env = dict(os.environ); env["CUDA_VISIBLE_DEVICES"] = str(gpu)
    module = "certvic.cvpr.generation" if PROVIDER == "controls" else "certvic.cvpr.semantic_edits"
    command = [sys.executable, "-m", module, "--task-manifest", str(shard_path),
               "--out-dir", str(pathlib.Path(OUTPUT_DIR) / f"generation_shard_{shard}"),
               "--seed", "12013", "--allow-full-run", "--resume"]
    if module.endswith("generation"): command += ["--engine", GENERATION_ENGINE]
    if SEMANTIC_ENGINE == "manifest_verified_offline_inpainting":
        if module == "certvic.cvpr.generation":
            raise RuntimeError("specificity controls require deterministic engines; optional inpainting is a separate diagnostic")
        if INPAINTING_SNAPSHOT == "REQUIRED_USER_FILL" or INPAINTING_MANIFEST == "REQUIRED_USER_FILL":
            raise RuntimeError("optional inpainting requires an explicit local snapshot and manifest")
        command += ["--inpainting-snapshot", INPAINTING_SNAPSHOT,
                    "--inpainting-manifest", INPAINTING_MANIFEST,
                    "--inpainting-model-id", MODEL_ID,
                    "--inpainting-model-commit", MODEL_COMMIT,
                    "--inpainting-architecture", EXPECTED_ARCHITECTURE,
                    "--batch-size", str(INITIAL_BATCH_SIZE)]
    log = open(pathlib.Path(OUTPUT_DIR) / f"generation_{shard}.stdout.log", "w")
    error = open(pathlib.Path(OUTPUT_DIR) / f"generation_{shard}.stderr.log", "w")
    processes.append((subprocess.Popen(command, env=env, stdout=log, stderr=error), log, error, shard))
for process, log, error, shard in processes:
    code = process.wait(); log.close(); error.close()
    if code: raise RuntimeError(f"generation shard {shard} failed; preserve outputs and inspect logs")
'''
    smoke = '''if STAGE == "snapshot_smoke":
    print({"status": "NON_EVIDENCE_RUNTIME_SMOKE", "snapshot_files_verified": snapshot["files_verified"]})
elif STAGE in {"mock_smoke", "real_model_smoke"}:
    tasks = [json.loads(line) for line in pathlib.Path(TASK_MANIFEST).read_text().splitlines() if line]
    if len(tasks) != 2: raise RuntimeError("adapter smoke requires exactly two fixture items")
    if STAGE == "real_model_smoke" and USE_REAL_MODEL is not True:
        raise RuntimeError("00C2 requires USE_REAL_MODEL=True after snapshot/environment preflight")
    runtime_class = "SYNTHETIC_SMOKE" if STAGE == "mock_smoke" else "REAL_MODEL_SMOKE"
    synthetic_snapshot_hash = hashlib.sha256(b"SYNTHETIC_MOCK_NO_MODEL_BYTES").hexdigest()
    runtime_model_id = "synthetic/mock" if STAGE == "mock_smoke" else MODEL_ID
    runtime_processor_id = "synthetic/mock" if STAGE == "mock_smoke" else PROCESSOR_ID
    runtime_model_commit = "0" * 40 if STAGE == "mock_smoke" else MODEL_COMMIT
    runtime_processor_commit = "0" * 40 if STAGE == "mock_smoke" else PROCESSOR_COMMIT
    runtime_snapshot_hash = synthetic_snapshot_hash if STAGE == "mock_smoke" else SNAPSHOT_MANIFEST_HASH
    runtime_snapshot_root_hash = synthetic_snapshot_hash if STAGE == "mock_smoke" else SNAPSHOT_ROOT_HASH
    runtime_environment_hash = (hashlib.sha256(b"SYNTHETIC_MOCK_ENVIRONMENT").hexdigest()
                                if STAGE == "mock_smoke" else ENVIRONMENT_LOCK_HASH)
    runtime_prompt_hash = hashlib.sha256(PROMPT_TEMPLATE.encode("utf-8")).hexdigest()
    runtime = {"study": STUDY, "runtime_class": runtime_class,
        "provider": PROVIDER, "model_id": runtime_model_id, "processor_id": runtime_processor_id,
        "model_path": MODEL_PATH, "processor_path": PROCESSOR_PATH,
        "processor_commit": runtime_processor_commit, "model_commit": runtime_model_commit,
        "model_snapshot_manifest_hash": runtime_snapshot_hash,
        "processor_snapshot_manifest_hash": runtime_snapshot_hash,
        "snapshot_root_hash": runtime_snapshot_root_hash,
        "snapshot_contract": SNAPSHOT_CONTRACT,
        "snapshot_manifest_path": SNAPSHOT_MANIFEST,
        "expected_architecture": EXPECTED_ARCHITECTURE,
        "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED" if STAGE == "real_model_smoke" else "REMOTE_COMMIT_DECLARED",
        "environment_lock_hash": runtime_environment_hash, "environment_lock_path": ENVIRONMENT_LOCK,
        "prompt_template_id": PROMPT_TEMPLATE_ID,
        "prompt_template": PROMPT_TEMPLATE,
        "prompt_template_hash": runtime_prompt_hash, "parser_version": "certvic.parse.v2",
        "output_schema": SCHEMA_VERSION, "strict_run_contract": STAGE == "real_model_smoke",
        "run_tag": RUN_TAG, "task_manifest": TASK_MANIFEST,
        "task_bundle_root": TASK_BUNDLE_ROOT, "task_bundle_manifest": TASK_BUNDLE_MANIFEST,
        "task_bundle_hash": TASK_BUNDLE_HASH,
        "output_dir": OUTPUT_DIR, "code_bundle_hash": CODE_BUNDLE_HASH, "seed": 12013,
        "defer_canonical_smoke_package": STAGE == "real_model_smoke",
        "generation_parameters": {"do_sample": False, "max_new_tokens": 8}}
    if STAGE == "real_model_smoke":
        runtime.update({
            "strict_permission_binding": True,
            "execution_permission_id": permission["permission_id"],
            "execution_permission_signature": permission["content_signature_sha256"],
            "provider_permission_path": PROVIDER_PERMISSION,
            "provider_permission_events_path": PROVIDER_PERMISSION_EVENTS,
            "permission_binding": permission_binding,
            "notebook_name": NOTEBOOK_NAME,
            "matrix_authorization": MATRIX_AUTHORIZATION,
            "smoke_gate_json": SMOKE_GATE_JSON,
            "final_task_freeze": FINAL_TASK_FREEZE,
            "final_review_ledger": FINAL_REVIEW_LEDGER,
            "model_registry": MODEL_REGISTRY,
            "study_config": STUDY_CONFIG,
            "code_bundle": CODE_BUNDLE,
        })
    pathlib.Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    smoke_seed = derive_seed_manifest(
        global_seed=GLOBAL_SEED, study=STUDY, provider=PROVIDER, gpu_id=0, shard_id=0,
        task_ids=[str(row["item_id"]) for row in tasks], attempts=2,
    )
    write_seed_manifest(pathlib.Path(OUTPUT_DIR) / "seed_manifest.json", smoke_seed)
    pathlib.Path(OUTPUT_DIR, "environment_manifest.json").write_text(json.dumps({
        "schema": "certvic.cvpr.smoke_environment.v1", "environment_hash": runtime_environment_hash,
        "environment_lock_hash": runtime_environment_hash, "status": environment_verification["status"],
        "passed": True, "paper_evidence": False,
    }, indent=2, sort_keys=True))
    pathlib.Path(RUNTIME_CONFIG).write_text(json.dumps(runtime, indent=2, sort_keys=True))
    SMOKE_NUM_SHARDS = 1  # intentional logical shard on both T4x2 and single-GPU fallback
    command = [sys.executable, "-m", "certvic.cvpr.worker", "--shard", "0", "--num-shards", "1",
               "--resume", "--batch-size", "2", "--oom-reduce-to-one", "--fail-closed",
               "--frozen-runtime-config", RUNTIME_CONFIG]
    if STAGE == "mock_smoke": command.append("--mock-runtime")
    subprocess.run(command, check=True)
    print(runtime_class)
else:
    print({"status": "NON_EVIDENCE_RUNTIME_SMOKE", "code_bundle_hash": CODE_BUNDLE_HASH})
'''
    package = '''required_outputs = ["merged_raw.jsonl", "runtime_manifest.json",
                    "environment_manifest.json", "validation_report.json",
                    "failure_report.json", "hash_manifest.json"]
if STAGE in {"evaluation", "mock_smoke", "real_model_smoke"}:
    expected_shards = 1 if STAGE in {"mock_smoke", "real_model_smoke"} else len(GPU_IDS)
    subprocess.run([sys.executable, "-m", "certvic.cvpr.package_run",
                    "--frozen-runtime-config", RUNTIME_CONFIG,
                    "--expected-shards", str(expected_shards)], check=True)
    package_source = pathlib.Path(OUTPUT_DIR) / f"certvic_cvpr_{RUN_TAG}_{PROVIDER}.zip"
    canonical_return = pathlib.Path(OUTPUT_DIR) / CANONICAL_RETURN_ZIP
    if STAGE == "evaluation":
        if not package_source.is_file(): raise RuntimeError("scientific package source ZIP is missing")
        if package_source != canonical_return: shutil.copyfile(package_source, canonical_return)
    if STAGE == "real_model_smoke":
        smoke_path = pathlib.Path(OUTPUT_DIR) / f"00C2_{PROVIDER}_real_model_smoke.zip"
        if not smoke_path.is_file():
            raise RuntimeError("package_run did not atomically create the canonical 00C2 ZIP")
        print({"canonical_smoke_zip": str(smoke_path)})
elif STAGE == "generation":
    root = pathlib.Path(OUTPUT_DIR); root.mkdir(parents=True, exist_ok=True)
    task_manifest_hash = hashlib.sha256(pathlib.Path(EDIT_PLAN).read_bytes()).hexdigest()
    generation_contract = {
        "schema": "certvic.cvpr.generation_run_contract.v1", "study": STUDY,
        "provider": PROVIDER, "task_manifest_sha256": task_manifest_hash,
        "code_bundle_hash": CODE_BUNDLE_HASH, "environment_lock_hash": ENVIRONMENT_LOCK_HASH,
        "seed": 12013, "generation_engine": GENERATION_ENGINE,
        "semantic_engine": SEMANTIC_ENGINE, "paper_evidence": False,
    }
    generation_contract["run_contract_hash"] = hashlib.sha256(json.dumps(
        generation_contract, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    generation_environment = {**hardware, "environment_lock_hash": ENVIRONMENT_LOCK_HASH,
                              "offline_environment_status": environment_verification["status"],
                              "paper_evidence": False}
    generation_runtime = {
        "schema": "certvic.cvpr.generation_runtime.v1", "study": STUDY,
        "provider": PROVIDER, "run_contract_hash": generation_contract["run_contract_hash"],
        "code_bundle_hash": CODE_BUNDLE_HASH, "task_manifest_sha256": task_manifest_hash,
        "paper_evidence": False,
    }
    run_contract_path = root / "run_contract.json"
    environment_path = root / "environment_manifest.json"
    runtime_path = root / "runtime_manifest.json"
    run_contract_path.write_text(json.dumps(generation_contract, indent=2, sort_keys=True))
    environment_path.write_text(json.dumps(generation_environment, indent=2, sort_keys=True))
    runtime_path.write_text(json.dumps(generation_runtime, indent=2, sort_keys=True))
    generation_zip = root / CANONICAL_RETURN_ZIP
    subprocess.run([sys.executable, "-m", "certvic.cvpr.package_generation",
                    "--study-manifest", EDIT_PLAN, "--generation-root", OUTPUT_DIR,
                    "--out-zip", str(generation_zip), "--assemble-shards",
                    "--run-contract", str(run_contract_path),
                    "--environment-manifest", str(environment_path),
                    "--runtime-manifest", str(runtime_path), "--strict"], check=True)
elif STAGE in {"code_smoke", "snapshot_smoke"}:
    from certvic.cvpr.smoke_artifacts import (
        write_environment_artifacts, write_snapshot_artifacts,
    )
    out = pathlib.Path(OUTPUT_DIR); out.mkdir(parents=True, exist_ok=True)
    if STAGE == "code_smoke":
        canonical_artifacts = write_environment_artifacts(out, {
            "status": environment_verification["status"], "passed": True,
            "environment_hash": ENVIRONMENT_LOCK_HASH,
            "environment_lock_hash": ENVIRONMENT_LOCK_HASH,
            "code_bundle_hash": CODE_BUNDLE_HASH, "hardware": hardware,
        })
    else:
        canonical_artifacts = write_snapshot_artifacts(out, PROVIDER, {
            **snapshot, "snapshot_contract": SNAPSHOT_CONTRACT,
            "model_id": MODEL_ID, "model_commit": MODEL_COMMIT,
            "processor_commit": PROCESSOR_COMMIT,
            "snapshot_root_hash": SNAPSHOT_ROOT_HASH,
        })
    print(canonical_artifacts)
canonical_return_path = pathlib.Path(OUTPUT_DIR) / CANONICAL_RETURN_ZIP
if STAGE != "mock_smoke" and not canonical_return_path.is_file():
    raise RuntimeError(f"canonical return ZIP missing: {CANONICAL_RETURN_ZIP}")
if canonical_return_path.is_file():
    print({"canonical_return_zip": str(canonical_return_path),
           "sha256": hashlib.sha256(canonical_return_path.read_bytes()).hexdigest()})
print({"required_outputs": required_outputs, "paper_evidence": False})
if STAGE in {"code_smoke", "snapshot_smoke", "real_model_smoke"}:
    print({"local_handoff_command": "python3 -m certvic.cvpr.smoke_handoff --artifacts-dir <RETURNED_ARTIFACTS> --smoke-contract <TRUSTED_SMOKE_CONTRACT> --model-registry configs/models/certvic_cvpr_model_registry.yaml --environment-lock configs/runtime/kaggle_t4x2_environment.lock.json --out-dir <SMOKE_GATE_DIR>"})
elif STAGE == "evaluation":
    print({"local_import_command": "python3 -m certvic.cvpr.import_transaction run --matrix <MATRIX_AUTHORIZATION> --provider-zip qwen2_5_vl_7b=<QWEN_ZIP> --provider-zip internvl_8b=<INTERNVL_ZIP> --provider-zip llava_onevision_7b=<LLAVA_ZIP> --destination <CANONICAL_DESTINATION> --nonce-ledger <CONSUMED_NONCES>"})
'''
    cells = [
        _cell("markdown", f"# {name}\n\nNON_EVIDENCE_RUNTIME_SMOKE or PLANNED_NOT_EXECUTED; paper_evidence=false.\n"),
        _cell("code", config),
        _cell("code", bootstrap),
        _cell("code", preflight),
    ]
    if stage == "evaluation":
        cells.append(_cell("code", worker))
    elif stage == "generation":
        cells.append(_cell("code", generation))
    elif stage.endswith("smoke"):
        cells.append(_cell("code", smoke))
    cells.append(_cell("code", package))
    return {
        "cells": cells,
        "metadata": {
            "certvic": {"stage": stage, "provider": provider, "paper_evidence": False},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def build_suite(out_dir: str | Path) -> dict[str, object]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for obsolete in (
        "00_certvic_cvpr_preflight_and_bundle_audit.ipynb",
        "00C_certvic_adapter_two_item_smoke.ipynb",
        "00C1_certvic_synthetic_mock_runtime_smoke.ipynb",
    ):
        (out / obsolete).unlink(missing_ok=True)
    expected = set(NOTEBOOKS) | {"notebook_manifest.json"}
    unexpected = sorted(path.name for path in out.iterdir() if path.is_file() and path.name not in expected)
    if unexpected:
        raise ValueError(f"refusing to delete notebook artifacts not owned by this builder: {unexpected}")
    hashes: dict[str, str] = {}
    for name, (stage, provider) in NOTEBOOKS.items():
        payload = (json.dumps(notebook(name, stage, provider), indent=1, sort_keys=True) + "\n").encode()
        (out / name).write_bytes(payload)
        hashes[name] = hashlib.sha256(payload).hexdigest()
    manifest = {
        "schema": "certvic.cvpr.notebook_suite.v2",
        "mode": "RUNTIME_HARDENED_NOT_EXECUTED_LOCALLY",
        "paper_evidence": False,
        "notebooks": hashes,
    }
    (out / "notebook_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
