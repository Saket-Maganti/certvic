# Paper Plan

Target venue: CVPR 2027.

Paper posture: method-first, recipe-first, and claim-gated.

Required result tables:

- main consistency/gap table
- by-family table
- by-domain table
- control-edit spurious flip table
- baseline/ablation table

Required figures:

- pipeline diagram
- example valid interventions
- failure gallery summary
- confidence-sequence plot after real runs

Kill gates:

- edit validity below acceptable level
- prompt leakage detected
- no reproducible open-model run
- no certifiable or honestly reportable result

All result cells remain `[RESULT REQUIRED]` until real artifacts exist.

## V2 reporting

`certvic.reporting.build_v2_report` auto-produces the required tables and figures
from real run outputs. All result cells remain `--` / `[RESULT REQUIRED]` until an
eligible open-model run exists; certified claims require an anytime-valid CS lower
bound above threshold plus a clean evidence context.

## Claim-gated result injection (V3)

Results are injected into the paper only from eligible, hash-stamped artifacts;
nothing is hand-entered. The flow:

```bash
python3 -m certvic.paper.result_manifest --report-dir data/results/v2_report --claim-ledger data/results/claim_ledger.json --out paper/result_manifest.json
python3 -m certvic.paper.inject_results --manifest paper/result_manifest.json --paper-dir paper --dry-run   # --allow-write when eligible
python3 -m certvic.paper.paper_trace_report --paper-dir paper --manifest paper/result_manifest.json --out docs/PAPER_TRACE_REPORT.md
```

Injection is dry-run by default, refuses non-evidence/unhashed artifacts, preserves
`[RESULT REQUIRED]` until eligible, and runs the number guard after any write. See
`docs/PAPER_RESULT_TRACEABILITY.md`.

## Related work scaffold (V3)

The related-work section is organized around 8 categories in
`paper/related_work_matrix.yaml` with CertVIC's positioning in each. Citations are
NOT fabricated — `representative_works` are filled by a human after verification
(`docs/CITATION_TODO.md`). Audit coverage + citation integrity + novelty claims:

```bash
python3 -m certvic.paper.related_work_audit --matrix paper/related_work_matrix.yaml --paper paper/sections/02_related.tex --out docs/RELATED_WORK_AUDIT.md
```

See `docs/RELATED_WORK_PLAN.md`.
