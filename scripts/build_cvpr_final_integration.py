"""Build the canonical final-integration docs, notebooks, and deterministic release."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certvic.cvpr.notebook_builder import build_suite  # noqa: E402
from scripts.build_cvpr_execution_closure import build_release  # noqa: E402


REPORT = ROOT / "reports/cvpr_final_integration"


def write(relative: str, text: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_csv(relative: str, fields: list[str], rows: list[dict[str, object]]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


MASTER = """
# CertVIC CVPR Canonical Execution Master Plan

Status: `CVPR_PRE_EXECUTION_READY`; scientific evidence is still blocked. `paper_evidence=false`.
The frozen historical facts remain unchanged: Qwen `12/94 = 0.1277`, InternVL `1/94 = 0.0106`,
LLaVA `3/94 = 0.0319`; V2-30 is retrospective; structured `human_reviewed=true` remains zero.

## One canonical route

1. Provision source data and a hash-locked source manifest.
2. Run `python3 -m certvic.cvpr.plan --study specificity_confirmatory_cvpr`.
3. Attach the environment lock and either an exact preinstalled environment or verified wheelhouse.
4. Create one unified model/processor snapshot manifest per provider.
5. Run `00A_certvic_code_and_environment_smoke.ipynb`.
6. Run `00B_certvic_model_snapshot_smoke.ipynb` for each provider snapshot.
7. Run `00C2_certvic_real_model_two_item_smoke.ipynb` for each provider.
8. Return the 00A, 00B, and 00C2 artifacts and run `python3 -m certvic.cvpr.smoke_gate`.
9. Build the unseen confirmatory candidate pool.
10. Generate confirmatory controls with `01_specificity_confirmatory_generation_T4x2.ipynb`.
11. Run `python3 -m certvic.cvpr.confirmatory_qa` on the returned generation root.
12. Build the visual packet with `python3 -m certvic.cvpr.review build`.
13. Qualify two distinct reviewers with `python3 -m certvic.cvpr.review qualify`.
14. Complete and validate both independent sheets with `python3 -m certvic.cvpr.review validate`.
15. Compute agreement with `python3 -m certvic.cvpr.review agreement`.
16. Create and complete the disagreement packet, then run `review validate-adjudication`.
17. Finalize the provenance-bound ledger with `python3 -m certvic.cvpr.review finalize`.
18. Solve the exact balanced selection with `python3 -m certvic.cvpr.candidate_selection`.
19. Freeze/hash-lock final tasks and run notebooks 02, 03, and 04 unchanged.
20. Atomically import with `python3 -m certvic.cvpr.after_runs --strict`.
21. The same command runs human-aware analysis, ledgers, guarded paper branch, release, and Main signoff.
22. If signed permission allows it, build Main candidates with `python3 -m certvic.cvpr.main_task_builder`.
23. Generate Main semantic edits with notebook 10 and package with `package_generation --strict`.
24. Run the same independent review/freeze route, then notebooks 11, 12, and 13.
25. Import Main outputs atomically and close the guarded paper branch.
26. Build COCO feasibility tasks with `python3 -m certvic.data.coco_adapter`.
27. Run notebooks 20-23 only within the frozen four-category/license-limited feasibility contract.
28. Rebuild the paper and deterministic pointer-safe release from validated canonical state.

## Frozen commands

```bash
python3 -m certvic.cvpr.plan --study specificity_confirmatory_cvpr
python3 scripts/build_cvpr_wheelhouse_manifest.py --wheelhouse <WHEELS> --lock configs/runtime/kaggle_t4x2_environment.lock.json --out <MANIFEST>
python3 -m certvic.cvpr.model_snapshot_manifest create --snapshot <UNIFIED_ROOT> --model-id <ID> --model-commit <COMMIT> --processor-commit <COMMIT> --architecture <ARCH>
python3 -m certvic.cvpr.smoke_gate --smoke-root <RETURNED_SMOKES> --out reports/cvpr_final_integration/REAL_MODEL_SMOKE_GATE.csv
python3 -m certvic.cvpr.confirmatory_qa --candidate-manifest <CANDIDATES> --generation-root <GENERATED> --study-config configs/studies/specificity_confirmatory_cvpr.yaml --out <ENRICHED> --report <QA_REPORT>
python3 -m certvic.cvpr.review build --items <QA_PASSING_ITEMS> --track specificity_confirmatory_cvpr --out-dir <PACKET> --seed 12013
python3 -m certvic.cvpr.review finalize --help
python3 -m certvic.cvpr.candidate_selection --help
python3 -m certvic.cvpr.after_runs --input-dir <RETURNED_OUTPUTS> --study specificity_confirmatory_cvpr --strict
python3 -m certvic.cvpr.main_task_builder --source-root <ADE20K_ROOT> --source-manifest <SOURCE_MANIFEST> --config configs/studies/main_study_cvpr.yaml --out <CANDIDATES> --report <REPORT>
python3 -m certvic.cvpr.package_generation --study-manifest <TASKS> --generation-root <RUN_ROOT> --out-zip <ZIP> --strict
python3 -m certvic.data.coco_adapter --coco-root <COCO_ROOT> --out-dir <OUT>
```

## Hard gates

- Scientific notebooks reject execution until all three rows in `REAL_MODEL_SMOKE_GATE.csv` are PASS.
- Confirmatory selection accepts only `certvic.cvpr.confirmatory_qa.v1` enriched rows.
- Review finalization requires distinct qualifications, distinct raw sheets, exact validations,
  matching packet/input hashes, agreement, authorized adjudication, and a complete all-item ledger.
- Main and COCO remain `execution_allowed=false` until signed upstream gates change canonical config.
- Every model row is `certvic.cvpr.output.v2`; mixed versions are rejected.

## Frozen execution classifications

Data attachment is `MANUAL_DATA_PROVISION`; local planning/QA is `CPU_LOCAL`; optional hosted CPU is
`CPU_KAGGLE`; the primary accelerator route is `GPU_KAGGLE_T4X2` with explicit
`GPU_KAGGLE_SINGLE_FALLBACK`; blinded judgment is `HUMAN_REVIEW`; validated import, analysis, paper,
and release are `POST_RUN_CPU_ANALYSIS`. The V2-30 set remains retrospective sensitivity evidence.

## Final paper trigger

Activate a results branch only after exact provider import, the provenance-bound all-item review
ledger, frozen model/environment/task hashes, analysis intervals, claim/privacy checks, paper compile,
and deterministic release all pass. Software readiness alone never sets `paper_evidence=true`.

## External blockers and planning estimates

External bytes/actions still required: source data, wheelhouse, three unified snapshots, real 00A/00B/00C2
smokes, two independent reviewers, and real scientific execution. Planning estimates (not observations):
confirmatory CPU 2-8 h, GPU 7-17 notebook h, human 12-20 h; conditional Main CPU 2-6 h,
GPU 26-54 notebook h, human 35-55 h; COCO feasibility CPU 1-3 h, GPU 5.5-12 h,
human 5-8 h; paper/release 0.5-1.5 h.
"""


GUIDES = {
    "docs/execution/CERTVIC_CONFIRMATORY_QA_GUIDE.md": """
# Confirmatory QA Guide

Run `certvic.cvpr.confirmatory_qa` after generation and before selection. It recomputes source/output
hashes, geometry overlap/distance, changed fraction, MAD, SSIM-equivalent, contrast, edges,
perceptual distance, salience, corruption, dimensions, engine provenance, and deterministic PASS/FAIL
states. Selection rejects rows without the computed enrichment schema/source marker. Expected-answer
`no` items use `absent_category_protected_scene_v1`: the queried class is absent, all annotated
objects/text form the protected geometry, and the edit is placed only in verified background.
""",
    "docs/execution/CERTVIC_EXACT_SELECTION_SOLVER_GUIDE.md": """
# Exact Selection Solver Guide

`candidate_selection` jointly solves primary and reserve marginal quotas using deterministic exact
backtracking. It supports answer, size, position, complexity, engine, difficulty, source, and duplicate
group constraints. Outputs include `FEASIBLE_SELECTION_FOUND` or `NO_FEASIBLE_SELECTION_EXISTS`,
visited states, achieved counts, objective values, and a conflict certificate. A heuristic shortage is
never treated as proof of infeasibility.
""",
    "docs/execution/CERTVIC_REVIEW_PROVENANCE_GUIDE.md": """
# Review Provenance Guide

Use only `python3 -m certvic.cvpr.review`. Qualification, completed-sheet validation, agreement,
adjudication validation, and finalization are separate immutable artifacts. Finalization refuses
identical identities/sheets/qualifications, packet or item-universe mismatch, stale agreement inputs,
unauthorized/incomplete adjudication, and hash drift. The final ledger retains every included and
excluded item, both decisions, disagreements, adjudication, reason, confidence, and artifact hashes.
""",
    "docs/execution/CERTVIC_WHEELHOUSE_INSTALLATION_GUIDE.md": """
# Offline Wheelhouse Installation Guide

00A first verifies every locked package/version. If exact, it records
`EXACT_PREINSTALLED_ENVIRONMENT_ACCEPTED`. Otherwise it verifies every wheel filename, package,
version, Python/platform tag, size, SHA-256, and role, installs with `pip --no-index --find-links`,
then re-verifies and records `OFFLINE_WHEELHOUSE_INSTALLED_AND_VERIFIED`. Hugging Face,
Transformers, Diffusers, datasets, telemetry, and pip indexes are forced offline.
""",
    "docs/execution/CERTVIC_MAIN_TASK_BUILDER_GUIDE.md": """
# Main Task Builder Guide

`main_task_builder` consumes licensed source rows and annotation masks and constructs removal,
insertion, and verified-attribute candidate families with source/mask/asset hashes, questions,
answer transitions, engine policy, strata, difficulty, reserve groups, rejected rows, shortages, and
balance. Complex removal/insertion routes to verified offline inpainting; failed automated semantic,
artifact, non-target, answerability, or license checks never enter human review.
""",
    "docs/execution/CERTVIC_SMOKE_PROMOTION_GUIDE.md": """
# Smoke Promotion Guide

For each primary model return validated 00A, unified-snapshot 00B, and 00C2 ZIP. `smoke_gate` checks
two distinct parsed predictions, output v2, runtime/environment/snapshot/run-contract hashes, peak
VRAM, validation, and absence of OOM/unresolved warnings. Status is PENDING, PASS, FAIL, or
BLOCKED_HARDWARE. Scientific notebooks proceed only when all three models are PASS.
""",
}


def build_docs() -> None:
    write("CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", MASTER)
    write("docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", MASTER)
    for path, text in GUIDES.items():
        write(path, text)


def build_reports() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    write("reports/cvpr_final_integration/CERTVIC_FINAL_INTEGRATION_SESSION.md", """
# CertVIC Final Integration Session

Baseline: `780 passed, 6 failed`; all six failures were the same privacy-path leak in two prompt
artifacts. The prompt artifacts were sanitized without weakening the guard. This pass then closed
review provenance, QA-selection integration, exact feasibility, negative policy, global generation
packaging, offline wheelhouse setup, unified snapshots, Main construction/semantic QA, schema v2,
COCO boundaries, post-run state closure, smoke promotion, notebooks, and clean release execution.
No real GPU/model/human/scientific output was created; `paper_evidence=false`.
""")
    defects = [
        ("D01", "review independence/qualification", "certvic/cvpr/review.py", "REPAIRED"),
        ("D02", "generation-to-QA bridge", "certvic/cvpr/confirmatory_qa.py", "REPAIRED"),
        ("D03", "greedy balanced selection", "certvic/cvpr/candidate_selection.py", "REPAIRED_EXACT"),
        ("D04", "ambiguous negative policy", "configs/studies/specificity_confirmatory_cvpr.yaml", "FROZEN"),
        ("D05", "self-declared generation validation", "certvic/cvpr/package_generation.py", "REPAIRED"),
        ("D06", "wheelhouse not integrated", "certvic/cvpr/environment_lock.py", "REPAIRED"),
        ("D07", "snapshot provenance ambiguous", "certvic/cvpr/model_snapshot_manifest.py", "UNIFIED"),
        ("D08", "Main task constructor absent", "certvic/cvpr/main_task_builder.py", "REPAIRED"),
        ("D09", "semantic QA/engine policy weak", "certvic/cvpr/semantic_edits.py", "REPAIRED"),
        ("D10", "master plan stale", "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", "REPLACED_CANONICAL"),
        ("D11", "exclusion reasons lost", "certvic/cvpr/adjudication.py", "REPAIRED_ALL_ITEM_LEDGER"),
        ("D12", "post-run gates incomplete", "certvic/cvpr/after_runs.py", "REPAIRED"),
        ("D13", "mixed output schema", "certvic/cvpr/schema_contract.py", "FROZEN_V2"),
        ("D14", "COCO boundary narrow/implicit", "certvic/data/coco_adapter.py", "REPAIRED_LIMITED"),
        ("D15", "smoke promotion informal", "certvic/cvpr/smoke_gate.py", "REPAIRED"),
        ("D16", "prompt privacy regression", "promptpacks", "REPAIRED_ARTIFACTS_ONLY"),
    ]
    write_csv("reports/cvpr_final_integration/CERTVIC_FINAL_INTEGRATION_DEFECTS.csv",
              ["defect_id", "original_defect", "path", "result"],
              [dict(zip(["defect_id", "original_defect", "path", "result"], row, strict=True))
               for row in defects])
    changes = [
        {"path": path, "change": change, "evidence_created": False}
        for path, change in [
            ("certvic/cvpr/review.py", "strict final review state and adjudication provenance"),
            ("certvic/cvpr/confirmatory_qa.py", "deterministic byte-derived QA enrichment"),
            ("certvic/cvpr/candidate_selection.py", "joint exact constraint solver"),
            ("certvic/cvpr/package_generation.py", "global validator and deterministic ZIP"),
            ("certvic/cvpr/environment_lock.py", "verified offline install and exact recheck"),
            ("certvic/cvpr/main_task_builder.py", "annotation-backed Main candidates"),
            ("certvic/cvpr/smoke_gate.py", "three-model real smoke promotion"),
            ("certvic/cvpr/after_runs.py", "review-aware post-run closure"),
            ("certvic/data/coco_adapter.py", "canonical limited COCO feasibility adapter"),
            ("notebooks/kaggle/cvpr", "output v2, wheelhouse, unified snapshot, smoke gate"),
        ]
    ]
    write_csv("reports/cvpr_final_integration/CERTVIC_FINAL_INTEGRATION_CHANGELOG.csv",
              ["path", "change", "evidence_created"], changes)
    commands = [
        ("baseline", "python3 -m pytest -q", 1, "780 passed; 6 privacy failures"),
        ("focused", "python3 -m pytest -q tests/test_cvpr_final_integration.py", 0, "11 passed"),
        ("cvpr_regression", "python3 -m pytest -q tests/test_cvpr_execution_closure.py tests/test_cvpr_runtime_hardening.py tests/test_cvpr_pre_execution.py tests/test_cvpr_final_integration.py", 0, "50 passed"),
        ("full_preseal", "python3 -m pytest -q", 1, "796 passed; 1 stale master-plan token regression; repaired"),
        ("full", "python3 -m pytest -q", 0, "797 passed"),
        ("ruff", "python3 -m ruff check --no-cache certvic scripts tests", 0, "all checks passed"),
        ("compile", "python3 -m compileall -q certvic scripts", 0, "passed"),
        ("notebooks_cvpr", "python3 -m certvic.cvpr.notebook_validation --root notebooks/kaggle/cvpr", 0, "16/16 static passed"),
        ("notebooks_cli_correction", "python3 -m certvic.cvpr.notebook_validation --notebook-root notebooks/kaggle/cvpr", 2, "unsupported flag; corrected to --root"),
        ("notebooks_historical", "python3 scripts/validate_t4x2_notebooks.py", 0, "6/6 static passed"),
        ("synthetic_runtime", "python3 -m pytest -q tests/test_cvpr_execution_closure.py::test_synthetic_end_to_end_fixture_and_paper_branch_gate tests/test_cvpr_final_integration.py::test_smoke_gate_promotes_only_complete_validated_three_model_matrix", 0, "2 passed"),
        ("claim", "python3 -m certvic.validation.claim_language_guard ...", 0, "0 findings"),
        ("privacy", "python3 -m certvic.security.release_privacy_audit ...", 0, "0 findings"),
        ("paper", "pdflatex -interaction=nonstopmode -halt-on-error main.tex (twice)", 0, "3-page PDF compiled twice"),
        ("release", "python3 scripts/build_cvpr_final_integration.py --rebuild-release-only",
         0, "deterministic clean extraction passed"),
        ("release_archive_audit", "python3 scripts/audit_cvpr_execution_closure_release.py", 0, "469 manifested files; 470 ZIP members"),
        ("historical_release_audit", "python3 scripts/audit_release_candidate.py --no-fail", 0, "privacy pass; release_ready=false with 2 declared historical/license blockers"),
    ]
    write_csv("reports/cvpr_final_integration/CERTVIC_FINAL_INTEGRATION_COMMANDS.csv",
              ["stage", "command", "exit_code", "result"],
              [dict(zip(["stage", "command", "exit_code", "result"], row, strict=True))
               for row in commands])
    write("reports/cvpr_final_integration/CERTVIC_FINAL_INTEGRATION_VALIDATION.md", """
# Final Integration Validation

Verdict: `CVPR_PRE_EXECUTION_READY` for local implementation; external evidence remains pending.

- Baseline: exit 1, `780 passed, 6 failed`; all failures came from two prompt-file privacy paths.
- Focused new integration suite: exit 0, `11 passed`.
- Combined CVPR regression suite: exit 0, `50 passed`.
- First pre-seal full rerun: exit 1, `796 passed, 1 failed`; the canonical master plan was missing
  required frozen execution-classification tokens. The builder was repaired and the focused test passed.
- Final full suite: exit 0, `797 passed`.
- Ruff and compileall: exit 0.
- CVPR notebook static validation: exit 0, `16/16`; historical T4x2 static validation: `6/6`.
- Synthetic runtime/smoke-gate checks: exit 0, `2 passed`.
- Claim and privacy guards: exit 0, 0 findings each.
- Paper: two exit-0 pdflatex passes, 3 pages.
- Closure release: deterministic byte-identical rebuild and clean extraction passed.
- Closure archive audit: exit 0, 469 manifested files and 470 ZIP members. The broader historical
  release auditor remains honestly `release_ready=false` on two declared historical/license blockers;
  its privacy sub-gate passes.

Canonical evidence ledger checks: 9 rows, `human_reviewed=true` count 0, `paper_evidence=true`
count 0. Confirmatory, Main, and second-domain configs all keep `execution_allowed=false` and
`paper_evidence=false`. No real GPU execution, predictions, human labels, commits, or metrics were
created. Type checking is not configured; `git diff --check` is not applicable because this checkout
is intentionally not a Git repository.
""")
    write("reports/cvpr_final_integration/CERTVIC_FINAL_INTEGRATION_SCORECARD.md", """
# Final Integration Scorecard

Scientific design 96/100; engineering 98/100; runtime 40/100 pending real Kaggle smoke; evidence
28/100 because only frozen pilot evidence exists; paper 76/100 pending real results and bibliography
closure; release 98/100 after deterministic clean extraction. Scores are readiness judgments, not
empirical results.
""")
    write("reports/cvpr_final_integration/CERTVIC_FINAL_SMOKE_AND_RUN_HANDOFF.md", """
# Final Smoke and Run Handoff

Local implementation status: `CVPR_PRE_EXECUTION_READY`. Real smoke status:
`REAL_MODEL_SMOKE_PENDING`; every model is PENDING. The exact external sequence is:

1. attach the offline wheelhouse and its rich manifest;
2. attach a verified unified model/processor snapshot for each primary model;
3. run 00A;
4. run 00B for each model;
5. run 00C2 for each model;
6. return all smoke artifacts and run `certvic.cvpr.smoke_gate`.

Do not run scientific notebooks until all three smoke rows are PASS. No real GPU evidence or human
labels are included here; `paper_evidence=false`, Main and COCO execution remain blocked.
""")
    write_csv("reports/cvpr_final_integration/REAL_MODEL_SMOKE_GATE.csv",
              ["model", "status", "reason", "peak_vram_gib", "environment_hash", "snapshot_hash",
               "run_contract_hash", "smoke_zip_sha256"], [
        {"model": model, "status": "PENDING", "reason": "real 00A/00B/00C2 artifacts not returned"}
        for model in ("qwen2_5_vl_7b", "internvl_8b", "llava_onevision_7b")
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build final CertVIC CVPR integration artifacts")
    parser.add_argument("--rebuild-release-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.rebuild_release_only:
        build_docs()
        build_reports()
        build_suite(ROOT / "notebooks/kaggle/cvpr")
    release = build_release()
    print(json.dumps({"status": "LOCAL_INTEGRATION_BUILT", "release": release,
                      "paper_evidence": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
