# Paper Result Injection and Traceability (V3)

A claim-gated paper update system. It injects **only** eligible (non-mock /
non-simulated), hash-stamped result artifacts into the paper, refuses everything
else, preserves `[RESULT REQUIRED]` placeholders when ineligible, and never
overwrites the paper without an explicit flag. Every injected number traces back
to its artifact.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.paper.result_manifest` | Scan a report dir; hash each artifact; record evidence status; mark eligibility. |
| `certvic.paper.inject_results` | Replace placeholders with `\input`/`\includegraphics` of eligible artifacts (dry-run by default). |
| `certvic.paper.paper_trace_report` | Trace each injected `\input` back to its manifest entry; list remaining placeholders. |

## Rules (hard)

- **Refuse non-evidence artifacts** — an artifact is injected only if its manifest
  entry is eligible (status not in the non-evidence set, provider not mock/baseline).
- **Require hashes** — entries without a `sha256` are refused.
- **Preserve placeholders** — ineligible/unhashed/missing references leave
  `[RESULT REQUIRED]` intact.
- **No overwrite by default** — `inject_results` is dry-run unless `--allow-write`.
- **Guard after write** — `certvic.validation.paper_numbers_guard` runs on every
  written file; injected `\input` targets must trace to eligible manifest entries.

## Commands

```bash
python3 -m certvic.paper.result_manifest \
  --report-dir data/results/v2_report --claim-ledger data/results/claim_ledger.json \
  --out paper/result_manifest.json

python3 -m certvic.paper.inject_results \
  --manifest paper/result_manifest.json --paper-dir paper --dry-run
# add --allow-write only when the manifest is eligible

python3 -m certvic.paper.paper_trace_report \
  --paper-dir paper --manifest paper/result_manifest.json \
  --out docs/PAPER_TRACE_REPORT.md
```

Until an eligible open-local run exists, the manifest is non-evidence, injection
writes nothing, and the paper keeps its `[RESULT REQUIRED]` placeholders — exactly
the safe default.
