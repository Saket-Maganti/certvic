"""Licensed external-byte input builder for Main and COCO generation notebooks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from certvic.cvpr.kaggle_bundle import build_bundle


STUDIES = {
    "main": {
        "study": "main_study_cvpr",
        "notebook": "10_main_study_generation_T4x2.ipynb",
        "output": "kaggle_uploads/07_main/certvic_main_generation_input.zip",
        "slug": "certvic/certvic-main-generation-input",
    },
    "coco": {
        "study": "coco_object_presence",
        "notebook": "20_second_domain_generation_T4x2.ipynb",
        "output": "kaggle_uploads/09_coco/certvic_coco_generation_input.zip",
        "slug": "certvic/certvic-coco-generation-input",
    },
}
REQUIRED_ROLES = (
    "source_manifest", "exclusion_inventory", "generation_config", "licenses",
    "engine_policy", "seed_plan", "shard_plan", "resume_ledger",
)


class GenerationInputBuilderError(ValueError):
    """External generation sources are incomplete or unlicensed."""


def _rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line]
    value = json.loads(path.read_text())
    return value if isinstance(value, list) else value.get("items", [])


def build_generation_input(
    study: str,
    roles: Mapping[str, str | Path],
    *,
    output: str | Path | None = None,
    synthetic_fixture: bool = False,
) -> dict[str, Any]:
    if study not in STUDIES:
        raise GenerationInputBuilderError(f"unknown generation study: {study}")
    missing = sorted(set(REQUIRED_ROLES) - set(roles))
    if missing:
        raise GenerationInputBuilderError(f"missing generation roles: {missing}")
    paths = {role: Path(value).resolve() for role, value in roles.items()}
    absent = sorted(role for role, path in paths.items() if not path.is_file() or path.is_symlink())
    if absent:
        raise GenerationInputBuilderError(f"missing or symlinked generation inputs: {absent}")
    source_rows = _rows(paths["source_manifest"])
    if not source_rows:
        raise GenerationInputBuilderError("source manifest is empty")
    files: dict[str, Path | bytes] = {}
    portable: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in source_rows:
        item_id = str(row.get("item_id") or row.get("source_image_id") or "")
        if not item_id or item_id in seen:
            raise GenerationInputBuilderError("source identities must be present and unique")
        seen.add(item_id)
        if row.get("license_eligible") is not True or not row.get("license_id"):
            raise GenerationInputBuilderError(f"source {item_id} lacks verified licensing")
        if not synthetic_fixture and row.get("synthetic_fixture") is True:
            raise GenerationInputBuilderError("synthetic source prohibited in a real generation input")
        rewritten = dict(row)
        for role in ("source_image_path", "annotation_path", "mask_path", "insertion_asset_path"):
            raw = row.get(role)
            if not raw:
                if role == "source_image_path":
                    raise GenerationInputBuilderError(f"source {item_id} lacks image bytes")
                continue
            source = Path(raw).resolve()
            if not source.is_file() or source.is_symlink():
                raise GenerationInputBuilderError(f"source asset missing or symlinked: {source}")
            archive_name = f"assets/{item_id}/{role.removesuffix('_path')}{source.suffix.lower()}"
            files[archive_name] = source
            rewritten[role] = archive_name
            rewritten[role.removesuffix("_path") + "_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        rewritten["synthetic_fixture"] = bool(synthetic_fixture)
        rewritten["paper_evidence"] = False
        portable.append(rewritten)
    files["controls/source_manifest.jsonl"] = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
        for row in sorted(portable, key=lambda row: str(row.get("item_id") or row.get("source_image_id")))
    )
    for role, path in sorted(paths.items()):
        if role != "source_manifest":
            files[f"controls/{role}{path.suffix.lower() or '.bin'}"] = path
    spec = STUDIES[study]
    destination = Path(output) if output else Path(spec["output"])
    return build_bundle(
        destination,
        files,
        bundle_type=f"{study.upper()}_GENERATION_INPUT",
        study=spec["study"],
        stage="generation",
        provider="controls",
        required_notebook=spec["notebook"],
        dataset_slug=spec["slug"],
        mount_path=f"/kaggle/input/{spec['slug'].split('/', 1)[1]}",
        external_dependency_status="EXTERNAL_BYTES_VERIFIED" if not synthetic_fixture else "SYNTHETIC_PROOF_ONLY",
        evidence_class="PROSPECTIVE_GENERATION_INPUT" if not synthetic_fixture else "SYNTHETIC_FIXTURE",
        builder_command=(
            "python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots "
            "<EXTERNAL_ROOTS_YAML>"
        ),
        readme=(
            f"# CertVIC {study} generation input\n\nAll source, annotation, mask, insertion, "
            "license, seed, shard, engine, exclusion, and resume controls are portable and hash-bound."
        ),
        extra_manifest={"synthetic_fixture": bool(synthetic_fixture)},
    )


def status(study: str) -> dict[str, Any]:
    base = "CONDITIONAL_ON_CONFIRMATORY" if study == "main" else "BLOCKED_BY_UPSTREAM_GATE"
    return {
        "status": base,
        "study": study,
        "required_roles": list(REQUIRED_ROLES),
        "builder_command": (
            "python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots "
            "<EXTERNAL_ROOTS_YAML>"
        ),
        "output": STUDIES[study]["output"],
        "expected_size": "1-60 GB depending on the frozen licensed source universe",
        "paper_evidence": False,
    }
