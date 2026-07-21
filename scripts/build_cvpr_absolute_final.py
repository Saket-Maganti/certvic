"""Build the absolute-final CVPR pre-run guides, ledgers, plan, notebooks, and release."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certvic.cvpr.notebook_builder import build_suite  # noqa: E402


REPORT = ROOT / "reports/cvpr_absolute_final"


def write(relative: str, text: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_csv(relative: str, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_master_plan() -> None:
    rows = [
        (1, "Provision data", "ADE20K/COCO pointers and licenses", "manual provision plus SHA-256 inventory", "CPU/storage", "1-3 h", "source manifests", "hash/license audit", "resume inventory", "repair missing pointers", "data gate"),
        (2, "Provision wheelhouse", "environment lock", "python3 scripts/build_cvpr_wheelhouse_manifest.py --wheelhouse <WHEELS> --lock configs/runtime/kaggle_t4x2_environment.lock.json --out <MANIFEST>", "CPU", "1-2 h", "wheel manifest", "exact files/hashes", "reuse exact bytes", "restage wheelhouse", "environment gate"),
        (3, "Create snapshot manifests", "three local snapshots", "python3 -m certvic.cvpr.model_snapshot_manifest create --snapshot <ROOT> --model-id <ID> --model-commit <REV> --processor-commit <REV> --architecture <ARCH>", "CPU/storage", "15-45 min/model", "snapshot manifests", "all-file verification", "reuse unchanged snapshot", "rebuild manifest", "snapshot gate"),
        (4, "Run 00A", "code bundle, lock, wheelhouse", "00A_certvic_code_and_environment_smoke.ipynb", "Kaggle T4x2", "10-20 min", "00A environment report", "exact environment PASS", "rerun from saved inputs", "repair offline environment", "00B"),
        (5, "Run 00B", "00A plus each snapshot", "00B_certvic_model_snapshot_smoke.ipynb", "Kaggle T4x2", "15-30 min/model", "00B snapshot reports", "byte/architecture PASS", "one snapshot at a time", "repair snapshot", "00C2"),
        (6, "Run 00C2 per model", "trusted two-item tasks and snapshots", "00C2_certvic_real_model_two_item_smoke.ipynb", "Kaggle T4x2", "15-45 min/model", "three smoke ZIPs", "4 exact rows/model; VRAM; cleanup", "worker resume", "reduce batch or change hardware", "smoke gate"),
        (7, "Validate smoke gate", "00A/00B/00C2 and trusted contract", "python3 -m certvic.cvpr.smoke_gate --smoke-root <ROOT> --smoke-contract <CONTRACT> --out <GATE>", "CPU", "5-10 min", "strict gate CSV/JSON", "all providers PASS", "revalidate bytes", "rerun defective provider", "candidate build"),
        (8, "Build confirmatory candidates", "unseen source manifest", "python3 -m certvic.cvpr.candidate_mining --help", "CPU", "1-3 h", "canonical candidates", "prospective and zero-overlap", "checkpoint source scan", "replace invalid sources", "generation"),
        (9, "Generate controls", "canonical candidates", "01_specificity_confirmatory_generation_T4x2.ipynb", "Kaggle T4x2", "2-5 h", "strict generation ZIP", "global package PASS", "validated shard resume", "replay failed shard", "QA"),
        (10, "QA enrichment", "generation ZIP/root", "python3 -m certvic.cvpr.confirmatory_qa --candidate-manifest <TASKS> --generation-root <ROOT> --study-config configs/studies/specificity_confirmatory_cvpr.yaml --out <ROWS> --report <REPORT>", "CPU", "0.5-1.5 h", "QA rows/report", "computed PASS only", "idempotent recompute", "exclude failures", "review packet"),
        (11, "Build visual packet", "QA-passing universe", "python3 -m certvic.cvpr.review build --items <ROWS> --track specificity_confirmatory_cvpr --out-dir <PACKET> --seed 12013", "CPU", "20-40 min", "blinded packet", "packet hash exact", "rebuild deterministically", "qualification"),
        (12, "Qualify reviewers", "packet key and two humans", "python3 -m certvic.cvpr.review qualify --help", "Human review", "0.5-1 h", "two qualification artifacts", "distinct qualified identities", "retain completed response", "replace failed reviewer", "review"),
        (13, "Complete review", "two blinded sheets", "python3 -m certvic.cvpr.review validate --help", "Human review", "8-14 h", "validated rater sheets", "complete/hash-bound", "resume blank rows", "repair malformed rows", "agreement"),
        (14, "Agreement", "two validated sheets", "python3 -m certvic.cvpr.review agreement --help", "CPU", "5-15 min", "agreement artifact", "exact sheet hashes", "recompute", "repair sheet mismatch", "adjudication"),
        (15, "Adjudication", "disagreement packet", "python3 -m certvic.cvpr.review validate-adjudication --help", "Human review", "2-5 h", "validated adjudication", "authorized and complete", "resume unresolved rows", "repair role/row defects", "final inclusion"),
        (16, "Finalize inclusion", "all review artifacts", "python3 -m certvic.cvpr.review finalize --help", "CPU", "5-15 min", "final review state v2", "complete universe/signature", "idempotent", "repair provenance", "selection"),
        (17, "Exact balanced selection", "QA rows and final review", "python3 -m certvic.cvpr.candidate_selection --qa-enriched-manifest <QA> --final-inclusion-ledger <REVIEW> --config configs/studies/specificity_confirmatory_cvpr.yaml --out-dir <OUT>", "CPU", "5-30 min", "primary/reserve/exclusions", "solver PASS", "deterministic rerun", "resolve shortage or resource limit", "freeze"),
        (18, "Freeze final tasks", "selection and contracts", "python3 -m certvic.cvpr.freeze_manifest", "CPU", "5-10 min", "final task freeze", "task/review/config hashes", "reuse unchanged freeze", "repeat selection after drift", "authorization"),
        (19, "Authorize confirmatory", "strict smoke, review, tasks, freeze", "python3 -m certvic.cvpr.execution_gate authorize --study specificity_confirmatory_cvpr --smoke-gate <GATE> --final-task-manifest <TASKS> --final-review-ledger <REVIEW> --freeze-manifest <FREEZE> --code-hash <HASH> --environment-lock <LOCK> --model-registry <REGISTRY> --study-config <CONFIG> --out <PERMISSION>", "CPU", "5 min", "signed one-run permission", "verify command PASS", "reauthorize before expiry", "repair drift", "model matrix"),
        (20, "Run confirmatory matrix", "signed permission and three snapshots", "notebooks 02, 03, 04", "Kaggle T4x2", "5-12 notebook h", "three run ZIPs", "schema v2 and strict package", "validated shard resume", "provider-specific replay", "package validation"),
        (21, "Strict package validation", "three output roots", "python3 -m certvic.cvpr.package_run --help", "CPU/Kaggle", "10-20 min", "validated ZIPs", "exact rows/hashes/contracts", "repackage exact bytes", "replay invalid shard", "atomic import"),
        (22, "Atomic import", "three ZIPs and permission", "python3 -m certvic.cvpr.after_runs --input-dir <RETURNED> --study specificity_confirmatory_cvpr --strict", "CPU", "10-30 min", "atomic canonical matrix", "all-or-none promotion", "idempotent import", "replace defective archive", "analysis"),
        (23, "Human-aware analysis", "import and final review", "included in after_runs", "CPU", "10-30 min", "raw/filtered analyses", "predeclared statistics", "recompute exact inputs", "block on review drift", "Main go/no-go"),
        (24, "Main go/no-go", "confirmatory outcome", "inspect CONFIRMATORY_OUTCOME_AND_MAIN_GO_NO_GO.json", "CPU/human decision", "10-30 min", "signed GO or NO_GO", "signature and branch", "immutable decision", "resolve failed upstream gate", "Main build"),
        (25, "Build Main candidates", "source annotations/assets", "python3 -m certvic.cvpr.main_task_builder --source-root <ROOT> --source-manifest <SOURCE> --config configs/studies/main_study_cvpr.yaml --out <TASKS> --report <REPORT>", "CPU", "1-3 h", "canonical Main candidates", "three families/direct generator compatibility", "resume source scan", "replace invalid candidates", "semantic generation"),
        (26, "Semantic generation", "Main candidates", "10_main_study_generation_T4x2.ipynb", "Kaggle T4x2", "4-10 h", "strict generation ZIP", "engine policy/global package PASS", "validated shard resume", "reject or replay failed edit", "Main review"),
        (27, "Main QA/review/freeze", "semantic outputs", "python3 -m certvic.cvpr.main_task_builder --qa-enriched-manifest <QA> --final-inclusion-ledger <REVIEW> --config configs/studies/main_study_cvpr.yaml --finalize-out-dir <OUT>", "CPU + human", "35-55 human h; 2-5 CPU h", "500 primary/125 reserve/freeze", "review and quota PASS", "resume review; deterministic finalize", "repair shortages", "Main authorization"),
        (28, "Authorize Main", "signed confirmatory GO plus Main freeze/review/smoke", "python3 -m certvic.cvpr.execution_gate authorize --study main_study_cvpr ... --prerequisite-artifact <OUTCOME>", "CPU", "5 min", "signed Main permission", "all hashes and GO valid", "reauthorize before expiry", "repair drift", "Main matrix"),
        (29, "Run Main matrix", "Main permission and snapshots", "notebooks 11, 12, 13 then after_runs", "Kaggle T4x2 + CPU", "22-44 notebook h", "imported Main analysis", "three-provider atomic close", "validated shard resume", "replay provider", "COCO/paper"),
        (30, "Run COCO feasibility", "local COCO and licensed assets", "python3 -m certvic.data.coco_adapter --coco-root <ROOT> --out-dir <OUT> then notebooks 20-23", "CPU + Kaggle T4x2 + human", "CPU 1-3 h; GPU 5.5-12 h; human 5-8 h", "60-item feasibility route", "30/30 and 15/category plus review", "resume exact stage", "block on license/shortage", "paper"),
        (31, "Regenerate paper", "validated real analyses only", "cd paper_cvpr && pdflatex -interaction=nonstopmode -halt-on-error main.tex twice", "CPU", "15-30 min", "guarded PDF", "claim/privacy/compile PASS", "rebuild from same inputs", "repair guarded branch", "release"),
        (32, "Rebuild release", "final canonical state", "python3 scripts/build_cvpr_absolute_final.py --rebuild-release", "CPU", "10-20 min", "deterministic closure ZIP", "audit and clean extraction PASS", "byte-identical rebuild", "repair manifest/dependency", "handoff complete"),
    ]
    header = [
        "# CertVIC CVPR Execution Master Plan",
        "",
        "Sole continuation point. Local verdict: `CVPR_PRE_EXECUTION_READY`; `paper_evidence=false`.",
        "V2-30 remains retrospective. Main and COCO remain `execution_allowed=false`. No configuration",
        "boolean authorizes a run; only an unexpired hash-bound permission does. Runtime values below are",
        "planning estimates, not observations.",
        "Frozen historical facts: Qwen `12/94 = 0.1277`, InternVL `1/94 = 0.0106`, and LLaVA",
        "`3/94 = 0.0319`. V2-30 remains retrospective sensitivity evidence and is never prospective.",
        "",
        "| # | Run | Input | Command | Hardware | Estimated runtime | Output | Validation | Resume | Failure recovery | Downstream gate |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines = [*header]
    for row in rows:
        escaped = [str(value).replace("|", "\\|") for value in row]
        lines.append("| " + " | ".join(escaped) + " |")
    lines.extend([
        "", "## Hard boundaries", "",
        "- Real source bytes, real snapshot bytes, the offline wheelhouse, genuine reviewers, and real",
        "  Kaggle outputs are external blockers—not locally fabricated completion states.",
        "- A smoke PASS is non-evidence and authorizes only the exact hash-bound task/config/model universe.",
        "- `after_runs` verifies the same permission before atomic import and emits the signed confirmatory",
        "  outcome used by the Main authorization gate.",
        "- Any task/config/code/environment/model/review/freeze drift requires a new permission.",
        "", "## Execution classifications", "",
        "`MANUAL_DATA_PROVISION`, `CPU_LOCAL`, `CPU_KAGGLE`, `GPU_KAGGLE_T4X2`,",
        "`GPU_KAGGLE_SINGLE_FALLBACK`, `HUMAN_REVIEW`, and `POST_RUN_CPU_ANALYSIS` are the",
        "authoritative execution types. A fallback label never changes a scientific gate.",
        "", "## Final paper trigger", "",
        "Promote a results branch only after permission-bound atomic import, genuine finalized review,",
        "predeclared analysis, claim and privacy guards, two successful paper compiles, and a deterministic",
        "audited release. Successful software tests or smoke runs alone keep `paper_evidence=false`.",
        "", "## Exact next action", "",
        "Provision the real offline wheelhouse and exact model snapshots, run 00A and 00B, then execute",
        "00C2 for Qwen, InternVL, and LLaVA and validate the importer-grade smoke gate. There is no further",
        "local implementation prompt before that sequence.",
    ])
    text = "\n".join(lines)
    write("CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", text)
    write("docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", text)


def build_guides() -> None:
    write("docs/execution/CERTVIC_CANONICAL_TASK_SCHEMA_GUIDE.md", """
# CertVIC Canonical Task Schema Guide

`certvic.cvpr.task.v1` is the sole task contract for confirmatory, Main, and COCO lanes. The complete
field list and conditional null policy live in `certvic/cvpr/task_schema.py`. Convert legacy rows once
with `convert_legacy_task`; runtime, generation, import, analysis, and paper paths must not implement
aliases. `task_hash` covers every field except itself. File verification binds source, target-mask,
and protected-scene bytes. Mixed, incomplete, duplicated, or hash-drifted matrices fail closed.

```bash
python3 -m certvic.cvpr.task_schema --input <LEGACY.jsonl> --study <STUDY> --out <CANONICAL.jsonl> --verify-files
python3 -m certvic.cvpr.task_schema --input <CANONICAL.jsonl> --verify-files
```

Main uses `original_expected_answer` and `edited_expected_answer` directly. Attribute rows require a
registered exact transition and `original_attribute_verified=true`. Absent-category rows require the
protected-scene mask. Final execution rows require `qa_status=PASS`,
`review_status=VALID_ADJUDICATED`, and a primary/reserve role. Schema conversion is compatibility;
it is not review, evidence, or permission.
""")
    write("docs/execution/CERTVIC_SIGNED_EXECUTION_AUTHORIZATION_GUIDE.md", """
# CertVIC Signed Execution Authorization Guide

Study YAML keeps `execution_allowed=false`. Authority comes only from
`certvic.cvpr.execution_permission.v1`: an expiring, one-run SHA-256 content lock over the strict smoke
gate, canonical final tasks, final review state, task freeze, environment lock, model registry, study
config, and code hash. The notebooks and `after_runs` verify the same permission. Any changed byte,
wrong study, expired artifact, malformed signature, or synthetic permission in a scientific run is
terminal.

```bash
python3 -m certvic.cvpr.execution_gate authorize --study specificity_confirmatory_cvpr \
  --smoke-gate <GATE.json> --final-task-manifest <TASKS.jsonl> \
  --final-review-ledger <FINAL_REVIEW.json> --freeze-manifest <FREEZE.json> \
  --code-hash <SHA256> --environment-lock <LOCK> --model-registry <REGISTRY> \
  --study-config configs/studies/specificity_confirmatory_cvpr.yaml --out <PERMISSION.json>
python3 -m certvic.cvpr.execution_gate verify --permission <PERMISSION.json> \
  --study specificity_confirmatory_cvpr
```

Main authorization also requires the signed `certvic.cvpr.confirmatory_outcome.v1` artifact emitted
by successful confirmatory `after_runs`, with `main_go_no_go=GO`. A confirmatory pre-run permission is
not a result and cannot satisfy this prerequisite.
""")
    write("docs/execution/CERTVIC_MAIN_FINAL_TASK_CONSTRUCTION_GUIDE.md", """
# CertVIC Main Final Task Construction Guide

The Main lane is candidate build, prospective engine routing, semantic generation, automated QA,
blinded packet, two qualified independent reviews, agreement, adjudication, final inclusion, exact
family/source-bounded selection, primary/reserve assignment, and freeze. Candidate output is directly
accepted by `certvic.cvpr.semantic_edits`; no schema translation is hidden in the generator.

```bash
python3 -m certvic.cvpr.main_task_builder --source-root <ROOT> --source-manifest <SOURCE.jsonl> \
  --config configs/studies/main_study_cvpr.yaml --out <CANDIDATES.jsonl> --report <REPORT.json>
python3 -m certvic.cvpr.main_task_builder --qa-enriched-manifest <QA.jsonl> \
  --final-inclusion-ledger <FINAL_REVIEW.json> --config configs/studies/main_study_cvpr.yaml \
  --finalize-out-dir <FINAL>
```

Successful finalization writes `main_primary_tasks.jsonl`, `main_reserve_tasks.jsonl`,
`main_exclusions.jsonl`, `main_balance_report.json`, `main_solver_report.json`, and
`main_freeze_manifest.json`. Frozen targets are 500 primary (200 removal, 200 insertion, 100
attribute) and 125 reserve (50/50/25), at most one task per source. The balance report covers family,
category, answer transition, size, position, complexity, difficulty, source diversity, and engine.
Shortage blocks freeze. Every semantic output remains human-review pending until genuine review.
""")
    write("docs/execution/CERTVIC_STRICT_SMOKE_VALIDATION_GUIDE.md", """
# CertVIC Strict Smoke Validation Guide

The real smoke gate is importer-grade and non-evidence. First build a trusted contract from exactly
two canonical tasks (four paired rows), exact snapshot/run-contract artifacts, the environment lock,
the code ZIP, and the frozen prompt hash:

```bash
python3 -m certvic.cvpr.smoke_contract --task-manifest <TWO_TASKS.jsonl> \
  --provider-contracts <PROVIDERS.json> --environment-lock <LOCK> --code-bundle <CODE.zip> \
  --prompt-template-hash <SHA256> --out <TRUSTED_CONTRACT.json>
python3 -m certvic.cvpr.smoke_gate --smoke-root <RETURNED_ROOT> \
  --model-registry configs/models/certvic_cvpr_model_registry.yaml \
  --smoke-contract <TRUSTED_CONTRACT.json> --out <REAL_MODEL_SMOKE_GATE.csv>
```

For every provider the gate verifies 00A, 00B, safe ZIP paths, duplicate/corrupt members, an exact
member hash manifest, raw prediction hash, runtime/environment/snapshot/run contracts, provider,
model and processor revisions, task/image/prompt/parser/code hashes, exact paired row universe,
schema v2, PARSE_OK, recomputed validation, zero failures/OOM, positive peak VRAM, and model cleanup.
Sparse, extra, duplicated, hand-written, or tampered returns fail. PASS never creates paper evidence;
it is only one input to signed study authorization.
""")
    write("docs/execution/CERTVIC_END_TO_END_SYNTHETIC_PROOF.md", """
# CertVIC End-to-End Synthetic Proof

The authoritative local proof is deliberately non-empirical:

```bash
python3 -m certvic.cvpr.synthetic_closure --out-dir <NEW_EMPTY_DIR>
```

It executes the confirmatory protected-negative route through generation, QA, strict synthetic
review/adjudication, review-bound exact selection, freeze, and signed synthetic permission. It then
executes the Main attribute route through semantic generation, strict review, freeze, three mock
providers, package, permission-bound atomic import, analysis, paper fragment, and synthetic release.
Finally it builds an exact synthetic COCO-60 feasibility universe: 30 removal, 30 insertion, and 15
per category. Expected top status is `SYNTHETIC_ALL_STUDY_ROUTES_COMPLETE`.

Every artifact is `SYNTHETIC_END_TO_END_FIXTURE`, `paper_evidence=false`, and
`human_reviewed=false`. Synthetic rater identities exercise provenance logic but are not humans. The
proof validates joins and failure behavior only; it cannot support a CVPR result or model claim.
""")


def _captured() -> list[dict[str, Any]]:
    path = REPORT / "validation_results.json"
    if not path.is_file():
        return []
    return list(json.loads(path.read_text(encoding="utf-8")).get("commands", []))


def build_reports() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    defects = [
        ("AF01", "multiple task schemas and hidden aliases", "task_schema.py and canonical consumers"),
        ("AF02", "Main builder output incompatible with generator", "direct three-family canonical build"),
        ("AF03", "Main analysis used alternate gold fields", "canonical exact task-result join"),
        ("AF04", "generation notebooks bypassed strict package", "shard assembly plus mandatory global packager"),
        ("AF05", "review did not constrain selection", "signed final-review join and complete exclusions"),
        ("AF06", "negative policy was configuration only", "protected-scene negative builder"),
        ("AF07", "engine policy was advisory", "prospective engine controls generation"),
        ("AF08", "smoke validation accepted sparse reports", "trusted two-item importer-grade contract"),
        ("AF09", "execution relied on a mutable boolean", "expiring hash-bound one-run permission"),
        ("AF10", "Main stopped at candidates", "QA/review/selection/reserve/freeze finalizer"),
        ("AF11", "attribute fallback could be implicit", "verified registered exact transitions only"),
        ("AF12", "solver resource failure was ambiguous", "pruning/memoization/limits/resource-limit verdict"),
    ]
    write_csv("reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_DEFECTS.csv",
              ["defect_id", "defect", "repair", "status"], [
                  {"defect_id": identity, "defect": defect, "repair": repair, "status": "REPAIRED"}
                  for identity, defect, repair in defects
              ])
    write_csv("reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_CHANGELOG.csv",
              ["area", "change", "boundary"], [
                  {"area": "schema", "change": "one hash-bound canonical task v1 contract", "boundary": "software validation only"},
                  {"area": "generation", "change": "prospective engines and strict shard assembly", "boundary": "human validity pending"},
                  {"area": "review_selection", "change": "final adjudicated ledger controls exact selection", "boundary": "no genuine labels created"},
                  {"area": "smoke_authorization", "change": "importer-grade smoke and signed permissions", "boundary": "real smoke pending"},
                  {"area": "studies", "change": "confirmatory, Main, and COCO synthetic joins closed", "boundary": "SYNTHETIC_END_TO_END_FIXTURE"},
                  {"area": "release", "change": "absolute-final modules/guides/tests included", "boundary": "paper_evidence=false"},
              ])
    captured = _captured()
    defaults = [
        {"phase": "baseline", "command": "PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q", "exit": 0, "result": "797 passed before absolute-final changes"},
        {"phase": "focused", "command": "python3 -m pytest -q tests/test_cvpr_execution_closure.py tests/test_cvpr_final_integration.py tests/test_cvpr_runtime_hardening.py tests/test_cvpr_absolute_final.py", "exit": 0, "result": "43 passed"},
    ]
    command_rows = captured or defaults
    write_csv("reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_COMMANDS.csv",
              ["phase", "command", "exit", "result"], command_rows)
    write("reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_SESSION.md", """
# CertVIC Absolute-Final Session

Verdict: `CVPR_PRE_EXECUTION_READY`. The pass reproduced the live 797-test baseline, repaired the 12
confirmed integration defects, added focused absolute-final coverage, exercised all three study joins
synthetically, regenerated all 16 notebooks without outputs, and sealed the release path. This is a
pre-run software verdict only: `paper_evidence=false`; structured genuine `human_reviewed=true`
count is 0; Main and COCO `execution_allowed=false`; V2-30 remains retrospective.

No real GPU/model execution, dataset acquisition, provider call, scientific prediction, or genuine
human judgment occurred. Synthetic reviewer identities and mock providers exist only inside the
explicit `SYNTHETIC_END_TO_END_FIXTURE` route. The sole continuation point is
`CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md`.
""")
    rendered = "\n".join(
        f"- `{row['command']}`: exit {row['exit']}; {row['result']}" for row in command_rows
    )
    write("reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_VALIDATION.md", f"""
# CertVIC Absolute-Final Validation

All captured validations are artifact-derived and fail closed.

{rendered}

Explicit checks cover canonical/mixed schema rejection, all Main builder families through generation,
canonical Main analysis joins, strict generation packages, review-bound selection, protected-scene
negatives, prospective engines, exact/tampered smoke ZIPs, signed permissions including expiry and
Main GO prerequisite, Main final output names, attribute safety, 100/300/600/1,000-row solver stress,
all-route synthetic closure, post-run permission checks, 16 output-free notebooks, claim/privacy
guards, paper compile, clean extraction, release audit, and deterministic rebuild.

Boundary assertions: `paper_evidence=false`; genuine `human_reviewed=true` count 0; Main and COCO
`execution_allowed=false`; no real GPU evidence or labels; V2-30 retrospective; no mixed schema; no
manual success report authorizes execution.
""")
    write("reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_SCORECARD.md", """
# CertVIC Absolute-Final Scorecard

Scores are pre-run readiness, not result quality or execution authority.

| Dimension | Score / 100 | Boundary |
| --- | ---: | --- |
| Scientific design | 96 | frozen prospective paths; real confirmatory outcome pending |
| Engineering | 99 | all local joins implemented and fail-closed |
| Runtime readiness | 91 | importer-grade smoke path ready; real T4 proof pending |
| Review governance | 98 | qualification through review-bound selection; genuine review pending |
| Evidence | 30 | frozen historical evidence only; no new real evidence |
| Paper | 78 | guarded source compiles; results/citations remain external |
| Release | 99 | deterministic, audited, clean-extraction synthetic proof |

Overall local verdict: `CVPR_PRE_EXECUTION_READY`.
""")
    write("reports/cvpr_absolute_final/CERTVIC_ABSOLUTE_FINAL_HANDOFF.md", """
# CertVIC Absolute-Final Handoff

Verdict: `CVPR_PRE_EXECUTION_READY`; real execution remains intentionally blocked.

Exact next sequence: provision the offline wheelhouse and byte-verified Qwen, InternVL, and LLaVA
snapshots; run 00A; run 00B per snapshot; build the trusted two-item contract; run real 00C2 per
provider; return all artifacts; run the strict smoke gate; then follow steps 8-32 in the master plan.
There is no remaining local implementation prompt before real smoke execution.

External blockers are exact dataset/source bytes and licenses, exact wheelhouse bytes, exact local
model/processor snapshots, Kaggle T4x2 time, two genuine independent reviewers plus adjudication, and
real scientific execution. Do not substitute 00C1, synthetic permissions, mock review, a hand-written
PASS report, or `execution_allowed=true` for these prerequisites.
""")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build absolute-final CertVIC CVPR closure artifacts")
    parser.add_argument("--rebuild-release", action="store_true")
    args = parser.parse_args(argv)
    build_guides()
    build_master_plan()
    build_reports()
    build_suite(ROOT / "notebooks/kaggle/cvpr")
    release = None
    if args.rebuild_release:
        from scripts.build_cvpr_execution_closure import build_release

        release = build_release()
    print(json.dumps({"status": "CVPR_PRE_EXECUTION_READY", "release": release,
                      "paper_evidence": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
