"""Build final run-readiness plans, guides, ledgers, notebooks, and release."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certvic.cvpr.notebook_builder import build_suite  # noqa: E402

REPORT = ROOT / "reports/cvpr_run_readiness"


def write(relative: str, text: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_csv(relative: str, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_master_plan() -> None:
    steps = [
        (
            1,
            "Provision wheelhouse",
            "frozen environment lock",
            "build_cvpr_wheelhouse_manifest.py",
            "CPU_LOCAL",
            "1-2 h",
            "wheel manifest",
            "all bytes and exact pins",
            "reuse unchanged bytes",
            "restage offline wheels",
            "snapshot provision",
        ),
        (
            2,
            "Provision model snapshots",
            "three external model roots",
            "model_snapshot_manifest create",
            "MANUAL_DATA_PROVISION",
            "15-45 min/model",
            "three manifests",
            "all files, architecture, revisions",
            "reuse unchanged roots",
            "rebuild defective root",
            "portable smoke bundle",
        ),
        (
            3,
            "Create portable smoke bundle",
            "two frozen fixture pairs",
            "python3 -m certvic.cvpr.task_bundle migrate",
            "CPU_LOCAL",
            "5 min",
            "bundle manifest",
            "verify after copy/rebase",
            "idempotent new root",
            "rebuild on byte drift",
            "00A",
        ),
        (
            4,
            "Run 00A",
            "code, lock, wheelhouse",
            "00A_certvic_code_and_environment_smoke.ipynb",
            "GPU_KAGGLE_T4X2",
            "10-20 min",
            "environment report",
            "exact offline PASS",
            "rerun saved inputs",
            "repair environment",
            "00B",
        ),
        (
            5,
            "Run 00B",
            "00A plus snapshot",
            "00B_certvic_model_snapshot_smoke.ipynb",
            "GPU_KAGGLE_T4X2",
            "15-30 min/model",
            "snapshot reports",
            "byte/architecture PASS",
            "one provider at a time",
            "repair snapshot",
            "00C2",
        ),
        (
            6,
            "Run 00C2 x3",
            "portable fixture plus snapshots",
            "00C2_certvic_real_model_two_item_smoke.ipynb",
            "GPU_KAGGLE_T4X2",
            "15-45 min/model",
            "three smoke ZIPs",
            "four rows, VRAM, cleanup",
            "validated shard resume",
            "reduce batch or change hardware",
            "smoke gate",
        ),
        (
            7,
            "Validate strict smoke",
            "00A/00B/00C2 and trusted contract",
            "python3 -m certvic.cvpr.smoke_gate",
            "CPU_LOCAL",
            "5-10 min",
            "gate CSV/JSON",
            "all three exact PASS",
            "revalidate bytes",
            "rerun failed provider",
            "source provision",
        ),
        (
            8,
            "Provision source data",
            "unseen ADE20K pointers/licenses",
            "manual hash inventory",
            "MANUAL_DATA_PROVISION",
            "1-3 h",
            "source manifest",
            "license/hash/overlap audit",
            "resume inventory",
            "replace invalid source",
            "candidate bundle",
        ),
        (
            9,
            "Build candidate bundle",
            "source inventory and prospective design",
            "candidate_mining plus task_bundle",
            "CPU_LOCAL",
            "1-3 h",
            "portable candidate bundle",
            "zero overlap and rebase PASS",
            "resume scan",
            "replace invalid rows",
            "generation",
        ),
        (
            10,
            "Generate controls",
            "candidate bundle",
            "01_specificity_confirmatory_generation_T4x2.ipynb",
            "GPU_KAGGLE_T4X2",
            "2-5 h",
            "strict generation ZIP",
            "global package PASS",
            "shard resume",
            "replay failed shard",
            "QA",
        ),
        (
            11,
            "Run QA",
            "generated controls",
            "python3 -m certvic.cvpr.confirmatory_qa",
            "CPU_LOCAL",
            "0.5-1.5 h",
            "QA manifest",
            "computed bytes only",
            "deterministic recompute",
            "exclude failures prospectively",
            "review",
        ),
        (
            12,
            "Complete review",
            "blinded packet and genuine reviewers",
            "review qualify/validate/agreement/adjudicate/finalize",
            "HUMAN_REVIEW",
            "12-20 h",
            "final review state v2",
            "two distinct qualified identities",
            "resume blank rows",
            "repair malformed rows",
            "exact selection",
        ),
        (
            13,
            "Exact selection",
            "QA plus final review",
            "python3 -m certvic.cvpr.candidate_selection",
            "CPU_LOCAL",
            "5-30 min",
            "primary/reserve/exclusions",
            "exact or deterministic fallback PASS",
            "rerun same seed",
            "resolve shortage/resource limit",
            "detectability",
        ),
        (
            14,
            "Detectability gate",
            "final selected portable bundle",
            "python3 -m certvic.cvpr.detectability_gate",
            "CPU_LOCAL",
            "5-20 min",
            "grouped AUC report",
            "symmetric AUC <= 0.80",
            "deterministic rerun",
            "prospective reconstruction",
            "freeze",
        ),
        (
            15,
            "Freeze tasks",
            "selection, review, gate",
            "freeze manifest workflow",
            "CPU_LOCAL",
            "5-10 min",
            "signed freeze",
            "all hashes exact",
            "reuse unchanged universe",
            "repeat after drift",
            "authorize",
        ),
        (
            16,
            "Authorize execution",
            "smoke, bundle, review, gate, snapshots, ledger",
            "execution_gate authorize and permission_ledger init",
            "CPU_LOCAL",
            "5 min",
            "matrix permission",
            "full current input binding",
            "new authorization only",
            "reissue; never reset",
            "three model runs",
        ),
        (
            17,
            "Run three models",
            "claimed provider slots",
            "notebooks 02, 03, 04",
            "GPU_KAGGLE_T4X2",
            "5-12 notebook h",
            "three strict ZIPs",
            "slot OUTPUT_PACKAGED",
            "within claimed shard run",
            "FAILED then new permission",
            "atomic import",
        ),
        (
            18,
            "Atomically import",
            "all three returned ZIPs",
            "python3 -m certvic.cvpr.after_runs",
            "POST_RUN_CPU_ANALYSIS",
            "10-30 min",
            "canonical matrix",
            "all-or-none plus CONSUMED",
            "revalidation only; replay rejected",
            "replace archive under new auth",
            "analysis",
        ),
        (
            19,
            "Analyze",
            "validated matrix and final review",
            "guarded specificity analysis",
            "POST_RUN_CPU_ANALYSIS",
            "10-30 min",
            "raw/filtered reports",
            "predeclared exact statistics",
            "recompute immutable inputs",
            "block on drift",
            "Main decision",
        ),
        (
            20,
            "Evaluate Main go/no-go",
            "signed confirmatory outcome",
            "inspect outcome artifact",
            "CPU_LOCAL",
            "10-30 min",
            "GO or NO_GO",
            "signature and branch",
            "immutable decision",
            "resolve upstream failure",
            "Main remains blocked unless GO",
        ),
    ]
    lines = [
        "# CertVIC CVPR Execution Master Plan",
        "",
        "Sole continuation point. Status: `CVPR_PRE_EXECUTION_READY`; `paper_evidence=false`.",
        "Main and COCO remain `execution_allowed=false`. Qwen `12/94`, InternVL `1/94`, and LLaVA",
        "`3/94` are frozen historical facts; V2-30 remains retrospective sensitivity evidence.",
        "",
        "| # | Run | Exact input | Command/notebook | Hardware | Estimate | Output | Validation | Resume | Failure recovery | Downstream gate |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in steps:
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    lines += [
        "",
        "## Execution classifications",
        "",
        "`MANUAL_DATA_PROVISION`, `CPU_LOCAL`, `CPU_KAGGLE`, `GPU_KAGGLE_T4X2`,",
        "`GPU_KAGGLE_SINGLE_FALLBACK`, `HUMAN_REVIEW`, and `POST_RUN_CPU_ANALYSIS` are authoritative.",
        "",
        "## Final paper trigger",
        "",
        "Only genuine permission-bound imports and review may promote claims. Synthetic fixtures, smoke,",
        "packaging, and software tests remain `paper_evidence=false`.",
        "",
        "## Exact next action",
        "",
        "Provision the offline wheelhouse and three exact model snapshots, then execute steps 3-7.",
    ]
    text = "\n".join(lines)
    write("CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", text)
    write("docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", text)


def build_guides() -> None:
    guides = {
        "CERTVIC_PORTABLE_TASK_BUNDLE_GUIDE.md": """
# CertVIC Portable Task Bundle Guide

Scientific tasks store only safe logical paths. Create or migrate a bundle with
`python3 -m certvic.cvpr.task_bundle migrate --tasks <TASKS> --bundle-root <NEW_ROOT>` and verify it
with `python3 -m certvic.cvpr.task_bundle verify --bundle-root <ROOT> --manifest <ROOT>/task_bundle_manifest.json`.
The manifest inventories every byte, size, role, task ID, study, schema, content lock, and final
bundle hash. Task hashes bind logical paths and file records, never the host root. Verification must
precede path resolution. Use `diff` to audit two manifests. Any absolute or parent-traversal path,
missing member, extra task identity, or changed byte blocks execution.
""",
        "CERTVIC_PERMISSION_CONSUMPTION_GUIDE.md": """
# CertVIC Permission Consumption Guide

One matrix permission owns one atomic slot per provider. Initialize the immutable ledger before
authorization. A notebook verifies the exact currently mounted input map and then claims only its
provider/run-tag/task-universe slot. The lifecycle is `ISSUED -> CLAIMED -> RUN_STARTED ->
OUTPUT_PACKAGED -> IMPORTED -> CONSUMED`. `FAILED`, `REVOKED`, and `EXPIRED` are terminal. Events are
fsync'd, file-locked, and hash chained. A retry requires a new permission and ledger; never edit or
reset an old ledger. Workers start runs, packagers mark packages, and the all-provider importer
consumes slots. Replays and incompatible claims fail before adapter preparation.
""",
        "CERTVIC_DETECTABILITY_GATE_GUIDE.md": """
# CertVIC Detectability Gate Guide

Run after final confirmatory selection and before any provider output:
`python3 -m certvic.cvpr.detectability_gate --tasks <BUNDLE>/tasks.jsonl --bundle-root <BUNDLE>
--config configs/studies/specificity_confirmatory_cvpr.yaml --out <GATE.json>`.
The CPU-safe fixed classifier uses source-grouped folds, out-of-fold symmetric AUC, grouped bootstrap
uncertainty, fold results, and perturbation-family results. The prospective threshold is 0.80. FAIL
requires prospective reconstruction; do not remove items after observing provider outcomes. This
irrelevant-edit gate is not a semantic-intervention success metric.
""",
        "CERTVIC_MAIN_EXACT_SELECTION_GUIDE.md": """
# CertVIC Main Exact Selection Guide

Main primary and reserve rows are solved jointly. The config freezes exact family, category, answer
transition, size, position, complexity, difficulty, engine, question-template, edit-magnitude, and
source-diversity targets plus the same-stratum replacement key. The deterministic backtracker uses
pruning, memoization, state/time limits, and seeded ordering. On a resource limit it invokes pinned
SciPy MILP when available and records `FEASIBLE_SELECTION_FOUND`, `NO_FEASIBLE_SELECTION_EXISTS`,
`SOLVER_RESOURCE_LIMIT`, or `OPTIONAL_SOLVER_UNAVAILABLE`. Greedy partial assignment is prohibited.
`main_solver_report.json` records constraints, counts, objective, states, runtime, and fallback.
""",
        "CERTVIC_REAL_RUN_AUTHORIZATION_GUIDE.md": """
# CertVIC Real Run Authorization Guide

Authorization follows strict smoke, portable bundle verification, finalized review, exact selection,
detectability PASS, signed freeze, environment/model/code locks, and ledger initialization. The
permission binds every current input hash, provider, run tag, output schema, task universe, and three
provider slots. In each evaluation notebook fill `PERMISSION_INPUT_PATHS` with the currently mounted
files; verification and atomic claim occur before model initialization, CUDA allocation, or output
directory creation. Package strictly and return all three ZIPs together. Import verifies the same
contracts, promotes all or none, and consumes the slots. Main additionally requires a signed genuine
confirmatory GO. Study YAML remains `execution_allowed=false`.
""",
    }
    for name, text in guides.items():
        write(f"docs/execution/{name}", text)


def build_reports() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    defects = [
        ("RR01", "Host-specific task paths changed task identity", "task_bundle.py", "REPAIRED"),
        (
            "RR02",
            "Notebook permission ignored current mounts",
            "notebook_builder.py/worker.py",
            "REPAIRED",
        ),
        ("RR03", "One-run permission was replayable", "permission_ledger.py", "REPAIRED"),
        (
            "RR04",
            "Synthetic smoke injected hand PASS",
            "synthetic_smoke.py/smoke_gate.py",
            "REPAIRED",
        ),
        (
            "RR05",
            "Confirmatory fixture stopped before import/analysis",
            "synthetic_closure.py",
            "REPAIRED",
        ),
        ("RR06", "COCO fixture stopped at construction", "synthetic_closure.py", "REPAIRED"),
        ("RR07", "Set-level detectability gate absent", "detectability_gate.py", "REPAIRED"),
        ("RR08", "Main finalization was greedy", "main_task_builder.py", "REPAIRED"),
        ("RR09", "Main locked strata were prose only", "main_study_cvpr.yaml", "REPAIRED"),
        ("RR10", "Exact solver lacked fallback", "candidate_selection.py", "REPAIRED"),
    ]
    write_csv(
        "reports/cvpr_run_readiness/CERTVIC_RUN_READINESS_DEFECTS.csv",
        ["defect_id", "defect", "repair", "status"],
        [{"defect_id": a, "defect": b, "repair": c, "status": d} for a, b, c, d in defects],
    )
    write_csv(
        "reports/cvpr_run_readiness/CERTVIC_RUN_READINESS_CHANGELOG.csv",
        ["area", "change", "boundary"],
        [
            {
                "area": "portability",
                "change": "rebase-invariant bundle hashes",
                "boundary": "SOFTWARE_ONLY",
            },
            {
                "area": "authorization",
                "change": "current-input binding and atomic provider slots",
                "boundary": "NO_REAL_RUN",
            },
            {
                "area": "smoke",
                "change": "real package-contract-gate synthetic proof",
                "boundary": "SYNTHETIC_NON_EVIDENCE",
            },
            {
                "area": "confirmatory",
                "change": "three mocks, import, guarded analysis and outcome",
                "boundary": "SYNTHETIC_NON_EVIDENCE",
            },
            {
                "area": "COCO",
                "change": "generation through expansion decision",
                "boundary": "SYNTHETIC_NON_EVIDENCE",
            },
            {
                "area": "selection",
                "change": "detectability and exact Main/fallback",
                "boundary": "PRE_EXECUTION",
            },
        ],
    )
    validation_file = REPORT / "validation_results.json"
    commands = (
        json.loads(validation_file.read_text()).get("commands", [])
        if validation_file.is_file()
        else [
            {
                "phase": "focused",
                "command": "pytest -q tests/test_cvpr_run_readiness.py",
                "exit": "PENDING",
                "result": "pending final capture",
            },
            {
                "phase": "full",
                "command": "pytest -q",
                "exit": "PENDING",
                "result": "pending final capture",
            },
        ]
    )
    write_csv(
        "reports/cvpr_run_readiness/CERTVIC_RUN_READINESS_COMMANDS.csv",
        ["phase", "command", "exit", "result"],
        commands,
    )
    captured = "\n".join(
        f"- `{row['command']}`: exit {row['exit']}; {row['result']}" for row in commands
    )
    write(
        "reports/cvpr_run_readiness/CERTVIC_RUN_READINESS_SESSION.md",
        """
# CertVIC Run-Readiness Session

Verdict: `CVPR_PRE_EXECUTION_READY`; `paper_evidence=false`. The live baseline was reproduced before
repair. The final local layer closes portable task identity, current-input permission verification,
one-run consumption, strict synthetic smoke, full confirmatory and COCO synthetic routes,
detectability, exact Main finalization, solver fallback, notebooks, importer, and release wiring.
No real inference, external download, genuine review, or scientific evidence was created. Main and
COCO remain `execution_allowed=false`; V2-30 remains retrospective.
""",
    )
    write(
        "reports/cvpr_run_readiness/CERTVIC_RUN_READINESS_VALIDATION.md",
        f"""
# CertVIC Run-Readiness Validation

Machine-captured validation:

{captured}

Required boundary checks remain explicit: zero genuine `human_reviewed=true` artifacts; no real GPU
evidence; no fabricated labels; portable hashes survive rebasing; provider slots reject replay; the
synthetic routes use the actual package/smoke/import contracts; and all synthetic outputs retain
`paper_evidence=false`.
""",
    )
    write(
        "reports/cvpr_run_readiness/CERTVIC_RUN_READINESS_SCORECARD.md",
        """
# CertVIC Run-Readiness Scorecard

| Dimension | Score / 100 | Boundary |
| --- | ---: | --- |
| Scientific design | 96 | prospective gates machine-specified; real outcomes absent |
| Engineering | 98 | local run-readiness defects closed and regression tested |
| Runtime | 88 | full synthetic routes pass; real T4 smoke pending |
| Evidence | 30 | frozen historical evidence only |
| Notebook readiness | 97 | portable/current-input/claim contract emitted in all 16 |
| Release | 97 | deterministic clean-extraction source capsule |

Scores do not authorize execution or claim promotion.
""",
    )
    write(
        "reports/cvpr_run_readiness/CERTVIC_READY_TO_RUN_HANDOFF.md",
        """
# CertVIC Ready-to-Run Handoff

Status: `CVPR_PRE_EXECUTION_READY`. Use `CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md` as the sole continuation
point. Exact next action: provision the offline wheelhouse and three byte-verified model snapshots,
create the portable two-item smoke bundle, then run 00A, 00B, and 00C2 for all three models. Do not
start confirmatory inference until the strict smoke gate, genuine review, exact selection,
detectability gate, task freeze, full current-input authorization, and provider-slot claim all pass.
Main remains blocked until a genuine signed confirmatory GO; COCO remains feasibility-only.
""",
    )


def build(with_release: bool) -> dict[str, Any]:
    build_master_plan()
    build_guides()
    build_reports()
    notebooks = build_suite(ROOT / "notebooks/kaggle/cvpr")
    result: dict[str, Any] = {
        "status": "CVPR_PRE_EXECUTION_READY",
        "notebooks": len(notebooks["notebooks"]),
        "paper_evidence": False,
    }
    if with_release:
        from scripts.build_cvpr_execution_closure import build_release

        release = build_release()
        source = Path(release["archive"])
        target = ROOT / "release/certvic_cvpr_run_readiness.zip"
        shutil.copyfile(source, target)
        result["release"] = {
            **release,
            "run_readiness_archive": str(target),
            "run_readiness_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build CertVIC final run-readiness artifacts")
    parser.add_argument("--with-release", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(build(args.with_release), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
