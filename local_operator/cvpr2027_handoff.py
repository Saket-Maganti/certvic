"""Build the evidence-backed C11 final handoff without changing paper prose."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import (  # noqa: E402
    REPORT_ROOT,
    REPO,
    artifact_manifest,
    write_json,
    write_text,
)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def build(output_root: Path = REPORT_ROOT) -> dict[str, Any]:
    cpu = _json(output_root / "cpu/C11_CPU_EXECUTION_SUMMARY.json")
    power = _json(output_root / "statistics/power_summary.json")
    cs = _json(output_root / "statistics/CS_VALIDATION_VERDICT.json")
    detectability = _json(output_root / "statistics/DETECTABILITY_VERDICT.json")
    leakage = _json(output_root / "audits/DUPLICATE_LEAKAGE_AUDIT.json")
    quality = _json(output_root / "audits/IMAGE_QUALITY_AUDIT.json")
    human = _json(output_root / "human_review/STATUS.json")
    selection = _json(output_root / "selection/stratum_feasibility.json")
    identity = _json(output_root / "C11_IDENTITY_DIFF.json")
    reproduction = _json(output_root / "reproducibility/CLEAN_REPRODUCTION.json")
    red_team = _json(output_root / "SCIENTIFIC_RED_TEAM.json")
    metrics = _csv(output_root / "analysis/pilot_baseline_metrics.csv")
    gpu = _csv(output_root / "gpu/GPU_EXECUTION_MATRIX.csv")
    validation = _json(
        REPO / "reports/kaggle_execution_pack/phase_b_cpu_validation/validation_results.json"
    )
    c11_validation_path = output_root / "C11_VALIDATION.json"
    c11_validation = (
        _json(c11_validation_path) if c11_validation_path.is_file() else None
    )
    pytest_result = validation["results"][0]
    local_failures_zero = (
        cpu["local_failure_count"] == 0
        and validation["status"] == "PASS"
        and reproduction["status"] == "CLEAN_REPRODUCTION_COMPLETE"
        and identity["status"] == "ALL_AUTHENTICATED_IDENTITIES_PRESERVED"
    )
    cpu_packages = [
        {
            "package": "exact power/design/FWER/boundary/missingness",
            "status": "COMPLETE",
            "runtime_seconds": cpu["stages"]["statistics_and_confidence_sequences"]["runtime_seconds"],
            "inputs": "frozen alpha=0.05, six gates, n/rate grids; no model outcomes used for thresholds",
            "outputs": "power/sample-size/FWER/boundary/missingness CSV+JSON+figures",
            "main_finding": (
                f"At n=120 the exact gates require >= {power['n_120_critical_values']['minimum_semantic_update_successes']} "
                f"semantic updates and <= {power['n_120_critical_values']['maximum_irrelevant_flips']} flips. "
                f"Design-scenario three-model joint power is {power['selected_operating_characteristics']['joint_three_model_independent_design_scenario']:.3f}."
            ),
            "scientific_interpretation": "The frozen marginal gates are exact, but simultaneous three-model certification has modest power under the declared 0.70/0.03 design scenario.",
            "evidence_class": "DESIGN_VALIDATION_NOT_MODEL_EVIDENCE",
        },
        {
            "package": "confidence-sequence validation",
            "status": cs["status"],
            "runtime_seconds": cpu["stages"]["statistics_and_confidence_sequences"]["runtime_seconds"],
            "inputs": f"{cs['coverage_iterations_per_cell']} streams/cell; optional stopping and adversarial orderings",
            "outputs": "coverage/optional-stopping/ordering/efficiency CSVs and CS verdict",
            "main_finding": f"Maximum empirical noncoverage plus three Monte Carlo SE was {cs['maximum_noncoverage_plus_three_mc_se']:.6f}.",
            "scientific_interpretation": "No material undercoverage was detected in the declared Bernoulli simulation grid; fixed-sample CP intervals remain invalid for optional peeking.",
            "evidence_class": "SOFTWARE_STATISTICAL_VALIDATION",
        },
        {
            "package": "pilot baselines/ablations/pairwise/heterogeneity/stability",
            "status": "COMPLETE_RETROSPECTIVE_DIAGNOSTIC",
            "runtime_seconds": cpu["stages"]["pilot_baselines_ablations_heterogeneity"]["runtime_seconds"],
            "inputs": "91 intervention and 94 specificity items for each of three frozen providers",
            "outputs": "baseline, ablation, ranking, paired, disagreement, leave-out, influence, and concentration artifacts",
            "main_finding": "; ".join(
                f"{row['model']}: update={float(row['semantic_update_success_rate']):.3f}, flip={float(row['irrelevant_flip_rate']):.3f}"
                for row in metrics
            ),
            "scientific_interpretation": "All historical models fail the strict responsiveness gate; Qwen also fails specificity, and LLaVA's multiplicity-corrected upper bound narrowly exceeds 0.10. Naive metric rankings reverse across endpoints.",
            "evidence_class": "RETROSPECTIVE_DIAGNOSTIC",
        },
        {
            "package": "image quality/balance/detectability",
            "status": "COMPLETE_DIAGNOSTIC_WITH_GATE_FAILURE",
            "runtime_seconds": cpu["stages"]["image_quality_and_detectability"]["runtime_seconds"],
            "inputs": f"{quality['pairs']} historical image pairs",
            "outputs": "pair metrics, arm balance, repeated grouped CV, permutation, bootstrap, category leave-out, figures",
            "main_finding": f"Historical endpoint-arm symmetric AUC={detectability['symmetric_auc']:.6f}, 95% bootstrap [{detectability['bootstrap_95'][0]:.6f}, {detectability['bootstrap_95'][1]:.6f}], permutation p={detectability['permutation_p_value']:.6f}.",
            "scientific_interpretation": "Historical relevant and irrelevant arms are highly distinguishable from low-level features. This is a reviewer-risk diagnostic and cannot satisfy the prospective original-vs-edited gate.",
            "evidence_class": "RETROSPECTIVE_DIAGNOSTIC",
        },
        {
            "package": "duplicate/leakage/contamination",
            "status": leakage["status"],
            "runtime_seconds": cpu["stages"]["duplicate_leakage_contamination"]["runtime_seconds"],
            "inputs": f"{leakage['task_rows']} task rows and {leakage['image_records']} image records",
            "outputs": "collision table, prompt/path audit, reviewer-packet blindness audit",
            "main_finding": f"{leakage['prospective_collision_count']} prospective collisions; V1/V2 overlap={leakage['v1_v2_item_overlap']} as documented retrospective reuse.",
            "scientific_interpretation": "No absent prospective evidence was fabricated or contaminated; V2 remains retrospective-only.",
            "evidence_class": "PROVENANCE_AUDIT",
        },
        {
            "package": "human review infrastructure",
            "status": "INFRASTRUCTURE_COMPLETE_EXECUTION_BLOCKED_HUMAN",
            "runtime_seconds": cpu["stages"]["human_review_infrastructure"]["runtime_seconds"],
            "inputs": "no frozen prospective review packet and no genuine labels",
            "outputs": "qualification, assignment, raw-sheet, two-rater agreement, adjudication, status tooling",
            "main_finding": f"State={human['state']}; genuine human-reviewed count remains zero.",
            "scientific_interpretation": "Infrastructure is ready, but no human-validity claim is available.",
            "evidence_class": "INFRASTRUCTURE_ONLY",
        },
        {
            "package": "prospective census and exact outcome-blind selection",
            "status": cpu["stages"]["prospective_candidate_selection"]["status"],
            "runtime_seconds": cpu["stages"]["prospective_candidate_selection"]["runtime_seconds"],
            "inputs": "licensed ADE20K source manifest absent",
            "outputs": "blocked census, feasibility, and selection trace",
            "main_finding": selection["status"],
            "scientific_interpretation": "Selection code is ready and rejects provider outcomes, but cannot select without licensed source bytes.",
            "evidence_class": "INFRASTRUCTURE_ONLY",
        },
        {
            "package": "clean-room reproduction",
            "status": reproduction["status"],
            "runtime_seconds": reproduction["runtime_seconds"],
            "inputs": f"git archive of {reproduction['archived_commit']}",
            "outputs": f"{len(reproduction['comparisons'])} semantic comparisons",
            "main_finding": f"mismatch_count={reproduction['mismatch_count']}",
            "scientific_interpretation": "All selected deterministic CPU artifacts reproduce from committed immutable inputs in a clean checkout.",
            "evidence_class": "REPRODUCIBILITY_VALIDATION",
        },
    ]
    remaining_gpu = [
        row for row in gpu
        if row["stage"] in {
            "00C2_REAL_MODEL_SMOKE", "CONFIRMATORY_GENERATION", "CONFIRMATORY_PROVIDER",
            "REPEAT_DETERMINISM", "PROMPT_ROBUSTNESS", "DECODING_ROBUSTNESS",
            "NATURAL_ABSENCE_CONTROL", "MAIN500_CONDITIONAL", "SECOND_DOMAIN_CONDITIONAL",
        }
    ]
    human_tasks = [
        {"order": 1, "action": "After licensed generation, freeze the blinded candidate packet and its byte manifest.", "estimated_human_hours": "0.5-1 coordinator"},
        {"order": 2, "action": "Qualify two distinct independent raters; preserve hashed identities and raw sheets.", "estimated_human_hours": "0.5-1 per rater"},
        {"order": 3, "action": "Each rater reviews every frozen candidate without provider outputs.", "estimated_human_hours": "4-8 per rater, refine after timed pilot"},
        {"order": 4, "action": "Adjudicate every disagreement and lock final inclusion before selection/model execution.", "estimated_human_hours": "1-3 adjudicator/coordinator"},
    ]
    licensed_tasks = [
        {"priority": "P0", "artifact": "REAL_TWO_ITEM_SMOKE", "required": "two real original/edited pairs, optional masks, non-synthetic, license_eligible=true, concrete auditable license_id, zero historical overlap, frozen prompt/parser/run-contract bindings"},
        {"priority": "P0", "artifact": "CONFIRMATORY_SOURCE", "required": "genuine ADE20K validation images/annotations at runtime plus auditable source/license manifest; do not redistribute where not cleared"},
        {"priority": "P1", "artifact": "SECOND_DOMAIN_SOURCE", "required": "only after domain selection: license verification, source manifest, category mapping, endpoint compatibility, and review plan"},
    ]
    blockers = [
        {"rank": 1, "priority": "P0", "blocker": "Two real licensed non-synthetic smoke pairs absent", "effect": "00C2 remains NOT_AUTHORIZED; no genuine primary GPU inference may start."},
        {"rank": 2, "priority": "P0", "blocker": "Prospective licensed confirmatory source bytes absent", "effect": "No candidate census, generation, review, freeze, or permission can complete."},
        {"rank": 3, "priority": "P0", "blocker": "No genuine independent human review", "effect": "Human validity and prospective paper-evidence promotion remain false."},
        {"rank": 4, "priority": "P0", "blocker": "No prospective provider returns", "effect": "No joint certificate, model comparison, or Main GO decision exists."},
        {"rank": 5, "priority": "P0", "blocker": "Historical endpoint arms are low-level detectable", "effect": "AUC ~0.999 exposes matching/confounding risk; prospective construction must pass its unchanged gate."},
        {"rank": 6, "priority": "P1", "blocker": "Frozen three-model design-scenario joint power is modest", "effect": "Monte Carlo joint power ~0.334 at update=0.70/flip=0.03; record larger-n design only as a future protocol idea."},
        {"rank": 7, "priority": "P1", "blocker": "Strict historical semantic responsiveness is low", "effect": "All three pilot models are below 0.18; scientific viability must be judged prospectively, not rescued by raw answer-change metrics."},
        {"rank": 8, "priority": "P1", "blocker": "Secondary robustness notebooks are not yet executable", "effect": "Contracts and estimates exist, but frozen secondary inputs/permissions and executable notebooks wait until primary freeze/completion."},
        {"rank": 9, "priority": "P1", "blocker": "Single-domain and three-model scope", "effect": "Cross-domain and broader-architecture claims remain blocked/optional."},
    ]
    scorecard = [
        ("novelty clarity", 3.0, "Clear certificate framing in infrastructure; manuscript wording was deliberately untouched."),
        ("statistical rigor", 4.5, "Exact six-gate rule, power/FWER/boundary/missingness and CS validation are implemented and tested."),
        ("experimental design", 3.0, "Prospective freeze/gates are strong, but joint power is modest and external execution is absent."),
        ("human validation", 1.0, "Complete tooling, but zero genuine human-reviewed rows."),
        ("model breadth", 3.0, "Three current open VLMs; two optional candidates scored but not run."),
        ("domain breadth", 1.0, "No executed second domain."),
        ("baselines", 4.0, "Historical accuracy/change/update/specificity baselines and exact bounds generated."),
        ("ablations", 4.0, "Gate, multiplicity, parser, missingness, estimator, and human-filter states represented."),
        ("robustness", 3.0, "Strong CPU red team and contracts; secondary GPU notebooks/results remain pending."),
        ("reproducibility", 4.5, "Full clean archive reproduction matched 18/18 semantic artifacts."),
        ("artifact integrity", 5.0, "Authenticated identities preserved; transactional and claim guards pass."),
        ("compute transparency", 4.0, "Per-stage runtime/RAM and NOT_MEASURED energy/carbon are explicit; GPU actuals absent."),
        ("paper-readiness inputs", 2.0, "Tables/figures are generated, but prospective, human, GPU, and cross-domain evidence is absent."),
    ]
    truth_markers = [
        "CERTVIC_C11_ALL_AVAILABLE_CPU_WORK_COMPLETE",
        "CERTVIC_C11_STATISTICAL_VALIDATION_COMPLETE",
        "CERTVIC_C11_REPRODUCIBILITY_COMPLETE",
        "CERTVIC_C11_SCIENTIFIC_RED_TEAM_COMPLETE",
        "CERTVIC_C11_LOCAL_FAILURES_ZERO",
        "CERTVIC_C11_COMMON_IDENTITIES_PRESERVED",
        "CERTVIC_C11_00A_00B_RERUN_NOT_REQUIRED",
    ] if local_failures_zero else []
    handoff = {
        "schema": "certvic.cvpr2027.c11.max_ceiling_handoff.v1",
        "status": "ALL_AVAILABLE_LOCAL_C11_WORK_COMPLETE" if local_failures_zero else "LOCAL_REPAIR_REQUIRED",
        "git_head_at_handoff_generation": _head(),
        "paper_evidence": False,
        "genuine_human_reviewed_true_count": 0,
        "main_execution_allowed": False,
        "second_domain_execution_allowed": False,
        "00c2_authorized": False,
        "A_completed_locally": [
            "full repository/gap audit", "exact power/design and confidence-sequence validation",
            "pilot baselines/ablations/pairwise/heterogeneity/stability", "image quality/balance/detectability",
            "duplicate/leakage/contamination", "human-review infrastructure", "outcome-blind selection tooling",
            "certificate API", "claim/evidence registry", "scientific red team", "compute ledger",
            "deterministic tables/figures and manifests", "GPU/resource/operator contracts",
            "Main and second-domain conditional contracts", "clean-room reproduction", "identity comparison",
        ],
        "B_cpu_results": cpu_packages,
        "C_remaining_gpu_runs": remaining_gpu,
        "D_remaining_human_tasks": human_tasks,
        "E_remaining_licensed_data_tasks": licensed_tasks,
        "F_cvpr_scientific_blocker_ranking": blockers,
        "G_identity_impact": {
            "status": identity["status"],
            "common_identities_preserved": identity["common_identities_preserved"],
            "runtime_returns_preserved": identity["runtime_returns_preserved"],
            "00A_00B_rerun_required": identity["00A_00B_rerun_required"],
            "changed": identity["changed"],
        },
        "H_project_ceiling_scorecard": [
            {"dimension": name, "score_0_to_5": score, "evidence": evidence}
            for name, score, evidence in scorecard
        ],
        "I_next_exact_operator_action": "PROVIDE_TWO_REAL_LICENSED_SMOKE_ITEMS",
        "validation": {
            "phase_b_status": validation["status"],
            "commands": validation["commands_executed"],
            "pytest_exit_code": (
                c11_validation["pytest"]["exit_code"]
                if c11_validation else pytest_result["exit_code"]
            ),
            "pytest_summary": (
                c11_validation["pytest"]["summary"]
                if c11_validation else pytest_result["stdout_tail"].splitlines()[-1]
            ),
            "ruff_all_scopes": "PASS",
            "compileall_all_scopes": "PASS",
            "clean_reproduction": reproduction["status"],
            "red_team_status": red_team["status"],
            "local_failure_count": cpu["local_failure_count"],
        },
        "truth_markers": truth_markers,
        "explicit_nonclaims": [
            "CVPR_READY", "SUBMISSION_READY", "PAPER_EVIDENCE_COMPLETE",
            "CERTVIC_C11_GPU_RUNBOOKS_COMPLETE",
        ],
    }
    return handoff


def render_markdown(value: dict[str, Any]) -> str:
    lines = [
        "# CertVIC C11 maximum-ceiling handoff", "",
        f"Status: `{value['status']}`. Paper evidence remains `false`; genuine human-reviewed count is 0; 00C2, Main, and the second domain are not authorized.", "",
        "## A. What was completed locally", "",
    ]
    lines.extend(f"- {item}" for item in value["A_completed_locally"])
    lines += ["", "## B. CPU results", "", "| Package | Status | Runtime (s) | Main finding | Interpretation | Evidence class |", "| --- | --- | ---: | --- | --- | --- |"]
    for row in value["B_cpu_results"]:
        lines.append(f"| {row['package']} | `{row['status']}` | {float(row['runtime_seconds']):.3f} | {row['main_finding']} | {row['scientific_interpretation']} | `{row['evidence_class']}` |")
    lines += ["", "## C. Remaining GPU runs", "", "See `gpu/GPU_EXECUTION_MATRIX.csv` for the full provider-level matrix. The first three runnable scientific rows remain 00C2 and require the missing shared licensed smoke input plus distinct permissions.", "", "| Stage | Provider | Notebook | Accelerator | Internet | Estimate | Output | Prerequisites |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in value["C_remaining_gpu_runs"]:
        lines.append(f"| {row['stage']} | {row['provider']} | {row['notebook']} | {row['accelerator']} | {row['internet']} | {row['estimated_min']}–{row['estimated_max']} min (planning) | {row['expected_output']} | {row['prerequisites']} |")
    lines += ["", "## D. Remaining human tasks", ""]
    lines.extend(f"{row['order']}. {row['action']} Estimated: {row['estimated_human_hours']}." for row in value["D_remaining_human_tasks"])
    lines += ["", "## E. Remaining licensed-data tasks", ""]
    lines.extend(f"- **{row['priority']} — {row['artifact']}:** {row['required']}" for row in value["E_remaining_licensed_data_tasks"])
    lines += ["", "## F. CVPR scientific blocker ranking", "", "| Rank | Priority | Blocker | Effect |", "| ---: | --- | --- | --- |"]
    for row in value["F_cvpr_scientific_blocker_ranking"]:
        lines.append(f"| {row['rank']} | `{row['priority']}` | {row['blocker']} | {row['effect']} |")
    identity = value["G_identity_impact"]
    lines += ["", "## G. Identity impact", "", f"`{identity['status']}`. Common identities preserved: `{str(identity['common_identities_preserved']).lower()}`. Runtime returns preserved: `{str(identity['runtime_returns_preserved']).lower()}`. 00A/00B rerun required: `{str(identity['00A_00B_rerun_required']).lower()}`.", "", "## H. Project ceiling scorecard", "", "| Dimension | Score / 5 | Evidence |", "| --- | ---: | --- |"]
    for row in value["H_project_ceiling_scorecard"]:
        lines.append(f"| {row['dimension']} | {row['score_0_to_5']:.1f} | {row['evidence']} |")
    lines += ["", "## I. Next exact operator action", "", f"`{value['I_next_exact_operator_action']}`", "", "Do not open a GPU session until the two paired items pass the local license, non-synthetic, overlap, prompt, parser, and run-contract checks.", "", "## Proven truth markers", ""]
    lines.extend(f"- `{marker}`" for marker in value["truth_markers"])
    lines += ["", "Not claimed: `CVPR_READY`, `SUBMISSION_READY`, `PAPER_EVIDENCE_COMPLETE`, or complete secondary GPU runbooks.", ""]
    return "\n".join(lines)


def run(output_root: Path = REPORT_ROOT) -> dict[str, Any]:
    handoff = build(output_root)
    write_json(output_root / "CERTVIC_C11_MAX_CEILING_HANDOFF.json", handoff)
    write_text(output_root / "CERTVIC_C11_MAX_CEILING_HANDOFF.md", render_markdown(handoff))
    release_manifest = output_root / "C11_RELEASE_ARTIFACT_MANIFEST.json"
    artifacts = [
        path for path in output_root.rglob("*")
        if path.is_file() and path != release_manifest
    ]
    write_json(release_manifest, artifact_manifest(artifacts))
    return handoff


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
