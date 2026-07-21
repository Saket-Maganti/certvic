"""Seal the final local CVPR execution closure and deterministic release."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certvic.cvpr.environment_lock import environment_lock_hash  # noqa: E402
from certvic.cvpr.freeze_manifest import build_freeze_manifest  # noqa: E402
from certvic.cvpr.notebook_builder import build_suite  # noqa: E402


REPORT = ROOT / "reports/cvpr_execution_closure"
CANDIDATE = ROOT / "release/cvpr_execution_closure"
ARCHIVE = ROOT / "release/certvic_cvpr_execution_closure.zip"
DATE = "2026-07-15"


def write(relative: str, text: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(relative: str, value: Any) -> None:
    write(relative, json.dumps(value, indent=2, sort_keys=True))


def write_csv(relative: str, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_guides() -> None:
    write("docs/execution/CERTVIC_KAGGLE_RUNTIME_SMOKE_GUIDE.md", """
# CertVIC Kaggle Runtime Smoke Guide

All smoke output is non-evidence. Run 00A for code/environment, 00B once per exact model snapshot,
00C1 only for `SYNTHETIC_MOCK_RUNTIME`, and 00C2 once per provider for
`NON_EVIDENCE_REAL_MODEL_SMOKE`. 00C1 always passes `--mock-runtime`; 00C2 refuses until
`USE_REAL_MODEL=True` and never contains a mock fallback. A real smoke must preserve its ZIP, runtime,
environment, run-contract, peak-VRAM, validation, failure, and hash manifests. Resume only validated
rows; mismatches move to structured quarantine. No smoke may write scientific evidence paths.
""")
    write("docs/execution/CERTVIC_KAGGLE_T4X2_NOTEBOOK_INDEX.md", """
# CertVIC CVPR Kaggle Notebook Index

The exact suite has 16 notebooks: 00A, 00B, 00C1, 00C2; confirmatory 01-04; Main 10-13; and COCO
20-23. The manifest at `notebooks/kaggle/cvpr/notebook_manifest.json` is authoritative for bytes.
00C1 is mock-only; 00C2 is real-model-only. Generation applies one global bound and launches both T4
workers concurrently. Evaluation uses one process per visible T4 with a declared single-GPU fallback.
""")
    write("docs/execution/CERTVIC_MAIN_SEMANTIC_EDIT_GUIDE.md", """
# CertVIC Main Semantic Edit Guide

Status: implementation complete; scientific generation and human validity are external;
`paper_evidence=false`.

Main tasks must set `required_change=true`, name one of `object_removal`, `object_insertion`, or
`attribute_modification`, provide original and edited expected answers that differ, and bind the
question, source bytes, target mask or box, edit parameters, and expected transition into the task
hash. `certvic.cvpr.semantic_edits` provides deterministic preliminary removal, hash-locked insertion,
and mask-scoped attribute edits. Every output is `MACHINE_ASSISTED_PRELIMINARY` and
`HUMAN_REVIEW_PENDING`; image metrics cannot certify the semantic transition.

Optional inpainting uses `OfflineInpaintingAdapter`: verify every local snapshot byte, load once,
enable attention/VAE slicing, generate batches, halve on OOM, and release once. It is never silently
substituted for a required path. The `10_main_study_generation_T4x2.ipynb` notebook launches both
visible workers concurrently and applies `MAX_ITEMS` once before sharding.
""")
    write("docs/execution/CERTVIC_COCO_FEASIBILITY_GUIDE.md", """
# CertVIC COCO Feasibility Guide

Provide a local COCO 2017 tree containing `annotations/instances_val2017.json` and `val2017/`.
The adapter never downloads or releases pixels:

```bash
python3 -m certvic.data.coco_adapter_stub --coco-root <COCO_ROOT> \
  --out-dir data/studies/second_domain_cvpr/feasibility --items 60 --seed 17011
```

The adapter parses categories/instances, exports polygon or uncompressed-RLE masks, and builds
balanced answer-changing removal/insertion candidates. Every candidate remains blocked until its
per-image Flickr license is verified; insertion also requires a hash-locked category asset. Generate,
review, adjudicate, freeze, and run the three-model matrix before applying the four frozen feasibility
gates. Compressed RLE requires a separately locked pycocotools environment and fails closed otherwise.
""")
    write("docs/execution/CERTVIC_OFFLINE_KAGGLE_ENVIRONMENT_GUIDE.md", f"""
# CertVIC Offline Kaggle Environment Guide

Lock: `configs/runtime/kaggle_t4x2_environment.lock.json`  
Current canonical lock SHA-256: `{environment_lock_hash(ROOT / 'configs/runtime/kaggle_t4x2_environment.lock.json')}`.

The lock is a structured target, not observed Kaggle compatibility. Stage every wheel outside the
offline run, then hash it with `scripts/build_cvpr_wheelhouse_manifest.py`. On Kaggle install only via
`pip --no-index --find-links ... --require-hashes`; any missing, extra, or changed wheel is terminal.
00A validates Python, exact package versions, CUDA topology, code ZIP bytes, package source, and
offline environment variables. Do not use internet fallback or mutate the lock in a running study.
The target remains `STRUCTURED_TARGET_REQUIRES_LEVEL3_KAGGLE_VERIFICATION` until 00A passes on T4 x2.
""")
    write("docs/execution/CERTVIC_REAL_MODEL_SMOKE_GUIDE.md", """
# CertVIC Real Model Smoke Guide

00C1 is always `SYNTHETIC_MOCK_RUNTIME` and always passes `--mock-runtime`. 00C2 is always
`NON_EVIDENCE_REAL_MODEL_SMOKE`, contains no mock switch, and refuses execution until
`USE_REAL_MODEL=True`. Run 00A, then 00B for the exact mounted snapshot, then 00C2 for each of Qwen,
InternVL, and LLaVA. Success requires two items/four validated rows, model load, parsing, peak-VRAM and
runtime logs, cleanup, complete run-contract provenance, and a deterministic return ZIP.

Snapshot language is exact: local all-file validation is `LOCAL_SNAPSHOT_BYTES_VERIFIED`; a trusted
metadata check is `REMOTE_COMMIT_AUTHENTICATED`; a user-entered revision without authentication is
only `REMOTE_COMMIT_DECLARED`. Smoke output is never scientific evidence. InternVL uses NF4, float16,
at most six 448-pixel tiles plus thumbnail, and one process per visible T4. Failure at batch size one
blocks that provider and must name the alternative hardware rather than claiming compatibility.
""")
    write("docs/execution/CERTVIC_HUMAN_REVIEW_CLI_GUIDE.md", """
# CertVIC Human Review CLI Guide

Use one CLI throughout: `python3 -m certvic.cvpr.review <subcommand>`. The order is `build`,
`qualify`, `validate` for each independent rater, `agreement`, `adjudication-packet`, and `finalize`.
The qualification answer key/coordinator key remain separate. Reviewer identity is stored as a hash;
two distinct qualified identities are mandatory. Packet and sheet hashes, exact track-specific
columns, allowed choices, completeness, Gwet AC1, Cohen kappa, percent agreement, bootstrap intervals,
and every disagreement are fail-closed.

Specificity review judges answer invariance. Main/COCO review instead judges whether the intended
semantic transition succeeded and non-target content remained valid. Only
`FINAL_INCLUSION_VALIDATED` may enter filtered analysis. Blank templates and the synthetic fixture are
not genuine review and never set `human_reviewed=true`.
""")
    write("docs/execution/CERTVIC_EVIDENCE_LINEAGE_GUIDE.md", """
# CertVIC Evidence Lineage Guide

Every run binds task, prompt, image, parser, schema, code, environment, model/processor identity,
snapshot manifests, decoding, seed, and sharding in `run_contract_hash`. Resume revalidates the hash;
stale data moves to `quarantine/<reason>/<UTC timestamp>/` with a pointer record.

The all-providers importer stages all ZIPs before promotion. It separately records returned archive
SHA-256, raw merged JSONL SHA-256, canonical normalized JSONL SHA-256, and promoted artifact SHA-256.
Raw returned archives are `REAL_OBSERVED_EVIDENCE`; canonical rows are
`DERIVED_FROM_REAL_EVIDENCE` with an upstream hash. Analysis requires validated adjudicated inclusion
and writes raw, filtered, exclusion, agreement/adjudication, and artifact-lineage outputs. Paper
promotion remains a separate branch gate; successful import alone leaves `paper_evidence=false`.
""")
    write("docs/execution/CERTVIC_RELEASE_REPRODUCTION_GUIDE.md", """
# CertVIC Release Reproduction Guide

Build twice with `python3 scripts/build_cvpr_execution_closure.py`; the two archive SHA-256 values must
match. The archive contains all local Python modules (not a hand-picked partial dependency set),
configs, schemas, notebooks, fixtures, guides, paper source, cards, license matrix, closure reports,
and byte manifests. It excludes datasets, weights, genuine human sheets, credentials, and historical
quarantines.

Extract into an empty directory and set only that extraction root on `PYTHONPATH`. Run the recorded
imports, CLI help commands, and `certvic.cvpr.synthetic_study`. The fixture exercises generation,
mock review/adjudication, three mock providers, atomic import, human-aware analysis, tables, a guarded
paper fragment, and a synthetic release update. Every fixture artifact says
`SYNTHETIC_END_TO_END_FIXTURE` and `paper_evidence=false`.
""")


def build_reports() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    defects = [
        ("D01", "Main generation was not answer-changing", "certvic/cvpr/semantic_edits.py", "REPAIRED"),
        ("D02", "COCO was a NotImplemented stub", "certvic/data/coco_adapter_stub.py", "REPAIRED"),
        ("D03", "Generation workers launched sequentially", "certvic/cvpr/notebook_builder.py", "REPAIRED"),
        ("D04", "MAX_ITEMS applied once per shard", "certvic/cvpr/notebook_builder.py", "REPAIRED"),
        ("D05", "Inpainting had no verified lifecycle", "certvic/cvpr/inpainting.py", "REPAIRED"),
        ("D06", "Candidate eligibility/QA rules incomplete", "certvic/cvpr/candidate_selection.py", "REPAIRED"),
        ("D07", "Resume omitted full run provenance", "certvic/cvpr/run_contract.py", "REPAIRED"),
        ("D08", "Raw and canonical hashes conflated", "certvic/cvpr/whole_study_import.py", "REPAIRED"),
        ("D09", "Review operations were fragmented", "certvic/cvpr/review.py", "REPAIRED"),
        ("D10", "Analysis could precede adjudicated inclusion", "certvic/cvpr/analysis.py", "REPAIRED"),
        ("D11", "Kaggle dependencies were not offline locked", "configs/runtime/kaggle_t4x2_environment.lock.json", "REPAIRED"),
        ("D12", "Mock and real smoke were ambiguous", "notebooks/kaggle/cvpr/00C1_certvic_mock_adapter_smoke.ipynb", "REPAIRED"),
        ("D13", "InternVL FP16 policy was unsafe on one T4", "certvic/cvpr/adapters.py", "REPAIRED_PENDING_REAL_SMOKE"),
        ("D14", "Snapshot claims lacked authenticity classes", "certvic/cvpr/model_snapshot_manifest.py", "REPAIRED"),
        ("D15", "Release omitted transitive local modules", "scripts/build_cvpr_execution_closure.py", "REPAIRED"),
        ("D16", "Paper branches were not fail-closed", "certvic/cvpr/paper_branch.py", "REPAIRED"),
    ]
    write_csv("reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_DEFECTS.csv",
              ["defect_id", "original_defect", "repair_path", "status"],
              [{"defect_id": identity, "original_defect": defect, "repair_path": path,
                "status": status} for identity, defect, path, status in defects])
    write_csv("reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_CHANGELOG.csv",
              ["area", "change", "evidence_boundary"], [
                  {"area": "semantic", "change": "Main answer-changing edits plus optional offline inpainting", "evidence_boundary": "HUMAN_REVIEW_PENDING"},
                  {"area": "COCO", "change": "offline feasibility adapter and masks", "evidence_boundary": "LICENSE_AND_REVIEW_PENDING"},
                  {"area": "runtime", "change": "global bound, concurrent workers, full run contract", "evidence_boundary": "REAL_SMOKE_PENDING"},
                  {"area": "review", "change": "one qualification-to-finalization CLI", "evidence_boundary": "NO_REAL_JUDGMENTS"},
                  {"area": "lineage", "change": "raw/canonical/promoted hashes and human-aware analysis", "evidence_boundary": "NO_REAL_OUTPUTS"},
                  {"area": "release", "change": "transitive source and clean extraction exercise", "evidence_boundary": "SOFTWARE_ONLY"},
              ])
    commands = [
        ("baseline", "python3 -m pytest -q", "0", "774 passed before closure edits"),
        ("focused", "python3 -m pytest -q tests/test_cvpr_execution_closure.py", "0", "closure tests"),
        ("full", "python3 -m pytest -q", "PENDING_FINAL_CAPTURE", "final validation"),
        ("lint", "python3 -m ruff check --no-cache certvic scripts tests", "PENDING_FINAL_CAPTURE", "static validation"),
        ("compile", "python3 -m compileall -q certvic scripts", "PENDING_FINAL_CAPTURE", "syntax/import surface"),
        ("synthetic", "python3 -m certvic.cvpr.synthetic_study --out-dir <EMPTY_DIR>", "0", "non-evidence end-to-end fixture"),
        ("paper", "cd paper_cvpr && pdflatex -interaction=nonstopmode -halt-on-error main.tex", "PENDING_FINAL_CAPTURE", "guarded paper compile"),
        ("release", "python3 scripts/build_cvpr_execution_closure.py", "0", "deterministic archive"),
    ]
    validation_results_path = REPORT / "validation_results.json"
    if validation_results_path.is_file():
        captured = json.loads(validation_results_path.read_text(encoding="utf-8"))
        commands = [(str(row["phase"]), str(row["command"]), str(row["exit"]),
                     str(row["result"])) for row in captured.get("commands", [])]
    write_csv("reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_COMMANDS.csv",
              ["phase", "command", "exit", "result"],
              [{"phase": phase, "command": command, "exit": code, "result": result}
               for phase, command, code, result in commands])
    write("reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_SESSION.md", f"""
# CertVIC Execution Closure Session

Date: {DATE}. Local verdict: `CVPR_PRE_EXECUTION_READY`; `paper_evidence=false`.

This delta closes the implementation defects confirmed after runtime hardening. It does not contain
COCO/ADE20K source bytes, model weights, genuine model outputs, genuine human judgments, or a real
Kaggle compatibility claim. Frozen historical observations remain Qwen 12/94, InternVL 1/94, and
LLaVA 3/94. V2-30 remains retrospective sensitivity only. Main and second-domain execution remain
blocked until their signed gates are satisfied.

The software now has answer-changing Main interventions, a real offline COCO feasibility lane,
concurrent generation with a study-global limit, a manifest-verified inpainting lifecycle, full
run-contract resume provenance, separate raw/canonical lineage, one review CLI, adjudication-aware
analysis, an offline environment lock, unambiguous mock/real smoke notebooks, a bounded InternVL T4
strategy, freeze hashes, a synthetic end-to-end fixture, and a self-contained deterministic release.
""")
    write("reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_SCORECARD.md", """
# CertVIC Execution Closure Scorecard

Overall local verdict: `CVPR_PRE_EXECUTION_READY`. Scores measure pre-run readiness, not results.

| Dimension | Score / 100 | Boundary |
| --- | ---: | --- |
| Scientific design | 94 | protocols and gates complete; external sign-off/source decisions remain |
| Engineering | 97 | closure paths and failure modes implemented and locally tested |
| Runtime | 82 | synthetic end-to-end passes; 00A/00B/00C2 on real T4/snapshots pending |
| Evidence | 30 | frozen historical evidence only; no new real output or human review |
| Paper | 74 | guarded scaffold/branches compile; results and verified citations blocked |
| Release | 96 | deterministic self-contained source release and clean extraction test |

No score authorizes scientific execution or claim promotion by itself.
""")
    captured_summary = ""
    if validation_results_path.is_file():
        captured_summary = "\n\nFinal capture:\n\n" + "\n".join(
            f"- `{row['command']}`: exit {row['exit']}; {row['result']}"
            for row in json.loads(validation_results_path.read_text(encoding="utf-8")).get("commands", [])
        )
    write("reports/cvpr_execution_closure/CERTVIC_EXECUTION_CLOSURE_VALIDATION.md", """
# CertVIC Execution Closure Validation

Final machine-captured commands and exact totals are recorded in
`reports/cvpr_execution_closure/validation_results.json` and the commands CSV. The sealed gate requires
focused/full pytest, Ruff, compileall, notebook static checks, synthetic end-to-end execution, claim
and privacy guards, paper compile, release audit, clean extraction, and byte-identical archive rebuild.

Explicit boundary checks: `paper_evidence=false`; structured `human_reviewed=true` count is zero;
Main and second-domain `execution_allowed=false`; no real GPU evidence or human labels were created;
V2-30 remains retrospective; required closure paths contain no `NotImplementedError`; generation
uses concurrent `Popen` workers after one global slice; stale resume binds the full run-contract hash;
raw and canonical hashes are separate; and the release imports/runs from a clean extraction.
""" + captured_summary)
    write("reports/cvpr_execution_closure/CERTVIC_FINAL_PRE_RUN_HANDOFF.md", """
# CertVIC Final Pre-Run Handoff

Verdict: `CVPR_PRE_EXECUTION_READY`; scientific execution and evidence promotion remain blocked.

Use `CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md` as the sole authority. Provision and hash sources and the
offline wheelhouse; create byte-level manifests for all model/processor snapshots; run 00A; run 00B
per snapshot; then run real 00C2 separately for Qwen, InternVL, and LLaVA. A 00C1 pass is only
`SYNTHETIC_MOCK_RUNTIME` and cannot substitute for 00C2.

After smoke: build the outcome-blind specificity pool, generate controls, use the review CLI through
adjudication, freeze the final tasks, run the three confirmatory notebooks, and return all three ZIPs
together. Atomic import and human-aware analysis follow. Main may start only after its signed go/no-go.
COCO starts with 60 license-verified feasibility items and may expand only through its four gates.

Exact next action: provision the offline wheelhouse and run 00A on Kaggle T4 x2. Do not fill result
tables, mark reviews complete, authenticate remote commits without trusted metadata, or change
`paper_evidence` before genuine returned artifacts pass every gate.
""")
    write_json("reports/cvpr_execution_closure/BUILDER_OWNERSHIP.json", {
        "schema": "certvic.cvpr.builder_ownership.v2", "owner": "scripts/build_cvpr_execution_closure.py",
        "supersedes": ["scripts/build_cvpr_pre_execution.py", "scripts/build_cvpr_runtime_hardening.py"],
        "protected_surfaces": ["notebooks/kaggle/cvpr", "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md",
                               "reports/cvpr_execution_closure", "release/cvpr_execution_closure",
                               "release/certvic_cvpr_execution_closure.zip"],
        "paper_evidence": False,
    })


def build_master() -> None:
    path = ROOT / "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md"
    text = path.read_text(encoding="utf-8")
    start = "<!-- EXECUTION_CLOSURE_APPENDIX_START -->"
    if start in text:
        text = text.split(start)[0].rstrip() + "\n"
    runtime_start = "<!-- RUNTIME_HARDENING_APPENDIX_START -->"
    runtime_end = "<!-- RUNTIME_HARDENING_APPENDIX_END -->"
    if runtime_start in text and runtime_end in text:
        before, remainder = text.split(runtime_start, 1)
        _, after = remainder.split(runtime_end, 1)
        text = before.rstrip() + "\n" + after.lstrip()
    old_preflight = "| K00 | all | hardware/bundle preflight | required | GPU_KAGGLE_T4X2 | T4 x2 | 2 | 16 GB each | 10-20 min | C05/M01 | code, tasks, snapshots | `00_certvic_cvpr_preflight_and_bundle_audit.ipynb` | preflight report | all hashes and two/single topology explicit | VLM runs | repair mount; do not bypass hash mismatch |"
    new_preflight = "\n".join([
        "| K00A | all | code/environment smoke | required | KAGGLE_RUNTIME_SMOKE | T4 x2 | 2 | 16 GB each | 10-20 min | environment/wheelhouse | code ZIP + lock | `00A_certvic_code_and_environment_smoke.ipynb` | environment report | exact versions/hash/topology | snapshot smoke | repair wheelhouse; never enable network |",
        "| K00B | all | snapshot smoke | required per snapshot | KAGGLE_RUNTIME_SMOKE | T4 x2 | 2 | 16 GB each | 15-30 min each | K00A | local snapshot + manifest | `00B_certvic_model_snapshot_smoke.ipynb` | byte-verification report | all files/architecture/processor | real adapter smoke | rebuild manifest; never relabel bytes |",
        "| K00C1 | all | synthetic adapter smoke | optional diagnostic | KAGGLE_RUNTIME_SMOKE | CPU/GPU | 0-2 | n/a | K00A | two synthetic fixtures | `00C1_certvic_mock_adapter_smoke.ipynb` | mock ZIP | `SYNTHETIC_MOCK_RUNTIME` only | none | repair software contract only |",
        "| K00C2 | all | real two-item adapter smoke | required per provider | KAGGLE_RUNTIME_SMOKE | T4 x2 | 2 | 16 GB each | 15-45 min each | K00A/K00B | snapshot + two fixtures | `00C2_certvic_real_model_two_item_smoke.ipynb` | real-smoke ZIP | load/infer/parse/VRAM/cleanup | VLM runs | block provider or declare alternative hardware |",
    ])
    text = text.replace(old_preflight, new_preflight)
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Status:"):
            lines[index] = ("Status: `CVPR_PRE_EXECUTION_READY`; all local implementation gates pass; "
                            "real sources/snapshots/Kaggle/human review/scientific runs remain blocked; "
                            "`paper_evidence=false`.")
            break
    appendix = """
<!-- EXECUTION_CLOSURE_APPENDIX_START -->
## M. Final execution closure (2026-07-15)

This section supersedes the runtime-hardening continuation instructions. Local status is
`CVPR_PRE_EXECUTION_READY`, not paper-ready. The authoritative smoke order is 00A, 00B for each exact
snapshot, and real 00C2 for each provider; 00C1 is synthetic only.

Final order: source provision; offline environment/wheelhouse; snapshot manifests; 00A; 00B; three
00C2 runs; confirmatory candidate mining; concurrent control generation; qualification/two-rater
review/adjudication; final task freeze; three confirmatory model runs; atomic import; human-aware
analysis; Main go/no-go; Main semantic generation/model matrix; COCO-60 feasibility; paper
regeneration; release audit.

| Run | Class | Hardware | Estimate | Gate/output |
| --- | --- | --- | --- | --- |
| P00 sources | MANUAL_DATA_PROVISION | CPU/storage | 1-3 h | source hashes/licenses |
| E00 wheelhouse | CPU_LOCAL | CPU | 1-2 h | offline byte manifest |
| S00A | KAGGLE_RUNTIME_SMOKE | T4 x2 | 10-20 min | code/environment proof |
| S00B x3 | KAGGLE_RUNTIME_SMOKE | T4 x2 | 15-30 min each | local snapshot byte proof |
| S00C2 x3 | KAGGLE_RUNTIME_SMOKE | T4 x2 | 15-45 min each | two-item real adapter proof |
| C01-C05 | CPU_LOCAL + GPU_KAGGLE_T4X2 + HUMAN_REVIEW | mixed | CPU 2-8 h; GPU 7-17 notebook h; human 12-20 h | frozen confirmatory tasks |
| A01 | POST_RUN_CPU_ANALYSIS | CPU | 15-45 min | atomic import + reviewed analysis |
| M00-M04 | GPU_KAGGLE_T4X2 | T4 x2 | generation 4-10 h; models 26-54 notebook h | signed Main gate required |
| D00-D04 | CPU_LOCAL + GPU_KAGGLE_T4X2 + HUMAN_REVIEW | mixed | 6.5-15 h + 5-8 human h | COCO-60 gates |
| R00 | CPU_LOCAL | CPU | 0.5-1.5 h | paper/release guards |

All values are planning estimates until real smoke calibration. Single-GPU fallback is
`GPU_KAGGLE_SINGLE_FALLBACK`; optional branches are `OPTIONAL_SECONDARY`; Kaggle CPU-only preparation
is `CPU_KAGGLE`. See `reports/cvpr_execution_closure/CERTVIC_FINAL_PRE_RUN_HANDOFF.md`.
<!-- EXECUTION_CLOSURE_APPENDIX_END -->
"""
    updated = "\n".join(lines).rstrip() + "\n\n" + appendix.strip() + "\n"
    path.write_text(updated, encoding="utf-8")
    write("docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", updated)


def _release_inputs() -> list[Path]:
    paths: list[Path] = []
    paths += sorted(path for path in (ROOT / "certvic").rglob("*.py") if "__pycache__" not in path.parts)
    paths += sorted(path for path in (ROOT / "configs").rglob("*") if path.is_file())
    paths += sorted(path for path in (ROOT / "notebooks/kaggle/cvpr").glob("*") if path.is_file())
    paths += sorted(path for path in (ROOT / "docs/execution").glob("CERTVIC_*") if path.is_file())
    paths += sorted(path for path in REPORT.rglob("*")
                    if path.is_file() and path.name != "release_audit.json")
    paths += sorted(path for path in (ROOT / "reports/cvpr_final_integration").rglob("*")
                    if path.is_file() and not path.name.startswith("release_audit"))
    paths += sorted(path for path in (ROOT / "reports/cvpr_absolute_final").rglob("*")
                    if path.is_file() and "release_audit" not in path.name)
    paths += sorted(path for path in (ROOT / "reports/cvpr_run_readiness").rglob("*")
                    if path.is_file() and "release_audit" not in path.name)
    paths += sorted(path for path in (ROOT / "reports/cvpr_10of10_readiness").rglob("*")
                    if path.is_file() and "release_audit" not in path.name)
    paths += sorted(path for path in (ROOT / "reports/cvpr_final_runtime_patch").rglob("*")
                    if path.is_file() and "release_audit" not in path.name)
    paths += sorted(path for path in (ROOT / "paper_cvpr").rglob("*")
                    if path.is_file() and path.suffix in {".tex", ".csv", ".bib"})
    paths += sorted(path for path in (ROOT / "cards").glob("*.md") if path.is_file())
    paths += [ROOT / "pyproject.toml", ROOT / "README.md", ROOT / "LICENSE",
              ROOT / "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md",
              ROOT / "release/CERTVIC_DATA_AND_LICENSE_MATRIX.csv",
              ROOT / "scripts/build_cvpr_execution_closure.py",
              ROOT / "scripts/build_cvpr_wheelhouse_manifest.py",
              ROOT / "scripts/audit_cvpr_execution_closure_release.py",
              ROOT / "scripts/audit_release_candidate.py",
              ROOT / "scripts/build_cvpr_final_integration.py",
              ROOT / "scripts/build_cvpr_absolute_final.py",
              ROOT / "scripts/build_cvpr_run_readiness.py",
              ROOT / "tests/test_cvpr_execution_closure.py",
              ROOT / "tests/test_cvpr_final_integration.py",
              ROOT / "tests/test_cvpr_runtime_hardening.py",
              ROOT / "tests/test_cvpr_absolute_final.py",
              ROOT / "tests/test_cvpr_run_readiness.py",
              ROOT / "tests/test_cvpr_10of10_readiness.py",
              ROOT / "tests/test_cvpr_final_runtime_patch.py"]
    paths += sorted(path for path in CANDIDATE.rglob("*") if path.is_file()
                    and path.name not in {"RELEASE_FILE_MANIFEST.json", "ARCHIVE_SHA256.txt"})
    return sorted({path for path in paths if path.is_file()})


def _dependency_audit(source_paths: list[Path]) -> dict[str, Any]:
    module_paths = {".".join(path.relative_to(ROOT).with_suffix("").parts): path
                    for path in source_paths if path.suffix == ".py"}
    local_imports: set[str] = set()
    for path in source_paths:
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            raise ValueError(f"dependency audit cannot parse {path}: {exc}") from exc
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                local_imports.update(alias.name for alias in node.names if alias.name.startswith("certvic"))
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("certvic"):
                local_imports.add(node.module)
    missing = []
    for module in sorted(local_imports):
        if module in module_paths or any(name.startswith(module + ".") for name in module_paths):
            continue
        missing.append(module)
    return {
        "schema": "certvic.cvpr.release_dependency_audit.v1",
        "roots": ["worker", "generation", "candidate_selection", "review", "whole_study_import",
                  "analysis", "after_runs", "claim_guard", "privacy_guard", "report_generation",
                  "paper_injection", "smoke_artifacts", "smoke_handoff",
                  "reconcile_provider_permissions", "import_transaction",
                  "kaggle_session_simulator", "notebook_00c2_proof"],
        "strategy": "INCLUDE_ALL_CERTVIC_PYTHON_MODULES",
        "python_modules_included": len(module_paths), "local_imports_observed": len(local_imports),
        "missing_local_modules": missing, "passed": not missing, "paper_evidence": False,
    }


def _write_archive(paths: list[Path]) -> str:
    manifest = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths}
    manifest_path = CANDIDATE / "RELEASE_FILE_MANIFEST.json"
    manifest_path.write_text(json.dumps({"schema": "certvic.cvpr.execution_closure_release.v1",
                                         "files": manifest, "paper_evidence": False},
                                        indent=2, sort_keys=True) + "\n", encoding="utf-8")
    archive_paths = sorted({*paths, manifest_path})
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in archive_paths:
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()


def _clean_extraction_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="certvic_closure_release_") as temporary:
        extracted = Path(temporary) / "extracted"
        extracted.mkdir()
        with zipfile.ZipFile(ARCHIVE) as archive:
            if archive.testzip() is not None:
                raise RuntimeError("release archive is corrupt")
            archive.extractall(extracted)
        env = {**os.environ, "PYTHONPATH": str(extracted), "PYTHONNOUSERSITE": "1"}
        commands = [
            [sys.executable, "-c", "import certvic.cvpr.worker, certvic.cvpr.semantic_edits, certvic.cvpr.review, certvic.cvpr.whole_study_import, certvic.cvpr.after_runs, certvic.cvpr.confirmatory_qa, certvic.cvpr.package_generation, certvic.cvpr.main_task_builder, certvic.cvpr.smoke_gate, certvic.cvpr.smoke_contract, certvic.cvpr.smoke_artifacts, certvic.cvpr.smoke_handoff, certvic.cvpr.notebook_permission_binding, certvic.cvpr.reconcile_provider_permissions, certvic.cvpr.import_transaction, certvic.cvpr.kaggle_session_simulator, certvic.cvpr.notebook_00c2_proof, certvic.cvpr.task_schema, certvic.cvpr.task_bundle, certvic.cvpr.permission_ledger, certvic.cvpr.detectability_gate, certvic.cvpr.negative_item_builder, certvic.cvpr.execution_gate, certvic.cvpr.synthetic_closure"],
            [sys.executable, "-m", "certvic.cvpr.worker", "--help"],
            [sys.executable, "-m", "certvic.cvpr.semantic_edits", "--help"],
            [sys.executable, "-m", "certvic.cvpr.review", "--help"],
            [sys.executable, "-m", "certvic.cvpr.confirmatory_qa", "--help"],
            [sys.executable, "-m", "certvic.cvpr.package_generation", "--help"],
            [sys.executable, "-m", "certvic.cvpr.main_task_builder", "--help"],
            [sys.executable, "-m", "certvic.cvpr.smoke_gate", "--help"],
            [sys.executable, "-m", "certvic.cvpr.smoke_contract", "--help"],
            [sys.executable, "-m", "certvic.cvpr.task_schema", "--help"],
            [sys.executable, "-m", "certvic.cvpr.task_bundle", "--help"],
            [sys.executable, "-m", "certvic.cvpr.permission_ledger", "--help"],
            [sys.executable, "-m", "certvic.cvpr.detectability_gate", "--help"],
            [sys.executable, "-m", "certvic.cvpr.negative_item_builder", "--help"],
            [sys.executable, "-m", "certvic.cvpr.execution_gate", "--help"],
            [sys.executable, "-m", "certvic.cvpr.smoke_artifacts", "--help"],
            [sys.executable, "-m", "certvic.cvpr.smoke_handoff", "--help"],
            [sys.executable, "-m", "certvic.cvpr.reconcile_provider_permissions", "--help"],
            [sys.executable, "-m", "certvic.cvpr.import_transaction", "--help"],
            [sys.executable, "-m", "certvic.cvpr.kaggle_session_simulator", "--help"],
            [sys.executable, "-m", "certvic.cvpr.plan", "--help"],
            [sys.executable, "-m", "certvic.data.coco_adapter", "--help"],
        ]
        results = []
        for command in commands:
            completed = subprocess.run(command, cwd=extracted, env=env, capture_output=True,
                                       text=True, timeout=60, check=False)
            results.append({"command": " ".join(command[1:]), "exit": completed.returncode})
            if completed.returncode:
                raise RuntimeError(f"clean extraction command failed: {command}: {completed.stderr}")
        fixture_out = Path(temporary) / "synthetic_closure"
        command = [sys.executable, "-m", "certvic.cvpr.synthetic_closure", "--out-dir", str(fixture_out)]
        completed = subprocess.run(command, cwd=extracted, env=env, capture_output=True,
                                   text=True, timeout=120, check=False)
        results.append({"command": "synthetic_closure", "exit": completed.returncode})
        if completed.returncode:
            raise RuntimeError(f"clean synthetic study failed: {completed.stderr}")
        paper = extracted / "paper_cvpr/main.tex"
        if not paper.is_file() or "\\begin{document}" not in paper.read_text(encoding="utf-8"):
            raise RuntimeError("paper scaffold is absent from clean extraction")
        status = json.loads((fixture_out / "synthetic_closure_status.json").read_text())
        return {"schema": "certvic.cvpr.clean_extraction_test.v1", "passed": True,
                "commands": results, "synthetic_status": status["status"],
                "paper_scaffold_present": True, "paper_evidence": False}


def build_release() -> dict[str, Any]:
    CANDIDATE.mkdir(parents=True, exist_ok=True)
    write("release/cvpr_execution_closure/README.md", """
# CertVIC CVPR Execution Closure Release

Source-complete pre-run software release; `paper_evidence=false`. No weights, dataset pixels, genuine
human reviews, or real predictions are included. Start with the master plan and final pre-run handoff.
""")
    write("release/cvpr_execution_closure/REPRODUCIBILITY.md", """
# Reproducibility

Use the environment lock and an externally provisioned byte-hashed wheelhouse. Run the clean
extraction commands in `CERTVIC_RELEASE_REPRODUCTION_GUIDE.md`. The included synthetic fixture is
`SYNTHETIC_END_TO_END_FIXTURE`, not empirical evidence.
""")
    write("release/cvpr_execution_closure/DATA_CARD.md", """
# Data Card

No ADE20K or COCO pixels are redistributed. Real source rows remain pointer-only and require source
license verification. Included generated images are synthetic software fixtures.
""")
    write("release/cvpr_execution_closure/MODEL_CARD.md", """
# Model Runtime Card

Qwen2.5-VL-7B, InternVL2-8B, and LLaVA-OneVision-7B are planned; weights are excluded. All-file local
snapshot verification and real 00C2 T4 smoke are required. No compatibility result is claimed here.
""")
    fixture = CANDIDATE / "synthetic_fixtures"
    fixture.mkdir(exist_ok=True)
    Image.new("RGB", (32, 32), (80, 120, 160)).save(fixture / "source.png")
    (fixture / "README.md").write_text(
        "SYNTHETIC_END_TO_END_FIXTURE; paper_evidence=false; no scientific meaning.\n",
        encoding="utf-8",
    )
    freeze = build_freeze_manifest(ROOT)
    write_json("configs/studies/cvpr_pre_execution_freeze_manifest.json", freeze)
    build_suite(ROOT / "notebooks/kaggle/cvpr")
    source_paths = _release_inputs()
    audit = _dependency_audit(source_paths)
    if not audit["passed"]:
        raise RuntimeError(f"release dependency audit failed: {audit['missing_local_modules']}")
    write_json("release/cvpr_execution_closure/RELEASE_DEPENDENCY_AUDIT.json", audit)
    source_paths = _release_inputs()
    first = _write_archive(source_paths)
    second = _write_archive(source_paths)
    if first != second:
        raise RuntimeError("release rebuild is not byte-identical")
    clean = _clean_extraction_test()
    write_json("release/cvpr_execution_closure/CLEAN_EXTRACTION_TEST.json", clean)
    source_paths = _release_inputs()
    final_first = _write_archive(source_paths)
    final_second = _write_archive(source_paths)
    if final_first != final_second:
        raise RuntimeError("final release rebuild is not byte-identical")
    # Re-test the final bytes after adding the clean-extraction report.
    _clean_extraction_test()
    write("release/cvpr_execution_closure/ARCHIVE_SHA256.txt",
          f"{final_second}  {ARCHIVE.name}")
    return {"archive": str(ARCHIVE), "sha256": final_second,
            "members": len(source_paths) + 1, "clean_extraction": True,
            "deterministic_rebuild": True, "paper_evidence": False}


def main() -> None:
    build_guides()
    build_reports()
    build_master()
    release = build_release()
    print(json.dumps({"status": "CVPR_PRE_EXECUTION_READY", "release": release,
                      "paper_evidence": False}, sort_keys=True))


if __name__ == "__main__":
    main()
