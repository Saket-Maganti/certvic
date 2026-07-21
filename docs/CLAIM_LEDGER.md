# Claim Ledger

Allowed claim templates:

- “On the configured item set, model X had an intervention-consistency rate of
  `[RESULT REQUIRED]`.”
- “Under the configured item order and anytime-valid confidence sequence, the
  lower bound exceeded the configured threshold `[RESULT REQUIRED]`.”

Forbidden claim types:

- broad causal-understanding claims
- deployment safety claims
- all-model claims
- frontier-model failure claims without reference-only evidence
- certification claims without confidence-sequence lower bounds

Smoke outputs are not evidence and must remain marked `MOCK_ONLY`.
Simulation outputs are not evidence and must remain marked `SIMULATED_ONLY`.
They may be used only for pipeline stress testing, never for paper claims.

## Certification policy gate (V2)

A certified gap claim is eligible only when `evaluate_certification_policy`
passes against `configs/certification_policy.yaml` AND an anytime-valid CS lower
bound exceeds the gap threshold. Bootstrap CIs and descriptive summaries are
never certification. Mock and baseline providers are disallowed for certified
claims.

The claim gate blocks non-evidence statuses including `CANDIDATE_ONLY`,
`PLANNED_ONLY`, `PREVIEW_ONLY`, `GENERATED_EDIT_ONLY`,
`EDIT_READY_NON_EVIDENCE`, `MOCK_ONLY`, and `SIMULATED_ONLY`.

## Failure gallery (V2)

Failure examples are QUALITATIVE_NON_EVIDENCE. Captions are constrained to
single-factor descriptive observations and never assert deployment safety or
causal-understanding failure.

## Run-ledger provenance trace (V3)

Every certified claim must be traceable to the run that produced its evidence.
`certvic.provenance.trace_claim` matches each claim's `evidence_files` against
the run ledger's recorded output hashes and the producing run's evidence status:

- `trace_complete` — evidence artifacts match an evidence-eligible producing run.
- `missing_artifact` / `hash_mismatch` — artifact absent or mutated since the run.
- `ineligible_evidence` — produced only by a mock/simulated/planned/unknown run.
- `unknown` — no recorded run produced the artifact.

A certified claim that is not `trace_complete` is an integrity violation; the
tracer exits non-zero. See `docs/RUN_LEDGER.md`.

## Edit detectability probe (V3)

The edit detectability probe (`certvic.validation.edit_detectability`) is a
construct-validity diagnostic, not evidence. Its outputs carry
`evidence_status = CONSTRUCT_VALIDITY_DIAGNOSTIC_NON_EVIDENCE` and must never be
used as certification or to support a gap claim on their own. High separability
AUC is a warning to strengthen edits/ablations, not a result. See
`docs/EDIT_DETECTABILITY_PROBE.md`.

## Paper result injection gate (V3)

`certvic.paper.inject_results` only writes numbers into the paper from manifest
entries that are eligible (non-mock/non-simulated) and hash-stamped; everything
else preserves the `[RESULT REQUIRED]` placeholder. It is dry-run by default,
requires `--allow-write`, and runs `paper_numbers_guard` after any write.
`certvic.paper.paper_trace_report` proves every injected `\input` traces to an
eligible artifact. See `docs/PAPER_RESULT_TRACEABILITY.md`.
