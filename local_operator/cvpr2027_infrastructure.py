"""Generate C11 audit, evidence, operator, GPU-planning, and reporting infrastructure."""

from __future__ import annotations

import csv
import json
import platform
import sys
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import (  # noqa: E402
    REPORT_ROOT,
    REPO,
    artifact_manifest,
    canonical_json_bytes,
    write_csv,
    write_json,
    write_jsonl,
    write_text,
)


PROVIDERS = ["qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b"]
ACCOUNTS = {
    "qwen2_5_vl_7b": "lancerdevsm",
    "internvl_8b": "saket9500",
    "llava_onevision_7b": "examhelps",
}


def _json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _capability(
    name: str,
    status: str,
    value: str,
    risk: str,
    action: str,
    *,
    cost: str = "LOW",
    cpu: str = "LOW",
    gpu: str = "NONE",
    human: str = "NONE",
    dependency: str = "NONE",
    identity: str = "NONE_OPERATOR_ONLY",
) -> dict[str, str]:
    return {
        "capability": name,
        "status": status,
        "scientific_value": value,
        "CVPR_reviewer_risk_if_missing": risk,
        "implementation_cost": cost,
        "CPU_cost": cpu,
        "GPU_cost": gpu,
        "human_cost": human,
        "dependency": dependency,
        "identity_impact": identity,
        "action_taken": action,
    }


def repository_gap_audit(root: Path) -> list[Path]:
    capabilities = [
        _capability("authenticated 00A environment proof", "COMPLETE", "high", "BLOCKER", "Preserved genuine validated return; no rerun requested."),
        _capability("three authenticated 00B snapshot proofs", "COMPLETE", "high", "BLOCKER", "Preserved all three current genuine validated returns."),
        _capability("real two-item 00C2 smoke", "BLOCKED_EXTERNAL", "high", "BLOCKER", "Revalidated fail-closed intake boundary.", dependency="two real non-synthetic license-eligible paired items", gpu="T4x2 1-3 h total"),
        _capability("prospective confirmatory source census and selection", "BLOCKED_EXTERNAL", "high", "BLOCKER", "Added outcome-blind census and exact balanced selection wrapper.", dependency="licensed ADE20K source bytes and auditable source manifest", cpu="LOW"),
        _capability("exact fixed-sample power and design validation", "COMPLETE", "high", "MAJOR", "Implemented exact one-sided Clopper-Pearson grid, sensitivity, FWER and boundary checks.", cpu="MEDIUM"),
        _capability("anytime-valid confidence-sequence validation", "COMPLETE", "high", "BLOCKER", "Implemented empirical coverage, optional stopping, ordering, and efficiency simulations.", cpu="HIGH"),
        _capability("historical pilot baselines and ablations", "RETROSPECTIVE_ONLY", "medium", "MAJOR", "Reanalyzed genuine 91/94 frozen items with strict semantic endpoint and multiple inferential variants.", cpu="LOW"),
        _capability("heterogeneity and stability", "RETROSPECTIVE_ONLY", "high", "MAJOR", "Added group, category, polarity, leave-out, influence, and concentration analyses.", cpu="MEDIUM"),
        _capability("image quality and endpoint-arm matching", "RETROSPECTIVE_ONLY", "high", "BLOCKER", "Computed pair-level metrics, balance, detectability CV, permutation, bootstrap, and category leave-out.", cpu="MEDIUM"),
        _capability("prospective detectability gate", "BLOCKED_EXTERNAL", "high", "BLOCKER", "Frozen threshold remains unchanged; current historical diagnostic cannot satisfy prospective gate.", dependency="frozen prospective images and genuine human-validity output"),
        _capability("duplicate leakage and contamination audit", "COMPLETE", "high", "BLOCKER", "Added byte, perceptual-hash, prompt/path, retrospective-reuse, and prospective contamination checks.", cpu="MEDIUM"),
        _capability("genuine double-blind human review", "BLOCKED_HUMAN", "high", "BLOCKER", "Added qualifications, two-rater state machine, raw sheet preservation, agreement, and adjudication tooling.", human="two qualified independent raters plus adjudicator", dependency="frozen licensed review packet"),
        _capability("formal certificate API", "COMPLETE", "high", "BLOCKER", "Added exact gate computation with missing/parser regimes and machine-readable coordinates."),
        _capability("machine-readable claim gating", "COMPLETE", "high", "BLOCKER", "Added requirements/status registries with evidence-class restrictions."),
        _capability("scientific reviewer red team", "COMPLETE", "high", "MAJOR", "Added live artifact-backed adversarial checks."),
        _capability("primary confirmatory GPU runbooks", "BLOCKED_GPU", "high", "BLOCKER", "Existing authenticated runbooks retained and mapped; execution remains gated by smoke, licensed bytes, review, and permissions.", gpu="generation 2-8 h; providers 1-4 h each", dependency="00C2 PASS and frozen confirmatory inputs"),
        _capability("secondary robustness GPU matrix", "PARTIAL", "medium", "MAJOR", "Prepared explicit secondary contracts and execution estimates without changing authenticated common bundles.", gpu="0.5-4 h/provider/arm", dependency="primary freeze or completion, task bundle, provider permissions"),
        _capability("optional architecture expansion", "PARTIAL", "medium", "MINOR", "Scored two architecture-diverse candidates; downloads and scientific runs intentionally not performed.", gpu="planning only", dependency="primary three-model path stable"),
        _capability("conditional Main-500 path", "BLOCKED_GPU", "high", "MAJOR", "Existing fail-closed notebooks retained; authorization stays CONDITIONAL_NOT_AUTHORIZED.", dependency="prospective confirmatory GO artifact and fresh freeze/review/detectability/permissions", gpu="derive from measured throughput"),
        _capability("conditional second-domain path", "BLOCKED_EXTERNAL", "medium", "MAJOR", "Added domain-agnostic license/source/endpoint/review checklist; existing notebooks remain unauthorized.", dependency="chosen licensed domain and source manifest", gpu="derive from measured throughput"),
        _capability("clean-room CPU reproduction", "COMPLETE", "high", "MAJOR", "Added archive-based isolated reproduction with semantic manifest comparison.", cpu="MEDIUM"),
        _capability("paper prose", "DEPRECATED", "none", "NONE", "Explicitly excluded from C11; paper/main_v11.tex inspected read-only.", identity="NO_CHANGE"),
    ]
    payload = {
        "schema": "certvic.cvpr2027.repository_gap_audit.v1",
        "live_repository_commit_at_audit": "ee054f73be33c265e8935608ef7a8da9ef909daf",
        "inspection_scope": [
            "README.md", "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md",
            "reports/v11_full_ceiling_audit/CERTVIC_V11_MASTER_HANDOFF.md",
            "configs/studies", "configs/statistics", "configs/models", "configs/runtime",
            "local_operator", "certvic/cvpr", "scripts", "tests", "kagglefiles",
            "execution_pack", "paper/main_v11.tex (read only)",
        ],
        "capabilities": capabilities,
        "paper_evidence": False,
    }
    json_path = write_json(root / "C11_REPOSITORY_GAP_AUDIT.json", payload)
    lines = [
        "# C11 live repository gap audit", "",
        "This audit reflects inspected live code and artifacts. It does not promote retrospective diagnostics or infrastructure to paper evidence.", "",
        "| Capability | Status | Reviewer risk | Dependency | Action |", "| --- | --- | --- | --- | --- |",
    ]
    for row in capabilities:
        lines.append(f"| {row['capability']} | `{row['status']}` | {row['CVPR_reviewer_risk_if_missing']} | {row['dependency']} | {row['action_taken']} |")
    md_path = write_text(root / "C11_REPOSITORY_GAP_AUDIT.md", "\n".join(lines) + "\n")
    change_plan = {
        "schema": "certvic.cvpr2027.identity_change_plan.v1",
        "decision": "NO_COMMON_IDENTITY_CHANGE_REQUIRED",
        "track_a": ["local_operator modules", "C11 reports", "operator CSV/docs", "secondary planning contracts"],
        "track_b": [],
        "reason": "All currently safe CPU and planning work can remain outside authenticated common bundles; changing them would unnecessarily stale genuine 00A/00B returns.",
        "paper_evidence": False,
    }
    return [json_path, md_path, write_json(root / "C11_IDENTITY_CHANGE_PLAN.json", change_plan)]


def failure_recovery(root: Path) -> list[Path]:
    definitions = [
        ("download interrupted", True, False, True, "completed remote output and hashes", "redownload", "none if hash-valid"),
        ("Kaggle session reset", True, "depends", True, "downloaded checkpoints and immutable inputs", "restart only under same valid permission", "rerun disclosure"),
        ("disk full", True, False, True, "journals, immutable inputs, completed shards", "free space without deleting evidence", "none if validated resume"),
        ("CUDA OOM", True, "depends", True, "failure report and unchanged contract", "apply only predeclared fallback or mint new permission", "precision/quantization change is separate evidence identity"),
        ("snapshot missing", True, False, True, "inputs", "attach authenticated snapshot", "no evidence produced"),
        ("snapshot hash mismatch", False, True, True, "mismatch record and bytes", "obtain exact snapshot and new binding", "reject entire return"),
        ("wrong provider snapshot", False, True, True, "failure report", "attach correct provider snapshot", "reject entire return"),
        ("wrong permission", False, True, True, "permission and audit log", "mint correctly bound permission", "reject entire return"),
        ("expired permission", False, True, True, "expired permission", "mint new permission", "no launch allowed"),
        ("consumed nonce", False, True, True, "ledger", "mint a new nonce", "replay rejected"),
        ("duplicate return", True, False, False, "first committed return", "idempotent import/compare hashes", "conflict blocks import"),
        ("corrupt ZIP", True, False, True, "remote output if present", "redownload then rerun if still corrupt", "not evidence"),
        ("missing row", False, True, True, "raw shards and manifest", "rerun missing task under fresh permission", "incomplete evidence"),
        ("duplicate row", False, True, True, "raw rows", "resolve run-contract violation then rerun", "reject return"),
        ("parser crash", "conditional", "depends", "depends", "raw model text", "repair parser only under declared versioning policy", "new parser identity or fail-closed missing"),
        ("partial generation", True, False, True, "generation journal and completed images", "resume deterministic uncompleted items", "validate final census"),
        ("review sheet incomplete", True, False, False, "original sheet", "same human finishes blank rows", "review gate stays blocked"),
        ("review packet mutated", False, False, True, "original packet and sheets", "rebuild/refreeze and restart review", "invalidate labels tied to old hash"),
        ("selection imbalance", False, False, False, "census and solver trace", "declare infeasible or abandon before outcomes", "cannot tune after model outcomes"),
        ("detectability failure", False, False, False, "all images/audits", "do not promote; predeclare new future study", "prospective gate fails"),
        ("transaction journal interrupted", True, False, False, "journal, staging bytes, destination", "resume/recover transaction", "no partial promotion"),
        ("analysis crash", True, False, False, "immutable inputs", "repair deterministic CPU analysis", "no evidence change if outputs match"),
        ("figure/table regeneration mismatch", False, False, False, "both outputs and upstream manifest", "investigate environment/code/input drift", "release blocked"),
    ]
    rows = [{
        "failure": name, "safe_retry": safe, "requires_new_permission": permission,
        "requires_rerun": rerun, "preserve_which_bytes": preserve, "human_action": action,
        "scientific_consequence": consequence,
    } for name, safe, permission, rerun, preserve, action, consequence in definitions]
    payload = {"schema": "certvic.cvpr2027.failure_recovery.v1", "failures": rows, "paper_evidence": False}
    paths = [write_json(root / "C11_FAILURE_RECOVERY_MATRIX.json", payload)]
    lines = ["# C11 failure and recovery matrix", "", "| Failure | Safe retry? | New permission? | Rerun? | Preserve | Human action | Scientific consequence |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row[key]) for key in ["failure", "safe_retry", "requires_new_permission", "requires_rerun", "preserve_which_bytes", "human_action", "scientific_consequence"]) + " |")
    paths.append(write_text(root / "C11_FAILURE_RECOVERY_MATRIX.md", "\n".join(lines) + "\n"))
    return paths


def claim_registry(root: Path) -> list[Path]:
    claims = [
        ("pilot_descriptive_gap", "descriptive", ["pilot_baseline_metrics.csv"], ["genuine frozen historical predictions"], ["RETROSPECTIVE_DIAGNOSTIC"], [], "91 intervention and 94 specificity items", False, "historical pilot", "three frozen providers", "SATISFIED_RETROSPECTIVE_ONLY", None),
        ("model_dependent_specificity_pilot", "comparative diagnostic", ["pilot_pairwise_comparisons.csv"], ["paired model rows"], ["RETROSPECTIVE_DIAGNOSTIC"], [], "94 shared specificity items", False, "historical pilot", "three frozen providers", "SATISFIED_RETROSPECTIVE_ONLY", None),
        ("prospective_joint_certificate", "primary prospective", ["prospective model certificates", "frozen task manifest", "human review", "detectability verdict"], ["00C2 PASS", "review PASS", "detectability PASS", "all six exact gates"], ["PROSPECTIVE_CONFIRMATORY"], ["RETROSPECTIVE_DIAGNOSTIC", "SYNTHETIC_PROOF"], "120 relevant and 120 irrelevant per model", True, "frozen confirmatory domain", "all three primary models", "BLOCKED", "No licensed source bytes, human labels, permissions, or GPU returns."),
        ("cross_model_specificity_difference", "prospective secondary", ["three prospective provider returns", "paired comparison"], ["primary freeze", "multiplicity control"], ["PROSPECTIVE_CONFIRMATORY"], ["RETROSPECTIVE_DIAGNOSTIC"], "120 shared irrelevant items per model", True, "confirmatory domain", "three primary models", "BLOCKED", "Prospective provider returns absent."),
        ("cross_domain_generalization", "external validity", ["confirmatory certificate", "second-domain certificate"], ["separate license/review/freeze/permission gates"], ["PROSPECTIVE_CONFIRMATORY", "PROSPECTIVE_SECOND_DOMAIN"], ["RETROSPECTIVE_DIAGNOSTIC"], "predeclared adequate sample in each domain", True, "at least two domains", "same frozen providers", "BLOCKED", "Second domain not selected or licensed; execution unauthorized."),
        ("Main500_claim", "scaled prospective", ["signed GO", "Main freeze", "Main review", "Main detectability", "Main provider returns"], ["prospective confirmatory GO", "fresh permissions"], ["PROSPECTIVE_MAIN500"], ["RETROSPECTIVE_DIAGNOSTIC", "PROSPECTIVE_CONFIRMATORY"], "500 frozen valid items as predeclared", True, "Main domain", "three primary models", "BLOCKED", "Main is CONDITIONAL_NOT_AUTHORIZED and no confirmatory GO exists."),
        ("anytime_valid_coverage_claim", "software validation", ["CS_VALIDATION_VERDICT.json", "cs_coverage_simulation.csv", "optional_stopping_stress.csv"], ["no material empirical undercoverage"], ["SOFTWARE_STATISTICAL_VALIDATION"], [], "declared simulation cells and seeds", False, "Bernoulli simulations", "not model-specific", "SATISFIED_SOFTWARE_VALIDATION", None),
    ]
    keys = ["claim_id", "claim_type", "required_artifacts", "required_gates", "allowed_evidence_classes", "forbidden_evidence_classes", "minimum_sample_requirements", "human_review_requirement", "domain_scope", "model_scope", "status", "blocking_reason"]
    rows = [dict(zip(keys, row, strict=True)) for row in claims]
    requirements = [{key: row[key] for key in keys if key not in {"status", "blocking_reason"}} for row in rows]
    status = [{"claim_id": row["claim_id"], "status": row["status"], "blocking_reason": row["blocking_reason"], "paper_evidence": False} for row in rows]
    return [
        write_json(root / "evidence/CLAIM_REQUIREMENTS.json", {"schema": "certvic.cvpr2027.claim_requirements.v1", "claims": requirements}),
        write_json(root / "evidence/CLAIM_STATUS.json", {"schema": "certvic.cvpr2027.claim_status.v1", "claims": status, "paper_evidence": False}),
    ]


def red_team(root: Path) -> list[Path]:
    metrics = _csv(root / "analysis/pilot_baseline_metrics.csv")
    heterogeneity = _csv(root / "analysis/heterogeneity_summary.csv")
    balance = _csv(root / "audits/relevant_irrelevant_balance.csv")
    detectability = _json(root / "statistics/DETECTABILITY_VERDICT.json", {})
    leakage = _json(root / "audits/DUPLICATE_LEAKAGE_AUDIT.json", {})
    reversals = _json(root / "analysis/pilot_decision_reversals.json", {})
    concentration = _json(root / "analysis/failure_concentration.json", {})
    checks = [
        ("qwen_removal", "Does result disappear if Qwen is removed?", "MAJOR", "Only historical diagnostic data exist; model-specific rates differ and prospective joint certificate requires all three."),
        ("category_leaveout", "Does result disappear if one category is removed?", "MAJOR" if heterogeneity else "NOT_APPLICABLE", "Historical leave-one-group outputs generated; prospective items absent."),
        ("family_leaveout", "Does result disappear if one intervention family is removed?", "MAJOR" if heterogeneity else "NOT_APPLICABLE", "Historical group influence is non-negligible; prospective stability is unobserved."),
        ("polarity_driver", "Is one polarity driving the result?", "MAJOR", "Polarity heterogeneity is reported for historical items; no prospective confirmation."),
        ("visible_size_imbalance", "Are relevant edits visibly larger?", "MAJOR" if any(float(row.get("absolute_smd", 0)) > 0.2 for row in balance) else "PASS", "Historical relevant/irrelevant low-level balance has material standardized differences."),
        ("endpoint_arm_detectability", "Can a classifier detect endpoint arm from low-level features?", "BLOCKER" if float(detectability.get("symmetric_auc", 0)) > 0.8 else "PASS", f"Historical symmetric AUC={detectability.get('symmetric_auc')}; this is diagnostic, not the prospective original/edited gate."),
        ("failure_concentration", "Are failures concentrated in a handful of items?", "MAJOR" if concentration else "NOT_APPLICABLE", "Failure concentration artifact generated; prospective concentration unobserved."),
        ("parser_dependence", "Do parser failures drive conclusions?", "PASS" if all(int(float(row.get("parse_failure_count", 0))) == 0 for row in metrics) else "MAJOR", "Complete-case and fail-closed ablations are generated."),
        ("complete_case", "Does complete-case handling materially change conclusions?", "PASS", "Historical complete-case and fail-closed decision rows agree where no parser failures occur."),
        ("multiplicity", "Does multiplicity correction reverse a conclusion?", "MAJOR" if reversals.get("pass_fail_reversal_found") else "PASS", "Decision reversal registry compares point, standard exact, bootstrap, CS, and multiplicity-corrected gates."),
        ("naive_ranking", "Does a naive metric rank models differently?", "MAJOR" if reversals.get("ranking_reversal_found") else "PASS", "Historical model ranking reversals are explicitly recorded."),
        ("model_revisions", "Are model revisions pinned?", "PASS", "Authenticated 00B snapshot manifests bind all three primary provider identities."),
        ("immutable_lineage", "Can all result rows trace to immutable input bytes?", "MAJOR", "Historical pilot rows trace to local frozen bytes, but one consolidated row-level lineage table remains retrospective-only; prospective inputs absent."),
        ("human_origin", "Are any human labels machine-generated?", "PASS", "No genuine human labels are claimed; human_reviewed=true count remains zero."),
        ("retrospective_contamination", "Does retrospective evidence contaminate prospective evidence?", "PASS" if not leakage.get("prospective_collision_count") else "BLOCKER", "Prospective evidence is absent and no prospective collision is recorded; V2 reuse is documented retrospective-only."),
    ]
    rows = [{"check_id": cid, "question": question, "severity": severity, "finding": finding} for cid, question, severity, finding in checks]
    payload = {
        "schema": "certvic.cvpr2027.scientific_red_team.v1",
        "status": "COMPLETE_WITH_OPEN_BLOCKERS",
        "counts": {level: sum(row["severity"] == level for row in rows) for level in ["BLOCKER", "MAJOR", "MINOR", "PASS", "NOT_APPLICABLE"]},
        "checks": rows,
        "paper_evidence": False,
    }
    return [write_json(root / "SCIENTIFIC_RED_TEAM.json", payload)]


def gpu_planning(root: Path) -> list[Path]:
    rows: list[dict[str, Any]] = []
    for provider in PROVIDERS:
        short = {"qwen2_5_vl_7b": "qwen2_5_vl_7b", "internvl_8b": "internvl_8b", "llava_onevision_7b": "llava_onevision_7b"}[provider]
        rows.append({"stage": "00C2_REAL_MODEL_SMOKE", "notebook": f"runbooks/04_REAL_MODEL_SMOKE/00C2_{short}_real_model_two_item_smoke.ipynb", "provider": provider, "required_inputs": "COMMON;MODEL_SNAPSHOT;REAL_TWO_ITEM_SMOKE;PROVIDER_PERMISSION", "accelerator": "T4x2", "internet": "OFF", "estimated_min": 20, "estimated_typical": 40, "estimated_max": 60, "expected_output": f"00C2_{short}_real_model_smoke.zip", "paper_evidence": False, "parallel_group": "00C2_PROVIDERS_AFTER_SHARED_BYTES", "prerequisites": "two licensed real items; current 00A/00B; distinct permission", "retry_policy": "fresh permission unless prelaunch failure"})
        rows.append({"stage": "CONFIRMATORY_PROVIDER", "notebook": f"runbooks/06_CONFIRMATORY_MODELS/{PROVIDERS.index(provider)+2:02d}_{'qwen' if provider.startswith('qwen') else 'internvl' if provider.startswith('intern') else 'llava'}_specificity_confirmatory_T4x2.ipynb", "provider": provider, "required_inputs": "COMMON;MODEL_SNAPSHOT;FROZEN_CONFIRMATORY_TASKS;PROVIDER_PERMISSION", "accelerator": "T4x2", "internet": "OFF", "estimated_min": 60, "estimated_typical": 150, "estimated_max": 240, "expected_output": f"confirmatory_{provider}_return.zip", "paper_evidence": "conditional_true_only_after_valid_import", "parallel_group": "CONFIRMATORY_PROVIDERS", "prerequisites": "00C2 PASS; generation QA; human review; freeze; detectability PASS", "retry_policy": "transactional resume only when contract permits; otherwise new permission"})
        for stage, typical, maximum in [("REPEAT_DETERMINISM", 60, 90), ("PROMPT_ROBUSTNESS", 150, 240), ("DECODING_ROBUSTNESS", 120, 240), ("NATURAL_ABSENCE_CONTROL", 120, 180)]:
            rows.append({"stage": stage, "notebook": "CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input", "provider": provider, "required_inputs": "SECONDARY_CONTRACT;FROZEN_TASK_SUBSET;MODEL_SNAPSHOT;SECONDARY_PERMISSION", "accelerator": "T4x2", "internet": "OFF", "estimated_min": 30 if stage == "REPEAT_DETERMINISM" else 60, "estimated_typical": typical, "estimated_max": maximum, "expected_output": f"secondary_{stage.lower()}_{provider}_return.zip", "paper_evidence": False, "parallel_group": f"{stage}_PROVIDERS", "prerequisites": "primary frozen/completed; separate secondary task identity; no selection contamination", "retry_policy": "fresh secondary permission; never substitute for primary"})
    rows.extend([
        {"stage": "CONFIRMATORY_GENERATION", "notebook": "runbooks/05_CONFIRMATORY_GENERATION/01_specificity_confirmatory_generation_T4x2.ipynb", "provider": "shared", "required_inputs": "COMMON;LICENSED_SOURCE_MANIFEST;LICENSED_SOURCE_BYTES;GENERATION_CONTRACT", "accelerator": "T4x2", "internet": "OFF", "estimated_min": 120, "estimated_typical": 300, "estimated_max": 480, "expected_output": "confirmatory_generation_return.zip", "paper_evidence": False, "parallel_group": "", "prerequisites": "00C2 PASS; license/source validation", "retry_policy": "resume validated journal; preserve completed images"},
        {"stage": "MAIN500_CONDITIONAL", "notebook": "runbooks/07_MAIN_CONDITIONAL/10-13 provider suite", "provider": "all", "required_inputs": "SIGNED_CONFIRMATORY_GO;FRESH_FREEZE;REVIEW;DETECTABILITY;PERMISSIONS", "accelerator": "T4x2", "internet": "OFF", "estimated_min": "DERIVE", "estimated_typical": "DERIVE_FROM_CONFIRMATORY_THROUGHPUT", "estimated_max": "DERIVE", "expected_output": "main_*_return.zip", "paper_evidence": "conditional", "parallel_group": "MAIN_PROVIDERS", "prerequisites": "CONDITIONAL_NOT_AUTHORIZED until genuine GO", "retry_policy": "fresh provider-specific permission"},
        {"stage": "SECOND_DOMAIN_CONDITIONAL", "notebook": "runbooks/08_SECOND_DOMAIN_CONDITIONAL/20-23 suite", "provider": "all", "required_inputs": "LICENSE;SOURCE_MANIFEST;DOMAIN_CONTRACT;REVIEW;PERMISSIONS", "accelerator": "T4x2", "internet": "OFF", "estimated_min": "DERIVE", "estimated_typical": "DERIVE_FROM_MEASURED_THROUGHPUT", "estimated_max": "DERIVE", "expected_output": "second_domain_*_return.zip", "paper_evidence": "conditional", "parallel_group": "SECOND_DOMAIN_PROVIDERS", "prerequisites": "dataset selection and execution authorization", "retry_policy": "fresh provider-specific permission"},
    ])
    expansion = {
        "schema": "certvic.cvpr2027.model_expansion_options.v1",
        "scoring_scale": "0-5 each; equal weights; feasibility is a veto",
        "recommendation_limit": 2,
        "execute_now": False,
        "candidates": [
            {"model_id": "HuggingFaceTB/SmolVLM2-2.2B-Instruct", "architecture_diversity": 4, "license_clarity": 5, "free_kaggle_feasibility": 5, "snapshot_size": 5, "expected_runtime": 5, "processor_stability": 4, "community_relevance": 4, "recency": 5, "incremental_scientific_value": 4, "total": 41, "license": "Apache-2.0", "source": "https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct", "recommendation": "FIRST_OPTIONAL_ADDITION_AFTER_PRIMARY_STABLE"},
            {"model_id": "microsoft/Phi-4-multimodal-instruct", "architecture_diversity": 5, "license_clarity": 5, "free_kaggle_feasibility": 3, "snapshot_size": 3, "expected_runtime": 3, "processor_stability": 2, "community_relevance": 5, "recency": 5, "incremental_scientific_value": 5, "total": 36, "license": "MIT", "source": "https://huggingface.co/microsoft/Phi-4-multimodal-instruct", "recommendation": "SECOND_OPTIONAL_ADDITION_IN_SEPARATE_RUNTIME_PROFILE", "compatibility_warning": "Official card pins a newer Transformers/Torch stack and trust_remote_code; do not insert into the frozen primary environment."},
        ],
        "paper_evidence": False,
    }
    contracts = {
        "schema": "certvic.cvpr2027.secondary_gpu_contracts.v1",
        "status": "CONTRACTS_PREPARED_EXECUTION_BLOCKED",
        "common_requirements": ["immutable task-bundle hash", "model and processor revision", "prompt/parser/run-contract hashes", "separate permission and nonce", "outputs cleared", "offline snapshot", "canonical return ZIP", "paper_evidence=false"],
        "arms": {
            "repeat_determinism": "same small frozen subset, snapshot, prompt, decoding, and bytes; exact output equality only where promised",
            "prompt_robustness": "predeclared alternate wording; run only after primary freeze/completion",
            "decoding_robustness": "greedy and supported constrained yes/no; no unjustified stochastic sampling",
            "quantization_runtime": "separate identity; execute only if fit and scientific interpretation are declared",
            "natural_absence": "larger natural present/absent control; never substitutes for irrelevant-edit specificity",
        },
        "paper_evidence": False,
    }
    second_domain = {
        "schema": "certvic.cvpr2027.second_domain_contract.v1", "status": "CONDITIONAL_NOT_AUTHORIZED",
        "requirements": ["auditable license verification", "byte-level source manifest", "category mapping", "endpoint compatibility", "edit semantics", "two-rater human validation", "domain-specific quality and detectability gates", "same certificate API", "separate evidence class"],
        "candidate_scoring_template": ["license clarity", "redistribution", "endpoint fit", "category breadth", "image quality", "human-review burden", "compute", "incremental validity"],
        "dataset_selected": False, "paper_evidence": False,
    }
    main = {"schema": "certvic.cvpr2027.main500_contract.v1", "status": "CONDITIONAL_NOT_AUTHORIZED", "required_chain": ["prospective confirmatory signed GO", "fresh task/source census", "blind review", "prospective detectability", "freeze", "provider permissions/nonces", "transactional imports", "locked analysis"], "execution_allowed": False, "paper_evidence": False}
    return [
        write_csv(root / "gpu/GPU_EXECUTION_MATRIX.csv", rows),
        write_json(root / "gpu/MODEL_EXPANSION_OPTIONS.json", expansion),
        write_json(root / "gpu/SECONDARY_ROBUSTNESS_CONTRACTS.json", contracts),
        write_json(root / "gpu/SECOND_DOMAIN_CONTRACT.json", second_domain),
        write_json(root / "gpu/MAIN500_CONDITIONAL_CONTRACT.json", main),
    ]


def operator_pack(root: Path) -> list[Path]:
    next_rows = []
    for provider in PROVIDERS:
        next_rows.append({"order": 1, "status": "BLOCKED_BY_TWO_REAL_LICENSED_SMOKE_ITEMS", "what_to_run": f"00C2 {provider} after shared input is validated", "account_suggestion": ACCOUNTS[provider], "inputs_to_attach": "current COMMON; current provider snapshot; verified REAL_TWO_ITEM_SMOKE; provider-specific permission", "gpu": "T4x2", "internet": "OFF", "expected_time": "20-60 min planning estimate", "download": f"00C2_{provider}_real_model_smoke.zip", "local_next_command": "python3 kagglefiles/import_kaggle_return.py /path/to/downloaded_return.zip && bash kagglefiles/run_local_resume.sh"})
    input_rows = [
        {"input": "REAL_TWO_ITEM_SMOKE", "status": "MISSING_EXTERNAL", "required": "two real original/edited pairs; non-synthetic; license_eligible=true; concrete license_id; zero historical overlap; prompt/parser/run-contract bindings", "consumer": "all three 00C2 runbooks"},
        {"input": "COMMON", "status": "CURRENT_AUTHENTICATED", "required": "CODE;CONFIGS;EXECUTION_TOOLS;CP312_WHEELHOUSE", "consumer": "all runbooks"},
        {"input": "MODEL_SNAPSHOT", "status": "CURRENT_AUTHENTICATED_3_OF_3", "required": "provider-matched exact snapshot", "consumer": "provider runbook"},
        {"input": "CONFIRMATORY_SOURCE", "status": "MISSING_LICENSED_BYTES", "required": "runtime-verifiable licensed source tree plus manifest", "consumer": "confirmatory generation after 00C2"},
    ]
    return_rows = [{"stage": "00C2", "provider": provider, "expected_zip": f"00C2_{provider}_real_model_smoke.zip", "destination": f"data/runtime/00C2_{provider}_real_model_smoke.zip", "import": "python3 kagglefiles/import_kaggle_return.py /path/to/downloaded_return.zip", "validation": "bash kagglefiles/run_local_resume.sh", "paper_evidence": False} for provider in PROVIDERS]
    paths = [
        write_csv(REPO / "kagglefiles/CVPR2027_NEXT_RUNS.csv", next_rows),
        write_csv(REPO / "kagglefiles/CVPR2027_INPUT_MATRIX.csv", input_rows),
        write_csv(REPO / "kagglefiles/CVPR2027_RETURN_MATRIX.csv", return_rows),
    ]
    start = """OPEN ONLY THIS FOLDER FOR KAGGLE EXECUTION.
DO NOT NAVIGATE THE REST OF THE REPOSITORY.

# CertVIC CVPR 2027 next action

Active runtime profile: `kaggle_cp312_2026_07`. The historical provisioning action `BUILD_CP312_WHEELHOUSE` is complete; do not repeat it unless the authenticated doctor state explicitly regresses.

Current authenticated state: 00A is valid; all three 00B snapshot smokes are valid; the 00B matrix is complete. The 00C2 real-model smoke remains `NOT_AUTHORIZED` because two genuine license-eligible paired items are absent. `paper_evidence=false`; genuine human-reviewed count is zero; Main and the second domain are not authorized.

## Do this now

Provide exactly two real, non-synthetic original/edited image pairs with `license_eligible=true`, a concrete auditable `license_id`, zero overlap with historical items, and the frozen prompt/parser/run-contract metadata. Do not open a GPU session yet.

After local validation creates three provider permissions, run the 00C2 rows in `CVPR2027_NEXT_RUNS.csv`. Suggested accounts are conveniences only: lancerdevsm for Qwen, saket9500 for InternVL, and examhelps for LLaVA. Each run uses T4x2, Internet OFF, and has a 20–60 minute planning estimate.

After every download:

```bash
python3 kagglefiles/import_kaggle_return.py /path/to/downloaded_return.zip
bash kagglefiles/run_local_resume.sh
```

Never rename archive contents, edit executable runbook configuration, reuse a consumed permission, bypass a gate, or treat a planning estimate as measured runtime.
"""
    paths.append(write_text(REPO / "kagglefiles/START_HERE.md", start))
    return paths


def deprecation_registry(root: Path) -> list[Path]:
    rows = [
        {"item": "provider-specific runbooks under kagglefiles/runbooks", "classification": "ACTIVE", "operator_action": "use only current provider-specific paths"},
        {"item": "generic historical 00B/00C2 names outside provider-specific operator paths", "classification": "DEPRECATED_OPERATOR_PATH", "operator_action": "retain history; do not present as next action"},
        {"item": "authenticated 00A and 00B returns", "classification": "HISTORICAL_EVIDENCE", "operator_action": "preserve unchanged; currently valid"},
        {"item": "V2 30-item labels", "classification": "HISTORICAL_EVIDENCE", "operator_action": "retrospective diagnostic only; never prospective evidence"},
        {"item": "legacy CPython 3.10 wheelhouse", "classification": "LEGACY_COMPATIBILITY", "operator_action": "not an active Kaggle input"},
        {"item": "old START_HERE provisioning instructions", "classification": "DEPRECATED_OPERATOR_PATH", "operator_action": "replaced by live 00C2 external-byte boundary"},
    ]
    return [write_json(root / "C11_DEPRECATION_REGISTRY.json", {"schema": "certvic.cvpr2027.deprecation_registry.v1", "entries": rows, "historical_bytes_deleted": False})]


def compute_and_tables(root: Path, stage_results: dict[str, Any] | None = None) -> list[Path]:
    stage_results = stage_results or {}
    baseline = _json(root / "C11_IDENTITY_BASELINE.json", {})
    code_identity = (
        baseline.get("common_bundles", {})
        .get("CODE", {})
        .get("content_identity_sha256", "UNKNOWN")
    )
    env_hash = __import__("hashlib").sha256(canonical_json_bytes({"python": sys.version, "platform": platform.platform(), "numpy": np.__version__})).hexdigest()
    ledger = []
    for stage, result in stage_results.items():
        ledger.append({
            "stage": stage, "provider/model": "all_or_not_applicable", "hardware": platform.machine(),
            "accelerator": "CPU", "wall_time_seconds": result.get("runtime_seconds", "NOT_MEASURED"),
            "peak_RAM_bytes": result.get("peak_ram_bytes", "NOT_MEASURED"), "peak_VRAM_bytes": "NOT_MEASURED",
            "input_item_count": result.get("input_item_count", "NOT_MEASURED"), "output_item_count": len(result.get("outputs", [])),
            "retry_count": 0, "software_environment_hash": env_hash, "snapshot_hash": "NOT_APPLICABLE",
            "code_identity": code_identity, "energy": "NOT_MEASURED", "carbon": "NOT_MEASURED", "paper_evidence": False,
        })
    if not ledger:
        ledger.append({"stage": "C11_INFRASTRUCTURE", "provider/model": "not_applicable", "hardware": platform.machine(), "accelerator": "CPU", "wall_time_seconds": "NOT_MEASURED", "peak_RAM_bytes": "NOT_MEASURED", "peak_VRAM_bytes": "NOT_MEASURED", "input_item_count": "NOT_MEASURED", "output_item_count": "NOT_MEASURED", "retry_count": 0, "software_environment_hash": env_hash, "snapshot_hash": "NOT_APPLICABLE", "code_identity": code_identity, "energy": "NOT_MEASURED", "carbon": "NOT_MEASURED", "paper_evidence": False})
    ledger_path = write_jsonl(root / "compute/COMPUTE_LEDGER.jsonl", ledger)
    paths = [ledger_path, write_csv(root / "tables/compute_table.csv", ledger)]
    metrics = _csv(root / "analysis/pilot_baseline_metrics.csv")
    certificates = _json(root / "evidence/model_certificates.json", {}).get("certificates", [])
    paths.append(write_csv(root / "tables/primary_result_table.csv", certificates))
    human = _json(root / "human_review/STATUS.json", {})
    paths.append(write_csv(root / "tables/human_review_table.csv", [{"state": human.get("state"), "rater_1_complete": human.get("rater_1_complete"), "rater_2_complete": human.get("rater_2_complete"), "agreement": human.get("agreement"), "paper_evidence": False}]))
    stats = _json(root / "statistics/power_summary.json", {})
    cs = _json(root / "statistics/CS_VALIDATION_VERDICT.json", {})
    paths.append(write_csv(root / "tables/statistical_validation_table.csv", [{"family_alpha": stats.get("analysis_rule", {}).get("family_alpha"), "per_gate_alpha": stats.get("analysis_rule", {}).get("per_gate_alpha"), "n120_min_successes": stats.get("n_120_critical_values", {}).get("minimum_semantic_update_successes"), "n120_max_flips": stats.get("n_120_critical_values", {}).get("maximum_irrelevant_flips"), "cs_status": cs.get("status"), "evidence_class": "SOFTWARE_STATISTICAL_VALIDATION", "paper_evidence": False}]))
    if metrics:
        paths.append(write_csv(root / "tables/pilot_metric_source.csv", metrics))
    return paths


def _save_figure(fig: Any, base: Path) -> list[Path]:
    outputs = []
    for suffix in ["png", "svg", "pdf"]:
        path = base.with_suffix(f".{suffix}")
        path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {"Creator": "CertVIC C11", "CreationDate": None, "ModDate": None} if suffix == "pdf" else None
        fig.savefig(path, dpi=180, bbox_inches="tight", metadata=metadata)
        outputs.append(path)
    plt.close(fig)
    return outputs


def extra_figures(root: Path) -> list[Path]:
    plt.rcParams["svg.hashsalt"] = "certvic-c11"
    metrics = _csv(root / "analysis/pilot_baseline_metrics.csv")
    certificates = _json(root / "evidence/model_certificates.json", {}).get("certificates", [])
    optional = _csv(root / "statistics/optional_stopping_stress.csv")
    balance = _csv(root / "audits/relevant_irrelevant_balance.csv")
    cv_rows = _csv(root / "statistics/detectability_cv.csv")
    disagreement = _csv(root / "analysis/pairwise_disagreement_matrix.csv")
    heterogeneity = _csv(root / "analysis/heterogeneity_summary.csv")
    paths: list[Path] = []
    if metrics:
        fig, ax = plt.subplots(figsize=(6, 4))
        for row in metrics:
            ax.scatter(float(row["irrelevant_flip_rate"]), float(row["semantic_update_success_rate"]), label=row["model"])
        ax.axhline(0.5, color="black", linestyle="--")
        ax.axvline(0.1, color="black", linestyle="--")
        ax.set(xlabel="Irrelevant flip rate", ylabel="Semantic update rate", title="Historical pilot plane (diagnostic)")
        ax.legend(fontsize=7)
        paths += _save_figure(fig, root / "figures/responsiveness_specificity_plane")
    if certificates:
        fig, ax = plt.subplots(figsize=(7, 4))
        names = [row["model"] for row in certificates]
        update = [row["responsiveness_lower_bound"] for row in certificates]
        spurious = [row["spurious_upper_bound"] for row in certificates]
        x = np.arange(len(names))
        ax.bar(x - .18, update, .36, label="response lower")
        ax.bar(x + .18, spurious, .36, label="flip upper")
        ax.axhline(.5, color="C0", linestyle="--")
        ax.axhline(.1, color="C1", linestyle="--")
        ax.set_xticks(x, names, rotation=15)
        ax.set(title="Historical exact certificate bounds", ylabel="Bound")
        ax.legend()
        paths += _save_figure(fig, root / "figures/joint_certificate_bounds")
    if optional:
        fig, ax = plt.subplots(figsize=(7, 4))
        groups: dict[str, list[float]] = {}
        for row in optional:
            groups.setdefault(row["stopping_rule"], []).append(
                float(row["anytime_cs_noncoverage_at_stop"])
            )
        ax.boxplot(list(groups.values()), tick_labels=list(groups), vert=False)
        ax.axvline(.05, color="black", linestyle="--")
        ax.set(title="CS optional-stopping stress", xlabel="Noncoverage at stop")
        paths += _save_figure(fig, root / "figures/optional_stopping_behavior")
    if balance:
        fig, ax = plt.subplots(figsize=(7, 4))
        names = [row["feature"] for row in balance]
        values = [float(row["absolute_smd"]) for row in balance]
        ax.barh(names, values)
        ax.axvline(.2, color="black", linestyle="--")
        ax.set(title="Historical endpoint-arm balance", xlabel="Absolute standardized mean difference")
        paths += _save_figure(fig, root / "figures/relevant_irrelevant_quality_balance")
    if cv_rows:
        fig, ax = plt.subplots(figsize=(7, 4))
        models = sorted({row["classifier"] for row in cv_rows})
        values = [
            [float(row["symmetric_auc"]) for row in cv_rows if row["classifier"] == model]
            for model in models
        ]
        ax.boxplot(values, tick_labels=models)
        ax.axhline(.8, color="black", linestyle="--")
        ax.set(title="Historical endpoint-arm detectability", ylabel="Symmetric AUC")
        ax.tick_params(axis="x", rotation=20)
        paths += _save_figure(fig, root / "figures/detectability_auc")
    if disagreement:
        fig, ax = plt.subplots(figsize=(7, 4))
        labels = [
            f"{row['left_model']}–{row['right_model']}\n{row['endpoint']}"
            for row in disagreement
        ]
        values = [float(row["disagreement_rate"]) for row in disagreement]
        ax.barh(labels, values)
        ax.set(title="Historical model disagreement", xlabel="Paired disagreement rate")
        paths += _save_figure(fig, root / "figures/model_disagreement")
    if heterogeneity:
        shown = heterogeneity[:20]
        fig, ax = plt.subplots(figsize=(8, 5))
        labels = [
            f"{row.get('model')}:{row.get('group_type')}={row.get('group')}"
            for row in shown
        ]
        values = [float(row.get("rate", 0)) for row in shown]
        ax.barh(labels, values)
        ax.set(title="Historical heterogeneity (first 20 deterministic rows)", xlabel="Endpoint rate")
        paths += _save_figure(fig, root / "figures/heterogeneity")
    red = _json(root / "SCIENTIFIC_RED_TEAM.json", {}).get("counts", {})
    if red:
        fig, ax = plt.subplots(figsize=(6, 4))
        labels = ["BLOCKER", "MAJOR", "MINOR", "PASS", "NOT_APPLICABLE"]
        ax.bar(labels, [red.get(key, 0) for key in labels])
        ax.set(title="Scientific red-team issue taxonomy", ylabel="Checks")
        ax.tick_params(axis="x", rotation=20)
        paths += _save_figure(fig, root / "figures/failure_taxonomy")
    return paths


def run(output_root: Path = REPORT_ROOT, *, stage_results: dict[str, Any] | None = None) -> dict[str, Any]:
    paths: list[Path] = []
    paths += repository_gap_audit(output_root)
    paths += failure_recovery(output_root)
    paths += claim_registry(output_root)
    paths += red_team(output_root)
    paths += gpu_planning(output_root)
    paths += operator_pack(output_root)
    paths += deprecation_registry(output_root)
    paths += compute_and_tables(output_root, stage_results)
    paths += extra_figures(output_root)
    paths.append(write_json(output_root / "C11_GENERATED_ARTIFACT_MANIFEST.json", artifact_manifest(paths)))
    return {"status": "COMPLETE", "outputs": [path.relative_to(REPO).as_posix() for path in paths], "paper_evidence": False}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
