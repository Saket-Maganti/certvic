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
    "00B_qwen2_5_vl_7b_snapshot_smoke.ipynb": ("snapshot_smoke", "qwen2_5_vl_7b"),
    "00B_internvl_8b_snapshot_smoke.ipynb": ("snapshot_smoke", "internvl_8b"),
    "00B_llava_onevision_7b_snapshot_smoke.ipynb": ("snapshot_smoke", "llava_onevision_7b"),
    "00C1_certvic_mock_adapter_smoke.ipynb": ("mock_smoke", "all"),
    "00C2_qwen2_5_vl_7b_real_model_two_item_smoke.ipynb": (
        "real_model_smoke", "qwen2_5_vl_7b"
    ),
    "00C2_internvl_8b_real_model_two_item_smoke.ipynb": (
        "real_model_smoke", "internvl_8b"
    ),
    "00C2_llava_onevision_7b_real_model_two_item_smoke.ipynb": (
        "real_model_smoke", "llava_onevision_7b"
    ),
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
        return f"00B_{provider}_snapshot_bundle.zip"
    if stage == "mock_smoke":
        return "00C1_synthetic_adapter_smoke.zip"
    if stage == "real_model_smoke":
        return f"00C2_{provider}_real_model_smoke.zip"
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


COMMON_DATASETS = {
    "code": ("certvic/certvic-code", "certvic_code_bundle.zip", "CODE"),
    "configs": ("certvic/certvic-configs", "certvic_configs_bundle.zip", "CONFIGS"),
    "tools": (
        "certvic/certvic-execution-tools",
        "certvic_execution_tools_bundle.zip",
        "EXECUTION_TOOLS",
    ),
    "wheelhouse": (
        "certvic/certvic-offline-wheelhouse",
        "certvic_offline_wheelhouse.zip",
        "OFFLINE_LINUX_WHEELHOUSE",
    ),
}

SNAPSHOT_DATASETS = {
    "qwen2_5_vl_7b": (
        "certvic/qwen2-5-vl-7b-snapshot",
        "qwen2_5_vl_7b_snapshot.zip",
    ),
    "internvl_8b": (
        "certvic/internvl2-8b-snapshot",
        "internvl2_8b_snapshot.zip",
    ),
    "llava_onevision_7b": (
        "certvic/llava-onevision-7b-snapshot",
        "llava_onevision_7b_snapshot.zip",
    ),
}


def _zero_edit_config(name: str, stage: str, provider: str) -> str:
    return_name = expected_return_zip(name, stage, provider)
    return f'''# Generated immutable run identity. There is nothing to edit in this notebook.
import os

STAGE = {stage!r}
PROVIDER = {provider!r}
NOTEBOOK_NAME = {name!r}
EXPECTED_GPUS = {0 if stage in {"code_smoke", "snapshot_smoke"} else 2}
ALLOW_SINGLE_GPU_FALLBACK = True
USE_REAL_MODEL = {stage == "real_model_smoke"!r}
MAX_ITEMS = 2
GLOBAL_SEED = 12013
SCHEMA_VERSION = "certvic.cvpr.output.v2"
SNAPSHOT_CONTRACT = "UNIFIED_SNAPSHOT"
PROMPT_TEMPLATE_ID = "certification_yes_no_v1"
PROMPT_TEMPLATE = "{{prompt}}\\n"
PARSER_VERSION = "certvic.parse.v2"
CANONICAL_RETURN_ZIP = {return_name!r}
LOCAL_DESTINATION = {f"data/runtime/{return_name}"!r}
WORKING_ROOT = os.environ.get("CERTVIC_KAGGLE_WORKING_ROOT", "/kaggle/working")
INPUT_ROOTS = [value for value in os.environ.get("CERTVIC_INPUT_ROOTS", "").split(os.pathsep)
               if value] or ["/kaggle/input", "/kaggle/working"]
for key, value in {{
    "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "DIFFUSERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1", "PIP_NO_INDEX": "1",
    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
}}.items():
    os.environ[key] = value
'''


def _early_code_bootstrap() -> str:
    slug, filename, bundle_type = COMMON_DATASETS["code"]
    return f'''import hashlib, json, pathlib, shutil, stat, subprocess, sys, zipfile

EARLY_ERRORS = {{
    "missing": "KAGGLE_BOOTSTRAP_01_DATASET_NOT_FOUND",
    "ambiguous": "KAGGLE_BOOTSTRAP_02_AMBIGUOUS_DATASET",
    "invalid": "KAGGLE_BOOTSTRAP_03_BUNDLE_INVALID",
    "unsafe": "KAGGLE_BOOTSTRAP_09_UNSAFE_EXTRACTION",
}}

def early_sha256(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def early_member(info):
    name = info.filename
    normalized = name.replace("\\\\", "/")
    value = pathlib.PurePosixPath(normalized)
    mode = (info.external_attr >> 16) & 0xFFFF
    if (not normalized or normalized != name or normalized.endswith("/") or value.is_absolute()
            or ".." in value.parts or "." in value.parts or normalized.startswith("~")
            or "\\x00" in normalized or info.is_dir() or stat.S_ISLNK(mode)
            or (mode and not stat.S_ISREG(mode))):
        raise RuntimeError(f"{{EARLY_ERRORS['unsafe']}}: unsafe member {{name!r}}")
    return value.as_posix()

def early_verify_and_extract(archive_path, destination):
    source = pathlib.Path(archive_path).resolve()
    try:
        with zipfile.ZipFile(source) as archive:
            infos = archive.infolist()
            names = [early_member(info) for info in infos]
            if len(names) != len(set(names)) or archive.testzip() is not None:
                raise RuntimeError(f"{{EARLY_ERRORS['invalid']}}: duplicate or corrupt members")
            manifest = json.loads(archive.read("bundle_manifest.json"))
            hashes = json.loads(archive.read("hash_manifest.json"))
            if (manifest.get("schema") != "certvic.kaggle.bundle.v1"
                    or hashes.get("schema") != "certvic.kaggle.hash_manifest.v1"
                    or manifest.get("bundle_type") != {bundle_type!r}
                    or manifest.get("expected_kaggle_dataset_slug") != {slug!r}):
                raise RuntimeError(f"{{EARLY_ERRORS['invalid']}}: code bundle identity mismatch")
            declared = manifest.get("files", {{}})
            hash_files = hashes.get("files", {{}})
            if (set(names) != set(hash_files) | {{"hash_manifest.json"}}
                    or set(declared) != set(names) - {{"bundle_manifest.json", "hash_manifest.json"}}):
                raise RuntimeError(f"{{EARLY_ERRORS['invalid']}}: code file universe mismatch")
            for name, record in hash_files.items():
                payload = archive.read(name)
                observed = {{"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}}
                if record != observed or (name in declared and declared[name] != observed):
                    raise RuntimeError(f"{{EARLY_ERRORS['invalid']}}: byte mismatch {{name}}")
            target = pathlib.Path(destination).resolve()
            if target.exists():
                if target.is_symlink() or not target.is_dir():
                    raise RuntimeError(f"{{EARLY_ERRORS['unsafe']}}: invalid destination")
                shutil.rmtree(target)
            target.mkdir(parents=True)
            for info, name in zip(infos, names, strict=True):
                output = (target / name).resolve()
                try:
                    output.relative_to(target)
                except ValueError as error:
                    raise RuntimeError(f"{{EARLY_ERRORS['unsafe']}}: traversal member") from error
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as reader, output.open("xb") as writer:
                    shutil.copyfileobj(reader, writer, length=1024 * 1024)
    except (OSError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        raise RuntimeError(f"{{EARLY_ERRORS['invalid']}}: {{error}}") from error
    return target, manifest

mount = pathlib.Path(INPUT_ROOT) / {slug.split('/', 1)[1]!r}
matches = sorted(path.resolve() for path in mount.rglob({filename!r}) if path.is_file()) if mount.is_dir() else []
if not matches:
    raise RuntimeError(f"{{EARLY_ERRORS['missing']}}: slug={slug} filename={filename}")
if len(matches) != 1:
    raise RuntimeError(f"{{EARLY_ERRORS['ambiguous']}}: slug={slug} candidates={{[str(p) for p in matches]}}")
CODE_BUNDLE_PATH = str(matches[0])
CODE_BUNDLE_HASH = early_sha256(matches[0])
CODE_EXTRACT_ROOT, CODE_OUTER_MANIFEST = early_verify_and_extract(
    matches[0], pathlib.Path(WORKING_ROOT) / "certvic_code"
)
project_candidates = sorted(path.parent.resolve() for path in CODE_EXTRACT_ROOT.rglob("pyproject.toml")
    if (path.parent / "certvic/__init__.py").is_file())
if len(project_candidates) != 1:
    raise RuntimeError("KAGGLE_BOOTSTRAP_10_AMBIGUOUS_CONTENT: project root")
PROJECT_ROOT = project_candidates[0]
sys.path.insert(0, str(PROJECT_ROOT))

from certvic.cvpr.notebook_bootstrap import (
    discover_unique_file, discover_unique_root, materialize_dataset, verify_attached_bundle,
)
verify_attached_bundle(CODE_BUNDLE_PATH, expected_type={bundle_type!r}, expected_slug={slug!r})
print({{"project_root": str(PROJECT_ROOT), "code_bundle_sha256": CODE_BUNDLE_HASH}})
'''


def _common_materialization() -> str:
    configs = COMMON_DATASETS["configs"]
    tools = COMMON_DATASETS["tools"]
    wheelhouse = COMMON_DATASETS["wheelhouse"]
    return f'''from certvic.cvpr.environment_lock import environment_lock_hash

CONFIG_DATASET = materialize_dataset(
    slug={configs[0]!r}, filename={configs[1]!r}, expected_type={configs[2]!r},
    input_root=INPUT_ROOT, destination=pathlib.Path(WORKING_ROOT) / "certvic_configs",
)
TOOLS_DATASET = materialize_dataset(
    slug={tools[0]!r}, filename={tools[1]!r}, expected_type={tools[2]!r},
    input_root=INPUT_ROOT, destination=pathlib.Path(WORKING_ROOT) / "certvic_execution_tools",
)
WHEELHOUSE_DATASET = materialize_dataset(
    slug={wheelhouse[0]!r}, filename={wheelhouse[1]!r}, expected_type={wheelhouse[2]!r},
    input_root=INPUT_ROOT, destination=pathlib.Path(WORKING_ROOT) / "certvic_offline_wheelhouse",
)
CONFIG_ROOT = pathlib.Path(CONFIG_DATASET["root"])
WHEELHOUSE_ROOT = pathlib.Path(WHEELHOUSE_DATASET["root"])
ENVIRONMENT_LOCK = str(discover_unique_file(CONFIG_ROOT, "kaggle_t4x2_environment.lock.json"))
ENVIRONMENT_LOCK_HASH = environment_lock_hash(ENVIRONMENT_LOCK)
WHEELHOUSE_MANIFEST = str(discover_unique_file(WHEELHOUSE_ROOT, "wheelhouse_manifest.json"))
WHEELHOUSE_PATH = str(WHEELHOUSE_ROOT / "wheels")
if not pathlib.Path(WHEELHOUSE_PATH).is_dir():
    raise RuntimeError("KAGGLE_BOOTSTRAP_04_WHEELHOUSE_INVALID: wheels directory missing")
MODEL_REGISTRY = str(discover_unique_file(CONFIG_ROOT, "certvic_immutable_model_registry.json"))
ATTACHED_INPUT_HASHES = {{
    "code": CODE_BUNDLE_HASH,
    "configs": CONFIG_DATASET["archive_sha256"],
    "tools": TOOLS_DATASET["archive_sha256"],
    "wheelhouse": WHEELHOUSE_DATASET["archive_sha256"],
}}
print({{"environment_lock": ENVIRONMENT_LOCK, "environment_lock_hash": ENVIRONMENT_LOCK_HASH,
       "wheelhouse_manifest": WHEELHOUSE_MANIFEST, "attached_input_hashes": ATTACHED_INPUT_HASHES}})
'''


def _content_early_code_bootstrap() -> str:
    """Stdlib-only CODE discovery used before the project package is importable."""
    return r'''import hashlib, json, os, pathlib, shutil, stat, sys, zipfile

DISCOVERY_ERRORS = {
    "missing": "CERTVIC_DISCOVERY_01_REQUIRED_ROLE_NOT_FOUND",
    "ambiguous": "CERTVIC_DISCOVERY_02_AMBIGUOUS_DISTINCT_CONTENT",
    "authentication": "CERTVIC_DISCOVERY_03_CONTENT_AUTHENTICATION_FAILED",
}
DISCOVERY_POLICY = "CONTENT_AUTHENTICATED_ANY_LOCATION"
OPERATIONAL_FIELDS = {
    "builder_command", "created_time", "expected_kaggle_dataset_slug", "mount_path",
    "required_notebook", "validation_command",
}

def early_sha256(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def early_safe_member(info):
    name = info.filename
    normalized = name.replace("\\", "/")
    value = pathlib.PurePosixPath(normalized)
    mode = (info.external_attr >> 16) & 0xFFFF
    if (not normalized or normalized != name or normalized.endswith("/") or value.is_absolute()
            or ".." in value.parts or "." in value.parts or normalized.startswith("~")
            or "\x00" in normalized or info.is_dir() or stat.S_ISLNK(mode)
            or (mode and not stat.S_ISREG(mode))):
        raise RuntimeError(f"{DISCOVERY_ERRORS['authentication']}: unsafe member {name!r}")
    return value.as_posix()

def early_content_identity(manifest, hash_files):
    identity_manifest = {key: value for key, value in manifest.items()
                         if key not in OPERATIONAL_FIELDS}
    identity_files = {name: record for name, record in hash_files.items()
                      if name not in {"README.md", "bundle_manifest.json"}}
    payload = json.dumps({"manifest": identity_manifest, "files": identity_files},
                         indent=2, sort_keys=True).encode() + b"\n"
    return hashlib.sha256(payload).hexdigest()

def early_verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [early_safe_member(info) for info in infos]
        if "bundle_manifest.json" not in names or "hash_manifest.json" not in names:
            return None
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise RuntimeError(f"{DISCOVERY_ERRORS['authentication']}: duplicate or corrupt archive")
        manifest_bytes = archive.read("bundle_manifest.json")
        hash_bytes = archive.read("hash_manifest.json")
        if len(manifest_bytes) > 8 * 1024 * 1024 or len(hash_bytes) > 8 * 1024 * 1024:
            raise RuntimeError(f"{DISCOVERY_ERRORS['authentication']}: oversized manifest")
        manifest = json.loads(manifest_bytes)
        hashes = json.loads(hash_bytes)
        if (manifest.get("schema") != "certvic.kaggle.bundle.v1"
                or hashes.get("schema") != "certvic.kaggle.hash_manifest.v1"
                or manifest.get("bundle_type") != "CODE"):
            return None
        declared, hash_files = manifest.get("files", {}), hashes.get("files", {})
        if (set(names) != set(hash_files) | {"hash_manifest.json"}
                or set(declared) != set(names) - {"bundle_manifest.json", "hash_manifest.json"}):
            raise RuntimeError(f"{DISCOVERY_ERRORS['authentication']}: file universe mismatch")
        for name, record in hash_files.items():
            payload = archive.read(name)
            observed = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
            if record != observed or (name in declared and declared[name] != observed):
                raise RuntimeError(f"{DISCOVERY_ERRORS['authentication']}: byte mismatch {name}")
        return manifest, hash_files, hashlib.sha256(manifest_bytes).hexdigest()

def early_verify_directory(path):
    root = pathlib.Path(path).resolve()
    manifest_path, hash_path = root / "bundle_manifest.json", root / "hash_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes = json.loads(hash_path.read_text(encoding="utf-8"))
    if (manifest.get("schema") != "certvic.kaggle.bundle.v1"
            or hashes.get("schema") != "certvic.kaggle.hash_manifest.v1"
            or manifest.get("bundle_type") != "CODE"):
        return None
    observed = {}
    for member in root.rglob("*"):
        mode = member.lstat().st_mode
        if member.is_symlink() or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise RuntimeError(f"{DISCOVERY_ERRORS['authentication']}: unsafe extracted member")
        if stat.S_ISREG(mode):
            observed[member.relative_to(root).as_posix()] = member
    declared, hash_files = manifest.get("files", {}), hashes.get("files", {})
    if (set(observed) != set(hash_files) | {"hash_manifest.json"}
            or set(declared) != set(observed) - {"bundle_manifest.json", "hash_manifest.json"}):
        raise RuntimeError(f"{DISCOVERY_ERRORS['authentication']}: extracted universe mismatch")
    for name, record in hash_files.items():
        member = observed[name]
        actual = {"size": member.stat().st_size, "sha256": early_sha256(member)}
        if actual != record or (name in declared and declared[name] != actual):
            raise RuntimeError(f"{DISCOVERY_ERRORS['authentication']}: extracted byte mismatch {name}")
    return manifest, hash_files, early_sha256(manifest_path)

configured_roots = [value for value in os.environ.get("CERTVIC_INPUT_ROOTS", "").split(os.pathsep)
                    if value]
if not configured_roots:
    configured_roots = ["/kaggle/input", "/kaggle/working"]
INPUT_ROOTS = sorted({str(pathlib.Path(value).resolve()) for value in configured_roots
                      if pathlib.Path(value).is_dir() and not pathlib.Path(value).is_symlink()})
archive_candidates, directory_candidates = [], []
for root_value in INPUT_ROOTS:
    root = pathlib.Path(root_value)
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        base = pathlib.Path(current)
        directory_names[:] = sorted(name for name in directory_names
                                     if not (base / name).is_symlink())
        if "bundle_manifest.json" in file_names and "hash_manifest.json" in file_names:
            directory_candidates.append(base.resolve())
        for name in sorted(file_names):
            candidate = base / name
            if candidate.is_symlink() or not candidate.is_file():
                continue
            try:
                with candidate.open("rb") as handle:
                    magic = handle.read(4)
            except OSError:
                continue
            if magic in {b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"}:
                archive_candidates.append(candidate.resolve())

valid, failures = [], []
for representation, candidates in (("zip_archive", sorted(set(archive_candidates))),
                                   ("extracted_directory", sorted(set(directory_candidates)))):
    for candidate in candidates:
        try:
            result = (early_verify_archive(candidate) if representation == "zip_archive"
                      else early_verify_directory(candidate))
        except (OSError, KeyError, json.JSONDecodeError, UnicodeDecodeError,
                zipfile.BadZipFile, RuntimeError) as error:
            failures.append(f"{candidate}: {error}")
            continue
        if result is None:
            continue
        manifest, hash_files, manifest_hash = result
        identity = early_content_identity(manifest, hash_files)
        expected = os.environ.get("CERTVIC_EXPECTED_CONTENT_ID_CODE")
        if expected and identity != expected.lower():
            failures.append(f"{candidate}: expected CODE content identity mismatch")
            continue
        valid.append({"path": candidate, "representation": representation,
                      "manifest": manifest, "manifest_sha256": manifest_hash,
                      "content_identity_sha256": identity})
if not valid:
    code = DISCOVERY_ERRORS["authentication"] if failures else DISCOVERY_ERRORS["missing"]
    raise RuntimeError(f"{code}: role=CODE failures={failures}")
identities = {row["content_identity_sha256"] for row in valid}
if len(identities) != 1:
    raise RuntimeError(f"{DISCOVERY_ERRORS['ambiguous']}: role=CODE candidates="
                       f"{[(row['content_identity_sha256'], str(row['path'])) for row in valid]}")
selected = min(valid, key=lambda row: os.path.normcase(str(row["path"])))
CODE_DISCOVERY_MIRRORS = sorted({str(row["path"]) for row in valid})
CODE_BUNDLE_SOURCE = str(selected["path"])
CODE_BUNDLE_HASH = selected["content_identity_sha256"]
CODE_ARCHIVE_SHA256 = (early_sha256(selected["path"])
                       if selected["representation"] == "zip_archive" else None)
if selected["representation"] == "zip_archive":
    CODE_EXTRACT_ROOT = pathlib.Path(os.environ.get(
        "CERTVIC_KAGGLE_WORKING_ROOT", "/kaggle/working")) / "certvic_code"
    if CODE_EXTRACT_ROOT.exists():
        if CODE_EXTRACT_ROOT.is_symlink() or not CODE_EXTRACT_ROOT.is_dir():
            raise RuntimeError(f"{DISCOVERY_ERRORS['authentication']}: unsafe CODE destination")
        shutil.rmtree(CODE_EXTRACT_ROOT)
    CODE_EXTRACT_ROOT.mkdir(parents=True)
    with zipfile.ZipFile(selected["path"]) as archive:
        for info in archive.infolist():
            name = early_safe_member(info)
            output = (CODE_EXTRACT_ROOT / name).resolve()
            output.relative_to(CODE_EXTRACT_ROOT.resolve())
            output.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as reader, output.open("xb") as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
else:
    CODE_EXTRACT_ROOT = pathlib.Path(selected["path"])
CODE_BUNDLE_PATH = (CODE_BUNDLE_SOURCE if selected["representation"] == "zip_archive"
                    else str(CODE_EXTRACT_ROOT / "bundle_manifest.json"))
CODE_BUNDLE = CODE_BUNDLE_PATH
project_candidates = sorted(path.parent.resolve() for path in CODE_EXTRACT_ROOT.rglob("pyproject.toml")
                            if (path.parent / "certvic/__init__.py").is_file())
if len(project_candidates) != 1:
    raise RuntimeError(f"{DISCOVERY_ERRORS['authentication']}: CODE project root ambiguous")
PROJECT_ROOT = project_candidates[0]
sys.path.insert(0, str(PROJECT_ROOT))
from certvic.cvpr.content_discovery import (
    DISCOVERY_POLICY, discover_authenticated_input, resolve_content_bound_roles,
)
from certvic.cvpr.notebook_bootstrap import discover_unique_file, discover_unique_root
authenticated_code = discover_authenticated_input(
    "CODE", roots=INPUT_ROOTS, expected_identity=CODE_BUNDLE_HASH,
    materialization_root=pathlib.Path(os.environ.get(
        "CERTVIC_KAGGLE_WORKING_ROOT", "/kaggle/working")) / "certvic_authenticated_inputs",
)
if authenticated_code["content_identity_sha256"] != CODE_BUNDLE_HASH:
    raise RuntimeError(f"{DISCOVERY_ERRORS['authentication']}: early/shared CODE identity mismatch")
AUTHENTICATED_CONTENT_IDENTITIES = {"code_bundle": CODE_BUNDLE_HASH}
DISCOVERED_PROVENANCE = {"CODE": authenticated_code}
print({"discovery_policy": DISCOVERY_POLICY, "role": "CODE", "provider": None,
       "study": selected["manifest"].get("study"), "stage": selected["manifest"].get("stage"),
       "representation": selected["representation"], "discovered_path": CODE_BUNDLE_SOURCE,
       "content_identity_sha256": CODE_BUNDLE_HASH, "archive_sha256": CODE_ARCHIVE_SHA256,
       "mirrors": CODE_DISCOVERY_MIRRORS, "project_root": str(PROJECT_ROOT)})
'''


def _content_common_materialization() -> str:
    return '''from certvic.cvpr.environment_lock import environment_lock_hash

DISCOVERY_MATERIALIZATION_ROOT = pathlib.Path(WORKING_ROOT) / "certvic_authenticated_inputs"
CONFIG_DATASET = discover_authenticated_input(
    "CONFIGS", roots=INPUT_ROOTS,
    materialization_root=DISCOVERY_MATERIALIZATION_ROOT,
)
TOOLS_DATASET = discover_authenticated_input(
    "EXECUTION_TOOLS", roots=INPUT_ROOTS,
    materialization_root=DISCOVERY_MATERIALIZATION_ROOT,
)
WHEELHOUSE_DATASET = discover_authenticated_input(
    "OFFLINE_LINUX_WHEELHOUSE", roots=INPUT_ROOTS,
    materialization_root=DISCOVERY_MATERIALIZATION_ROOT,
)
for discovered in (CONFIG_DATASET, TOOLS_DATASET, WHEELHOUSE_DATASET):
    DISCOVERED_PROVENANCE[discovered["role"]] = discovered
    print({key: discovered[key] for key in (
        "role", "provider", "study", "stage", "representation", "discovered_path",
        "materialized_root", "content_identity_sha256", "archive_sha256", "mirrors",
        "observed_mount", "observed_dataset_folder",
    )})
CONFIG_ROOT = pathlib.Path(CONFIG_DATASET["materialized_root"])
WHEELHOUSE_ROOT = pathlib.Path(WHEELHOUSE_DATASET["materialized_root"])
ENVIRONMENT_LOCK = str(discover_unique_file(CONFIG_ROOT, "kaggle_t4x2_environment.lock.json"))
ENVIRONMENT_LOCK_HASH = environment_lock_hash(ENVIRONMENT_LOCK)
WHEELHOUSE_MANIFEST = str(discover_unique_file(WHEELHOUSE_ROOT, "wheelhouse_manifest.json"))
WHEELHOUSE_PATH = str(WHEELHOUSE_ROOT / "wheels")
if not pathlib.Path(WHEELHOUSE_PATH).is_dir():
    raise RuntimeError("KAGGLE_BOOTSTRAP_04_WHEELHOUSE_INVALID: wheels directory missing")
MODEL_REGISTRY = str(discover_unique_file(CONFIG_ROOT, "certvic_immutable_model_registry.json"))
ATTACHED_INPUT_HASHES = {
    "code": CODE_BUNDLE_HASH,
    "configs": CONFIG_DATASET["content_identity_sha256"],
    "tools": TOOLS_DATASET["content_identity_sha256"],
    "wheelhouse": WHEELHOUSE_DATASET["content_identity_sha256"],
}
AUTHENTICATED_CONTENT_IDENTITIES.update({
    "configs": CONFIG_DATASET["content_identity_sha256"],
    "tools": TOOLS_DATASET["content_identity_sha256"],
    "wheelhouse": WHEELHOUSE_DATASET["content_identity_sha256"],
})
print({"environment_lock": ENVIRONMENT_LOCK, "environment_lock_hash": ENVIRONMENT_LOCK_HASH,
       "wheelhouse_manifest": WHEELHOUSE_MANIFEST,
       "authenticated_content_identities": AUTHENTICATED_CONTENT_IDENTITIES})
'''


def _content_snapshot_materialization(provider: str) -> str:
    return f'''from certvic.cvpr.model_snapshot_manifest import verify_manifest

SNAPSHOT_DATASET = discover_authenticated_input(
    "MODEL_SNAPSHOT", provider={provider!r}, stage="model_snapshot", roots=INPUT_ROOTS,
    materialization_root=DISCOVERY_MATERIALIZATION_ROOT,
)
DISCOVERED_PROVENANCE["MODEL_SNAPSHOT"] = SNAPSHOT_DATASET
print({{key: SNAPSHOT_DATASET[key] for key in (
    "role", "provider", "study", "stage", "representation", "discovered_path",
    "materialized_root", "content_identity_sha256", "archive_sha256", "mirrors",
    "observed_mount", "observed_dataset_folder",
)}})
SNAPSHOT_CONTAINER = pathlib.Path(SNAPSHOT_DATASET["materialized_root"])
SNAPSHOT_MANIFEST = str(discover_unique_file(
    SNAPSHOT_CONTAINER, "certvic_model_snapshot_manifest.json"
))
SNAPSHOT_ROOT = pathlib.Path(SNAPSHOT_MANIFEST).parent.resolve()
MODEL_PATH = str(SNAPSHOT_ROOT)
PROCESSOR_PATH = str(SNAPSHOT_ROOT)
SNAPSHOT_MANIFEST_HASH = early_sha256(SNAPSHOT_MANIFEST)
snapshot_identity = json.loads(pathlib.Path(SNAPSHOT_MANIFEST).read_text(encoding="utf-8"))
MODEL_ID = str(snapshot_identity["model_id"])
PROCESSOR_ID = str(snapshot_identity["processor_id"])
MODEL_COMMIT = str(snapshot_identity["model_commit"])
PROCESSOR_COMMIT = str(snapshot_identity["processor_commit"])
EXPECTED_ARCHITECTURE = str(snapshot_identity["expected_architecture"])
SNAPSHOT_ROOT_HASH = str(snapshot_identity["unified_snapshot_root_sha256"])
outer_snapshot = SNAPSHOT_DATASET["bundle_manifest"]
for field, expected in {{
    "provider": PROVIDER, "model_id": MODEL_ID, "model_commit": MODEL_COMMIT,
    "processor_commit": PROCESSOR_COMMIT, "expected_architecture": EXPECTED_ARCHITECTURE,
    "unified_snapshot_root_sha256": SNAPSHOT_ROOT_HASH,
}}.items():
    if outer_snapshot.get(field) != expected:
        raise RuntimeError(f"CERTVIC_DISCOVERY_03_CONTENT_AUTHENTICATION_FAILED: snapshot {{field}} mismatch")
registry = json.loads(pathlib.Path(MODEL_REGISTRY).read_text(encoding="utf-8"))["models"][PROVIDER]
if (registry.get("repository_id") != MODEL_ID
        or registry.get("model_commit") != MODEL_COMMIT
        or registry.get("processor_commit") != PROCESSOR_COMMIT
        or registry.get("architecture") != EXPECTED_ARCHITECTURE):
    raise RuntimeError("CERTVIC_DISCOVERY_03_CONTENT_AUTHENTICATION_FAILED: immutable registry mismatch")
ATTACHED_INPUT_HASHES["snapshot"] = SNAPSHOT_DATASET["content_identity_sha256"]
AUTHENTICATED_CONTENT_IDENTITIES["snapshot"] = SNAPSHOT_DATASET["content_identity_sha256"]
print({{"snapshot_root": MODEL_PATH, "snapshot_manifest": SNAPSHOT_MANIFEST,
       "snapshot_manifest_sha256": SNAPSHOT_MANIFEST_HASH,
       "snapshot_root_sha256": SNAPSHOT_ROOT_HASH, "model_id": MODEL_ID,
       "model_commit": MODEL_COMMIT, "processor_commit": PROCESSOR_COMMIT,
       "expected_architecture": EXPECTED_ARCHITECTURE}})
'''


def _snapshot_materialization(provider: str) -> str:
    slug, filename = SNAPSHOT_DATASETS[provider]
    return f'''from certvic.cvpr.model_snapshot_manifest import verify_manifest

SNAPSHOT_DATASET = materialize_dataset(
    slug={slug!r}, filename={filename!r}, expected_type="MODEL_SNAPSHOT",
    input_root=INPUT_ROOT,
    destination=pathlib.Path(WORKING_ROOT) / {f"certvic_snapshot_{provider}"!r},
)
SNAPSHOT_CONTAINER = pathlib.Path(SNAPSHOT_DATASET["root"])
SNAPSHOT_MANIFEST = str(discover_unique_file(
    SNAPSHOT_CONTAINER, "certvic_model_snapshot_manifest.json"
))
SNAPSHOT_ROOT = pathlib.Path(SNAPSHOT_MANIFEST).parent.resolve()
MODEL_PATH = str(SNAPSHOT_ROOT)
PROCESSOR_PATH = str(SNAPSHOT_ROOT)
SNAPSHOT_MANIFEST_HASH = early_sha256(SNAPSHOT_MANIFEST)
snapshot_identity = json.loads(pathlib.Path(SNAPSHOT_MANIFEST).read_text(encoding="utf-8"))
MODEL_ID = str(snapshot_identity["model_id"])
PROCESSOR_ID = str(snapshot_identity["processor_id"])
MODEL_COMMIT = str(snapshot_identity["model_commit"])
PROCESSOR_COMMIT = str(snapshot_identity["processor_commit"])
EXPECTED_ARCHITECTURE = str(snapshot_identity["expected_architecture"])
SNAPSHOT_ROOT_HASH = str(snapshot_identity["unified_snapshot_root_sha256"])
outer_snapshot = SNAPSHOT_DATASET["bundle_manifest"]
for field, expected in {{
    "provider": PROVIDER, "model_id": MODEL_ID, "model_commit": MODEL_COMMIT,
    "processor_commit": PROCESSOR_COMMIT, "expected_architecture": EXPECTED_ARCHITECTURE,
    "unified_snapshot_root_sha256": SNAPSHOT_ROOT_HASH,
}}.items():
    if outer_snapshot.get(field) != expected:
        raise RuntimeError(f"KAGGLE_BOOTSTRAP_03_BUNDLE_INVALID: snapshot {{field}} mismatch")
registry = json.loads(pathlib.Path(MODEL_REGISTRY).read_text(encoding="utf-8"))["models"][PROVIDER]
if (registry.get("repository_id") != MODEL_ID
        or registry.get("model_commit") != MODEL_COMMIT
        or registry.get("processor_commit") != PROCESSOR_COMMIT
        or registry.get("architecture") != EXPECTED_ARCHITECTURE):
    raise RuntimeError("KAGGLE_BOOTSTRAP_08_RUN_IDENTITY_INCOMPLETE: immutable registry mismatch")
ATTACHED_INPUT_HASHES["snapshot"] = SNAPSHOT_DATASET["archive_sha256"]
print({{"snapshot_root": MODEL_PATH, "snapshot_manifest": SNAPSHOT_MANIFEST,
       "snapshot_manifest_sha256": SNAPSHOT_MANIFEST_HASH,
       "snapshot_root_sha256": SNAPSHOT_ROOT_HASH, "model_id": MODEL_ID,
       "model_commit": MODEL_COMMIT, "processor_commit": PROCESSOR_COMMIT,
       "expected_architecture": EXPECTED_ARCHITECTURE}})
'''


def _offline_environment_cell(*, require_gpu: bool) -> str:
    return f'''from certvic.cvpr.environment_lock import (
    offline_environment_flags, prepare_offline_environment,
)
from certvic.cvpr.notebook_bootstrap import configure_offline_environment, import_smoke
from certvic.cvpr.runtime_preflight import hardware_report

configure_offline_environment()
if offline_environment_flags().get("HF_HUB_OFFLINE") != "1" or os.environ.get("PIP_NO_INDEX") != "1":
    raise RuntimeError("KAGGLE_ZERO_EDIT_OFFLINE_POLICY_INCOMPLETE")
environment_verification = prepare_offline_environment(
    ENVIRONMENT_LOCK,
    wheelhouse=WHEELHOUSE_PATH,
    wheelhouse_manifest=WHEELHOUSE_MANIFEST,
    allow_preinstalled=True,
    require_exact=True,
    require_cuda={require_gpu!r},
)
if environment_verification["status"] not in {{
    "EXACT_PREINSTALLED_ENVIRONMENT_ACCEPTED", "OFFLINE_WHEELHOUSE_INSTALLED_AND_VERIFIED",
}}:
    raise RuntimeError("KAGGLE_ZERO_EDIT_EXACT_ENVIRONMENT_NOT_ESTABLISHED")
hardware = hardware_report()
print(hardware)
if EXPECTED_GPUS == 0 and (hardware["cuda_available"] or hardware["gpu_count"] != 0):
    raise RuntimeError("KAGGLE_ZERO_EDIT_CPU_ACCELERATOR_MUST_BE_OFF")
if EXPECTED_GPUS > 0:
    names = [row["name"] for row in hardware.get("gpus", [])]
    if not hardware["cuda_available"]:
        raise RuntimeError("KAGGLE_BOOTSTRAP_07_GPU_CONTRACT_FAILED: CUDA unavailable")
    if len(names) < 2 and not (len(names) == 1 and ALLOW_SINGLE_GPU_FALLBACK):
        raise RuntimeError(f"KAGGLE_BOOTSTRAP_07_GPU_CONTRACT_FAILED: device_count={{len(names)}}")
    if not all("T4" in name.upper() for name in names[:2]):
        raise RuntimeError(f"KAGGLE_BOOTSTRAP_07_GPU_CONTRACT_FAILED: devices={{names}}")
import_versions = import_smoke(["certvic", "numpy", "pandas", "torch", "transformers"])
print({{"offline": True, "network_used": False, "imports": import_versions,
       "environment_status": environment_verification["status"]}})
'''


def _code_smoke_output() -> str:
    return '''from certvic.cvpr.smoke_artifacts import write_environment_artifacts

artifact = write_environment_artifacts(WORKING_ROOT, {
    "stage": "00A", "status": environment_verification["status"], "passed": True,
    "environment_hash": ENVIRONMENT_LOCK_HASH,
    "environment_lock_hash": ENVIRONMENT_LOCK_HASH,
    "code_bundle_hash": CODE_BUNDLE_HASH,
    "attached_input_hashes": ATTACHED_INPUT_HASHES,
    "hardware": hardware, "network_used": False,
})
canonical = pathlib.Path(WORKING_ROOT) / CANONICAL_RETURN_ZIP
if not canonical.is_file() or canonical.resolve() != pathlib.Path(
        "/kaggle/working/00A_environment_bundle.zip").resolve():
    raise RuntimeError("KAGGLE_ZERO_EDIT_CANONICAL_RETURN_MISSING: 00A_environment_bundle.zip")
print(str(canonical))
print(f"DOWNLOAD_FILENAME={CANONICAL_RETURN_ZIP}")
print(f"LOCAL_DESTINATION={LOCAL_DESTINATION}")
print("RESUME_COMMAND=python3 scripts/run_all_cpu_workflows.py --resume")
'''


def _snapshot_smoke_output() -> str:
    return '''from certvic.cvpr.smoke_artifacts import write_snapshot_artifacts

snapshot = verify_manifest(
    MODEL_PATH, SNAPSHOT_MANIFEST,
    expected_model_id=MODEL_ID,
    expected_model_commit=MODEL_COMMIT,
    expected_processor_commit=PROCESSOR_COMMIT,
    expected_architecture=EXPECTED_ARCHITECTURE,
)
if not snapshot["passed"]:
    raise RuntimeError(f"KAGGLE_ZERO_EDIT_SNAPSHOT_INVALID: {snapshot['errors']}")
artifact = write_snapshot_artifacts(WORKING_ROOT, PROVIDER, {
    **snapshot,
    "snapshot_contract": SNAPSHOT_CONTRACT,
    "model_id": MODEL_ID,
    "processor_id": PROCESSOR_ID,
    "model_commit": MODEL_COMMIT,
    "processor_commit": PROCESSOR_COMMIT,
    "expected_architecture": EXPECTED_ARCHITECTURE,
    "snapshot_manifest_file_sha256": SNAPSHOT_MANIFEST_HASH,
    "snapshot_root_hash": SNAPSHOT_ROOT_HASH,
    "snapshot_archive_sha256": SNAPSHOT_DATASET.get("archive_sha256"),
    "snapshot_content_identity_sha256": SNAPSHOT_DATASET["content_identity_sha256"],
})
canonical = pathlib.Path(WORKING_ROOT) / CANONICAL_RETURN_ZIP
if not canonical.is_file():
    raise RuntimeError(f"KAGGLE_ZERO_EDIT_CANONICAL_RETURN_MISSING: {CANONICAL_RETURN_ZIP}")
print(str(canonical))
print(f"DOWNLOAD_FILENAME={CANONICAL_RETURN_ZIP}")
print(f"LOCAL_DESTINATION={LOCAL_DESTINATION}")
print("RESUME_COMMAND=python3 scripts/run_all_cpu_workflows.py --resume")
'''


def _real_smoke_inputs_and_permission() -> str:
    return '''from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.notebook_permission_binding import derive_permission_binding
from certvic.cvpr.reconcile_provider_permissions import (
    provider_state, transition_provider_permission, verify_matrix_authorization,
    verify_provider_permission,
)
from certvic.cvpr.run_contract import build_run_contract
from certvic.cvpr.task_bundle import verify_bundle as verify_task_bundle

SMOKE_DATASET = discover_authenticated_input(
    "REAL_TWO_ITEM_SMOKE", study="pre_smoke", stage="real_model_smoke",
    roots=INPUT_ROOTS, materialization_root=DISCOVERY_MATERIALIZATION_ROOT,
)
PERMISSION_DATASET = discover_authenticated_input(
    "PRE_SMOKE_PERMISSIONS", stage="authorization", roots=INPUT_ROOTS,
    materialization_root=DISCOVERY_MATERIALIZATION_ROOT,
)
for discovered in (SMOKE_DATASET, PERMISSION_DATASET):
    DISCOVERED_PROVENANCE[discovered["role"]] = discovered
    print({key: discovered[key] for key in (
        "role", "provider", "study", "stage", "representation", "discovered_path",
        "materialized_root", "content_identity_sha256", "archive_sha256", "mirrors",
        "observed_mount", "observed_dataset_folder",
    )})
SMOKE_ROOT = pathlib.Path(SMOKE_DATASET["materialized_root"])
PERMISSION_ROOT = pathlib.Path(PERMISSION_DATASET["materialized_root"])
TASK_BUNDLE_MANIFEST = str(discover_unique_file(SMOKE_ROOT, "task_bundle_manifest.json"))
TASK_BUNDLE_ROOT = str(pathlib.Path(TASK_BUNDLE_MANIFEST).parent)
bundle_verification = verify_task_bundle(TASK_BUNDLE_ROOT, TASK_BUNDLE_MANIFEST)
TASK_BUNDLE_HASH = str(bundle_verification["bundle_hash"])
TASK_MANIFEST = str(pathlib.Path(bundle_verification["tasks_path"]).resolve())
active_tasks = [json.loads(line) for line in pathlib.Path(TASK_MANIFEST).read_text(
    encoding="utf-8").splitlines() if line]
if len(active_tasks) != 2:
    raise RuntimeError("KAGGLE_ZERO_EDIT_00C2_TASK_CARDINALITY_INVALID")

def unique_schema_file(root, schema, *, provider=None):
    matches = []
    for path in pathlib.Path(root).rglob("*.json"):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if value.get("schema") == schema and (provider is None or value.get("provider") == provider):
            matches.append(path.resolve())
    if len(matches) != 1:
        raise RuntimeError(
            f"KAGGLE_ZERO_EDIT_00C2_PERMISSION_ARTIFACT_INVALID: schema={schema} provider={provider} "
            f"matches={[str(path) for path in matches]}"
        )
    return matches[0]

MATRIX_AUTHORIZATION = str(unique_schema_file(
    PERMISSION_ROOT, "certvic.cvpr.matrix_authorization.v1"
))
PROVIDER_PERMISSION = str(unique_schema_file(
    PERMISSION_ROOT, "certvic.cvpr.provider_permission.v1", provider=PROVIDER
))
matrix_authorization = verify_matrix_authorization(MATRIX_AUTHORIZATION)
permission = verify_provider_permission(
    PROVIDER_PERMISSION, matrix=MATRIX_AUTHORIZATION, expected_provider=PROVIDER
)
if permission.get("runtime_class") != "REAL_MODEL_SMOKE":
    raise RuntimeError("KAGGLE_ZERO_EDIT_00C2_PERMISSION_CLASS_INVALID")

known_role_paths = {
    "task_bundle_manifest": pathlib.Path(TASK_BUNDLE_MANIFEST),
    "environment_lock": pathlib.Path(ENVIRONMENT_LOCK),
    "model_registry": pathlib.Path(MODEL_REGISTRY),
    "snapshot_manifest": pathlib.Path(SNAPSHOT_MANIFEST),
    "code_bundle": pathlib.Path(CODE_BUNDLE_PATH),
    "matrix_authorization": pathlib.Path(MATRIX_AUTHORIZATION),
}
search_roots = [PERMISSION_ROOT, SMOKE_ROOT, CONFIG_ROOT]
resolved_roles = {}
for role, expected_hash in sorted(permission["active_input_hashes"].items()):
    preferred = known_role_paths.get(role)
    if preferred is not None and preferred.is_file() and early_sha256(preferred) == expected_hash:
        matches = [preferred.resolve()]
    else:
        matches = sorted({
            path.resolve() for root in search_roots for path in root.rglob("*")
            if path.is_file() and not path.is_symlink() and early_sha256(path) == expected_hash
        })
    if len(matches) != 1:
        raise RuntimeError(
            f"KAGGLE_ZERO_EDIT_00C2_PERMISSION_BINDING_MISSING: role={role} "
            f"matches={[str(path) for path in matches]}"
        )
    resolved_roles[role] = str(matches[0])

required_roles = {
    "task_bundle_manifest", "freeze_manifest", "final_review", "smoke_gate",
    "environment_lock", "model_registry", "snapshot_manifest", "code_bundle",
    "study_config", "matrix_authorization",
}
if set(resolved_roles) != required_roles:
    raise RuntimeError("KAGGLE_ZERO_EDIT_00C2_PERMISSION_ROLE_MATRIX_INCOMPLETE")
FINAL_TASK_FREEZE = resolved_roles["freeze_manifest"]
FINAL_REVIEW_LEDGER = resolved_roles["final_review"]
SMOKE_GATE_JSON = resolved_roles["smoke_gate"]
STUDY_CONFIG = resolved_roles["study_config"]
RUN_TAG = str(permission["active_scalars"]["run_tag"])
STUDY = str(permission["study"])
if permission["active_scalars"].get("provider") != PROVIDER:
    raise RuntimeError("KAGGLE_ZERO_EDIT_00C2_PROVIDER_SCALAR_MISMATCH")
if permission["active_scalars"].get("schema_version") != SCHEMA_VERSION:
    raise RuntimeError("KAGGLE_ZERO_EDIT_00C2_SCHEMA_SCALAR_MISMATCH")
PROMPT_TEMPLATE_HASH = hashlib.sha256(PROMPT_TEMPLATE.encode("utf-8")).hexdigest()
if permission.get("prompt_template_hash") != PROMPT_TEMPLATE_HASH:
    raise RuntimeError("KAGGLE_ZERO_EDIT_00C2_PROMPT_HASH_MISMATCH")

permission_binding = derive_permission_binding(globals())
active_runtime_contract_input = {
    "study": STUDY, "runtime_class": "REAL_MODEL_SMOKE", "provider": PROVIDER,
    "model_id": MODEL_ID, "processor_id": PROCESSOR_ID,
    "model_commit": MODEL_COMMIT, "processor_commit": PROCESSOR_COMMIT,
    "model_snapshot_manifest_hash": SNAPSHOT_MANIFEST_HASH,
    "processor_snapshot_manifest_hash": SNAPSHOT_MANIFEST_HASH,
    "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
    "snapshot_contract": SNAPSHOT_CONTRACT,
    "environment_lock_hash": ENVIRONMENT_LOCK_HASH,
    "prompt_template_id": PROMPT_TEMPLATE_ID,
    "prompt_template_hash": PROMPT_TEMPLATE_HASH,
    "parser_version": PARSER_VERSION, "output_schema": SCHEMA_VERSION,
    "run_tag": RUN_TAG, "code_bundle_hash": CODE_BUNDLE_HASH, "seed": GLOBAL_SEED,
    "generation_parameters": {"do_sample": False, "max_new_tokens": 8},
}
active_run_contract = build_run_contract(
    active_runtime_contract_input,
    task_manifest_sha256=sha256_bytes(canonical_json_bytes(active_tasks)), strict=True,
)
checks = {
    "active_input_hashes": permission["active_input_hashes"] == permission_binding["input_hashes"],
    "active_scalars": permission["active_scalars"] == permission_binding["scalars"],
    "task_bundle_hash": permission["task_bundle_hash"] == TASK_BUNDLE_HASH,
    "environment_hash": permission["environment_hash"] == ENVIRONMENT_LOCK_HASH,
    "snapshot_hash": permission["snapshot_hash"] == SNAPSHOT_MANIFEST_HASH,
    "snapshot_root_hash": permission["snapshot_root_hash"] == SNAPSHOT_ROOT_HASH,
    "code_hash": permission["code_hash"] == CODE_BUNDLE_HASH,
    "prompt_template_hash": permission["prompt_template_hash"] == PROMPT_TEMPLATE_HASH,
    "run_contract_hash": permission["run_contract_hash"] == active_run_contract["run_contract_hash"],
    "parser_version": permission["parser_version"] == PARSER_VERSION,
}
if not all(checks.values()):
    raise RuntimeError(f"KAGGLE_ZERO_EDIT_00C2_PERMISSION_IDENTITY_MISMATCH: {checks}")
PROVIDER_PERMISSION_EVENTS = str(
    pathlib.Path(WORKING_ROOT) / f"{PROVIDER}_permission_events.jsonl"
)
state = provider_state(PROVIDER_PERMISSION_EVENTS, permission)
if state == "ISSUED":
    transition_provider_permission(
        permission, PROVIDER_PERMISSION_EVENTS, to_state="CLAIMED",
        actor=NOTEBOOK_NAME, detail={"binding_hash": permission_binding["binding_hash"]},
    )
elif state not in {"CLAIMED", "RUN_STARTED", "PACKAGING_FAILED"}:
    raise RuntimeError(f"KAGGLE_ZERO_EDIT_00C2_PERMISSION_NOT_RESUMABLE: state={state}")
ATTACHED_INPUT_HASHES.update({
    "snapshot": SNAPSHOT_DATASET["content_identity_sha256"],
    "smoke": SMOKE_DATASET["content_identity_sha256"],
    "permissions": PERMISSION_DATASET["content_identity_sha256"],
})
AUTHENTICATED_CONTENT_IDENTITIES.update({
    "snapshot": SNAPSHOT_DATASET["content_identity_sha256"],
    "tasks": SMOKE_DATASET["content_identity_sha256"],
    "permissions": PERMISSION_DATASET["content_identity_sha256"],
})
print({"permission_id": permission["permission_id"], "run_tag": RUN_TAG,
       "task_bundle_hash": TASK_BUNDLE_HASH, "resolved_permission_roles": resolved_roles})
'''


def _real_smoke_execution() -> str:
    return '''from certvic.cvpr.model_snapshot_manifest import verify_manifest
from certvic.cvpr.t4x2 import derive_seed_manifest, detect_topology, write_seed_manifest

snapshot = verify_manifest(
    MODEL_PATH, SNAPSHOT_MANIFEST,
    expected_model_id=MODEL_ID,
    expected_model_commit=MODEL_COMMIT,
    expected_processor_commit=PROCESSOR_COMMIT,
    expected_architecture=EXPECTED_ARCHITECTURE,
)
if not snapshot["passed"]:
    raise RuntimeError(f"KAGGLE_ZERO_EDIT_SNAPSHOT_INVALID: {snapshot['errors']}")
device_names = [row["name"] for row in hardware.get("gpus", [])]
T4_PLAN = detect_topology(
    device_names=device_names, allow_single_t4=ALLOW_SINGLE_GPU_FALLBACK
)
print(T4_PLAN.as_dict())

OUTPUT_DIR = str(pathlib.Path(WORKING_ROOT) / f"certvic_00c2_{PROVIDER}")
RUNTIME_CONFIG = str(pathlib.Path(WORKING_ROOT) / f"00C2_{PROVIDER}_runtime.json")
runtime = {
    **active_runtime_contract_input,
    "model_path": MODEL_PATH, "processor_path": PROCESSOR_PATH,
    "snapshot_root_hash": SNAPSHOT_ROOT_HASH,
    "snapshot_manifest_path": SNAPSHOT_MANIFEST,
    "expected_architecture": EXPECTED_ARCHITECTURE,
    "environment_lock_path": ENVIRONMENT_LOCK,
    "prompt_template": PROMPT_TEMPLATE,
    "strict_run_contract": True, "strict_permission_binding": True,
    "task_manifest": TASK_MANIFEST, "task_bundle_root": TASK_BUNDLE_ROOT,
    "task_bundle_manifest": TASK_BUNDLE_MANIFEST, "task_bundle_hash": TASK_BUNDLE_HASH,
    "output_dir": OUTPUT_DIR,
    "final_task_freeze": FINAL_TASK_FREEZE,
    "final_review_ledger": FINAL_REVIEW_LEDGER,
    "smoke_gate_json": SMOKE_GATE_JSON,
    "model_registry": MODEL_REGISTRY, "study_config": STUDY_CONFIG,
    "code_bundle": CODE_BUNDLE_PATH,
    "matrix_authorization": MATRIX_AUTHORIZATION,
    "execution_permission_id": permission["permission_id"],
    "execution_permission_signature": permission["content_signature_sha256"],
    "provider_permission_path": PROVIDER_PERMISSION,
    "provider_permission_events_path": PROVIDER_PERMISSION_EVENTS,
    "permission_binding": permission_binding,
    "notebook_name": NOTEBOOK_NAME,
    "canonical_smoke_destination": str(pathlib.Path(WORKING_ROOT) / CANONICAL_RETURN_ZIP),
    "defer_canonical_smoke_package": True,
}
output_root = pathlib.Path(OUTPUT_DIR)
output_root.mkdir(parents=True, exist_ok=True)
write_seed_manifest(output_root / "seed_manifest.json", derive_seed_manifest(
    global_seed=GLOBAL_SEED, study=STUDY, provider=PROVIDER, gpu_id=0, shard_id=0,
    task_ids=[str(row["item_id"]) for row in active_tasks], attempts=2,
))
(output_root / "environment_manifest.json").write_text(json.dumps({
    "schema": "certvic.cvpr.smoke_environment.v1",
    "environment_hash": ENVIRONMENT_LOCK_HASH,
    "environment_lock_hash": ENVIRONMENT_LOCK_HASH,
    "status": environment_verification["status"], "passed": True,
    "hardware": hardware, "network_used": False, "paper_evidence": False,
}, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
pathlib.Path(RUNTIME_CONFIG).write_text(
    json.dumps(runtime, indent=2, sort_keys=True) + "\\n", encoding="utf-8"
)
command = [
    sys.executable, "-m", "certvic.cvpr.worker", "--shard", "0", "--num-shards", "1",
    "--resume", "--batch-size", "2", "--oom-reduce-to-one", "--fail-closed",
    "--frozen-runtime-config", RUNTIME_CONFIG,
]
subprocess.run(command, check=True, env={**os.environ, "CUDA_VISIBLE_DEVICES": "0"})
subprocess.run([
    sys.executable, "-m", "certvic.cvpr.package_run",
    "--frozen-runtime-config", RUNTIME_CONFIG, "--expected-shards", "1",
], check=True)
canonical = pathlib.Path(WORKING_ROOT) / CANONICAL_RETURN_ZIP
if not canonical.is_file():
    raise RuntimeError(f"KAGGLE_ZERO_EDIT_CANONICAL_RETURN_MISSING: {CANONICAL_RETURN_ZIP}")
print(str(canonical))
print(f"DOWNLOAD_FILENAME={CANONICAL_RETURN_ZIP}")
print(f"LOCAL_DESTINATION={LOCAL_DESTINATION}")
print("RESUME_COMMAND=python3 scripts/run_all_cpu_workflows.py --resume")
'''


def _zero_edit_notebook(name: str, stage: str, provider: str) -> dict:
    cells = [
        _cell(
            "markdown",
            f"# {name}\n\n"
            "Generated zero-edit Kaggle runbook. Attach authenticated inputs under any account, "
            "dataset title, archive name, mount, or nesting; keep Internet off, choose the "
            "documented accelerator, and click Run All. "
            "NON_EVIDENCE_RUNTIME_SMOKE; paper_evidence=false.\n",
        ),
        _cell("code", _zero_edit_config(name, stage, provider)),
        _cell("code", _content_early_code_bootstrap()),
        _cell("code", _content_common_materialization()),
    ]
    if stage in {"snapshot_smoke", "real_model_smoke"}:
        cells.append(_cell("code", _content_snapshot_materialization(provider)))
    if stage == "real_model_smoke":
        cells.append(_cell("code", _real_smoke_inputs_and_permission()))
    cells.append(_cell("code", _offline_environment_cell(require_gpu=stage == "real_model_smoke")))
    if stage == "code_smoke":
        cells.append(_cell("code", _code_smoke_output()))
    elif stage == "snapshot_smoke":
        cells.append(_cell("code", _snapshot_smoke_output()))
    else:
        cells.append(_cell("code", _real_smoke_execution()))
    return {
        "cells": cells,
        "metadata": {
            "certvic": {
                "stage": stage, "provider": provider, "zero_edit": True,
                "content_discovery": True, "owner_binding": False,
                "filename_binding": False, "mount_binding": False,
                "paper_evidence": False,
            },
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _study_for_notebook(name: str, stage: str) -> str:
    if stage == "mock_smoke":
        return "synthetic_smoke"
    if name.startswith(("01_", "02_", "03_", "04_")):
        return "specificity_confirmatory_cvpr"
    if name.startswith(("10_", "11_", "12_", "13_")):
        return "main_study_cvpr"
    return "coco_object_presence"


def _universal_runtime_config(name: str, stage: str, provider: str) -> str:
    study = _study_for_notebook(name, stage)
    return_name = expected_return_zip(name, stage, provider)
    return f'''# Generated content-authenticated runtime identity. Nothing in this cell is editable.
import hashlib, json, os, pathlib, shutil, subprocess, sys

STAGE = {stage!r}
PROVIDER = {provider!r}
NOTEBOOK_NAME = {name!r}
STUDY = {study!r}
EXPECTED_GPUS = {0 if stage in {"code_smoke", "snapshot_smoke"} else 2}
ALLOW_SINGLE_GPU_FALLBACK = True
USE_REAL_MODEL = {stage in {"evaluation", "real_model_smoke"}!r}
MAX_ITEMS = 2
ALLOW_FULL_RUN = False
INITIAL_BATCH_SIZE = 4
GLOBAL_SEED = 12013
SCHEMA_VERSION = "certvic.cvpr.output.v2"
SNAPSHOT_CONTRACT = "UNIFIED_SNAPSHOT"
PROMPT_TEMPLATE_ID = "certification_yes_no_v1"
PROMPT_TEMPLATE = "{{prompt}}\\n"
PROMPT_TEMPLATE_HASH = hashlib.sha256(PROMPT_TEMPLATE.encode("utf-8")).hexdigest()
PARSER_VERSION = "certvic.parse.v2"
PRIMARY_PROVIDERS = ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]
CANONICAL_RETURN_ZIP = {return_name!r}
LOCAL_DESTINATION = {f"data/runtime/{return_name}"!r}
WORKING_ROOT = os.environ.get("CERTVIC_KAGGLE_WORKING_ROOT", "/kaggle/working")
INPUT_ROOTS = [value for value in os.environ.get("CERTVIC_INPUT_ROOTS", "").split(os.pathsep)
               if value] or ["/kaggle/input", "/kaggle/working"]
OUTPUT_DIR = str(pathlib.Path(WORKING_ROOT) / "certvic_cvpr")
RUNTIME_CONFIG = str(pathlib.Path(WORKING_ROOT) / "certvic_cvpr_runtime.json")
PROVIDER_PERMISSION_EVENTS = str(
    pathlib.Path(WORKING_ROOT) / f"{{PROVIDER}}_provider_permission_events.jsonl"
)
GENERATION_ENGINE = "structured_texture_patch"
SEMANTIC_ENGINE = "deterministic_preliminary"
INPAINTING_SNAPSHOT = None
INPAINTING_MANIFEST = None
ALLOW_USE_PREINSTALLED_ENVIRONMENT = True
REQUIRE_EXACT_ENVIRONMENT = True
def shard_for(item_id, n):
    return int(hashlib.sha256(str(item_id).encode("utf-8")).hexdigest(), 16) % n
for key, value in {{
    "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "DIFFUSERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1", "PIP_NO_INDEX": "1",
    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
}}.items():
    os.environ[key] = value
'''


def _universal_stage_discovery(name: str, stage: str, provider: str) -> str:
    study = _study_for_notebook(name, stage)
    if stage == "generation":
        role = "CONFIRMATORY_GENERATION_INPUT" if name.startswith("01_") else "GENERATION_INPUT"
        return f'''GENERATION_DATASET = discover_authenticated_input(
    {role!r}, provider="controls", study={study!r}, stage="generation",
    roots=INPUT_ROOTS, materialization_root=DISCOVERY_MATERIALIZATION_ROOT,
)
DISCOVERED_PROVENANCE["GENERATION_INPUT"] = GENERATION_DATASET
print({{key: GENERATION_DATASET[key] for key in (
    "role", "provider", "study", "stage", "representation", "discovered_path",
    "materialized_root", "content_identity_sha256", "archive_sha256", "mirrors",
    "observed_mount", "observed_dataset_folder",
)}})
GENERATION_ROOT = pathlib.Path(GENERATION_DATASET["materialized_root"])
EDIT_PLAN = str(discover_unique_file(GENERATION_ROOT, "source_manifest.jsonl"))
TASK_MANIFEST = EDIT_PLAN
TASK_BUNDLE_ROOT = str(GENERATION_ROOT)
TASK_BUNDLE_MANIFEST = str(GENERATION_ROOT / "bundle_manifest.json")
TASK_BUNDLE_HASH = GENERATION_DATASET["content_identity_sha256"]
RUN_TAG = f"{{STUDY}}_generation_{{TASK_BUNDLE_HASH[:12]}}"
MODEL_ID = "controls/no-model"
PROCESSOR_ID = MODEL_ID
MODEL_COMMIT = "0" * 40
PROCESSOR_COMMIT = "0" * 40
MODEL_PATH = str(GENERATION_ROOT)
PROCESSOR_PATH = MODEL_PATH
SNAPSHOT_MANIFEST = TASK_BUNDLE_MANIFEST
SNAPSHOT_MANIFEST_HASH = GENERATION_DATASET["manifest_sha256"]
SNAPSHOT_ROOT_HASH = TASK_BUNDLE_HASH
EXPECTED_ARCHITECTURE = "NO_MODEL_GENERATION_CONTROLS"
FINAL_TASK_FREEZE = None
FINAL_REVIEW_LEDGER = None
DETECTABILITY_GATE = None
SMOKE_GATE_JSON = None
MATRIX_AUTHORIZATION = None
PROVIDER_PERMISSION = None
STUDY_CONFIG = None
ATTACHED_INPUT_HASHES["tasks"] = TASK_BUNDLE_HASH
AUTHENTICATED_CONTENT_IDENTITIES["tasks"] = TASK_BUNDLE_HASH
'''
    if stage == "evaluation":
        return _content_snapshot_materialization(provider) + f'''
SCIENTIFIC_DATASET = discover_authenticated_input(
    "SCIENTIFIC_PROVIDER_INPUT", provider={provider!r}, study={study!r}, stage="evaluation",
    roots=INPUT_ROOTS, materialization_root=DISCOVERY_MATERIALIZATION_ROOT,
)
DISCOVERED_PROVENANCE["SCIENTIFIC_PROVIDER_INPUT"] = SCIENTIFIC_DATASET
print({{key: SCIENTIFIC_DATASET[key] for key in (
    "role", "provider", "study", "stage", "representation", "discovered_path",
    "materialized_root", "content_identity_sha256", "archive_sha256", "mirrors",
    "observed_mount", "observed_dataset_folder",
)}})
SCIENTIFIC_ROOT = pathlib.Path(SCIENTIFIC_DATASET["materialized_root"])
binding_candidates = []
for candidate in SCIENTIFIC_ROOT.rglob("*.json"):
    if candidate.is_symlink() or not candidate.is_file():
        continue
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        continue
    if value.get("schema") == "certvic.kaggle.scientific_input_binding.v1":
        binding_candidates.append((candidate.resolve(), value))
if len(binding_candidates) != 1:
    raise RuntimeError("CERTVIC_DISCOVERY_03_CONTENT_AUTHENTICATION_FAILED: scientific binding")
SCIENTIFIC_BINDING_PATH, scientific_binding = binding_candidates[0]
if (scientific_binding.get("provider") != PROVIDER
        or scientific_binding.get("study") != STUDY):
    raise RuntimeError("CERTVIC_DISCOVERY_03_CONTENT_AUTHENTICATION_FAILED: scientific identity")
BOUND_ROLES = resolve_content_bound_roles(
    SCIENTIFIC_ROOT, scientific_binding["role_sha256"]
)
FINAL_TASK_FREEZE = BOUND_ROLES["task_freeze"]
FINAL_REVIEW_LEDGER = BOUND_ROLES["review_ledger"]
DETECTABILITY_GATE = BOUND_ROLES["detectability_gate"]
SMOKE_GATE_JSON = BOUND_ROLES["smoke_gate"]
ENVIRONMENT_LOCK = BOUND_ROLES["environment_lock"]
ENVIRONMENT_LOCK_HASH = early_sha256(ENVIRONMENT_LOCK)
MODEL_REGISTRY = BOUND_ROLES["model_registry"]
MATRIX_AUTHORIZATION = BOUND_ROLES["parent_authorization"]
PROVIDER_PERMISSION = BOUND_ROLES["child_permission"]
RUN_TAG = str(scientific_binding["run_tag"])
TASK_BUNDLE_MANIFEST = BOUND_ROLES["task_bundle"]
TASK_BUNDLE_ROOT = str(pathlib.Path(TASK_BUNDLE_MANIFEST).parent)
from certvic.cvpr.task_bundle import verify_bundle as verify_task_bundle
bundle_verification = verify_task_bundle(TASK_BUNDLE_ROOT, TASK_BUNDLE_MANIFEST)
TASK_BUNDLE_HASH = str(bundle_verification["bundle_hash"])
TASK_MANIFEST = str(pathlib.Path(bundle_verification["tasks_path"]).resolve())
active_tasks = [json.loads(line) for line in pathlib.Path(TASK_MANIFEST).read_text(
    encoding="utf-8").splitlines() if line]
STUDY_CONFIG = str(next(path for path in CONFIG_ROOT.rglob("*.yaml")
                        if path.is_file() and STUDY in path.read_text(encoding="utf-8")))
AUTHENTICATED_CONTENT_IDENTITIES.update({{
    "snapshot": SNAPSHOT_DATASET["content_identity_sha256"],
    "permissions": SCIENTIFIC_DATASET["content_identity_sha256"],
    "code_bundle": CODE_BUNDLE_HASH,
}})
ATTACHED_INPUT_HASHES.update({{
    "snapshot": SNAPSHOT_DATASET["content_identity_sha256"],
    "permissions": SCIENTIFIC_DATASET["content_identity_sha256"],
}})
'''
    return '''SYNTHETIC_DATASET = discover_authenticated_input(
    "SYNTHETIC_VALIDATION", roots=INPUT_ROOTS,
    materialization_root=DISCOVERY_MATERIALIZATION_ROOT,
)
DISCOVERED_PROVENANCE["SYNTHETIC_VALIDATION"] = SYNTHETIC_DATASET
print({key: SYNTHETIC_DATASET[key] for key in (
    "role", "provider", "study", "stage", "representation", "discovered_path",
    "materialized_root", "content_identity_sha256", "archive_sha256", "mirrors",
    "observed_mount", "observed_dataset_folder",
)})
SYNTHETIC_ROOT = pathlib.Path(SYNTHETIC_DATASET["materialized_root"])
TASK_MANIFEST = str(discover_unique_file(SYNTHETIC_ROOT, "smoke_tasks.jsonl"))
TASK_BUNDLE_ROOT = str(SYNTHETIC_ROOT)
TASK_BUNDLE_MANIFEST = str(SYNTHETIC_ROOT / "bundle_manifest.json")
TASK_BUNDLE_HASH = SYNTHETIC_DATASET["content_identity_sha256"]
EDIT_PLAN = TASK_MANIFEST
RUN_TAG = f"synthetic_smoke_{TASK_BUNDLE_HASH[:12]}"
MODEL_ID = "synthetic/mock"
PROCESSOR_ID = MODEL_ID
MODEL_COMMIT = "0" * 40
PROCESSOR_COMMIT = "0" * 40
MODEL_PATH = str(SYNTHETIC_ROOT)
PROCESSOR_PATH = MODEL_PATH
SNAPSHOT_MANIFEST = TASK_BUNDLE_MANIFEST
SNAPSHOT_MANIFEST_HASH = SYNTHETIC_DATASET["manifest_sha256"]
SNAPSHOT_ROOT_HASH = TASK_BUNDLE_HASH
EXPECTED_ARCHITECTURE = "SYNTHETIC_MOCK"
FINAL_TASK_FREEZE = None
FINAL_REVIEW_LEDGER = None
DETECTABILITY_GATE = None
SMOKE_GATE_JSON = None
MATRIX_AUTHORIZATION = None
PROVIDER_PERMISSION = None
STUDY_CONFIG = None
ATTACHED_INPUT_HASHES["tasks"] = TASK_BUNDLE_HASH
AUTHENTICATED_CONTENT_IDENTITIES["tasks"] = TASK_BUNDLE_HASH
'''


def _universal_bootstrap(name: str, stage: str, provider: str) -> str:
    return (
        _content_early_code_bootstrap()
        + "\n"
        + _content_common_materialization()
        + "\n"
        + _universal_stage_discovery(name, stage, provider)
    )


def notebook(name: str, stage: str, provider: str) -> dict:
    if stage in {"code_smoke", "snapshot_smoke", "real_model_smoke"}:
        return _zero_edit_notebook(name, stage, provider)
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
    # The legacy hand-filled strings above remain source-compatible reference
    # material only.  Every generated active runbook uses authenticated,
    # account-independent content discovery.
    config = _universal_runtime_config(name, stage, provider)
    bootstrap = _universal_bootstrap(name, stage, provider)
    preflight = '''import certvic
from certvic.cvpr.contracts import canonical_json_bytes, sha256_bytes
from certvic.cvpr.environment_lock import (
    offline_environment_flags, prepare_offline_environment,
)
from certvic.cvpr.notebook_bootstrap import configure_offline_environment
from certvic.cvpr.notebook_permission_binding import derive_permission_binding
from certvic.cvpr.reconcile_provider_permissions import (
    transition_provider_permission, verify_matrix_authorization, verify_provider_permission,
)
from certvic.cvpr.run_contract import build_run_contract
from certvic.cvpr.runtime_preflight import hardware_report
from certvic.cvpr.schema_contract import OUTPUT_SCHEMA
from certvic.cvpr.smoke_gate import require_scientific_run_gate
from certvic.cvpr.t4x2 import derive_seed_manifest, detect_topology, write_seed_manifest

PACKAGE_SOURCE_HASH = hashlib.sha256((PROJECT_ROOT / "certvic/__init__.py").read_bytes()).hexdigest()
print({"certvic_source": certvic.__file__, "package_source_hash": PACKAGE_SOURCE_HASH})
configure_offline_environment()
if environment_lock_hash(ENVIRONMENT_LOCK) != ENVIRONMENT_LOCK_HASH:
    raise RuntimeError("environment lock hash mismatch")
if (offline_environment_flags().get("HF_HUB_OFFLINE") != "1"
        or offline_environment_flags().get("PIP_NO_INDEX") != "1"):
    raise RuntimeError("offline environment flag contract is incomplete")
if SCHEMA_VERSION != OUTPUT_SCHEMA:
    raise RuntimeError(f"mixed output schema prohibited: {SCHEMA_VERSION} != {OUTPUT_SCHEMA}")
if any(len(str(identity)) != 64 for identity in ATTACHED_INPUT_HASHES.values()):
    raise RuntimeError("CERTVIC_DISCOVERY_03_CONTENT_AUTHENTICATION_FAILED: invalid content identity")
if any(record.get("discovery_policy") != "CONTENT_AUTHENTICATED_ANY_LOCATION"
       for record in DISCOVERED_PROVENANCE.values()):
    raise RuntimeError("CERTVIC_DISCOVERY_03_CONTENT_AUTHENTICATION_FAILED: discovery policy drift")

# Evaluation permission verification and nonce claim occur before hardware inspection,
# snapshot/model access, CUDA access, adapter creation, or scientific output creation.
if STAGE == "evaluation":
    matrix_authorization = verify_matrix_authorization(MATRIX_AUTHORIZATION)
    require_scientific_run_gate(SMOKE_GATE_JSON, PRIMARY_PROVIDERS)
    permission_binding = derive_permission_binding(globals())
    active_runtime_contract_input = {
        "study": STUDY, "runtime_class": "SCIENTIFIC_RUN", "provider": PROVIDER,
        "model_id": MODEL_ID, "processor_id": PROCESSOR_ID,
        "model_commit": MODEL_COMMIT, "processor_commit": PROCESSOR_COMMIT,
        "model_snapshot_manifest_hash": SNAPSHOT_MANIFEST_HASH,
        "processor_snapshot_manifest_hash": SNAPSHOT_MANIFEST_HASH,
        "snapshot_status": "LOCAL_SNAPSHOT_BYTES_VERIFIED",
        "snapshot_contract": SNAPSHOT_CONTRACT,
        "environment_lock_hash": ENVIRONMENT_LOCK_HASH,
        "prompt_template_id": PROMPT_TEMPLATE_ID,
        "prompt_template_hash": PROMPT_TEMPLATE_HASH,
        "parser_version": PARSER_VERSION, "output_schema": SCHEMA_VERSION,
        "run_tag": RUN_TAG, "code_bundle_hash": CODE_BUNDLE_HASH,
        "seed": GLOBAL_SEED,
        "generation_parameters": {"do_sample": False, "temperature": 0.0,
                                  "max_new_tokens": 16},
    }
    active_run_contract = build_run_contract(
        active_runtime_contract_input,
        task_manifest_sha256=sha256_bytes(canonical_json_bytes(active_tasks)), strict=True,
    )
    permission = verify_provider_permission(
        PROVIDER_PERMISSION, matrix=matrix_authorization,
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
            or permission["parser_version"] != PARSER_VERSION):
        raise RuntimeError("provider permission differs from authenticated runtime identity")
    permission_claim = transition_provider_permission(
        permission, PROVIDER_PERMISSION_EVENTS, to_state="CLAIMED",
        actor=NOTEBOOK_NAME, detail={"binding_hash": permission_binding["binding_hash"]},
    )

if STAGE in {"evaluation", "snapshot_smoke", "real_model_smoke"}:
    if any(value in {None, ""} for value in
           [MODEL_COMMIT, PROCESSOR_COMMIT, MODEL_PATH, SNAPSHOT_MANIFEST,
            SNAPSHOT_MANIFEST_HASH, EXPECTED_ARCHITECTURE]):
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

environment_verification = prepare_offline_environment(
    ENVIRONMENT_LOCK, wheelhouse=WHEELHOUSE_PATH, wheelhouse_manifest=WHEELHOUSE_MANIFEST,
    allow_preinstalled=ALLOW_USE_PREINSTALLED_ENVIRONMENT,
    require_exact=REQUIRE_EXACT_ENVIRONMENT,
    require_cuda=STAGE in {"generation", "evaluation", "real_model_smoke"},
)
if environment_verification["status"] not in {
    "EXACT_PREINSTALLED_ENVIRONMENT_ACCEPTED",
    "OFFLINE_WHEELHOUSE_INSTALLED_AND_VERIFIED",
}:
    raise RuntimeError("exact offline environment was not established")

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
        if not INPAINTING_SNAPSHOT or not INPAINTING_MANIFEST:
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
        _cell(
            "markdown",
            f"# {name}\n\nAuthenticated content is discovered under any account, name, mount, "
            "archive extension, or nesting. No runtime path or identity edits are accepted. "
            "NON_EVIDENCE_RUNTIME_SMOKE or PLANNED_NOT_EXECUTED; paper_evidence=false.\n",
        ),
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
            "certvic": {
                "stage": stage, "provider": provider, "zero_edit": True,
                "content_discovery": True, "owner_binding": False,
                "filename_binding": False, "mount_binding": False,
                "paper_evidence": False,
            },
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
        "00B_certvic_model_snapshot_smoke.ipynb",
        "00C_certvic_adapter_two_item_smoke.ipynb",
        "00C1_certvic_synthetic_mock_runtime_smoke.ipynb",
        "00C2_certvic_real_model_two_item_smoke.ipynb",
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
