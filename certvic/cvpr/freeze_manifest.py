"""Hash-lock study, model, analysis, and review pre-execution contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from certvic.cvpr.contracts import load_yaml, unresolved_freeze_fields
from certvic.cvpr.human_review import JUDGMENT_FIELDS, SEMANTIC_JUDGMENT_FIELDS


def build_freeze_manifest(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    paths = {
        "protocol_authority": root / "configs/studies/certvic_confirmatory_authority.json",
        "primary_analysis": root / "configs/statistics/certvic_confirmatory_primary_analysis.json",
        "confirmatory_study": root / "configs/studies/specificity_confirmatory_cvpr.yaml",
        "main_study": root / "configs/studies/main_study_cvpr.yaml",
        "coco_feasibility": root / "configs/studies/second_domain_cvpr.yaml",
        "model_matrix": root / "configs/models/certvic_cvpr_model_registry.yaml",
        "environment": root / "configs/runtime/kaggle_t4x2_environment.lock.json",
    }
    records: dict[str, Any] = {}
    unresolved: dict[str, list[str]] = {}
    for role, path in paths.items():
        if not path.is_file():
            raise ValueError(f"missing freeze input: {path}")
        records[role] = {"path": path.relative_to(root).as_posix(),
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        if path.suffix in {".yaml", ".yml"}:
            fields = unresolved_freeze_fields(load_yaml(path))
            if fields:
                unresolved[role] = fields
    analysis_plan = {
        "primary_endpoint": "SEMANTIC_UPDATE_SUCCESS",
        "specificity_failure": "IRRELEVANT_FLIP",
        "missing_policy": "RELEVANT_UPDATE_FAILURE_IRRELEVANT_FLIP",
        "primary_intervals": "FIXED_SAMPLE_ONE_SIDED_CLOPPER_PEARSON",
        "certificate": "RESPONSIVENESS_LOWER_GTE_0.50_AND_SPECIFICITY_UPPER_LTE_0.10",
        "multiplicity": "BONFERRONI_THREE_MODELS_BY_TWO_GATES",
        "confidence_sequences": "SECONDARY_OPERATIONAL_ONLY",
        "legacy_gap": "SECONDARY_DESCRIPTIVE_NOT_A_CERTIFICATE",
        "human_filter": "FINAL_ADJUDICATED_INCLUSION",
        "paper_promotion": "SEPARATE_CLAIM_GATE_REQUIRED",
    }
    review_rules = {
        "specificity_fields": list(JUDGMENT_FIELDS),
        "semantic_fields": list(SEMANTIC_JUDGMENT_FIELDS),
        "raters": 2, "distinct_identities": True, "adjudication": "OUTCOME_BLIND",
    }
    for role, payload in (("analysis_plan", analysis_plan), ("human_review_rules", review_rules)):
        raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
        records[role] = {"inline_contract": payload, "sha256": hashlib.sha256(raw).hexdigest()}
    return {
        "schema": "certvic.cvpr.pre_execution_freeze_manifest.v1",
        "status": ("HASH_LOCKED_WITH_EXTERNAL_FIELDS_UNRESOLVED" if unresolved
                   else "FULLY_HASH_LOCKED"),
        "contracts": records, "unresolved_external_fields": unresolved,
        "signature_type": "SHA256_CONTENT_LOCK_NOT_CRYPTOGRAPHIC_IDENTITY_SIGNATURE",
        "paper_evidence": False,
    }
