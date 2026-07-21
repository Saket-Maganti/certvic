"""Deterministically build the CertVIC CVPR pre-execution documentation and package surfaces."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certvic.cvpr.notebook_builder import NOTEBOOKS, build_suite  # noqa: E402
from certvic.cvpr.statistics import specificity_operating_characteristic  # noqa: E402


DATE = "2026-07-13"


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_csv(path: str, fields: list[str], rows: list[dict[str, object]]) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_exclusion_inventory() -> None:
    manifests = [
        ROOT / "data/edits/spurious_flip_control/pilot_eval_tasks_reviewed.jsonl",
        ROOT / "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl",
    ]
    item_ids: set[str] = set()
    source_ids: set[str] = set()
    source_image_ids: set[str] = set()
    image_hashes: set[str] = set()
    manifest_hashes: dict[str, str] = {}
    for path in manifests:
        payload = path.read_bytes()
        manifest_hashes[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest()
        for line in payload.decode().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            item_ids.add(str(row["item_id"]))
            source_id = str(row.get("source", {}).get("source_id", row["item_id"]))
            source_ids.add(source_id)
            match = re.search(r"ADE_(?:train|val)_\d+", source_id)
            if match:
                source_image_ids.add(match.group(0))
            original_hash = row.get("metadata", {}).get("original_image_sha256")
            if original_hash:
                image_hashes.add(str(original_hash))
    inventory = {
        "schema": "certvic.cvpr.confirmatory_exclusions.v1",
        "status": "FROZEN_FROM_HISTORICAL_MANIFESTS",
        "manifest_sha256": manifest_hashes,
        "item_ids": sorted(item_ids),
        "source_ids": sorted(source_ids),
        "source_image_ids": sorted(source_image_ids),
        "original_image_sha256": sorted(image_hashes),
        "paper_evidence": False,
    }
    write("configs/studies/specificity_confirmatory_exclusions.json",
          json.dumps(inventory, indent=2, sort_keys=True))


MASTER_PLAN = r"""# CertVIC CVPR Execution Master Plan

Status: `CVPR_PRE_EXECUTION_READY`; real inputs/review/runs blocked; `paper_evidence=false`.
Generated 2026-07-13. This file supersedes conflicting V7-V11 run instructions for new work.
Historical artifacts remain authoritative for the historical run they describe.

## A. Current readiness

The V11 pilot evidence, frozen V1 decisions, and retrospective V2-30 boundary are preserved. The
prospective specificity protocol, Main-500 design, COCO second-domain design, model contracts,
human-review schemas, output schema, importer, analysis formulas, paper scaffold, and notebook
contracts are built. No new provider output or human judgment was created.

Frozen V1 observations remain Qwen `12/94` (fail under observed rate <=0.10), InternVL `1/94`, and
LLaVA `3/94`. All twelve Qwen flips are Qwen-only in the current three-model matrix; this is a
model-dependent diagnostic, not a causal explanation.

Blocked now: source-pool provisioning, researcher sign-off on the generated prior-item exclusion
inventory, real two-rater review, immutable model/processor commits, and every real CPU/GPU run.
Do not run Main-500 or second-domain confirmation. The existing V2-30 may be run only as an
optional retrospective sensitivity check and cannot unlock Main-500.

## B. Required inputs

| Input | Expected path or mount | Expected structure | License/hash action | User action |
| --- | --- | --- | --- | --- |
| ADE20K source pool | CLI `--source-manifest <PATH>` plus image root referenced by rows | JSONL with source_id, image_path, category, target_bbox or target_mask_path | verify ADE20K terms; run `sha256sum <ARCHIVE>` | required |
| COCO 2017 val | Kaggle input or local root chosen at execution | images, instances_val2017.json, panoptic files if used | record COCO source/license; hash archives | required later |
| Three model snapshots | three Kaggle datasets | immutable snapshot directory plus processor files | fill both 40-character commits in model registry; hash every snapshot | required |
| Reviewers | two independent raters plus outcome-blind adjudicator | completed unmodified CSV copies | preserve originals read-only and hash them | required |
| Returned run ZIPs | `<RETURNED_OUTPUTS>/*.zip` | merged_raw.jsonl, runtime_manifest.json, validation and hash manifests, shard files | importer checks ZIP and row contracts | required after runs |

Never place a host-private absolute path in a committed config or report.

## C. Run classification table

All times are conservative planning estimates, not measured runtimes.

| Run ID | Study | Stage | Req/Opt | Execution type | Hardware | GPUs | VRAM | Estimated runtime | Prerequisites | Input | Command/notebook | Output | Validation | Downstream gate | Recovery |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P00 | all | provision ADE20K and COCO | required | MANUAL_DATA_PROVISION | storage | 0 | n/a | 1-3 h | licenses | archives | manual | mounted sources + hashes | `sha256sum` | source gate | remount; never rewrite sources |
| C01 | confirmatory | verify exclusion inventory and freeze source manifest | required | CPU_LOCAL | CPU, 16 GB RAM | 0 | n/a | 0.5-1 h | P00 | generated V1/V2 exclusion inventory + source | peer sign-off | signed config/inventory hashes | `python3 -m pytest -q tests/test_cvpr_pre_execution.py` | construction freeze | version config; do not mutate signed copy |
| C02 | confirmatory | outcome-blind candidate census | required | CPU_LOCAL | CPU, 16 GB RAM | 0 | n/a | 0.5-2 h | C01 | source manifest | `python3 -m certvic.cvpr.candidate_mining --source-manifest <PATH> --out-dir data/studies/specificity_confirmatory_cvpr/candidates --seed 12013` | eligible/rejected JSONL | inspect status + duplicate counts | candidate pool | correct source row and rerun versioned output |
| C03 | confirmatory | deterministic control build | required | CPU_LOCAL | CPU, 16 GB RAM | 0 | n/a | 1-4 h | C02 | eligible pool | frozen builder command recorded with pool | candidate pairs | hashes, geometry, salience | review pool | resume by item ID; never overwrite images |
| C04 | confirmatory | optional inpainting controls | optional | GPU_KAGGLE_T4X2 | T4 x2 | 2 | 16 GB each | 1-3 h | C02 | candidates + code bundle | `01_specificity_confirmatory_generation_T4x2.ipynb` | generation ZIP | schema/hash/quality report | review pool | resume shards; batch 1 on OOM |
| H01 | confirmatory | two-rater validity + adjudication | required | HUMAN_REVIEW | two raters | 0 | n/a | 12-20 person-h | C03/C04 | blinded packet | follow human protocol | two raw sheets + adjudication | fail-closed sheet validator | final 240 + reserve | adjudicate blind; replace from same stratum |
| C05 | confirmatory | finalize task manifest | required | CPU_LOCAL | CPU | 0 | n/a | 0.5-1 h | H01 | accepted pairs | locked selection command | final_tasks.jsonl + hashes | 240 unique, no overlap, strata check | model preflight | replace only by frozen rule |
| M01 | all VLM | pin model/processor revisions | required | MANUAL_DATA_PROVISION | storage | 0 | n/a | 1-2 h | snapshots mounted | model snapshots | fill model registry | registry hash | execution-mode registry validator | VLM execution | use another immutable snapshot and new protocol version |
| K00 | all | hardware/bundle preflight | required | GPU_KAGGLE_T4X2 | T4 x2 | 2 | 16 GB each | 10-20 min | C05/M01 | code, tasks, snapshots | `00_certvic_cvpr_preflight_and_bundle_audit.ipynb` | preflight report | all hashes and two/single topology explicit | VLM runs | repair mount; do not bypass hash mismatch |
| K02 | confirmatory | Qwen evaluation | required | GPU_KAGGLE_T4X2 | T4 x2 | 2 | 16 GB each | 2-5 h | K00 | final set | `02_qwen_specificity_confirmatory_T4x2.ipynb` | Qwen ZIP | expected 480 rows + manifests | import | resume verified shard; batch reduction |
| K03 | confirmatory | InternVL evaluation | required | GPU_KAGGLE_T4X2 | T4 x2/shared fallback | 2 | 16 GB each | 3-7 h | K00 | final set | `03_internvl_specificity_confirmatory_T4x2.ipynb` | InternVL ZIP | expected 480 rows + manifests | import | shared model/single fallback; no dropped rows |
| K04 | confirmatory | LLaVA evaluation | required | GPU_KAGGLE_T4X2 | T4 x2 | 2 | 16 GB each | 2-5 h | K00 | final set | `04_llava_specificity_confirmatory_T4x2.ipynb` | LLaVA ZIP | expected 480 rows + manifests | import | resume verified shard; batch reduction |
| A01 | confirmatory | import and primary decision | required | POST_RUN_CPU_ANALYSIS | CPU | 0 | n/a | 15-45 min | K02-K04 | three ZIPs | `python3 -m certvic.cvpr.after_runs --input-dir <RETURNED_OUTPUTS> --study specificity_confirmatory_cvpr --strict` | immutable raw, canonical rows, decision status | full tests + guards | specificity sign-off | repair/re-export invalid archive; conflicts are never overwritten |
| H02 | pilot/V1 | complete existing blinded review | required | HUMAN_REVIEW | two raters | 0 | n/a | 10-18 person-h | V11 packet | 91+94 pairs | V11 review protocol | raw sheets + adjudication | V11 validator without `--allow-blank` | paper validity | preserve raw; adjudicate blind |
| G10 | Main-500 | relevant edit generation | conditional | GPU_KAGGLE_T4X2 | T4 x2 | 2 | 16 GB each | 8-18 h | specificity sign-off + all Main gates | 625-item pool | `10_main_study_generation_T4x2.ipynb` | edits ZIP | quality/detectability/hashes | Main review | resume shards; quarantine failed edits |
| H10 | Main-500 | validity review | conditional | HUMAN_REVIEW | two raters | 0 | n/a | 35-55 person-h | G10 | blinded pairs | Main review track | accepted 500 + reserve | IAA + adjudication | Main VLM | same-stratum replacement only |
| K11 | Main-500 | Qwen evaluation | conditional | GPU_KAGGLE_T4X2 | T4 x2 | 2 | 16 GB each | 5-10 h | H10 | locked Main tasks | `11_qwen_main_study_T4x2.ipynb` | Qwen ZIP | 1000 rows + manifests | Main import | resume shards |
| K12 | Main-500 | InternVL evaluation | conditional | GPU_KAGGLE_T4X2 | T4 x2/shared | 2 | 16 GB each | 8-16 h | H10 | locked Main tasks | `12_internvl_main_study_T4x2.ipynb` | InternVL ZIP | 1000 rows + manifests | Main import | shared/single fallback |
| K13 | Main-500 | LLaVA evaluation | conditional | GPU_KAGGLE_T4X2 | T4 x2 | 2 | 16 GB each | 5-10 h | H10 | locked Main tasks | `13_llava_main_study_T4x2.ipynb` | LLaVA ZIP | 1000 rows + manifests | Main import | resume shards |
| A10 | Main-500 | import/analysis | conditional | POST_RUN_CPU_ANALYSIS | CPU | 0 | n/a | 0.5-2 h | K11-K13 | three ZIPs | after-runs command with `main_study_cvpr` | tables/figures/decision | gate + claim firewall | paper branch | version invalid returns; preserve raw |
| G20 | second domain | COCO feasibility generation | conditional | GPU_KAGGLE_T4X2 | T4 x2 | 2 | 16 GB each | 2-5 h | specificity sign-off + COCO license | 60 tasks | `20_second_domain_generation_T4x2.ipynb` | feasibility edits ZIP | >=80% edit success, detectability AUC <=0.80 | feasibility review | resume/quarantine |
| H20 | second domain | feasibility review | conditional | HUMAN_REVIEW | two raters | 0 | n/a | 5-8 person-h | G20 | blinded 60 | second-domain review track | accepted set | >=85% human-valid | VLM feasibility | revise method, not thresholds |
| K21 | second domain | Qwen feasibility | conditional | GPU_KAGGLE_T4X2 | T4 x2 | 2 | 16 GB each | 1-2 h | H20 | 60 tasks | `21_second_domain_qwen_T4x2.ipynb` | ZIP | 120 rows | feasibility import | resume |
| K22 | second domain | InternVL feasibility | conditional | GPU_KAGGLE_T4X2 | T4 x2/shared | 2 | 16 GB each | 1.5-3 h | H20 | 60 tasks | `22_second_domain_internvl_T4x2.ipynb` | ZIP | 120 rows | feasibility import | shared fallback |
| K23 | second domain | LLaVA feasibility | conditional | GPU_KAGGLE_T4X2 | T4 x2 | 2 | 16 GB each | 1-2 h | H20 | 60 tasks | `23_second_domain_llava_T4x2.ipynb` | ZIP | 120 rows | feasibility import | resume |
| A20 | second domain | feasibility decision | conditional | POST_RUN_CPU_ANALYSIS | CPU | 0 | n/a | 15-45 min | K21-K23 | three ZIPs | after-runs command with `second_domain_cvpr` | go/no-go | all staged thresholds | powered 240 confirmation | stop or revise protocol before new data |
| P90 | paper | regenerate guarded paper | required after evidence | POST_RUN_CPU_ANALYSIS | CPU + TeX | 0 | n/a | 10-30 min | validated imports/review | decision reports | `cd paper_cvpr && pdflatex -halt-on-error main.tex` | anonymous PDF | claim/privacy/bibliography checks | release | placeholders stay blocked on missing data |
| R90 | release | build and audit release | required | POST_RUN_CPU_ANALYSIS | CPU | 0 | n/a | 15-45 min | P90 + license matrix | manifest | release recipe/audit | release ZIP + checksums | privacy/anonymity/license gates | exclude blocked artifacts; never weaken scanner |

Single-GPU fallback uses the same run IDs and shards sequentially; its execution type is
`GPU_KAGGLE_SINGLE_FALLBACK`. CPU Kaggle is optional only when local storage is insufficient and
uses `CPU_KAGGLE`; it does not change a scientific rule.

## D. Exact critical path

1. Provision and hash ADE20K; verify and sign the generated V1/V2 exclusion inventory.
2. Run the candidate census, build controls, and complete automatic quality checks.
3. Complete two independent blinded reviews and outcome-blind adjudication.
4. Freeze exactly 240 primary items plus 60 same-stratum reserves and hash-lock the manifest.
5. Pin all six immutable model/processor revisions and rebuild/hash-lock the code package.
6. Run the preflight notebook, then K02, K03, and K04 without changing prompts or decoding.
7. Return all three ZIPs and run A01 transactionally; complete H02 in parallel.
8. Sign the specificity branch. Main-500 remains blocked until every listed Main gate passes.
9. If permitted, execute G10, H10, K11-K13, and A10.
10. Execute the 60-item COCO feasibility lane; progress to 240 only if its frozen gates pass.
11. Regenerate paper and release artifacts only from validated imports and completed review hashes.

## E. Effort estimates

- Confirmatory CPU: 2-8 h; GPU: 7-17 notebook h (14-34 T4 GPU-h); human: 12-20 h.
- Main conditional: CPU 2-6 h; GPU: 26-54 notebook h (52-108 T4 GPU-h); human: 35-55 h.
- Second-domain feasibility: CPU 1-3 h; GPU 5.5-12 h (11-24 T4 GPU-h); human 5-8 h.
- Paper/release: 0.5-1.5 h. Critical-path elapsed time is estimated at 2-5 weeks depending on
  reviewer availability and Kaggle quotas. These are planning estimates, not observed runtimes.

## F. Kaggle instructions

For every notebook: accelerator = GPU T4 x2; internet = off after attached snapshots are verified;
attach the hash-locked code ZIP, task/image bundle, and provider snapshot. Fill only the configuration
cell. Run top-to-bottom. A single T4 is allowed only when the notebook reports the fallback. Download
the named final ZIP plus the validation report. On timeout, reattach the prior working-output dataset
and rerun; verified shard rows are skipped. Never resume from a file failing hashes or schema.

## G. Local commands

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest -q
python3 -m ruff check --no-cache certvic scripts tests
python3 -m compileall -q certvic scripts
python3 -m certvic.cvpr.candidate_mining --source-manifest <SOURCE.jsonl> --out-dir data/studies/specificity_confirmatory_cvpr/candidates --seed 12013 --dry-run
python3 -m certvic.cvpr.human_review --items <FINAL_TASKS.jsonl> --track specificity_confirmatory_cvpr --out-dir review_packet/cvpr/specificity_confirmatory --seed 12013
python3 scripts/validate_v11_human_review.py --packet-dir reports/v11_full_ceiling_audit/human_review_packet
python3 -m certvic.cvpr.after_runs --input-dir <RETURNED_OUTPUTS> --study specificity_confirmatory_cvpr --strict
python3 -m certvic.validation.claim_language_guard --root README.md docs paper paper_cvpr reports/cvpr_pre_execution --out reports/cvpr_pre_execution/claim_guard.md
python3 -m certvic.security.release_privacy_audit --root . --out reports/cvpr_pre_execution/privacy_audit.md --json-out reports/cvpr_pre_execution/privacy_audit.json
cd paper_cvpr && pdflatex -interaction=nonstopmode -halt-on-error main.tex
python3 scripts/audit_release_candidate.py --no-fail
```

## H. Gate decisions

- Independent specificity: for each model, the one-sided Clopper-Pearson upper bound must be at
  most 0.10; the three-model claim uses alpha 0.05/3. Missing/unparseable pairs count as flips.
- Human validity: both raters accept all required fields; disagreements require blind adjudication;
  no outcome-based exclusion.
- Main study: every boolean in `main_study_cvpr.yaml#go_requirements` must be true in a signed gate
  report. Model-dependent specificity may still motivate the study; the rule does not require all
  models to pass if the approved estimand is comparative.
- Second domain: progress from 60 only when human-valid >=0.85, parse completeness >=0.95, edit
  success >=0.80, and symmetric detectability AUC <=0.80.
- Paper evidence: all required returned archives imported, review complete, revisions pinned,
  ledgers regenerated, and claim/privacy/release checks pass. A green software suite alone is not
  paper evidence.

## I. Outcome branches

- Qwen passes: report that the independent stricter control changes the interpretation; do not
  rewrite its frozen V1 failure.
- Qwen fails: report model-dependent specificity if human validity and multiplicity gates pass.
- Multiple models fail: frame generic perturbation sensitivity; do not claim a mechanism.
- All models pass: report the protocol and bounded results, not universal robustness.
- High human rejection: stop, diagnose construction, version the protocol, rebuild outcome-blind.
- Poor generation: stop the affected strategy; deterministic controls remain a separate branch.
- OOM: halve batch, clear cache, reload, then single-GPU fallback; batch-size 1 failure is terminal.
- Revision unavailable: choose a new immutable revision and create a new run version; never relabel.
- Dataset non-releaseable: ship manifests, adapters, hashes, and reproduction instructions only.

## J. Output return checklist

After each Kaggle run return the final ZIP, all raw shard JSONL, merged raw JSONL, runtime and
environment manifests, validation/failure reports, and hash manifest. After human stages return
both untouched rater sheets, coordinator key separately, adjudication sheet, training quiz record,
and SHA-256 list. After generation return source/task manifests, images or permitted pointers,
quality/detectability reports, and rejected-item ledger.

## K. Final paper trigger

Switch to final CVPR-paper mode only after A01 is complete for all three models, human review is
validated, immutable revisions are recorded, the specificity decision is signed, any reported Main
or second-domain results have their own completed gates, the evidence ledger contains only validated
provenance, and claim/privacy/bibliography/anonymity/release checks all pass. Until then,
`paper_evidence=false`.
"""


def build_docs() -> None:
    index = """# CertVIC Canonical Project Index

Status: pre-execution, `paper_evidence=false`. For the current operational route, start with the
master plan and the CVPR handoff. V7-V10.3 documents are historical; V11 remains the baseline audit.

| Surface | Canonical path |
| --- | --- |
| Scientific protocol | `docs/methodology/CERTVIC_CVPR_SCIENTIFIC_PROTOCOL.md` |
| Statistical plan | `docs/methodology/CERTVIC_CVPR_STATISTICAL_ANALYSIS_PLAN.md` |
| Evidence/gate ledgers | `reports/cvpr_pre_execution/CERTVIC_CVPR_EVIDENCE_LEDGER.csv`, `CERTVIC_CVPR_GATE_LEDGER.csv` |
| Human review | `docs/methodology/CERTVIC_CVPR_HUMAN_REVIEW_PROTOCOL.md` and V11 blinded packet |
| Prospective specificity | `configs/studies/specificity_confirmatory_cvpr.yaml` |
| Main study | `configs/studies/main_study_cvpr.yaml` |
| Second domain | `configs/studies/second_domain_cvpr.yaml` |
| Models | `configs/models/certvic_cvpr_model_registry.yaml` |
| Kaggle notebooks | `notebooks/kaggle/cvpr/` |
| Import | `python3 -m certvic.cvpr.after_runs` |
| Paper | `paper_cvpr/main.tex` |
| Release | `release/CERTVIC_CVPR_RELEASE_MANIFEST.md` |
| Every remaining run | `CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md` |
"""
    protocol = """# CertVIC CVPR Scientific Protocol

Status: prospectively specified, not executed; `paper_evidence=false`.

CertVIC separates semantic responsiveness from intervention specificity. Original and relevant-edit
pairs measure correct answer updating; original and irrelevant-edit pairs measure inappropriate
answer flips. Primary rows retain raw provider text, parser status/version, image/task/prompt hashes,
and immutable model/processor identities. Certification-critical parsing fails closed.

The historical V1 decision remains observed flip rate <=0.10; Qwen remains 12/94 and fails it.
InternVL is 1/94 and LLaVA is 3/94 under that historical rule only. V2-30 overlaps V1 and remains
retrospective sensitivity evidence. The new `specificity_confirmatory_cvpr` set is outcome-unseen,
zero-overlap, 240 items plus 60 reserve, reviewed before outcomes, and evaluated under a one-sided
exact-binomial rule. Main-500 and COCO confirmation remain gated.

Raw provider artifacts, review sheets, source images, and source manifests are immutable. Derived
normalization is versioned and reproducible. No missing parse is converted into a valid answer; the
confirmatory primary analysis counts a missing/unparseable pair as a flip.
"""
    stats = """# CertVIC CVPR Statistical Analysis Plan

The confirmatory endpoint is the paired original/irrelevant-edit flip indicator. For each primary
model, report k/n and the one-sided Clopper-Pearson upper bound. Qwen primary uses alpha 0.05; a joint
three-model claim uses Bonferroni alpha 0.05/3 per model and passes only if every upper bound is <=0.10.
Report paired risk differences, exact McNemar tests, Holm-adjusted exploratory comparisons, raw
missing-as-failure primary results, preregistered human-validity-filtered results, and sensitivities.

Main estimands are original and edited correctness, raw answer change, correct semantic update,
correct semantic-update rate, irrelevant-edit specificity, the secondary descriptive old gap, and the existing
time-uniform confidence-sequence lane after its assumptions pass. Bootstrap and mixed models are
secondary. Families are models within domain for confirmatory specificity, then separately Main and
second domain; no result-dependent choice of correction is allowed.
"""
    human = """# CertVIC CVPR Human Review Protocol

Seven tracks are separate: pilot intervention validity, V1 specificity validity, retrospective
V2-30 sensitivity, Qwen-12 forensics, prospective specificity, Main study, and COCO second domain.
Reviewers see anonymous IDs and randomized A/B order, never provider identity, model answers,
failure status, prior machine decisions, or paper examples. Two independent raters judge target
unaffected, expected answer unchanged, perturbation acceptable, answerability, prompt ambiguity,
retain/exclude, confidence, and reason code. Disagreement requires outcome-blind adjudication.

Primary agreement reporting is percent agreement per required binary field; Cohen's kappa and Gwet's
AC1 are secondary with per-question and confidence-stratified summaries. Raw sheets are immutable.
The inclusion rule is frozen before outcomes and failures cannot be excluded because they are
failures. Blank templates remain `HUMAN_REVIEW_PENDING` and do not constitute labels.
"""
    terminology = """# CertVIC Certification Terminology

`certification` means a declared statistical decision under a fixed endpoint, threshold, confidence
procedure, multiplicity family, missingness policy, item order, and evidence-provenance gate. It does
not mean formal verification, causal identification, deployment safety, or universal model behavior.
Use `numerical bound passed` when review, sample, provenance, or specificity gates remain blocked.
Use `full protocol decision passed` only after every declared gate passes. Historical observed-rate
rules are never rewritten by prospective interval rules.
"""
    write("docs/CERTVIC_CANONICAL_PROJECT_INDEX.md", index)
    write("docs/methodology/CERTVIC_CVPR_SCIENTIFIC_PROTOCOL.md", protocol)
    write("docs/methodology/CERTVIC_CVPR_STATISTICAL_ANALYSIS_PLAN.md", stats)
    write("docs/methodology/CERTVIC_CVPR_HUMAN_REVIEW_PROTOCOL.md", human)
    write("docs/methodology/CERTVIC_CERTIFICATION_TERMINOLOGY.md", terminology)
    write("docs/studies/SPECIFICITY_CONFIRMATORY_DESIGN.md", protocol + "\n\nSee the locked study YAML for thresholds and strata.")
    write("docs/studies/MAIN_STUDY_DESIGN_LOCK.md", """# Main Study Design Lock

Historical name Main-500 is retained and the target remains 500 with 125 same-stratum reserves.
Selection is outcome-blind across the twelve strata in the study config. Relevant edits retain
source/image hashes, intended semantic change, masks, method/parameters/seed, output hash, automated
quality and detectability status, and human-review status. `execution_allowed=false` until every
machine-readable go requirement passes. A comparative model-dependent paper branch is allowed after
specificity sign-off; favorable-model selection is not.
""")
    write("docs/studies/SECOND_DOMAIN_DECISION_AND_DESIGN.md", """# Second-Domain Decision and Design

The single selected second domain is COCO 2017 object presence/absence. It complements ADE20K,
provides instance geometry and public annotations, and supports relevant removal/insertion plus
distant outcome-invariant controls. Start with 60 feasibility items. Progress to 240 plus 60 reserve
only when the locked human-validity, parse, generation, and detectability gates pass. No second-domain
result exists now.
""")
    write("docs/studies/CERTVIC_MODEL_MATRIX.md", """# CertVIC Model Matrix

Primary models remain Qwen2.5-VL-7B-Instruct, InternVL2-8B, and LLaVA-OneVision-Qwen2-7B. An optional
fourth model is not selected because the immediate value does not justify another execution family.
Planned non-VLM diagnostics are fixed-answer, text-only, image-shuffled, seeded random-change,
confidence-only heuristic, visual-difference detector, and a validity oracle where defined. They are
not observed model results. Prompt/decoding robustness is secondary and must not alter the primary
frozen prompt.
""")
    write("docs/execution/CERTVIC_FAILURE_RESUME_AND_RECOVERY.md", """# Failure, Resume, and Recovery

Workers write shard-local partial JSONL, validate exact keys, then atomically promote. A rerun skips
verified rows, quarantines a corrupt final line, reruns only missing/corrupt keys, and refuses a
conflicting completed output. OOM recovery halves the batch and clears cache; batch size 1 failure is
terminal. One completed shard is retained while the other resumes. Hash, revision, provider, run-tag,
image, task, duplicate, or variant mismatches are terminal until the input is corrected. A single T4
may run shards sequentially under the same contract. Raw archives and sheets are never overwritten.
""")
    write("docs/execution/CERTVIC_MODEL_REVISION_LOCK_GUIDE.md", """# Model Revision Lock Guide

Resolve each model and processor to a 40-character immutable commit, download the exact snapshot
outside the evidence tree, hash its files, record package/CUDA/GPU details, and fill the registry.
Re-run the execution-mode registry validator and rebuild the code ZIP. A branch, tag, cache name, or
`main` is not an immutable revision. If a snapshot disappears, create a new protocol/run version;
never relabel old outputs.
""")
    lines = ["# CertVIC Kaggle T4x2 Notebook Index", "", "All are CPU-static only and not executed.", "", "| Notebook | Stage/provider |", "| --- | --- |"]
    for name, (stage, provider) in NOTEBOOKS.items():
        lines.append(f"| `{name}` | {stage} / {provider} |")
    lines += ["", "Attach code, task/image bundle, and immutable model snapshot; use T4 x2, internet off after preflight. Every evaluation must return raw shards, merged raw, runtime/environment/validation/failure/hash manifests, and a ZIP."]
    write("docs/execution/CERTVIC_KAGGLE_T4X2_NOTEBOOK_INDEX.md", "\n".join(lines))
    write("CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", MASTER_PLAN)
    write("docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md", MASTER_PLAN)


def build_ledgers() -> None:
    evidence = [
        ("v11_main91_raw", "reports/v11_full_ceiling_audit/CERTVIC_EVIDENCE_LEDGER.json", "DERIVED_FROM_REAL_EVIDENCE", "canonical V11 baseline"),
        ("v1_specificity_raw", "data/results/main_real_200/kaggle_spurious", "REAL_OBSERVED_EVIDENCE", "frozen historical V1"),
        ("v2_30_tasks", "data/edits/spurious_v2_control/pilot_eval_tasks_reviewed.jsonl", "RETROSPECTIVE_SENSITIVITY_ONLY", "30/30 overlaps V1"),
        ("confirmatory_protocol", "configs/studies/specificity_confirmatory_cvpr.yaml", "PLANNED_NOT_EXECUTED", "prospective; no items built"),
        ("main_protocol", "configs/studies/main_study_cvpr.yaml", "PLANNED_NOT_EXECUTED", "execution blocked"),
        ("second_domain_protocol", "configs/studies/second_domain_cvpr.yaml", "PLANNED_NOT_EXECUTED", "feasibility not run"),
        ("human_templates", "docs/methodology/CERTVIC_CVPR_HUMAN_REVIEW_PROTOCOL.md", "HUMAN_REVIEW_PENDING", "zero new judgments"),
        ("notebook_suite", "notebooks/kaggle/cvpr/notebook_manifest.json", "PLANNED_NOT_EXECUTED", "CPU-static only"),
        ("paper_scaffold", "paper_cvpr/main.tex", "PLANNED_NOT_EXECUTED", "guarded placeholders"),
    ]
    rows = [{"artifact_id": a, "artifact_path": p, "evidence_class": c,
             "paper_evidence": False, "human_reviewed": False, "status": s}
            for a, p, c, s in evidence]
    write_csv("reports/cvpr_pre_execution/CERTVIC_CVPR_EVIDENCE_LEDGER.csv",
              list(rows[0]), rows)
    gates = [
        ("v11_baseline", "PASS", "V11 raw and derived pilot artifacts retained"),
        ("historical_v1_qwen", "FAIL_FROZEN", "12/94 > 0.10"),
        ("v2_30_independence", "FAIL_RETROSPECTIVE_ONLY", "30/30 overlaps V1"),
        ("confirmatory_source_pool", "BLOCKED", "source manifest and exclusions not supplied"),
        ("confirmatory_human_validity", "BLOCKED", "no completed real sheets"),
        ("model_revision_lock", "BLOCKED", "six immutable commits required"),
        ("confirmatory_execution", "BLOCKED", "tasks/review/revisions absent"),
        ("main_study_execution", "BLOCKED", "go requirements false"),
        ("second_domain_execution", "BLOCKED", "specificity and COCO feasibility pending"),
        ("paper_evidence", "BLOCKED", "paper_evidence=false"),
        ("release", "BLOCKED", "license and bibliography work pending"),
    ]
    gate_rows = [{"gate": a, "status": b, "reason": c, "paper_evidence": False}
                 for a, b, c in gates]
    write_csv("reports/cvpr_pre_execution/CERTVIC_CVPR_GATE_LEDGER.csv",
              list(gate_rows[0]), gate_rows)
    blockers = [
        ("B01", "data", "critical", "Provide and hash ADE20K/COCO sources"),
        ("B02", "scientific validity", "critical", "Verify frozen exclusions and build unseen set"),
        ("B03", "human review", "critical", "Complete two-rater blinded review"),
        ("B04", "reproducibility", "critical", "Pin model and processor commits"),
        ("B05", "missing real evidence", "critical", "Run and return three confirmatory archives"),
        ("B06", "release", "major", "Verify source/image licensing and bibliography"),
    ]
    blocker_rows = [{"blocker_id": a, "category": b, "severity": c, "next_action": d,
                     "status": "OPEN"} for a, b, c, d in blockers]
    write_csv("reports/cvpr_pre_execution/CERTVIC_CVPR_BLOCKER_REGISTER.csv",
              list(blocker_rows[0]), blocker_rows)


def build_reports() -> None:
    write("reports/cvpr_pre_execution/CERTVIC_CVPR_READINESS_AUDIT.md", """# CertVIC CVPR Readiness Audit

Verdict: `CVPR_PRE_EXECUTION_READY`. The protocol, contracts, ledgers, review schema, notebook
family, importer, paper scaffold, release architecture, and master plan exist. V11 empirical truth is
unchanged. The prospective item pool, model revision locks, human decisions, real GPU outputs,
Main-500, and second-domain evidence do not exist. `paper_evidence=false`.
""")
    write("reports/cvpr_pre_execution/CERTVIC_POWER_AND_RUNTIME_PLAN.md", """# Power and Runtime Plan

The confirmatory primary target is 240 with 60 reserve. This is deliberately larger than the
zero-failure exact-bound minimum and supports plausible nonzero rates, three-model multiplicity,
paired comparisons, exclusions, and strata. Main remains 500 plus 125 reserve for precision and
coverage. COCO begins with 60 feasibility, then 240 plus 60 reserve only after go criteria.

Planning estimates: confirmatory 14-34 T4 GPU-hours and 12-20 human-hours; conditional Main 52-108
T4 GPU-hours and 35-55 human-hours; COCO feasibility 11-24 T4 GPU-hours and 5-8 human-hours. These
are unmeasured ranges. See the master plan for per-stage estimates and recovery.
""")
    power = {
        "schema": "certvic.cvpr.specificity_power_plan.v1",
        "method": "exact_binomial_operating_characteristic",
        "threshold": 0.10,
        "design_targets": {"minimum_viable": 120, "primary": 240, "reserve": 60},
        "grid": [
            specificity_operating_characteristic(n, rate, alpha=alpha)
            for alpha in (0.05, 0.05 / 3.0)
            for n in (60, 120, 180, 240)
            for rate in (0.01, 0.03, 0.05, 0.08)
        ],
        "paper_evidence": False,
        "note": "Planning probabilities only; not observed outcomes.",
    }
    write("reports/cvpr_pre_execution/CERTVIC_POWER_PLAN.json",
          json.dumps(power, indent=2, sort_keys=True))
    write("reports/cvpr_pre_execution/CERTVIC_REVIEWER_RED_TEAM.md", """# CertVIC Reviewer Red Team

| Reviewer concern | Local repair | Future evidence | Blocks now |
| --- | --- | --- | --- |
| post-selection/V2 reuse | new outcome-unseen namespace and zero-overlap rule | independent set | yes |
| small controls | 240+60 power/attrition design | real completion | yes |
| certification overreach | terminology contract and all-gates language | signed gate report | yes |
| single domain | one COCO staged design | feasibility then confirmation | yes for generality |
| patch salience/contamination | geometry, salience, detectability, human gates | quality reports | yes |
| prompt/parser dependence | frozen prompt, strict parser provenance, bounded secondary robustness | returned runs | partly |
| model revision dependence | six immutable commits required | snapshot hashes | yes |
| multiplicity | Bonferroni primary, Holm exploratory | complete three-model family | yes |
| human-review bias | outcome blinding, two raters, adjudication, raw retention | completed sheets | yes |
| consistency-only critique | joint responsiveness/specificity estimands | Main and controls | yes |
| open-model scope | explicit scope, no universal claim | optional future family | no if scoped |
| benchmark gaming | locked strata/replacements and raw analysis | preregistered manifest | yes |

No concern is repaired by weakening a threshold or removing an unfavorable item.
""")
    validation_path = ROOT / "reports/cvpr_pre_execution/CERTVIC_FINAL_VALIDATION.md"
    if not validation_path.exists():
        write("reports/cvpr_pre_execution/CERTVIC_FINAL_VALIDATION.md", """# CertVIC Final Validation

Generated placeholder. Replace only with exact final commands, exit codes, totals, hashes, paper
pages, and expected blocker exits after the last deterministic rebuild. `paper_evidence=false`.
""")
    handoff_path = ROOT / "reports/cvpr_pre_execution/CERTVIC_CVPR_PRE_EXECUTION_HANDOFF.md"
    if not handoff_path.exists():
        write("reports/cvpr_pre_execution/CERTVIC_CVPR_PRE_EXECUTION_HANDOFF.md", """# CertVIC CVPR Pre-Execution Handoff

Verdict: `CVPR_PRE_EXECUTION_READY`. The repository has one canonical protocol/run route, real lazy
adapter implementations, deterministic T4x2 sharding, mock-runtime coverage, transactional import,
and fail-closed scientific gates. No new scientific output or human label was created. Main-500
remains `execution_allowed=false`; V2-30 is retrospective; `paper_evidence=false`.

Exact continuation point: `CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md`. First scientific action: provide
the outcome-unseen ADE20K source manifest, verify the generated V1/V2 exclusion inventory, and run
the confirmatory candidate census. Do not begin Main-500.
""")


def build_release_and_paper() -> None:
    write("release/CERTVIC_CVPR_RELEASE_MANIFEST.md", """# CertVIC CVPR Release Manifest

Pre-execution release architecture only. Include source, configs, schemas, notebook suite, builders,
analysis, synthetic fixtures, paper source, environment/lock files, license matrix, data/model cards,
and reproduction commands. Exclude private paths, credentials, datasets/pixels without redistribution
rights, raw model weights, unreviewed human data, and quarantined historical archives. Every release
file must have a SHA-256 entry and `paper_evidence=false` until post-run gates pass.
""")
    write_csv("release/CERTVIC_DATA_AND_LICENSE_MATRIX.csv",
              ["asset", "license_status", "redistribution", "release_action"], [
        {"asset": "ADE20K images/annotations", "license_status": "USER_VERIFY", "redistribution": "blocked_pending_verification", "release_action": "ship pointers/manifests only"},
        {"asset": "COCO 2017", "license_status": "USER_VERIFY", "redistribution": "follow_source_terms", "release_action": "ship pointers/manifests only"},
        {"asset": "model snapshots", "license_status": "per_model", "redistribution": "no", "release_action": "ship IDs, commits, hashes"},
        {"asset": "human sheets", "license_status": "private_review_data", "redistribution": "no_before_consent", "release_action": "aggregate only after approval"},
        {"asset": "CertVIC source", "license_status": "REQUIRED_USER_FILL", "redistribution": "blocked_until_license_added", "release_action": "add project license"},
    ])
    write("release/CERTVIC_REPRODUCIBILITY_CHECKLIST.md", """# CertVIC Reproducibility Checklist

- [ ] source licenses verified; no redistributed private pixels
- [ ] study configs and task manifests hash-locked
- [ ] model and processor commits immutable and complete
- [ ] code bundle and notebook hashes recorded
- [ ] raw shards/ZIPs preserved; canonical import idempotent
- [ ] human sheets complete, blinded, hashed, and adjudicated
- [ ] all endpoints/multiplicity/missingness rules frozen
- [ ] full tests, lint, compile, notebook static/mock tests pass
- [ ] claim, privacy, anonymity, bibliography, package, and release scans pass
- [ ] paper placeholders populated only from validated evidence
""")
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
\input{sections/related_work}
\input{sections/method}
\input{sections/experiments}
\input{sections/results_guarded}
\input{sections/human_validation}
\input{sections/cross_domain}
\input{sections/limitations}
\input{sections/conclusion}
% Bibliography activation is blocked until the citation TODO matrix is source-verified.
% \bibliographystyle{plain}
% \bibliography{references}
\end{document}
""")
    sections = {
        "abstract": "\\begin{abstract}Result-free scaffold. The validated pilot motivates a prospective protocol; no new confirmatory, human, Main, or cross-domain result is claimed.\\end{abstract}",
        "introduction": "\\section{Introduction}Semantic response and irrelevant-edit stability are distinct. Contributions remain conditional on the evidence gates.",
        "related_work": "\\section{Related Work}Citation slots are tracked in the comparison matrix; entries require researcher verification before submission.",
        "method": "\\section{Protocol and Statistical Decision}We define paired responsiveness and specificity endpoints, strict parsing, provenance, exact one-sided bounds, and multiplicity.",
        "experiments": "\\section{Experimental Setup}Three open model families, an outcome-unseen control set, Main-500, and a staged COCO study are planned but not executed here.",
        "results_guarded": "\\section{Results}\\textbf{BLOCKED: validated returned outputs and completed human review are required.} Outcome branches are injected only by the post-run gate.",
        "human_validation": "\\section{Human Validation}\\textbf{BLOCKED: two independent blinded ratings and adjudication are pending.}",
        "cross_domain": "\\section{Cross-Domain Study}\\textbf{BLOCKED: COCO feasibility has not run.}",
        "limitations": "\\section{Limitations and Broader Impact}Current evidence is a small open-model pilot with machine-assisted validity screening and unpinned historical revisions.",
        "conclusion": "\\section{Conclusion}This scaffold states the prospective question without selecting an outcome branch.",
    }
    for name, text in sections.items():
        write(f"paper_cvpr/sections/{name}.tex", text)
    write("paper_cvpr/references.bib", "% Intentionally empty: citations require source verification.\n")
    write("paper_cvpr/RELATED_WORK_CITATION_TODO.csv", "topic,comparison_needed,verification_status\nVLM robustness,metric and threat model,REQUIRED_RESEARCHER_VERIFICATION\ncounterfactual VQA,edit and answer validity,REQUIRED_RESEARCHER_VERIFICATION\nvisual consistency,response versus specificity,REQUIRED_RESEARCHER_VERIFICATION\nimage edit evaluation,quality and detectability,REQUIRED_RESEARCHER_VERIFICATION\ncertified robustness,terminology and guarantees,REQUIRED_RESEARCHER_VERIFICATION\nsequential testing,optional stopping and CS,REQUIRED_RESEARCHER_VERIFICATION\nbenchmark validity,human review and post-selection,REQUIRED_RESEARCHER_VERIFICATION")
    write("paper_cvpr/OUTCOME_BRANCHES.json", json.dumps({
        "status": "BLOCKED_NO_VALIDATED_CONFIRMATORY_RESULTS",
        "active_branch": None,
        "branches": ["qwen_fails_again", "qwen_passes", "multiple_models_fail", "all_models_pass"],
        "paper_evidence": False,
    }, indent=2))


def build_manifests() -> None:
    paths = [
        "certvic/eval/parse.py",
        "certvic/cvpr/contracts.py",
        "certvic/cvpr/transactional.py",
        "certvic/cvpr/statistics.py",
        "certvic/cvpr/candidate_mining.py",
        "certvic/cvpr/human_review.py",
        "certvic/cvpr/adapters.py",
        "certvic/cvpr/worker.py",
        "certvic/cvpr/package_run.py",
        "certvic/cvpr/after_runs.py",
        "certvic/cvpr/notebook_builder.py",
        "scripts/build_cvpr_pre_execution.py",
        "tests/test_cvpr_pre_execution.py",
        "docs/CERTVIC_CANONICAL_PROJECT_INDEX.md",
        "configs/models/certvic_cvpr_model_registry.yaml",
        "configs/studies/specificity_confirmatory_cvpr.yaml",
        "configs/studies/main_study_cvpr.yaml",
        "configs/studies/second_domain_cvpr.yaml",
        "CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md",
        "docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md",
        "reports/cvpr_pre_execution/CERTVIC_CVPR_PRE_EXECUTION_HANDOFF.md",
        "paper_cvpr/main.tex",
        "release/CERTVIC_CVPR_RELEASE_MANIFEST.md",
    ]
    paths.extend(f"notebooks/kaggle/cvpr/{name}" for name in sorted(NOTEBOOKS))
    paths.extend(
        str(path.relative_to(ROOT))
        for path in sorted((ROOT / "paper_cvpr").rglob("*"))
        if path.is_file() and path.suffix in {".tex", ".bib", ".csv", ".json"}
    )
    rows = [{"artifact_path": path, "change_type": "created_or_regenerated",
             "root_cause": "CVPR canonical pre-execution surface absent",
             "action": "built deterministic evidence-bounded artifact",
             "validation": "CVPR contract tests and final validation",
             "evidence_created": False} for path in paths]
    rows.insert(0, {"artifact_path": "promptpacks/CERTVIC_CVPR_PRE_EXECUTION_MAX_BUILD_PROMPT.md",
                    "change_type": "privacy_repair",
                    "root_cause": "prompt pack embedded a private host path",
                    "action": "replaced literal checkout path with <PROJECT_ROOT>",
                    "validation": "release privacy audit", "evidence_created": False})
    write_csv("reports/cvpr_pre_execution/CERTVIC_CHANGE_MANIFEST.csv", list(rows[0]), rows)
    command_rows = [
        {"stage": "baseline", "command": "python3 -m pytest -q", "exit_code": 1,
         "result": "741 passed, 6 failed; prompt pack private path"},
        {"stage": "baseline", "command": "python3 -m ruff check --no-cache certvic scripts tests",
         "exit_code": 0, "result": "all checks passed before changes"},
        {"stage": "baseline", "command": "python3 scripts/validate_t4x2_notebooks.py --out <TEMP>",
         "exit_code": 0, "result": "6/6 historical notebooks static-valid"},
    ]
    command_path = ROOT / "reports/cvpr_pre_execution/CERTVIC_COMMAND_LEDGER.csv"
    if not command_path.exists():
        write_csv("reports/cvpr_pre_execution/CERTVIC_COMMAND_LEDGER.csv",
                  list(command_rows[0]), command_rows)


def main() -> None:
    runtime_owner = ROOT / "reports/cvpr_runtime_hardening/BUILDER_OWNERSHIP.json"
    if runtime_owner.is_file():
        ownership = json.loads(runtime_owner.read_text(encoding="utf-8"))
        if ownership.get("runtime_hardening_owns_shared_surfaces") is not True:
            raise ValueError("runtime ownership marker is malformed")
        print(json.dumps({
            "status": "PRESERVED_RUNTIME_HARDENED_SURFACES",
            "paper_evidence": False,
            "ownership_marker": str(runtime_owner.relative_to(ROOT)),
        }, sort_keys=True))
        return
    build_exclusion_inventory()
    build_suite(ROOT / "notebooks/kaggle/cvpr")
    build_docs()
    build_ledgers()
    build_reports()
    build_release_and_paper()
    build_manifests()
    print(json.dumps({"status": "BUILT_PRE_EXECUTION_ONLY", "paper_evidence": False,
                      "notebooks": len(NOTEBOOKS)}, sort_keys=True))


if __name__ == "__main__":
    main()
