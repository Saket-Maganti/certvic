"""Canonical provider input builder for confirmatory, Main, and COCO runs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from certvic.cvpr.kaggle_bundle import build_bundle


PROVIDERS = ("qwen", "internvl", "llava")
PROVIDER_IDS = {
    "qwen": "qwen2_5_vl_7b",
    "internvl": "internvl_8b",
    "llava": "llava_onevision_7b",
}
STUDIES: dict[str, dict[str, str]] = {
    "confirmatory": {"study": "specificity_confirmatory_cvpr", "directory": "06_confirmatory_runs"},
    "main": {"study": "main_study_cvpr", "directory": "08_main_runs"},
    "coco": {"study": "coco_object_presence", "directory": "10_coco_runs"},
}
NOTEBOOKS = {
    ("confirmatory", "qwen"): "02_qwen_specificity_confirmatory_T4x2.ipynb",
    ("confirmatory", "internvl"): "03_internvl_specificity_confirmatory_T4x2.ipynb",
    ("confirmatory", "llava"): "04_llava_specificity_confirmatory_T4x2.ipynb",
    ("main", "qwen"): "11_qwen_main_study_T4x2.ipynb",
    ("main", "internvl"): "12_internvl_main_study_T4x2.ipynb",
    ("main", "llava"): "13_llava_main_study_T4x2.ipynb",
    ("coco", "qwen"): "21_second_domain_qwen_T4x2.ipynb",
    ("coco", "internvl"): "22_second_domain_internvl_T4x2.ipynb",
    ("coco", "llava"): "23_second_domain_llava_T4x2.ipynb",
}
REQUIRED_ROLES = (
    "task_bundle", "task_freeze", "review_ledger", "detectability_gate", "environment_lock",
    "model_registry", "snapshot_manifest", "code_bundle", "prompt_contract", "run_contract",
    "parent_authorization", "child_permission", "output_schema",
)


class ScientificInputBuilderError(ValueError):
    """Scientific inputs or their prospective authorization binding are incomplete."""


def _load(path: Path) -> Any:
    if path.suffix in {".yaml", ".yml"}:
        import yaml
        return yaml.safe_load(path.read_text())
    try:
        return json.loads(path.read_text())
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def build_scientific_input(
    study: str,
    provider: str,
    roles: Mapping[str, str | Path],
    *,
    run_tag: str,
    output: str | Path | None = None,
    synthetic_fixture: bool = False,
) -> dict[str, Any]:
    if study not in STUDIES or provider not in PROVIDERS:
        raise ScientificInputBuilderError("unknown study/provider")
    missing = sorted(set(REQUIRED_ROLES) - set(roles))
    if missing:
        raise ScientificInputBuilderError(f"missing scientific roles: {missing}")
    paths = {role: Path(value).resolve() for role, value in roles.items()}
    absent = sorted(role for role, path in paths.items() if not path.is_file() or path.is_symlink())
    if absent:
        raise ScientificInputBuilderError(f"missing or symlinked scientific inputs: {absent}")
    provider_id = PROVIDER_IDS[provider]
    parent = _load(paths["parent_authorization"])
    child = _load(paths["child_permission"])
    if not isinstance(parent, dict) or not isinstance(child, dict):
        raise ScientificInputBuilderError("authorization and child permission must be structured")
    if child.get("provider") not in {provider, provider_id}:
        raise ScientificInputBuilderError("child permission provider mismatch")
    if not synthetic_fixture and parent.get("execution_allowed") is not True:
        raise ScientificInputBuilderError("parent authorization does not allow execution")
    if not synthetic_fixture and (parent.get("synthetic_fixture") is True or child.get("synthetic_fixture") is True):
        raise ScientificInputBuilderError("synthetic permissions cannot authorize a real scientific run")
    hashes = {role: hashlib.sha256(path.read_bytes()).hexdigest() for role, path in sorted(paths.items())}
    binding = {
        "schema": "certvic.kaggle.scientific_input_binding.v1",
        "study": STUDIES[study]["study"],
        "provider": provider_id,
        "run_tag": run_tag,
        "role_sha256": hashes,
        "synthetic_fixture": bool(synthetic_fixture),
        "paper_evidence": False,
    }
    files: dict[str, Path | bytes] = {
        f"inputs/{role}{path.suffix.lower() or '.bin'}": path for role, path in sorted(paths.items())
    }
    files["scientific_input_binding.json"] = (
        json.dumps(binding, indent=2, sort_keys=True) + "\n"
    ).encode()
    filename = f"certvic_{study}_{provider}_input.zip"
    destination = Path(output) if output else Path("kaggle_uploads") / STUDIES[study]["directory"] / filename
    slug = f"certvic/certvic-{study}-{provider}-input"
    return build_bundle(
        destination,
        files,
        bundle_type=f"{study.upper()}_SCIENTIFIC_PROVIDER_INPUT",
        study=STUDIES[study]["study"],
        stage="evaluation",
        provider=provider_id,
        required_notebook=NOTEBOOKS[(study, provider)],
        dataset_slug=slug,
        mount_path=f"/kaggle/input/{slug.split('/', 1)[1]}",
        external_dependency_status="UPSTREAM_GATES_AND_BYTES_VERIFIED" if not synthetic_fixture else "SYNTHETIC_PROOF_ONLY",
        evidence_class="PROSPECTIVE_SCIENTIFIC_INPUT" if not synthetic_fixture else "SYNTHETIC_FIXTURE",
        builder_command=(
            "python3 -m certvic.cvpr.scientific_input_builder "
            f"--study {study} --provider {provider} --config <ROLE_CONFIG_JSON> --run-tag {run_tag}"
        ),
        readme=(
            f"# CertVIC {study} / {provider_id} scientific input\n\n"
            "All task, review, environment, snapshot, code, prompt, run-contract, and authorization "
            "roles are individually hash-bound. The notebook must reject any active-byte mismatch."
        ),
        extra_manifest={"run_tag": run_tag, "role_sha256": hashes, "synthetic_fixture": bool(synthetic_fixture)},
    )


def status(study: str, provider: str) -> dict[str, Any]:
    gate_status = "BLOCKED_BY_UPSTREAM_GATE"
    if study == "main":
        gate_status = "CONDITIONAL_ON_CONFIRMATORY"
    return {
        "status": gate_status,
        "study": study,
        "provider": provider,
        "required_roles": list(REQUIRED_ROLES),
        "builder_command": (
            "python3 -m certvic.cvpr.scientific_input_builder "
            f"--study {study} --provider {provider} --config <ROLE_CONFIG_JSON> --run-tag <RUN_TAG>"
        ),
        "output": f"kaggle_uploads/{STUDIES[study]['directory']}/certvic_{study}_{provider}_input.zip",
        "expected_size": "1 MB-25 GB depending on redistributable task-bundle bytes",
        "paper_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", choices=sorted(STUDIES), required=True)
    parser.add_argument("--provider", choices=PROVIDERS, required=True)
    parser.add_argument("--config")
    parser.add_argument("--run-tag")
    parser.add_argument("--output")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    if args.status or not args.config:
        result = status(args.study, args.provider)
    else:
        if not args.run_tag:
            parser.error("--run-tag is required for a build")
        config = json.loads(Path(args.config).read_text())
        result = build_scientific_input(
            args.study,
            args.provider,
            config["roles"],
            run_tag=args.run_tag,
            output=args.output,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
