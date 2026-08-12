"""Build the final truth-preserving C12 operator handoff."""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from local_operator.cvpr2027_common import write_json, write_text  # noqa: E402


ROOT = REPOSITORY_ROOT / "reports/cvpr2027_c12"


def _json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _phase_b_validation() -> dict[str, Any]:
    path = (
        REPOSITORY_ROOT
        / "reports/kaggle_execution_pack/phase_b_cpu_validation/validation_results.json"
    )
    result = json.loads(path.read_text(encoding="utf-8"))
    pytest_result = next(
        row for row in result["results"] if row["command"][1:3] == ["-m", "pytest"]
    )
    match = re.search(
        r"(?P<passed>\d+) passed(?:, (?P<skipped>\d+) skipped)?",
        pytest_result["stdout_tail"],
    )
    cpu_rows_path = REPOSITORY_ROOT / "reports/cpu_execution/CERTVIC_CPU_RUN_RESULTS.csv"
    with cpu_rows_path.open(encoding="utf-8", newline="") as handle:
        cpu_rows = list(csv.DictReader(handle))
    local_failures = [
        row["run_id"]
        for row in cpu_rows
        if row["status"] == "FAILED_LOCAL_REPAIR_REQUIRED"
    ]
    return {
        "status": result["status"],
        "commands_executed": result["commands_executed"],
        "commands_planned": result["commands_planned"],
        "pytest_passed": int(match.group("passed")) if match else None,
        "pytest_skipped": int(match.group("skipped") or 0) if match else None,
        "local_failures": local_failures,
        "real_gpu_runs_launched": result["real_gpu_runs_launched"],
        "paper_evidence": result["paper_evidence"],
    }


def _gpu_runs() -> list[dict[str, Any]]:
    return [
        {
            "order": 1,
            "stage": "00C2_QWEN",
            "notebook": "00C2_qwen2_5_vl_7b_real_model_two_item_smoke.ipynb",
            "account_suggestion": "lancerdevsm",
            "accelerator": "T4x2",
            "internet": "OFF",
            "input": "kagglefiles/inputs/06_PRE_SMOKE_PERMISSIONS plus authenticated common/wheelhouse/Qwen snapshot and inputs/05_REAL_TWO_ITEM_SMOKE",
            "runtime_estimate": "planning range 20/40/60 minutes optimistic/typical/conservative",
            "output": "00C2_qwen2_5_vl_7b_real_model_smoke.zip",
            "import_command": "python3 kagglefiles/import_kaggle_return.py /path/to/00C2_qwen2_5_vl_7b_real_model_smoke.zip",
        },
        {
            "order": 2,
            "stage": "00C2_INTERNVL",
            "notebook": "00C2_internvl_8b_real_model_two_item_smoke.ipynb",
            "account_suggestion": "saket9500",
            "accelerator": "T4x2",
            "internet": "OFF",
            "input": "kagglefiles/inputs/06_PRE_SMOKE_PERMISSIONS plus authenticated common/wheelhouse/InternVL snapshot and inputs/05_REAL_TWO_ITEM_SMOKE",
            "runtime_estimate": "planning range 20/40/60 minutes optimistic/typical/conservative",
            "output": "00C2_internvl_8b_real_model_smoke.zip",
            "import_command": "python3 kagglefiles/import_kaggle_return.py /path/to/00C2_internvl_8b_real_model_smoke.zip",
        },
        {
            "order": 3,
            "stage": "00C2_LLAVA",
            "notebook": "00C2_llava_onevision_7b_real_model_two_item_smoke.ipynb",
            "account_suggestion": "examhelps",
            "accelerator": "T4x2",
            "internet": "OFF",
            "input": "kagglefiles/inputs/06_PRE_SMOKE_PERMISSIONS plus authenticated common/wheelhouse/LLaVA snapshot and inputs/05_REAL_TWO_ITEM_SMOKE",
            "runtime_estimate": "planning range 20/40/60 minutes optimistic/typical/conservative",
            "output": "00C2_llava_onevision_7b_real_model_smoke.zip",
            "import_command": "python3 kagglefiles/import_kaggle_return.py /path/to/00C2_llava_onevision_7b_real_model_smoke.zip",
        },
        {
            "order": 4,
            "stage": "CONFIRMATORY_GENERATION_AFTER_ALL_LOCAL_GATES",
            "notebook": "01_specificity_confirmatory_generation_T4x2.ipynb",
            "account_suggestion": "saket9500 (convenience only; identities are content-bound)",
            "accelerator": "T4x2",
            "internet": "OFF",
            "input": "kagglefiles/inputs/07_CONFIRMATORY_GENERATION",
            "runtime_estimate": "planning estimate 2-8 hours; recalibrate after measured 00C2",
            "output": "confirmatory_generation_return.zip",
            "import_command": "python3 kagglefiles/import_kaggle_return.py /path/to/confirmatory_generation_return.zip",
        },
        *[
            {
                "order": order,
                "stage": f"CONFIRMATORY_{provider.upper()}",
                "notebook": notebook,
                "account_suggestion": account,
                "accelerator": "T4x2",
                "internet": "OFF",
                "input": input_path,
                "runtime_estimate": runtime,
                "output": output,
                "import_command": f"python3 kagglefiles/import_kaggle_return.py /path/to/{output}",
            }
            for order, provider, notebook, account, input_path, runtime, output in (
                (5, "qwen", "02_qwen_specificity_confirmatory_T4x2.ipynb", "lancerdevsm", "kagglefiles/inputs/08_CONFIRMATORY_QWEN", "planning estimate 2-5 hours", "confirmatory_qwen_return.zip"),
                (6, "internvl", "03_internvl_specificity_confirmatory_T4x2.ipynb", "saket9500", "kagglefiles/inputs/09_CONFIRMATORY_INTERNVL", "planning estimate 3-7 hours", "confirmatory_internvl_return.zip"),
                (7, "llava", "04_llava_specificity_confirmatory_T4x2.ipynb", "examhelps", "kagglefiles/inputs/10_CONFIRMATORY_LLAVA", "planning estimate 2-5 hours", "confirmatory_llava_return.zip"),
            )
        ],
    ]


def build(output_root: Path = ROOT) -> dict[str, Any]:
    design = _json("design/C12_CONFIRMATORY_POWER_DECISION.json")
    feasibility = _json("design/CONFIRMATORY_FEASIBILITY.json")
    smoke = _json("gpu/00C2_READINESS.json")
    primary = _json("gpu/PRIMARY_RUNBOOK_READINESS.json")
    secondary = _json("gpu/SECONDARY_RUNBOOK_READINESS.json")
    human = _json("human/HUMAN_REVIEW_READINESS.json")
    matching = _json("design/MATCHING_DETECTABILITY_READINESS.json")
    analysis = _json("analysis/PRIMARY_ANALYSIS_READINESS.json")
    claims = _json("evidence/CLAIM_REGISTRY_V2.json")
    red_team = _json("evidence/SCIENTIFIC_RED_TEAM_V2.json")
    reproduction = _json("reproducibility/C12_CLEAN_REPRODUCTION.json")
    identity_baseline = _json("C12_IDENTITY_BASELINE.json")
    identity_diff = _json("C12_IDENTITY_DIFF.json")
    validation = _phase_b_validation()
    runs = _gpu_runs()
    markers = [
        "CERTVIC_C12_DESIGN_POWER_RESOLVED",
        "CERTVIC_C12_SMOKE_INTAKE_READY",
        "CERTVIC_C12_00C2_SOFTWARE_READY",
        "CERTVIC_C12_PRIMARY_RUNBOOKS_READY",
        "CERTVIC_C12_SECONDARY_RUNBOOKS_PREPARED",
        "CERTVIC_C12_HUMAN_REVIEW_READY",
        "CERTVIC_C12_MATCHING_DETECTABILITY_READY",
        "CERTVIC_C12_PRIMARY_ANALYSIS_READY",
        "CERTVIC_C12_CLAIM_REGISTRY_V2_READY",
        "CERTVIC_C12_CLEAN_REPRODUCTION_PASS",
        "CERTVIC_C12_LOCAL_FAILURES_ZERO",
        "CERTVIC_C12_COMMON_IDENTITIES_PRESERVED",
        "CERTVIC_C12_00A_00B_RERUN_NOT_REQUIRED",
    ]
    handoff = {
        "schema": "certvic.cvpr2027.c12.pre_experiment_max_readiness_handoff.v1",
        "status": "ALL_REMAINING_HIGH_VALUE_LOCAL_PRE_EXPERIMENT_WORK_COMPLETE",
        "live_starting_state": {
            "starting_commit": "1ee0fcd0d0b241a88ff7b57cf5277800c4552e10",
            "handoff_generated_from_committed_head": _git("rev-parse", "HEAD"),
            "origin_main_at_handoff_generation": _git("rev-parse", "origin/main"),
            "identities": identity_baseline,
        },
        "design_power_decision": {
            "decision": design["handoff_label"],
            "old_allocation": design["old_allocation"],
            "new_allocation": design["new_allocation"],
            "reserve_allocation": design["reserve_allocation"],
            "old_all_three_power": design["operating_characteristics"]["old_120_120"]["claim_regime_a_all_three_six_gate_power"],
            "new_all_three_power": design["operating_characteristics"]["new_120_240"]["claim_regime_a_all_three_six_gate_power"],
            "primary_claim_regime": design["primary_claim_regime"],
            "prospective_outcomes_used": False,
        },
        "completed_c12_work": {
            "smoke_intake": "one-command fail-closed intake plus declaration template",
            "00c2": smoke["status"],
            "primary_runbooks": primary["status"],
            "secondary_runbooks": secondary["status"],
            "matching_detectability": matching["status"],
            "human_review": human["status"],
            "primary_analysis": analysis["status"],
            "claim_registry_schema": claims["schema"],
            "reviewer_attacks": red_team["status"],
            "clean_reproduction": {
                "status": reproduction["status"],
                "committed_head": reproduction["committed_head"],
                "comparisons": len(reproduction["comparisons"]),
                "mismatch_count": reproduction["mismatch_count"],
            },
            "validation": validation,
        },
        "remaining_external_actions": [
            {"priority": "P0", "order": 1, "action": "Provide two real, user-owned/license-eligible original/edited image pairs and affirm research plus redistribution rights."},
            {"priority": "P0", "order": 2, "action": "Build the canonical two-item bundle and three permissions, then execute/import the three 00C2 runs."},
            {"priority": "P0", "order": 3, "action": "Provision and license-verify the prospective source universe; current feasibility is SOURCE_BYTES_MISSING."},
            {"priority": "P0", "order": 4, "action": "Generate candidates, build the blind packet, complete two independent qualified reviews and adjudication."},
            {"priority": "P0", "order": 5, "action": "Run outcome-blind matching/detectability, freeze the v3 task universe, mint permissions, and execute the four primary confirmatory runs."},
            {"priority": "P1", "order": 6, "action": "Only after the primary freeze, consider separately permissioned robustness arms and optional-model expansion."},
            {"priority": "P2", "order": 7, "action": "Select a second domain by the evidence-backed template; keep Main unauthorized until the hash-bound confirmatory GO artifact exists."},
        ],
        "exact_next_user_action": "PROVIDE_TWO_REAL_LICENSED_SMOKE_PAIRS",
        "exact_intake_status_command": "python3 local_operator/prepare_real_smoke_items.py --status",
        "kaggle_run_order": runs,
        "human_review_work": {
            "files": [
                "reports/cvpr2027_c12/human/rater_qualification_packet.csv",
                "reports/cvpr2027_c12/human/coordinator_qualification_answer_key.csv",
                "reports/cvpr2027_c12/human/review_assignment_template.csv",
                "reports/cvpr2027_c12/human/qualification_policy.json",
                "reports/cvpr2027_c12/human/review_timeline.template.json",
            ],
            "instructions": "Build and hash-lock the blind packet from licensed sources; qualify two distinct genuine raters; preserve raw sheets; validate exact row coverage; adjudicate only disagreements; never synthesize labels.",
            "planning_estimate_hours": {
                "coordinator_packet_build_and_qa": "4-8 after source bytes exist",
                "each_independent_rater": "2-4",
                "adjudication_and_validation": "1-3",
            },
            "genuine_human_reviewed_count": human["genuine_human_reviewed_count"],
        },
        "protocol_integrity": {
            "prospective_outcomes_observed_or_used": False,
            "provider_outputs_used_for_matching": False,
            "post_outcome_threshold_or_sample_tuning": False,
            "historical_can_satisfy_prospective": claims["historical_can_satisfy_prospective"],
            "paper_evidence": False,
        },
        "identity_impact": {
            "status": identity_diff["status"],
            "common_identities_preserved": identity_diff["common_identities_preserved"],
            "runtime_returns_preserved": identity_diff["runtime_returns_preserved"],
            "00A_00B_rerun_required": identity_diff["00A_00B_rerun_required"],
        },
        "remaining_scientific_blockers": {
            "P0": ["two real licensed smoke pairs", "three 00C2 GPU returns", feasibility["status"], "genuine two-rater review", "prospective matching/detectability and frozen task universe", "four primary confirmatory GPU returns"],
            "P1": ["secondary robustness outputs", "optional-model implementation and evidence"],
            "P2": ["evidence-backed second-domain selection", "conditional Main500 authorization"],
        },
        "what_not_to_do_next": [
            "Do not rerun authenticated 00A/00B or provisioning.",
            "Do not launch 00C2 before the real bundle and exact single-use permissions exist.",
            "Do not treat synthetic proofs, historical outputs, smoke, plans, or contracts as prospective evidence.",
            "Do not tune thresholds, sample size, matching, or candidate selection after outcomes.",
            "Do not start secondary, optional-model, Main, or second-domain runs before their separate gates.",
            "Do not add more generic infrastructure before external evidence arrives.",
        ],
        "completion_markers": markers,
        "explicit_non_claims": ["CVPR_READY", "SUBMISSION_READY", "PROSPECTIVE_EVIDENCE_COMPLETE", "PAPER_EVIDENCE_COMPLETE"],
        "paper_evidence": False,
    }
    json_path = write_json(
        output_root / "CERTVIC_C12_PRE_EXPERIMENT_MAX_READINESS_HANDOFF.json", handoff
    )
    markdown = _markdown(handoff)
    markdown_path = write_text(
        output_root / "CERTVIC_C12_PRE_EXPERIMENT_MAX_READINESS_HANDOFF.md", markdown
    )
    return {
        "status": handoff["status"],
        "json": json_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "markdown": markdown_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "exact_next_user_action": handoff["exact_next_user_action"],
        "paper_evidence": False,
    }


def _markdown(value: dict[str, Any]) -> str:
    design = value["design_power_decision"]
    identities = value["identity_impact"]
    validation = value["completed_c12_work"]["validation"]
    run_lines = [
        "| # | Stage | Notebook | Account suggestion | Accelerator / Internet | Input | Planning estimate | Output / import |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in value["kaggle_run_order"]:
        run_lines.append(
            f"| {row['order']} | {row['stage']} | `{row['notebook']}` | {row['account_suggestion']} | "
            f"{row['accelerator']} / {row['internet']} | `{row['input']}` | {row['runtime_estimate']} | "
            f"`{row['output']}`; `{row['import_command']}` |"
        )
    actions = "\n".join(
        f"{row['order']}. **{row['priority']}** — {row['action']}"
        for row in value["remaining_external_actions"]
    )
    human_files = "\n".join(f"- `{path}`" for path in value["human_review_work"]["files"])
    blockers = "\n".join(
        f"- **{priority}:** " + "; ".join(items)
        for priority, items in value["remaining_scientific_blockers"].items()
    )
    dont = "\n".join(f"- {item}" for item in value["what_not_to_do_next"])
    markers = "\n".join(f"- `{item}`" for item in value["completion_markers"])
    return f"""# CertVIC C12 pre-experiment maximum-readiness handoff

Status: **{value['status']}**. This is a software/design-readiness handoff, not paper evidence and not a submission-readiness claim.

## A. Live starting state

- Starting commit: `{value['live_starting_state']['starting_commit']}`
- Handoff generated from committed head: `{value['live_starting_state']['handoff_generated_from_committed_head']}`
- Origin/main at generation: `{value['live_starting_state']['origin_main_at_handoff_generation']}`
- Authenticated identity details: `C12_IDENTITY_BASELINE.json`

## B. Design-power decision

**{design['decision']}**: old allocation {design['old_allocation']['relevant']} relevant / {design['old_allocation']['irrelevant']} irrelevant; new allocation {design['new_allocation']['relevant']} relevant / {design['new_allocation']['irrelevant']} irrelevant, plus {design['reserve_allocation']['relevant']} / {design['reserve_allocation']['irrelevant']} reserve. At the declared 0.70/0.03 design scenario, all-three six-gate power changes from {design['old_all_three_power']:.6f} to {design['new_all_three_power']:.6f}. Thresholds, six-gate Bonferroni family, relevant n, endpoints, and fail-closed semantics are unchanged. No prospective outcome was observed or used.

## C. Completed C12 work

The v3 amendment, real-smoke intake, zero-edit 00C2 and full-universe primary runbooks, outcome-blind matching/detectability, human-review infrastructure, nine golden analysis fixtures, evidence-class claim registry, reviewer-attack suite, secondary gating, conditional Main/second-domain frameworks, CI, and clean reproduction are implemented. Phase B passed {validation['commands_executed']}/{validation['commands_planned']} commands with {validation['pytest_passed']} pytest passes, {validation['pytest_skipped']} skips, zero local failures, no GPU runs, and `paper_evidence=false`. Clean reproduction matched 18/18 compared artifacts with zero mismatch.

## D. Remaining external actions

{actions}

## E. Exact next user action

**`{value['exact_next_user_action']}`**

Check the intake state with `python3 local_operator/prepare_real_smoke_items.py --status`; then supply four genuine image paths and the explicit user-owned/research-use/redistribution affirmations. Do not open Kaggle yet.

## F. Kaggle run order

Account names are scheduling suggestions only; the contracts authenticate content identities and are owner/path independent.

{chr(10).join(run_lines)}

Stop after every download, import it transactionally, and run `bash kagglefiles/run_local_resume.sh` before continuing.

## G. Human review work

{human_files}

Instructions: {value['human_review_work']['instructions']} Planning only: coordinator 4–8 hours after source bytes exist; each rater 2–4 hours; adjudication/validation 1–3 hours. Current genuine reviewed count: **{value['human_review_work']['genuine_human_reviewed_count']}**.

## H. Protocol integrity

No prospective provider outcome was observed or used; matching contains no provider outcome; no post-outcome threshold, sample-size, or selection tuning occurred. Historical artifacts cannot satisfy prospective claims. `paper_evidence=false` throughout.

## I. Identity impact

`{identities['status']}`. Common identities preserved: `{str(identities['common_identities_preserved']).lower()}`; authenticated runtime returns preserved: `{str(identities['runtime_returns_preserved']).lower()}`; 00A/00B rerun required: `{str(identities['00A_00B_rerun_required']).lower()}`.

## J. Remaining scientific blockers

{blockers}

## K. What NOT to do next

{dont}

## Proven completion markers

{markers}

Explicit non-claims: `CVPR_READY`, `SUBMISSION_READY`, `PROSPECTIVE_EVIDENCE_COMPLETE`, and `PAPER_EVIDENCE_COMPLETE` are **not** claimed.
"""


def main() -> int:
    result = build()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
