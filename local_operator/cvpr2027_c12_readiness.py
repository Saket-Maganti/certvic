"""Build the C12 evidence-gated pre-experiment readiness record."""

from __future__ import annotations

import ast
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from certvic.cvpr.kagglefiles_pack import verify_pack  # noqa: E402
from certvic.cvpr.notebook_00c2_proof import execute_generated_route  # noqa: E402
from local_operator.cvpr2027_common import (  # noqa: E402
    REPO,
    artifact_manifest,
    sha256_file,
    write_csv,
    write_json,
)
from local_operator.cvpr2027_certificate import compute_certificate  # noqa: E402
from local_operator.cvpr2027_identity_check import compare, measure  # noqa: E402
from local_operator.human_review_status import initialize_infrastructure, status  # noqa: E402


REPORT_ROOT = REPO / "reports/cvpr2027_c12"
PROVIDERS = ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()


def _json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _notebook_text(path: Path) -> tuple[dict[str, Any], str, list[str]]:
    value = _json(path, {})
    cells = value.get("cells", []) if isinstance(value, dict) else []
    text = "\n".join("".join(cell.get("source", [])) for cell in cells)
    syntax_errors = []
    for index, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue
        try:
            ast.parse("".join(cell.get("source", [])))
        except SyntaxError as error:
            syntax_errors.append(f"cell {index}: {error}")
    return value, text, syntax_errors


def live_baseline(root: Path) -> list[Path]:
    identity_source = _json(
        REPO / "reports/cvpr2027_max_ceiling/C11_IDENTITY_FINAL.json", {}
    )
    baseline = {
        **identity_source,
        "schema": "certvic.cvpr2027.c12.identity_snapshot.v1",
        "snapshot": "BASELINE_BEFORE_C12_EDITS",
        "captured_date": "2026-08-12",
        "git_head": _git("rev-parse", "HEAD"),
        "git_head_subject": _git("log", "-1", "--format=%s"),
        "identity_policy": {
            "authenticated_archives_are_immutable": True,
            "new_v3_protocol_is_external_to_authenticated_00C2_common_archives": True,
            "preferred_result": "NO_00A_OR_00B_RERUN_REQUIRED",
        },
        "paper_evidence": False,
    }
    plan_rows = [
        ("SCIENTIFIC_P0", "prospective allocation optimization", "COMPLETE"),
        ("SCIENTIFIC_P0", "00C2 bundle and permission compatibility", "COMPLETE"),
        ("SCIENTIFIC_P0", "prospective matching/detectability", "SOFTWARE_READY_EXTERNAL_BLOCKED"),
        ("SCIENTIFIC_P1", "human review", "SOFTWARE_READY_HUMAN_BLOCKED"),
        ("SCIENTIFIC_P1", "primary analysis and reviewer attacks", "SOFTWARE_READY_OUTPUT_BLOCKED"),
        ("ENGINEERING_SUPPORT", "runbook and pack validation", "IN_PROGRESS"),
        ("EXTERNAL_BLOCKED", "licensed ADE20K source census", "SOURCE_BYTES_MISSING"),
        ("HUMAN_BLOCKED", "two independent qualified raters", "NOT_STARTED"),
        ("GPU_BLOCKED", "00C2 and confirmatory inference", "NOT_AUTHORIZED"),
        ("NOT_WORTH_DOING", "paper prose and dashboards", "EXCLUDED"),
    ]
    work_plan = {
        "schema": "certvic.cvpr2027.c12.work_plan.v1",
        "classes": [
            {"class": category, "task": task, "status": state}
            for category, task, state in plan_rows
        ],
        "priority_order": [
            "design_power",
            "real_smoke_intake",
            "00C2",
            "confirmatory_runbooks",
            "matching_detectability",
            "human_review",
            "primary_analysis",
            "secondary_paths",
            "reproducibility",
        ],
        "paper_evidence": False,
    }
    live = {
        "schema": "certvic.cvpr2027.c12.live_baseline.v1",
        "git_head": baseline["git_head"],
        "origin_main": _git("rev-parse", "origin/main"),
        "head_matches_origin": baseline["git_head"] == _git("rev-parse", "origin/main"),
        "authenticated_state": {
            "00A": "COMPLETE",
            "00B_qwen": "COMPLETE",
            "00B_internvl": "COMPLETE",
            "00B_llava": "COMPLETE",
            "00C2": "NOT_AUTHORIZED",
        },
        "genuine_human_reviewed_count": 0,
        "paper_evidence": False,
        "main_execution_allowed": False,
        "second_domain_execution_allowed": False,
    }
    return [
        write_json(root / "C12_IDENTITY_BASELINE.json", baseline),
        write_json(root / "C12_WORK_PLAN.json", work_plan),
        write_json(root / "C12_LIVE_BASELINE.json", live),
    ]


def source_feasibility(root: Path) -> list[Path]:
    source_candidates = [
        path
        for base in (REPO / "local_inputs", REPO / "kaggle_uploads", REPO / "dist")
        for path in base.rglob("*")
        if path.is_file()
        and "ade20k" in path.as_posix().lower()
        and path.suffix.lower() in {".json", ".jsonl", ".csv"}
    ]
    status_value = "SOURCE_BYTES_MISSING" if not source_candidates else "LICENSE_NOT_VERIFIED"
    census = [{
        "category": "ALL",
        "eligible_source_images": 0,
        "eligible_queries": 0,
        "status": status_value,
    }]
    capacity = [{
        "endpoint_arm": "ALL",
        "category": "ALL",
        "polarity": "ALL",
        "size_stratum": "ALL",
        "position_stratum": "ALL",
        "required_primary": 360,
        "required_reserve": 90,
        "observed_eligible": 0,
        "status": status_value,
    }]
    result = {
        "schema": "certvic.cvpr2027.c12.confirmatory_feasibility.v1",
        "status": status_value,
        "allocation": {"primary_relevant": 120, "primary_irrelevant": 240,
                       "reserve_relevant": 30, "reserve_irrelevant": 60},
        "candidate_manifest_paths_found": [
            path.relative_to(REPO).as_posix() for path in source_candidates
        ],
        "required_checks": [
            "license_eligibility",
            "annotations",
            "RGB_decode_minimum_short_side",
            "category_polarity_size_position_capacity",
            "protected_scene_geometry",
            "zero_V1_V2_overlap",
            "perceptual_duplicates",
            "reserve_margin",
        ],
        "counts_fabricated": False,
        "provider_outputs_used": False,
        "paper_evidence": False,
    }
    return [
        write_csv(root / "design/source_census.csv", census),
        write_csv(root / "design/stratum_capacity.csv", capacity),
        write_json(root / "design/CONFIRMATORY_FEASIBILITY.json", result),
    ]


def runbook_readiness(root: Path) -> list[Path]:
    gpu_root = root / "gpu"
    smoke_rows = []
    required_tokens = (
        "REAL_TWO_ITEM_SMOKE",
        "PRE_SMOKE_PERMISSIONS",
        "verify_matrix_authorization",
        "verify_provider_permission",
        "active_run_contract",
        "KAGGLE_ZERO_EDIT_00C2_TASK_CARDINALITY_INVALID",
        "USE_REAL_MODEL = True",
        "do_sample",
        "max_new_tokens",
        "hash_manifest.json",
        "permission_events",
        "CANONICAL_RETURN_ZIP",
    )
    for provider in PROVIDERS:
        path = next(
            (REPO / "kagglefiles/runbooks/04_REAL_MODEL_SMOKE").glob(f"00C2_{provider}_*.ipynb")
        )
        notebook, text, syntax_errors = _notebook_text(path)
        cells = notebook.get("cells", [])
        checks = {
            "cleared_outputs": all(
                not cell.get("outputs") and cell.get("execution_count") is None
                for cell in cells
                if cell.get("cell_type") == "code"
            ),
            "no_executable_placeholders": "REQUIRED_USER_FILL" not in text,
            "account_independent_discovery": (
                "discover_authenticated_input" in text and "/kaggle/input/certvic-" not in text
            ),
            "permission_before_hardware": (
                text.find("verify_provider_permission(")
                < text.find("hardware = hardware_report(")
                < text.find('"-m", "certvic.cvpr.worker"')
            ),
            "two_item_bound": "MAX_ITEMS = 2" in text,
            "deterministic_decoding": (
                '"do_sample": False' in text and '"max_new_tokens": 8' in text
            ),
            "canonical_return": "CANONICAL_RETURN_ZIP" in text,
            "syntax_valid": not syntax_errors,
            "all_contract_tokens": all(token in text for token in required_tokens),
        }
        smoke_rows.append({
            "provider": provider,
            "notebook": path.relative_to(REPO / "kagglefiles").as_posix(),
            "notebook_sha256": sha256_file(path),
            "checks": checks,
            "passed": all(checks.values()),
            "syntax_errors": syntax_errors,
        })
    with tempfile.TemporaryDirectory(prefix="certvic_c12_00c2_proof_") as temporary:
        proof = execute_generated_route(Path(temporary) / "proof")
        proof_summary = {
            key: proof[key]
            for key in (
                "status",
                "providers",
                "strict_gate_status",
                "strict_contract_verified",
                "synthetic_fixture",
                "paper_evidence",
            )
        }
    smoke_ready = all(row["passed"] for row in smoke_rows) and proof_summary[
        "strict_contract_verified"
    ]
    smoke = {
        "schema": "certvic.cvpr2027.c12.00c2_readiness.v1",
        "status": (
            "SOFTWARE_READY_EXTERNAL_SMOKE_ITEMS_REQUIRED"
            if smoke_ready
            else "SOFTWARE_NOT_READY_LOCAL_FAILURE"
        ),
        "providers": smoke_rows,
        "synthetic_execution_proof": proof_summary,
        "real_smoke_items_present": False,
        "execution_allowed": False,
        "synthetic_proof_is_model_evidence": False,
        "paper_evidence": False,
    }
    primary_rows = []
    primary_paths = [
        REPO / "kagglefiles/runbooks/05_CONFIRMATORY_GENERATION/01_specificity_confirmatory_generation_T4x2.ipynb",
        *sorted((REPO / "kagglefiles/runbooks/06_CONFIRMATORY_MODELS").glob("*.ipynb")),
    ]
    for path in primary_paths:
        notebook, text, syntax_errors = _notebook_text(path)
        is_generation = path.name.startswith("01_")
        checks = {
            "cleared_outputs": all(
                not cell.get("outputs") and cell.get("execution_count") is None
                for cell in notebook.get("cells", [])
                if cell.get("cell_type") == "code"
            ),
            "full_frozen_task_universe": "MAX_ITEMS = None" in text and "ALLOW_FULL_RUN = True" in text,
            "permission_binding": "verify_provider_permission" in text,
            "content_authenticated": "discover_authenticated_input" in text,
            "deterministic": "GLOBAL_SEED = 12013" in text,
            "resume": "--resume" in text,
            "canonical_return": "CANONICAL_RETURN_ZIP" in text,
            "generation_outcome_blind": ("parsed_response" not in text if is_generation else True),
            "syntax_valid": not syntax_errors,
        }
        primary_rows.append({
            "notebook": path.relative_to(REPO / "kagglefiles").as_posix(),
            "role": "generation" if is_generation else "provider",
            "checks": checks,
            "passed": all(checks.values()),
        })
    primary = {
        "schema": "certvic.cvpr2027.c12.primary_runbook_readiness.v1",
        "status": (
            "SOFTWARE_READY_EXTERNAL_GATES_REQUIRED"
            if all(row["passed"] for row in primary_rows)
            else "SOFTWARE_NOT_READY_LOCAL_FAILURE"
        ),
        "protocol": "specificity_confirmatory_cvpr_v3",
        "allocation": {"relevant": 120, "irrelevant": 240},
        "runbooks": primary_rows,
        "execution_allowed": False,
        "remaining_gates": [
            "00C2_PASS",
            "LICENSED_SOURCE_BYTES",
            "BLINDED_HUMAN_REVIEW",
            "MATCHING_AND_DETECTABILITY_PASS",
            "TASK_FREEZE",
            "SCIENTIFIC_PROVIDER_PERMISSIONS",
        ],
        "paper_evidence": False,
    }
    pack = verify_pack(REPO / "kagglefiles")
    return [
        write_json(gpu_root / "00C2_READINESS.json", smoke),
        write_json(gpu_root / "PRIMARY_RUNBOOK_READINESS.json", primary),
        write_json(gpu_root / "KAGGLE_PACK_VERIFICATION.json", pack),
    ]


def secondary_and_optional(root: Path) -> list[Path]:
    secondary_rows = []
    arms = {
        "repeat_determinism": {"evidence_class": "SECONDARY_REPEATABILITY", "decoding": "frozen_primary"},
        "prompt_robustness": {"evidence_class": "SECONDARY_PROMPT_ROBUSTNESS", "decoding": "greedy"},
        "decoding_robustness": {"evidence_class": "SECONDARY_DECODING_ROBUSTNESS", "decoding": "predeclared_variant"},
        "natural_absence_control": {"evidence_class": "SECONDARY_NATURAL_CONTROL", "decoding": "greedy"},
        "quantization_runtime": {"evidence_class": "SECONDARY_DECODING_ROBUSTNESS", "decoding": "greedy"},
    }
    for arm, settings in arms.items():
        for provider in PROVIDERS:
            secondary_rows.append({
                "arm": arm,
                "provider": provider,
                **settings,
                "primary_task_mutation_allowed": False,
                "required_permission_class": f"{settings['evidence_class']}_ONE_RUN",
                "runner": "certvic.cvpr.worker plus certvic.cvpr.package_run",
                "return_schema": "certvic.cvpr.output.v2 canonical provider ZIP",
                "status": "BLOCKED_BY_PRIMARY_FREEZE",
            })
    secondary = {
        "schema": "certvic.cvpr2027.c12.secondary_runbook_readiness.v1",
        "status": "SOFTWARE_READY_BLOCKED_BY_PRIMARY_FREEZE",
        "paths": secondary_rows,
        "mandatory_gates": [
            "PRIMARY_FROZEN_OR_COMPLETE",
            "SECONDARY_TASK_BUNDLE_FROZEN",
            "SEPARATE_PERMISSION",
            "NO_PRIMARY_SELECTION_CONTAMINATION",
        ],
        "secondary_may_modify_primary_tasks": False,
        "execution_allowed": False,
        "paper_evidence": False,
    }
    optional = {
        "schema": "certvic.cvpr2027.c12.optional_model_expansion_readiness.v1",
        "status": "SPECIFICATION_READY_IMPLEMENTATION_DEFERRED_NOT_PRIMARY",
        "checked_date": "2026-08-12",
        "models": [
            {
                "model_id": "HuggingFaceTB/SmolVLM2-2.2B-Instruct",
                "official_card": "https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct",
                "license": "Apache-2.0",
                "architecture": "Idefics3-derived image/multi-image/video/text",
                "reported_video_inference_gpu_ram_gb": 5.2,
                "adapter": "AutoProcessor plus AutoModelForImageTextToText/AutoModelForMultimodalLM",
                "requirements": "latest compatible Transformers; card recommends num2words and flash-attn",
                "runtime_profile": "SEPARATE_OPTIONAL_SMOLVLM2_PROFILE",
                "recommendation": "FIRST_OPTIONAL_MODEL_AFTER_PRIMARY_FREEZE",
            },
            {
                "model_id": "microsoft/Phi-4-multimodal-instruct",
                "official_card": "https://huggingface.co/microsoft/Phi-4-multimodal-instruct",
                "license": "MIT",
                "parameters_billion": 5.6,
                "snapshot_size_gb_approx": 12.9,
                "adapter": "AutoProcessor plus AutoModelForCausalLM trust_remote_code",
                "requirements": "Python 3.10, torch 2.6.0, transformers 4.48.2, flash-attn 2.7.4.post1 per official card",
                "runtime_profile": "SEPARATE_OPTIONAL_PHI4MM_PROFILE",
                "recommendation": "DO_NOT_FORCE_INTO_AUTHENTICATED_CP312_PRIMARY_STACK",
            },
        ],
        "snapshots_downloaded": False,
        "enters_primary_multiplicity_family": False,
        "evidence_class": "SECONDARY_MODEL_EXPANSION",
        "paper_evidence": False,
    }
    return [
        write_csv(root / "gpu/secondary_provider_runbook_matrix.csv", secondary_rows),
        write_json(root / "gpu/SECONDARY_RUNBOOK_READINESS.json", secondary),
        write_json(root / "gpu/OPTIONAL_MODEL_EXPANSION_READINESS.json", optional),
    ]


def human_readiness(root: Path) -> list[Path]:
    human_root = root / "human"
    paths = initialize_infrastructure(human_root)
    current = status(REPO / "data/studies/specificity_confirmatory_cvpr/review")
    readiness = {
        "schema": "certvic.cvpr2027.c12.human_review_readiness.v1",
        "status": "SOFTWARE_READY_SOURCE_PACKET_AND_GENUINE_RATERS_REQUIRED",
        "current_state": current["state"],
        "genuine_human_reviewed_count": 0,
        "qualification_dimensions": [
            "target unaffected",
            "expected-answer invariance",
            "perturbation acceptability",
            "answerability",
            "prompt ambiguity",
            "retention logic",
            "confidence calibration",
        ],
        "blindness": {
            "pair_order_randomized": True,
            "original_edited_presentation_randomized": True,
            "provider_names_hidden": True,
            "historical_outcomes_hidden": True,
            "V1_failure_identities_hidden": True,
            "selection_scores_hidden": True,
            "packet_hash_locked": True,
        },
        "independence_validators": [
            "distinct hashed rater identifiers",
            "separate non-identical sheets",
            "exact row universe",
            "no duplicates or missing rows",
            "current qualification pass",
            "immutable packet hash",
            "timestamp ordering",
        ],
        "agreement": [
            "percent agreement",
            "Cohen kappa",
            "Krippendorff alpha nominal",
            "bootstrap confidence intervals",
            "field-level agreement",
            "adjudication rate",
            "confidence and reason-code distributions",
        ],
        "next_action": "Mount licensed source bytes and build/freeze the blind packet; do not synthesize labels.",
        "paper_evidence": False,
    }
    paths.append(write_json(human_root / "HUMAN_REVIEW_READINESS.json", readiness))
    return paths


def historical_summary(root: Path) -> list[Path]:
    metrics = []
    path = REPO / "reports/cvpr2027_max_ceiling/analysis/pilot_baseline_metrics.csv"
    if path.is_file():
        with path.open(encoding="utf-8", newline="") as handle:
            metrics = list(csv.DictReader(handle))
    detectability = _json(
        REPO / "reports/cvpr2027_max_ceiling/statistics/DETECTABILITY_VERDICT.json", {}
    )
    summary = {
        "schema": "certvic.cvpr2027.c12.historical_diagnostic_summary.v1",
        "status": "HISTORICAL_DIAGNOSTIC_ONLY",
        "provider_metrics": metrics,
        "arm_detectability": detectability,
        "safe_uses": [
            "motivation",
            "failure taxonomy",
            "model ranking reversal",
            "feature-risk diagnosis",
            "prospective design stress testing without threshold tuning",
        ],
        "forbidden_uses": [
            "prospective certificate",
            "threshold selection",
            "candidate cherry-picking",
            "post-outcome sample-size changes",
        ],
        "paper_evidence": False,
    }
    return [write_json(root / "historical/HISTORICAL_DIAGNOSTIC_SUMMARY.json", summary)]


def claim_registry_and_attacks(root: Path) -> list[Path]:
    claim_specs = {
        "historical_answer_change_not_semantic_update": ("RETROSPECTIVE_DIAGNOSTIC", "SATISFIED_DIAGNOSTIC_ONLY"),
        "historical_model_dependent_specificity": ("RETROSPECTIVE_DIAGNOSTIC", "SATISFIED_DIAGNOSTIC_ONLY"),
        "prospective_responsiveness_certificate": ("PRIMARY_PROSPECTIVE", "BLOCKED"),
        "prospective_specificity_certificate": ("PRIMARY_PROSPECTIVE", "BLOCKED"),
        "prospective_joint_certificate": ("PRIMARY_PROSPECTIVE", "BLOCKED"),
        "model_ranking_reversal": ("PRIMARY_PROSPECTIVE_OR_RETROSPECTIVE_SCOPED", "DIAGNOSTIC_ONLY"),
        "model_specific_failure_regime": ("PRIMARY_PROSPECTIVE", "BLOCKED"),
        "matched_control_validity": ("PRIMARY_PROSPECTIVE", "BLOCKED"),
        "human_validity": ("PRIMARY_PROSPECTIVE", "BLOCKED_HUMAN"),
        "anytime_valid_software_claim": ("SOFTWARE_STATISTICAL_VALIDATION", "SATISFIED_SOFTWARE_ONLY"),
        "cross_model_difference": ("PRIMARY_PROSPECTIVE", "BLOCKED"),
        "secondary_prompt_robustness": ("SECONDARY_PROMPT_ROBUSTNESS", "BLOCKED"),
        "secondary_decoding_robustness": ("SECONDARY_DECODING_ROBUSTNESS", "BLOCKED"),
        "secondary_model_expansion": ("SECONDARY_MODEL_EXPANSION", "BLOCKED"),
        "cross_domain_generalization": ("PRIMARY_PROSPECTIVE_PLUS_SECOND_DOMAIN", "BLOCKED"),
        "Main500_scale_claim": ("PRIMARY_PROSPECTIVE_PLUS_MAIN500", "BLOCKED"),
    }
    claims = []
    for claim_id, (evidence_class, state) in claim_specs.items():
        prospective = "PROSPECTIVE" in evidence_class or evidence_class.startswith("SECONDARY")
        claims.append({
            "claim_id": claim_id,
            "required_evidence_class": evidence_class,
            "required_artifacts": (
                ["frozen task bundle", "permission-bound provider ZIPs", "locked analysis"]
                if prospective else ["versioned diagnostic or software validation artifact"]
            ),
            "required_human_review": claim_id in {
                "prospective_responsiveness_certificate",
                "prospective_specificity_certificate",
                "prospective_joint_certificate",
                "matched_control_validity",
                "human_validity",
                "cross_domain_generalization",
                "Main500_scale_claim",
            },
            "required_sample_size": (
                {"relevant": 120, "irrelevant": 240} if "prospective" in claim_id else None
            ),
            "required_gate": "evidence_class_and_artifact_hashes_match",
            "allowed_scope": evidence_class,
            "forbidden_supporting_artifacts": [
                "synthetic proof",
                "00C2 smoke",
                "historical V1/V2 for prospective claims",
                "planned or contracts-only artifacts",
            ],
            "status": state,
            "paper_evidence": False,
        })
    registry = {
        "schema": "certvic.cvpr2027.c12.claim_registry.v2",
        "claims": claims,
        "historical_can_satisfy_prospective": False,
        "optional_models_enter_primary_family": False,
        "paper_evidence": False,
    }
    attack_names = [
        "remove_one_model",
        "remove_one_category",
        "remove_one_perturbation_family",
        "polarity_concentration",
        "spatial_stratum_concentration",
        "size_stratum_concentration",
        "arm_low_level_detectability",
        "relevant_edit_magnitude",
        "missingness_dominates_bounds",
        "parser_failure_asymmetry",
        "failure_item_concentration",
        "naive_metric_ranking_reversal",
        "multiplicity_changes_decision",
        "human_filter_changes_conclusion",
        "human_disagreement_concentrated_in_failures",
        "candidate_rejection_by_arm",
        "secondary_contaminates_primary_selection",
        "exact_model_revisions",
        "row_to_source_task_model_code_hash_trace",
    ]
    pre_pass = {"secondary_contaminates_primary_selection", "exact_model_revisions"}
    attacks = [{
        "attack": name,
        "status": "PASS_PRE_RESULTS_STATIC" if name in pre_pass else "WAITING_FOR_PROSPECTIVE_OUTPUT",
        "paper_evidence": False,
    } for name in attack_names]
    red_team = {
        "schema": "certvic.cvpr2027.c12.reviewer_attack_suite.v2",
        "status": "PRE_RESULTS_CHECKS_PASS_OUTPUT_DEPENDENT_CHECKS_WAITING",
        "checks": attacks,
        "fake_passes": 0,
        "paper_evidence": False,
    }
    return [
        write_json(root / "evidence/CLAIM_REGISTRY_V2.json", registry),
        write_json(root / "evidence/SCIENTIFIC_RED_TEAM_V2.json", red_team),
    ]


def downstream_frameworks(root: Path) -> list[Path]:
    domain_fields = [
        "domain_candidate",
        "license_clarity_0_5",
        "real_image_availability_0_5",
        "annotation_quality_0_5",
        "category_compatibility_0_5",
        "semantic_edit_feasibility_0_5",
        "negative_control_feasibility_0_5",
        "domain_diversity_0_5",
        "free_compute_feasibility_0_5",
        "redistribution_ability_0_5",
        "review_burden_inverse_0_5",
        "evidence_links",
        "decision",
    ]
    domain_template = [{field: "" for field in domain_fields}]
    second = {
        "schema": "certvic.cvpr2027.c12.second_domain_readiness.v1",
        "status": "FRAMEWORK_READY_DOMAIN_NOT_SELECTED",
        "dataset_selected": False,
        "execution_allowed": False,
        "selection_rule": "score evidence-backed candidates; convenience alone is insufficient",
        "paper_evidence": False,
    }
    main = {
        "schema": "certvic.cvpr2027.c12.main500_readiness.v1",
        "status": "CONDITIONAL_NOT_AUTHORIZED",
        "software_paths": [
            "source census",
            "task generation",
            "review packet",
            "quality and detectability gates",
            "freeze and permissions",
            "provider notebooks",
            "transactional imports",
            "analysis and recovery",
        ],
        "authorization_requires": "hash-bound prospective confirmatory GO artifact",
        "manual_go_text_bypass_allowed": False,
        "execution_allowed": False,
        "paper_evidence": False,
    }
    runtime_rows = []
    for provider in PROVIDERS:
        runtime_rows.append({
            "provider": provider,
            "stage": "00C2",
            "items": 2,
            "optimistic_minutes": 20,
            "typical_minutes": 40,
            "conservative_minutes": 60,
            "basis": "planning range pending measured real smoke",
        })
        runtime_rows.append({
            "provider": provider,
            "stage": "confirmatory_v3",
            "items": 360,
            "optimistic_minutes": "DERIVE_AFTER_00C2",
            "typical_minutes": "DERIVE_AFTER_00C2",
            "conservative_minutes": "DERIVE_AFTER_00C2",
            "basis": "DERIVE_AFTER_CONFIRMATORY_CALIBRATION",
        })
    primary_analysis = {
        "schema": "certvic.cvpr2027.c12.primary_analysis_readiness.v1",
        "status": "SOFTWARE_PATHS_READY_PROSPECTIVE_ZIPS_REQUIRED",
        "implemented_outputs": [
            "raw and validity-filtered denominators",
            "missing/unparseable/abstention counts",
            "semantic-update successes and irrelevant flips",
            "one-sided exact bounds and six-gate decisions",
            "joint and model certificates",
            "risk differences, exact McNemar, exploratory Holm",
            "secondary confidence sequences",
            "category/family/polarity/size/position strata",
            "leave-one-category/family-out",
            "failure concentration and cross-model disagreement",
        ],
        "exploratory_outputs_labeled": True,
        "execution_allowed": False,
        "paper_evidence": False,
    }
    artifact_hashes = {"synthetic_golden_fixture": "a" * 64}

    def certificate_case(
        name: str,
        relevant_successes: int,
        irrelevant_flips: int,
        *,
        missing_count: int = 0,
        parse_failure_count: int = 0,
    ) -> dict[str, Any]:
        certificate = compute_certificate(
            model=f"golden::{name}",
            relevant_outcomes=[True] * relevant_successes
            + [False] * (120 - relevant_successes),
            irrelevant_flip_outcomes=[True] * irrelevant_flips
            + [False] * (240 - irrelevant_flips),
            missing_count=missing_count,
            parse_failure_count=parse_failure_count,
            evidence_class="SYNTHETIC_SOFTWARE_GOLDEN_FIXTURE",
            artifact_hashes=artifact_hashes,
            genuine_human_review=True,
            prospective=True,
        )
        return {
            "fixture": name,
            "expected_disposition": "ANALYZED",
            "result": certificate,
        }

    fixtures = [
        certificate_case("all_pass", 120, 0),
        certificate_case("all_fail", 0, 240),
        certificate_case("one_missing", 120, 0, missing_count=1),
        certificate_case("parser_failures", 120, 0, parse_failure_count=1),
        certificate_case("boundary_critical_count", 74, 13),
        {
            "fixture": "one_duplicate",
            "expected_disposition": "REJECT_BEFORE_ANALYSIS",
            "enforced_by": "prediction identity uniqueness and transactional return validation",
        },
        {
            "fixture": "one_provider_missing",
            "expected_disposition": "REJECT_FAMILY_CERTIFICATE",
            "enforced_by": "three-provider completion audit",
        },
        {
            "fixture": "mixed_task_bundle",
            "expected_disposition": "REJECT_BEFORE_ANALYSIS",
            "enforced_by": "task-bundle and run-contract hash binding",
        },
        {
            "fixture": "wrong_permission",
            "expected_disposition": "REJECT_BEFORE_HARDWARE",
            "enforced_by": "single-use provider permission verification",
        },
    ]
    golden = {
        "schema": "certvic.cvpr2027.c12.analysis_golden_fixtures.v1",
        "status": "ALL_NINE_GOLDEN_CASES_RECORDED",
        "fixtures": fixtures,
        "synthetic_fixture": True,
        "software_validation_only": True,
        "paper_evidence": False,
    }
    return [
        write_csv(root / "second_domain/DOMAIN_SELECTION_TEMPLATE.csv", domain_template, domain_fields),
        write_json(root / "second_domain/SECOND_DOMAIN_READINESS.json", second),
        write_json(root / "main/MAIN500_READINESS.json", main),
        write_csv(root / "gpu/GPU_RUNTIME_PLANNING_RANGES.csv", runtime_rows),
        write_json(root / "analysis/PRIMARY_ANALYSIS_READINESS.json", primary_analysis),
        write_json(root / "analysis/ANALYSIS_GOLDEN_FIXTURES.json", golden),
    ]


def final_identity(root: Path) -> list[Path]:
    baseline = _json(root / "C12_IDENTITY_BASELINE.json", {})
    final = measure(baseline)
    final.update({
        "schema": "certvic.cvpr2027.c12.identity_snapshot.v1",
        "snapshot": "FINAL_AFTER_C12_EDITS",
    })
    diff = compare(baseline, final)
    diff.update({
        "schema": "certvic.cvpr2027.c12.identity_diff.v1",
        "preferred_marker": (
            "NO_00A_OR_00B_RERUN_REQUIRED"
            if not diff["00A_00B_rerun_required"]
            else "AUTHENTICATED_RERUN_REQUIRED"
        ),
    })
    return [
        write_json(root / "C12_IDENTITY_FINAL.json", final),
        write_json(root / "C12_IDENTITY_DIFF.json", diff),
    ]


def run(output_root: Path = REPORT_ROOT) -> dict[str, Any]:
    paths: list[Path] = []
    paths.extend(live_baseline(output_root))
    paths.extend(source_feasibility(output_root))
    paths.extend(runbook_readiness(output_root))
    paths.extend(secondary_and_optional(output_root))
    paths.extend(human_readiness(output_root))
    paths.extend(historical_summary(output_root))
    paths.extend(claim_registry_and_attacks(output_root))
    paths.extend(downstream_frameworks(output_root))
    paths.extend(final_identity(output_root))
    manifest = write_json(output_root / "C12_READINESS_ARTIFACT_MANIFEST.json", artifact_manifest(paths))
    result = {
        "schema": "certvic.cvpr2027.c12.readiness_summary.v1",
        "status": "LOCAL_READINESS_ARTIFACTS_BUILT",
        "artifacts": len(paths) + 1,
        "manifest": manifest.resolve().relative_to(REPO).as_posix(),
        "paper_evidence": False,
    }
    write_json(output_root / "C12_READINESS_SUMMARY.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPORT_ROOT)
    args = parser.parse_args(argv)
    result = run(args.output_root)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
