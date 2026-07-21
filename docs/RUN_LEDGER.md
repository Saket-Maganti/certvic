# Run Ledger and Provenance (V3)

The run ledger is the single source of truth that ties every CertVIC artifact —
masks, edits, predictions, scores, reports, paper numbers — back to the command,
config, inputs, outputs, hashes, and evidence status that produced it. It exists
so that any number in the paper can be traced to a real, hash-verified,
evidence-eligible run, or else flagged as untraceable.

It is metadata only. It never downloads data, runs GPU jobs, calls paid
services, or makes evidence claims.

## Components

| Module | Purpose |
| --- | --- |
| `certvic.provenance.run_ledger` | Append-only JSONL ledger of run entries; hashing of inputs/outputs/config. |
| `certvic.provenance.artifact_graph` | Bipartite `input -> run -> output` graph; detects missing artifacts and hash drift. |
| `certvic.provenance.trace_claim` | Traces each claim-ledger entry back to producing runs; flags integrity violations. |

## Ledger entry schema (`LedgerEntry`)

| Field | Meaning |
| --- | --- |
| `run_id` | Stable identifier for the run. |
| `stage` | Pipeline stage (see `KNOWN_STAGES`; free-form allowed with a warning). |
| `timestamp_utc` | ISO-8601 UTC timestamp. |
| `command` | The command that produced the artifacts. |
| `config_hash` | sha256 of the config file (or `null`). |
| `input_hashes` / `output_hashes` | `{path: sha256 or null}` maps. Missing/remote pointers hash to `null` (never fetched). |
| `evidence_status` | e.g. `REAL_EVIDENCE`, `MOCK_ONLY`, `SIMULATED_ONLY`, `PLANNED_ONLY`. |
| `zero_cost` / `paid_services_used` | Cost discipline flags (`paid_services_used` forces `zero_cost=false`). |
| `environment` | Light, import-safe environment summary (python/platform + dep availability). |
| `user_notes` | Free-form operator notes. |

Directories are hashed as the stable hash of their `{relative_path: file_hash}`
map, so any content change is detected deterministically.

## Commands

```bash
# Create an empty ledger.
python3 -m certvic.provenance.run_ledger init --out data/provenance/run_ledger.jsonl

# Record a stage (hashes all listed inputs/outputs/config on disk).
python3 -m certvic.provenance.run_ledger add \
  --ledger data/provenance/run_ledger.jsonl \
  --stage edit_generation --run-id pilot_edits_v1 \
  --inputs data/manifests/pilot_edit_plan.jsonl \
  --outputs data/manifests/pilot_generated_edits.jsonl \
  --config configs/real_pilot_ade20k.yaml \
  --command "python3 -m certvic.edit.build_edits ..." \
  --evidence-status REAL_EVIDENCE --notes "tiny real pilot edits"

# Build the artifact dependency graph (JSON + markdown + DOT).
python3 -m certvic.provenance.artifact_graph \
  --ledger data/provenance/run_ledger.jsonl \
  --out-dir data/provenance/artifact_graph

# Trace each claim back to its producing runs.
python3 -m certvic.provenance.trace_claim \
  --claim-ledger data/results/claim_ledger.json \
  --run-ledger data/provenance/run_ledger.jsonl \
  --out data/provenance/claim_trace_report.md
```

## Trace statuses

| Status | Meaning |
| --- | --- |
| `trace_complete` | Every evidence artifact matches an evidence-eligible producing run. |
| `missing_artifact` | An evidence artifact is not present on disk. |
| `hash_mismatch` | The on-disk artifact hash matches no recorded output hash. |
| `ineligible_evidence` | The producing run is non-evidence (mock/simulated/planned/unknown). |
| `unknown` | No recorded run produced the artifact. |

A **certified** claim that is not `trace_complete` is an `integrity_violation`
and the tracer exits non-zero. Certified numbers must always be fully traceable.

## Evidence eligibility

Evidence-eligible statuses: `REAL_EVIDENCE`, `EVIDENCE_ELIGIBLE`, `REAL_PILOT`,
`REAL_MAIN`. Everything else is non-evidence by construction and is kept in sync
with `certvic.validation.claims.NON_EVIDENCE_STATUSES`.
