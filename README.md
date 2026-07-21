# CertVIC

Certified Visual Consistency / CertVIC is a zero-cost research-code scaffold for
the project “Certifying When Vision-Language Models See the Change: Anytime-Valid
Consistency Under Controlled Real-Image Interventions.”

## Thesis

CertVIC evaluates whether a vision-language model updates a decision when a
controlled single-factor visual intervention changes the expected answer. The
method is recipe-first: source pointers, hashes, masks, edit parameters, task
manifests, predictions, and claim gates are tracked so results can be audited
without overclaiming.

## Current Verified State (V11)

The repository contains real 91-item intervention-pilot predictions and real
94-item V1 spurious-control predictions for three open VLMs. Their numerical
results are reproducible locally, but the item-validity labels are
`MACHINE_ASSISTED_PRELIMINARY`, the full certification policy requires at least
150 overall items and 40 per family, and no independent confirmatory specificity
set has been executed. The existing 30-item stricter-control set reuses V1 items
selected after V1 outcomes existed; it is therefore `DIAGNOSTIC_ONLY`, not a
confirmatory Spurious V2 result. Main-500 remains blocked.

The canonical state, evidence ledger, blocker register, exact next actions, and
validation record are in
`reports/v11_full_ceiling_audit/CERTVIC_V11_MASTER_HANDOFF.md`.

## Zero-Cost Rule

The core project uses only local CPU/Mac, free Kaggle GPU, free Colab fallback,
open-source models, and public/free datasets. Paid APIs, paid cloud, paid
datasets, paid annotation, paid storage, and paid experiment tracking are not
part of the core workflow.

Optional free-tier reference checks must be disabled by default, version-dated,
and marked non-core/reference-only.

## Pre-run operator quickstart

```bash
python3 -m certvic.cvpr.doctor --json
python3 -m certvic.cvpr.next_action
python3 -m certvic.cvpr.run_graph status
python3 -m certvic.cvpr.runtime_planner --provider qwen2_5_vl_7b --items 240
```

The canonical 28-step order, exact inputs/outputs, retry rules, and gates are in
`CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md`; the user-facing external route begins at
`execution_pack/00_READ_ME_FIRST.md`. Pre-smoke and scientific authorizations are separate. The
artifact registry, reproducibility capsule, notebook runner, license registry, chaos suite, guarded
paper compiler, and deterministic release builder all fail closed and keep pre-run outputs at
`paper_evidence=false`.

The required repaired full-project replacement ZIP was not available during the maximum-ceiling
migration. Accordingly, repository replacement remains an explicit blocker even though the active
runtime baseline and local upgrade paths validate. No patch-only or historical release ZIP was used
as a substitute.

## Original scaffold quickstart

```bash
python -m pytest -q
python -m certvic.data.build_tasks --smoke --out data/manifests/smoke_tasks.jsonl
python -m certvic.data.manifest_checks --tasks data/manifests/smoke_tasks.jsonl --strict
python -m certvic.eval.run_eval --config configs/smoke.yaml --tasks data/manifests/smoke_tasks.jsonl --out data/predictions/smoke_mock_inconsistent.jsonl --provider mock_inconsistent --run-id smoke_mock_inconsistent_v1 --max-items 10
python -m certvic.metrics.score_predictions --tasks data/manifests/smoke_tasks.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --out-scores data/results/smoke_pair_scores.jsonl --out-summary data/results/smoke_summary.json
python -m certvic.reporting.build_report --tasks data/manifests/smoke_tasks.jsonl --scores data/results/smoke_pair_scores.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --out-dir data/results/smoke_report --alpha 0.05 --gap-threshold 0.05
python -m certvic.audit --config configs/smoke.yaml --tasks data/manifests/smoke_tasks.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --scores data/results/smoke_pair_scores.jsonl --paper paper/main.tex --strict
```

## Implemented

- Pydantic schemas for sources, masks, edits, task items, predictions, scores,
  manifests, and claims.
- Leakage guards for prompts and filenames.
- Local synthetic smoke fixtures marked `MOCK_ONLY`.
- Deterministic mock providers and import-safe open-VLM adapter skeletons.
- Resume/sharded evaluation runner with JSONL flushing.
- Scoring, summaries, bootstrap intervals, optional `confseq` wrappers, claim
  certification gates, and report generation.
- Source/license manifest tooling, human-validation sheet tooling, baseline
  stubs, paper scaffold, Kaggle markdown guides, and audit gates.

## Required Next Evidence

- Complete independent, blinded two-rater validity review before outcome
  unblinding.
- Construct and lock a new outcome-unseen spurious-control set.
- Pin exact model revisions, run the independent control, and import it through
  the fail-closed transactional gate.
- Recompute the prospective specificity decision; only then reconsider the
  Main-500 go/no-go gate.

## Claim Safety

Smoke outputs are implementation checks, not evidence. CertVIC makes no
universal claims about model behavior, causal reasoning, or deployment safety.
Claims must be tied to artifacts, metrics, confidence
sequences when available, and explicit limitations.
