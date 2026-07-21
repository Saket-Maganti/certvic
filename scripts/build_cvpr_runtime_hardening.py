"""Build deterministic runtime-hardening docs, paper scaffold, and release candidate."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/cvpr_runtime_hardening"


def write(relative: str, text: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_csv(relative: str, fields: list[str], rows: list[dict[str, object]]) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_guides() -> None:
    write("docs/execution/CERTVIC_KAGGLE_RUNTIME_SMOKE_GUIDE.md", """
# CertVIC Kaggle Runtime Smoke Guide

Status: runtime proof only; `NON_EVIDENCE_RUNTIME_SMOKE`; `paper_evidence=false`.

Run `00A` first to verify a hash-locked code ZIP, safe extraction, offline environment variables,
package import, source hash, disk, and Python. Run `00B` separately for each locally mounted snapshot;
it refuses missing, extra, or modified files, fake revisions, processor mismatch, and architecture
mismatch. Run `00C` with exactly two fixture items. Its default mock mode exercises worker batching,
resume, packaging, and output schemas without a model; set `USE_MOCK_RUNTIME=False` only after `00B`
passes to exercise the real adapter. None of these notebooks writes under scientific evidence paths.

For GPU notebooks choose T4 x2, attach the code ZIP, frozen tasks/images, and snapshot datasets, then
turn internet off. Fill only the first cell. Every discovered input candidate is printed; ambiguity is
a failure. The notebooks report GPU names, VRAM, compute capability, float16/BF16 support, disk, and
single-GPU fallback. Each worker receives one physical GPU through `CUDA_VISIBLE_DEVICES`; stdout and
stderr are separate files. On timeout, download the output ZIP or shard files, attach them to a new
session, and rerun with `--resume`. The worker revalidates every prior row and quarantines stale files.

Smoke ladder:

1. Level 0: compile, lint, static notebook/schema checks.
2. Level 1: local synthetic code extraction, two-worker mock, OOM halving, stale resume, package/import.
3. Level 2: optional dependency imports and mock model interfaces.
4. Level 3: user-run Kaggle environment, snapshot, and two-item adapter smoke.
5. Level 4: scientific execution, blocked until source, review, snapshot, and study gates are signed.
""")
    write("docs/execution/CERTVIC_MODEL_SNAPSHOT_MANIFEST_GUIDE.md", """
# CertVIC Model Snapshot Manifest Guide

The 40-character revision is a label until the mounted files are proven. Create a manifest only from
the exact local directory that will be attached to Kaggle:

```bash
python3 -m certvic.cvpr.model_snapshot_manifest create \
  --snapshot <SNAPSHOT> --model-id <MODEL_ID> \
  --model-commit <40_HEX> --processor-commit <40_HEX> \
  --architecture <EXPECTED_CLASS>
sha256sum <SNAPSHOT>/certvic_model_snapshot_manifest.json
```

The manifest records every regular file, size and SHA-256; config architecture/model type;
tokenizer/processor files; weight files; model and processor commits; and an offline-only rule. Run
`verify` with all expected fields before any adapter load. Verification rejects missing or extra files,
modified bytes, architecture drift, processor omissions, fake revisions, and manifests that permit
network access. Copy the manifest-file SHA-256 into the frozen runtime config and registry. A changed
snapshot requires a new manifest and run version; never relabel old outputs.
""")
    write("docs/execution/CERTVIC_HUMAN_REVIEW_OPERATIONS_GUIDE.md", """
# CertVIC Human Review Operations Guide

Build one track-specific visual packet with `certvic.cvpr.review_packets.build_visual_packet`. It
copies anonymous A/B images, randomizes order deterministically, displays the task question and
candidate expected answer, and omits model outcomes and original/edited identity. Keep the
coordinator key and qualification answer key outside reviewer delivery.

Each reviewer reads the codebook, completes the five-item qualification quiz, and must score at
least 80%. Two distinct qualified identities independently complete copies of the blank sheets. Never
edit the packet templates or hash manifest; completed sheets are new immutable files. Compute percent
agreement, Cohen kappa, the preregistered primary Gwet AC1 statistic, per-question results,
confidence strata, and bootstrap intervals. Extract only disagreements for the adjudicator. Preserve
both raw sheets and adjudication separately.

Final inclusion fails closed unless packet image/document hashes match, sheets are complete, rater
identities differ, every disagreement has an adjudicated value, and all validity fields satisfy the
frozen rule. A structurally valid blank sheet remains `HUMAN_REVIEW_PENDING`; it is never completion.
""")
    write("docs/execution/CERTVIC_POST_RUN_ATOMIC_IMPORT_GUIDE.md", """
# CertVIC Post-Run Atomic Import Guide

Place exactly one returned ZIP for each frozen provider in a new input directory. Do not unpack or
edit them. The whole-study importer checks ZIP integrity, duplicate/path-unsafe members, the complete
member hash manifest, runtime/environment/validation manifests, provider/study/schema/row count,
merged-output hash, and every row against frozen item, variant, prompt, image, task, model, processor,
parser, code-bundle, and snapshot hashes.

All providers are validated in a temporary staging directory. The matrix must have identical task
identity and study-wide provenance. Only then are canonical rows, immutable raw ZIPs, audit report,
and evidence ledger promoted with one directory rename. A failure promotes none. An identical import
is an idempotent no-op; conflicting prior output is refused and gets a quarantine marker. Successful
raw predictions are `REAL_OBSERVED_EVIDENCE`, while paper eligibility remains
`HUMAN_REVIEW_PENDING` and `paper_evidence=false` until the separate review and claim gates pass.
""")


def build_paper() -> None:
    sections = {
        "abstract": r"""\begin{abstract}
We study whether vision--language model responses change for answer-relevant interventions while
remaining stable under independently constructed, answer-irrelevant controls. This artifact defines
a prospective protocol with target-safe deterministic controls, exact specificity decisions, blinded
human validity review, immutable model/runtime provenance, and atomic multi-model import. The frozen
pilot motivates the design but does not supply confirmatory evidence. Confirmatory, Main-study,
human-review, and cross-domain result text remains blocked pending validated returned artifacts.
\end{abstract}""",
        "introduction": r"""\section{Introduction}
Visual question answering systems can appear responsive because their answers change after an image
edit, yet answer changes alone do not establish that the response tracks the intended semantic
intervention. A model may also react to irrelevant texture, color, or local processing artifacts.
CertVIC therefore separates two empirical questions: responsiveness to an answer-relevant edit and
specificity under a matched irrelevant edit. The current work turns that distinction into a
pre-specified, provenance-aware evaluation rather than treating a software pass as scientific proof.

Our planned contribution is a paired protocol with outcome-unseen control construction, exact
one-sided decisions with multiplicity, independent visual validity review, three immutable open-model
snapshots, and fail-closed import. The frozen V1 pilot remains historical motivation. The independent
confirmatory set, Main study, and second-domain stage have not run, so this draft states methods and
decision branches without selecting a result narrative.""",
        "problem_formulation": r"""\section{Problem Formulation}
For item $i$ and model $m$, let $Y^o_{im}$ and $Y^e_{im}$ be strictly parsed responses for the original
and edited images. Relevant interventions have a prespecified answer transition; irrelevant controls
prespecify answer invariance. Responsiveness measures correct semantic updates on relevant pairs.
Specificity measures $F_{im}=\mathbf{1}\{Y^o_{im}\ne Y^e_{im}\}$ on irrelevant pairs, with missing or
unparseable responses counted as flips in the primary analysis. The estimands are model-specific and
bounded to the sampled tasks, prompts, snapshot revisions, and edit families. They are not formal
adversarial robustness certificates or universal causal claims.""",
        "method": r"""\section{Protocol}
Candidate construction is outcome blind: model predictions are unavailable to mining, placement,
quality screening, human review, and replacement. The independent specificity design targets 240
primary and 60 same-stratum reserve items across twelve frozen categories. V1/V2 item, source-image,
exact-pixel, and perceptual overlap is prohibited. Selection balances target size, target position,
answer polarity, category, and perturbation family using a frozen seed. Shortages stop selection rather
than silently changing targets.

Every run binds tasks, prompts, image bytes, parser, code ZIP, model files, processor files, decoding,
and sharding to hashes. Workers write partial state frequently, validate it against the live contract,
quarantine stale rows, and promote only complete shards. The required three-provider import is atomic.""",
        "intervention_construction": r"""\section{Intervention Construction and Controls}
The required control path uses three deterministic families outside a protected target region: a
structured texture patch, a luminance/color-controlled neutral patch, and distant-region blur. Frozen
area, boundary, overlap, and target-distance rules are enforced before generation. Each output retains
source dimensions and mode and records placement, parameters, engine version, seeds, source/output
hashes, and CPU-safe quality metrics. Optional offline diffusion inpainting is a separate diagnostic
branch available only with a complete local snapshot manifest; its absence cannot disable the three
required deterministic families. Outputs failing readability, difference, geometry, area, salience,
similarity, or duplicate checks are rejected before review.""",
        "statistical_analysis": r"""\section{Statistical Analysis}
For each model, the primary specificity statistic is the observed paired flip rate with missing or
unparseable pairs counted as flips. We compute a one-sided Clopper--Pearson upper bound at familywise
$\alpha/3$ and compare it with the frozen 0.10 threshold. The simultaneous three-model statement
requires all three bounds to pass. Prespecified secondary outputs include raw parsed-only rates,
pairwise risk differences, exact McNemar tests, Holm-adjusted exploratory comparisons, perturbation-
family and geometry strata, and the preregistered human-validity-filtered sensitivity analysis.
Main-study outputs add original/edited correctness, correct semantic updates, the secondary descriptive old gap, and
an anytime-valid confidence-sequence gate under the existing certification policy. No branch is
activated from partial or unreviewed results.""",
        "experiments": r"""\section{Experimental Setup}
The planned matrix contains Qwen2.5-VL-7B-Instruct, InternVL2-8B, and LLaVA-OneVision-7B. Exact model
and processor commits remain external freeze fields. Each mounted snapshot must pass an all-file
offline manifest, architecture assertion, and tokenizer/processor verification. Qwen and LLaVA use
native processors with a T4-safe float16/NF4 policy. InternVL uses revision-compatible dynamic tiling,
thumbnail policy, patch bounds, normalization, image-token prompting, and float16 on T4. Kaggle
execution uses one worker per visible GPU, true tensor batching where supported, OOM halving to one,
single-GPU fallback, and deterministic multi-session resume. These descriptions are implementation
contracts, not observed runtime claims.""",
        "human_validation": r"""\section{Human Evaluation}
Two distinct qualified raters independently inspect anonymous A/B visual packets without model
outcomes or original/edited identity. They judge target preservation, expected-answer invariance,
perturbation acceptability, answerability, prompt clarity, retention, confidence, and reason code.
Training includes valid, ambiguous, answer-changing, and target-contaminating examples plus a scored
qualification quiz. The primary agreement summary is Gwet's AC1 for retention, accompanied by percent
agreement, Cohen's kappa, per-question agreement, confidence strata, and bootstrap intervals. An
outcome-blind adjudicator resolves disagreements; packet hashes and both raw sheets remain immutable.
No completed human judgments are present in this artifact.""",
        "results_guarded": r"""\section{Results}
\textbf{BLOCKED:} independent confirmatory model outputs, completed human review, and atomic import are
absent. The historical V1 counts remain motivation only. Tables and branch text are generated only by
the validated post-run analysis and remain marked \texttt{paper\_evidence=false} until all gates pass.""",
        "cross_domain": r"""\section{Cross-Domain Evaluation}
The second-domain lane begins with a 60-item COCO feasibility stage and cannot expand automatically.
The frozen gates require edit success at least 0.80, human validity at least 0.85, parse completeness
at least 0.95, and symmetric detectability AUC at most 0.80. A powered comparison, domain interaction,
and narrative are conditional on those gates. No second-domain execution has occurred.""",
        "limitations": r"""\section{Limitations}
The design targets three open-model families, selected datasets, yes/no-style prompts, and bounded edit
families; conclusions need not transfer beyond them. Automated image metrics cannot replace semantic
human judgment. Human validity itself is fallible and workload intensive. Deterministic controls may
not span all irrelevant transformations, while optional learned detectability is diagnostic rather
than a validity oracle. Exact intervals address sampling uncertainty but not dataset representativeness
or construct validity. Historical model revisions are not retroactively upgraded by future snapshots.""",
        "ethics": r"""\section{Ethics and Data Governance}
The protocol uses public research datasets subject to their source licenses and releases no model
weights. Reviewer packets expose only study images and anonymous pair IDs; coordinator keys and rater
identities remain separate. Release tooling scans for host-private paths, credentials, paid endpoints,
and disallowed archives. Negative findings are reported as bounded model behavior, not claims about
people or demographic groups. Dataset and license verification remains a manual precondition.""",
        "reproducibility": r"""\section{Reproducibility}
The release candidate contains source, frozen schemas/configs, clean notebooks, synthetic fixtures,
tests, guides, data/model cards, paper source, and a deterministic file manifest. Real data and model
weights are represented by source instructions and immutable manifests. Runtime records include GPU
topology, revisions, snapshot and code hashes, task/image/prompt hashes, batch/OOM events, shard
assignment, parser version, raw outputs, and validation reports. Reimport is idempotent for identical
bytes and refuses conflict.""",
        "conclusion": r"""\section{Conclusion}
CertVIC now has an executable, fail-closed path from outcome-blind controls through multi-model import
and guarded analysis. The remaining work is external execution and genuine human review. Until those
artifacts return and validate, the strongest honest conclusion is runtime-hardened pre-execution
readiness with scientific evidence and final paper claims still blocked.""",
    }
    for name, text in sections.items():
        write(f"paper_cvpr/sections/{name}.tex", text)
    write("paper_cvpr/main.tex", r"""\documentclass[10pt,twocolumn,letterpaper]{article}
\usepackage[margin=0.75in]{geometry}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{hyperref}
\hbadness=10000
\title{CertVIC: Separating Semantic Responsiveness from Intervention Specificity}
\author{Anonymous CVPR submission}
\date{}
\begin{document}
\maketitle
\input{sections/abstract}
\input{sections/introduction}
\input{sections/problem_formulation}
\input{sections/method}
\input{sections/intervention_construction}
\input{sections/statistical_analysis}
\input{sections/experiments}
\input{sections/human_validation}
\input{sections/results_guarded}
\input{sections/cross_domain}
\input{sections/limitations}
\input{sections/ethics}
\input{sections/reproducibility}
\input{sections/conclusion}
% Bibliography remains disabled until every source in the TODO matrix is researcher-verified.
\end{document}""")
    topics = ["VLM robustness", "counterfactual VQA", "image-edit evaluation", "consistency testing",
              "certified robustness", "confidence sequences", "sequential testing",
              "benchmark validity", "human evaluation"]
    write_csv("paper_cvpr/RELATED_WORK_CITATION_TODO.csv",
              ["topic", "comparison_needed", "verification_status"],
              [{"topic": topic, "comparison_needed": "scope, estimand, threat model, evidence",
                "verification_status": "REQUIRED_RESEARCHER_SOURCE_VERIFICATION"} for topic in topics])
    write("paper_cvpr/figures/protocol_overview.tex", r"""\begin{tabular}{ccccc}
Frozen source $\rightarrow$ & outcome-blind controls $\rightarrow$ & blinded review $\rightarrow$ &
three frozen models $\rightarrow$ & atomic analysis \\
\end{tabular}""")
    write("paper_cvpr/figures/study_flow.tex", r"""\begin{tabular}{lll}
Specificity confirmation & required first & 240 primary + 60 reserve \\
Main study & conditional on signed gates & execution blocked \\
Second domain & 60-item feasibility first & powered expansion conditional \\
\end{tabular}""")


def build_master_appendix() -> None:
    appendix = """
<!-- RUNTIME_HARDENING_APPENDIX_START -->
## L. Execution-realization and runtime smoke update (2026-07-14)

Runtime status: `PARTIALLY_READY_WITH_BLOCKERS`; `paper_evidence=false`. Deterministic control
generation, balanced candidate selection, snapshot verification, adapter lifecycle, T4-safe InternVL
tiling/float16, real batching/OOM fallback, stale-resume quarantine, code extraction, visual review,
agreement/adjudication, whole-study atomic import, guarded analysis, and 16 notebooks are implemented
and covered by local synthetic tests. Level-3 Kaggle environment/model smoke and Level-4 scientific
execution remain external.

`KAGGLE_RUNTIME_SMOKE` is a distinct execution type. It is non-evidence and may process only the
bounded fixture count recorded by the smoke notebook.

| Smoke run | Level | Execution type | Items | Required input | Success output | Evidence class |
| --- | ---: | --- | ---: | --- | --- | --- |
| S00A code/environment | 1/3 | KAGGLE_RUNTIME_SMOKE | 0 | code ZIP + hash | import/source/hardware report | NON_EVIDENCE_RUNTIME_SMOKE |
| S00B snapshot | 2/3 | KAGGLE_RUNTIME_SMOKE | 0 | one snapshot + manifest | all-file/architecture verification | NON_EVIDENCE_RUNTIME_SMOKE |
| S00C adapter | 3 | KAGGLE_RUNTIME_SMOKE | 2 | frozen snapshot + two fixtures | four validated pair rows + ZIP | NON_EVIDENCE_RUNTIME_SMOKE |

The next continuation point is `reports/cvpr_runtime_hardening/CERTVIC_EXECUTION_REALIZATION_HANDOFF.md`.
Do not run Main, promote evidence, fill review sheets, or interpret smoke output scientifically.
<!-- RUNTIME_HARDENING_APPENDIX_END -->
"""
    marker_start = "<!-- RUNTIME_HARDENING_APPENDIX_START -->"
    root_plan = ROOT / "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md"
    base = root_plan.read_text(encoding="utf-8")
    if marker_start in base:
        base = base.split(marker_start)[0].rstrip() + "\n"
    base = base.replace(
        "Status: `CVPR_PRE_EXECUTION_READY`; real inputs/review/runs blocked; `paper_evidence=false`.",
        "Status: `PARTIALLY_READY_WITH_BLOCKERS`; runtime Level-3 smoke and all real runs are "
        "external; `paper_evidence=false`. The earlier `CVPR_PRE_EXECUTION_READY` label is "
        "superseded by this runtime audit.",
    )
    updated = base.rstrip() + "\n\n" + appendix.strip() + "\n"
    root_plan.write_text(updated, encoding="utf-8")
    write("docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", updated)


def build_reports() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    ownership = {
        "schema": "certvic.cvpr.builder_ownership.v1",
        "runtime_hardening_owns_shared_surfaces": True,
        "owner": "scripts/build_cvpr_runtime_hardening.py",
        "protected_from_legacy_builder": [
            "notebooks/kaggle/cvpr", "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md",
            "docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", "paper_cvpr", "release",
            "reports/cvpr_runtime_hardening",
        ],
        "paper_evidence": False,
    }
    write("reports/cvpr_runtime_hardening/BUILDER_OWNERSHIP.json",
          json.dumps(ownership, indent=2, sort_keys=True))
    write("reports/cvpr_runtime_hardening/CERTVIC_RUNTIME_HARDENING_SESSION.md", """
# CertVIC Runtime Hardening Session

Date: 2026-07-14. Verdict: `PARTIALLY_READY_WITH_BLOCKERS`; `paper_evidence=false`.

The live checkout reproduced a 758-pass/6-fail baseline: all six failures came from the new prompt
pack's host-private path. The focused legacy CVPR suite passed 17/17 while leaving the named runtime
behaviors unexercised. This pass repaired the implementation rather than weakening guards. No GPU,
provider, dataset-scale, or human-review execution occurred, and no empirical result was created.

Implemented surfaces cover deterministic generation and QA, perceptual/balanced selection, snapshot
manifests, provider adapters, batch/OOM/resume state, Kaggle setup, visual review, agreement,
adjudication, atomic study import, guarded post-run analysis, paper methods, release packaging, and a
five-level smoke ladder. External source data, real snapshot bytes/commits, Kaggle Level-3 smoke, and
genuine reviewers remain blockers.
""")
    defects = [
        ("D01", "generation notebooks omitted explicit run bound", "REPAIRED_LOCAL_SYNTHETIC"),
        ("D02", "required path selected disabled diffusion stub", "REPAIRED_DETERMINISTIC_PATH_OPTIONAL_OFFLINE_API"),
        ("D03", "worker batch/OOM/fail/resume flags decorative", "REPAIRED_LOCAL_SYNTHETIC"),
        ("D04", "partial/complete shards trusted without contract validation", "REPAIRED_LOCAL_SYNTHETIC"),
        ("D05", "code ZIP verified but not safely extracted/imported", "REPAIRED_LOCAL_SYNTHETIC"),
        ("D06", "revision locks declarative only", "REPAIRED_IMPLEMENTATION_EXTERNAL_SNAPSHOTS_PENDING"),
        ("D07", "InternVL fixed 448 resize and BF16 on T4", "REPAIRED_IMPLEMENTATION_KAGGLE_SMOKE_PENDING"),
        ("D08", "candidate miner stopped at census", "REPAIRED_LOCAL_SYNTHETIC_SOURCE_CENSUS_PENDING"),
        ("D09", "review infrastructure lacked visual/training/agreement operations", "REPAIRED_IMPLEMENTATION_HUMANS_PENDING"),
        ("D10", "importer incomplete and per-provider promotion", "REPAIRED_LOCAL_SYNTHETIC"),
        ("D11", "post-run analysis incomplete", "REPAIRED_SYNTHETIC_REAL_INPUTS_PENDING"),
        ("D12", "notebook tests static only", "REPAIRED_LEVEL1_LOCAL_LEVEL3_PENDING"),
        ("D13", "paper and release were thin scaffolds", "REPAIRED_RESULT_SECTIONS_STILL_BLOCKED"),
    ]
    write_csv("reports/cvpr_runtime_hardening/CERTVIC_RUNTIME_DEFECT_REGISTER.csv",
              ["defect_id", "confirmed_lead", "status", "paper_evidence"],
              [{"defect_id": defect, "confirmed_lead": lead, "status": status,
                "paper_evidence": False} for defect, lead, status in defects])
    changes = [
        ("certvic/cvpr/generation.py", "three deterministic engines, optional offline inpainting, QA, safety"),
        ("certvic/cvpr/candidate_selection.py", "perceptual dedup, strata, proposals, balancing, overlap proof"),
        ("certvic/cvpr/model_snapshot_manifest.py", "strict all-file offline snapshot create/verify"),
        ("certvic/cvpr/runtime_preflight.py", "safe code discovery/extraction/import and hardware report"),
        ("certvic/cvpr/adapters.py", "shared lifecycle, batching, dynamic InternVL tiling, float16"),
        ("certvic/cvpr/worker.py", "real batching, OOM halving, assignment, quarantine, resume validation"),
        ("certvic/cvpr/review_packets.py", "blinded HTML packets, training, quiz, immutable hashes"),
        ("certvic/cvpr/agreement.py", "agreement statistics and bootstrap intervals"),
        ("certvic/cvpr/adjudication.py", "disagreement extraction and fail-closed inclusion"),
        ("certvic/cvpr/whole_study_import.py", "three-provider staging, expected hashes, atomic promotion"),
        ("certvic/cvpr/analysis.py", "specificity/Main/second-domain branches and artifacts"),
        ("certvic/cvpr/notebook_builder.py", "16 runtime-hardened notebooks including 00A/00B/00C"),
    ]
    write_csv("reports/cvpr_runtime_hardening/CERTVIC_RUNTIME_REPAIR_CHANGELOG.csv",
              ["artifact", "repair", "validation"],
              [{"artifact": artifact, "repair": repair, "validation": "focused + full suite + guards"}
               for artifact, repair in changes])
    write("reports/cvpr_runtime_hardening/CERTVIC_RUNTIME_VALIDATION.md", """
# CertVIC Runtime Validation

Final local validation date: 2026-07-14. Verdict: `PARTIALLY_READY_WITH_BLOCKERS`;
`paper_evidence=false`.

| Gate | Command or assertion | Result |
| --- | --- | --- |
| Reproduced baseline | `python3 -m pytest -q` before privacy repair | 758 passed, 6 failed; all six were the new prompt pack's private host path |
| Legacy focused baseline | `python3 -m pytest -q tests/test_cvpr_pre_execution.py` | 17 passed; confirmed it did not exercise named runtime behaviors |
| Repaired focused paths | runtime-hardening plus legacy CVPR tests | 27 passed |
| Full suite | `python3 -m pytest -q` | 774 passed in 36.86 s |
| Lint | `python3 -m ruff check --no-cache certvic scripts tests` | pass, all checks |
| Byte compilation | `python3 -m compileall -q certvic scripts` | pass |
| Notebook static | JSON parse, clean cells, notebook contract tests | 16/16 pass |
| Synthetic runtime | generation, selection, snapshot, code extraction, batch/OOM, resume quarantine, review, atomic import, analysis | pass |
| Claim guard | README/docs/paper/reports scan | pass, 0 findings |
| Privacy guard | repository release privacy audit | pass, 0 findings |
| Paper | `pdflatex -interaction=nonstopmode -halt-on-error main.tex` | pass, 3-page PDF |
| Release determinism | two runtime-candidate builds | identical SHA-256 (recorded in candidate archive checksum) |
| Existing release audit | `python3 scripts/audit_release_candidate.py --no-fail` | privacy pass; release-ready false with two declared historical/license blockers |
| Builder ownership | rerun legacy pre-execution builder | runtime-owned surfaces preserved |

Evidence assertions: zero structured `human_reviewed=true` records; all runtime artifacts retain
`paper_evidence=false`; Main execution remains false; V2-30 remains retrospective sensitivity only;
no GPU/provider result or human label was created; required generation no longer selects a disabled
engine; worker flags affect tested behavior; stale shards are quarantined before regeneration.

Level 3 (Kaggle environment plus real two-item adapter smoke) and Level 4 (scientific execution) are
`NOT_RUN_EXTERNAL`. They cannot be converted into local passes.
""")
    write("reports/cvpr_runtime_hardening/CERTVIC_RUNTIME_READINESS_SCORECARD.md", """
# CertVIC Runtime Readiness Scorecard

Overall verdict: `PARTIALLY_READY_WITH_BLOCKERS`; software success is not empirical evidence.

| Dimension | Score / 100 | Boundary |
| --- | ---: | --- |
| Engineering | 92 | local implementations and synthetic failure paths built; Kaggle/model compatibility unproven |
| Execution | 70 | Level 0/1 local path built; Level 3 and all scientific runs external |
| Evidence | 30 | historical V1/V11 boundaries only; no new confirmatory or human evidence |
| Paper | 68 | substantive non-result sections; results/citations still gated |
| Release | 82 | deterministic candidate with code/config/notebooks/fixtures/docs/cards; real-data license decisions pending |

Promotion to `CVPR_PRE_EXECUTION_READY` requires successful 00A, one 00B per snapshot, one real-adapter
00C per provider, exact snapshot/commit freeze, and no unresolved implementation defect. It still would
not imply paper readiness.
""")
    write("reports/cvpr_runtime_hardening/CERTVIC_EXECUTION_REALIZATION_HANDOFF.md", """
# CertVIC Execution Realization Handoff

Verdict: `PARTIALLY_READY_WITH_BLOCKERS`; `paper_evidence=false`.

Start from the root `CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md`, then run the non-evidence smoke sequence:
00A once; 00B for Qwen, InternVL, and LLaVA; 00C with exactly two fixtures for each provider. Freeze
the six 40-character revisions and three snapshot-manifest hashes only after those pass. Then provision
and hash ADE20K, run outcome-blind candidate selection, generate deterministic controls, and complete
two-rater review/adjudication. Only after the final 240-task manifest is hash-locked may the three
confirmatory notebooks run. Return all three ZIPs together for atomic import.

Main remains blocked. V2-30 remains retrospective sensitivity only. Frozen V1 observations remain
Qwen 12/94, InternVL 1/94, and LLaVA 3/94; no result in this pass modifies them. Human sheets are blank,
no real GPU output exists, and smoke artifacts are `NON_EVIDENCE_RUNTIME_SMOKE`.

External blockers: source archives/license sign-off, real immutable model/processor snapshots and
commits, Kaggle T4 environment/model smoke, two distinct qualified reviewers plus adjudicator, and all
scientific runs. The exact next action is to build the code ZIP, attach it to Kaggle, and run 00A without
altering scientific configs or evidence directories.
""")


def build_release() -> None:
    candidate = ROOT / "release/cvpr_runtime_candidate"
    candidate.mkdir(parents=True, exist_ok=True)
    write("release/cvpr_runtime_candidate/README.md", """
# CertVIC CVPR Runtime Candidate

Pre-execution software artifact only; `paper_evidence=false`. This candidate includes no model weights,
private data, real predictions, completed reviews, or credentials. Use the root execution plan and
runtime-hardening handoff. Synthetic fixtures are non-evidence and test contracts only.
""")
    write("release/cvpr_runtime_candidate/REPRODUCIBILITY.md", """
# Reproducibility

Install with `python3 -m pip install -e '.[dev]'`; run `python3 -m pytest -q`, Ruff, compileall, claim
and privacy guards, notebook checks, paper compile, and release audit. Real execution requires source
license confirmation and user-created all-file snapshot manifests. Returned three-model ZIPs are
imported atomically. Identical imports are idempotent and conflicts are refused.
""")
    write("release/cvpr_runtime_candidate/DATA_CARD.md", """
# Data Card

No dataset bytes are redistributed. ADE20K validation is the planned confirmatory source and COCO 2017
validation is the staged second domain, both subject to source terms and manual hash/license records.
The included two-item images and tasks are synthetic software fixtures with no scientific meaning.
""")
    write("release/cvpr_runtime_candidate/MODEL_CARD.md", """
# Model Runtime Card

Planned families: Qwen2.5-VL-7B-Instruct, InternVL2-8B, and LLaVA-OneVision-7B. Weights are excluded.
Users must supply immutable offline snapshots, model/processor commits, expected architecture, and a
strict file manifest. Snapshot smoke output is non-evidence. T4 execution uses float16 or explicitly
verified NF4; InternVL BF16 is forbidden without capability proof.
""")
    fixture_dir = candidate / "synthetic_fixtures"
    fixture_dir.mkdir(exist_ok=True)
    tasks = []
    for index, color in enumerate(((40, 80, 120), (120, 80, 40)), start=1):
        original = fixture_dir / f"fixture_{index}_original.png"
        edited = fixture_dir / f"fixture_{index}_edited.png"
        Image.new("RGB", (32, 32), color).save(original)
        image = Image.new("RGB", (32, 32), color)
        image.putpixel((1, 1), tuple(255 - value for value in color))
        image.save(edited)
        tasks.append({"item_id": f"runtime_fixture_{index}",
                      "original_image_path": original.name, "edited_image_path": edited.name,
                      "question": "Is the synthetic square present?", "answer_format": "yes_no",
                      "mock_raw_response": "yes", "evidence_class": "SYNTHETIC_TEST_FIXTURE",
                      "paper_evidence": False})
    (fixture_dir / "two_item_tasks.jsonl").write_text(
        "".join(json.dumps(task, sort_keys=True) + "\n" for task in tasks), encoding="utf-8"
    )
    include = [ROOT / "pyproject.toml", ROOT / "README.md",
               ROOT / "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md",
               ROOT / "tests/test_cvpr_runtime_hardening.py",
               ROOT / "scripts/build_cvpr_runtime_hardening.py",
               ROOT / "scripts/build_cvpr_pre_execution.py",
               ROOT / "certvic/eval/parse.py", ROOT / "certvic/eval/sharding.py"]
    include += sorted((ROOT / "certvic/cvpr").glob("*.py"))
    include += sorted((ROOT / "certvic/schema").glob("*.py"))
    include += sorted((ROOT / "cards").glob("*.md"))
    include += sorted((ROOT / "configs/studies").glob("*cvpr*"))
    include += [ROOT / "configs/models/certvic_cvpr_model_registry.yaml"]
    include += sorted((ROOT / "notebooks/kaggle/cvpr").glob("*"))
    include += sorted((ROOT / "docs/execution").glob("CERTVIC_*"))
    include += sorted((ROOT / "paper_cvpr").rglob("*.tex"))
    include += [ROOT / "paper_cvpr/RELATED_WORK_CITATION_TODO.csv",
                ROOT / "release/CERTVIC_DATA_AND_LICENSE_MATRIX.csv"]
    generated_release_files = {"RELEASE_FILE_MANIFEST.json", "ARCHIVE_SHA256.txt"}
    include += sorted(
        path for path in candidate.rglob("*")
        if path.is_file() and path.name not in generated_release_files
    )
    include = sorted({path for path in include if path.is_file()})
    manifest = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in include}
    manifest_path = candidate / "RELEASE_FILE_MANIFEST.json"
    manifest_path.write_text(json.dumps({"schema": "certvic.cvpr.release_candidate.v1",
                                         "paper_evidence": False, "files": manifest},
                                        indent=2, sort_keys=True) + "\n")
    include.append(manifest_path)
    archive_path = ROOT / "release/certvic_cvpr_runtime_candidate.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(set(include)):
            info = zipfile.ZipInfo(str(path.relative_to(ROOT)), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    write("release/cvpr_runtime_candidate/ARCHIVE_SHA256.txt",
          f"{hashlib.sha256(archive_path.read_bytes()).hexdigest()}  {archive_path.name}")


def main() -> None:
    closure_owner = ROOT / "reports/cvpr_execution_closure/BUILDER_OWNERSHIP.json"
    if closure_owner.is_file():
        raise RuntimeError(
            "execution-closure builder owns shared CVPR surfaces; do not rerun runtime hardening"
        )
    build_guides()
    build_paper()
    build_master_appendix()
    build_reports()
    build_release()
    print(json.dumps({"status": "RUNTIME_HARDENING_SURFACES_BUILT", "paper_evidence": False},
                     sort_keys=True))


if __name__ == "__main__":
    main()
